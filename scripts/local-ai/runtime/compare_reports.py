"""Compare process outcomes and exact diagnostic counts."""

import collections
import xml.etree.ElementTree as ET
from artifact_store import manifest, process_facts, stream_text, STREAMS
from diagnostic_context import DIAGNOSTIC, TIMESTAMP, ANSI
from validation_report import validation
from tool_config import mcp, bounded
import asyncio
from mcp.types import ToolAnnotations


def compare(before, after):
    left, right = manifest(before), manifest(after)
    result = {
        "before": process_facts(left),
        "after": process_facts(right),
        "same_command": left.get("argv") == right.get("argv")
        and left.get("cwd") == right.get("cwd"),
        "duration_delta_seconds": None,
        "streams": {},
    }
    if (
        left.get("duration_seconds") is not None
        and right.get("duration_seconds") is not None
    ):
        result["duration_delta_seconds"] = round(
            right["duration_seconds"] - left["duration_seconds"], 3
        )
    for stream in sorted(STREAMS):
        a, ap = stream_text(before, stream)
        b, bp = stream_text(after, stream)
        ac = collections.Counter(
            TIMESTAMP.sub("", ANSI.sub("", line))
            for line in a.splitlines()
            if DIAGNOSTIC.search(line)
        )
        bc = collections.Counter(
            TIMESTAMP.sub("", ANSI.sub("", line))
            for line in b.splitlines()
            if DIAGNOSTIC.search(line)
        )
        added, removed = bc - ac, ac - bc
        result["streams"][stream] = {
            "added": [
                {"text": line[:800], "count": n} for line, n in added.most_common(8)
            ],
            "removed": [
                {"text": line[:800], "count": n} for line, n in removed.most_common(8)
            ],
            "added_groups": len(added),
            "removed_groups": len(removed),
            "scan_truncated": ap or bp,
        }
    result["validation"] = {}
    for label, ident in (("before", before), ("after", after)):
        try:
            report = validation(ident)
            result["validation"][label] = {
                k: report.get(k)
                for k in (
                    "format",
                    "counts",
                    "issue_count",
                    "outcome",
                    "outcome_provisional",
                )
            }
        except (ValueError, OSError, ET.ParseError) as error:
            result["validation"][label] = {"error": str(error)[:300]}
    result["comparison"] = "Exact diagnostic counts; timestamp prefixes normalized."
    return result


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False, openWorldHint=False
    )
)
async def compare_reports(before_id: str, after_id: str) -> dict:
    """Compare saved status, duration, validation counts and diagnostic occurrences. Normalizes leading ISO timestamps; no semantic regression claim or inference."""
    return await bounded(asyncio.to_thread(compare, before_id, after_id))
