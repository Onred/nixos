"""Group repeated captured log lines while preserving late diagnostics."""

import collections
import asyncio
from mcp.types import ToolAnnotations
from tool_config import mcp, bounded
import artifact_store as store
from diagnostic_context import ANSI, TIMESTAMP, severity, excerpt
from candidate_selection import choose


def group_log(text, contains="", limit=5000):
    groups = collections.OrderedDict()
    dropped = matched = evicted = 0
    for number, line in enumerate(text.splitlines(), 1):
        if contains and contains.casefold() not in line.casefold():
            continue
        matched += 1
        clean = ANSI.sub("", line)
        key = TIMESTAMP.sub("", clean)
        if key not in groups:
            level = severity(clean)
            if len(groups) >= limit:
                # Late errors displace ordinary groups; full capture remains unchanged.
                victim = next(
                    (k for k, v in groups.items() if v["severity"] < level), None
                )
                if victim is None and level == 2:
                    victim = next(iter(groups))
                if victim is None:
                    dropped += 1
                    continue
                dropped += groups[victim]["count"]
                evicted += 1
                del groups[victim]
            groups[key] = {
                "first_line": number,
                "last_line": number,
                "count": 0,
                "severity": level,
                **excerpt(line),
            }
            if clean != key:
                groups[key]["timestamp_grouped"] = True
        groups[key]["count"] += 1
        groups[key]["last_line"] = number
    return list(groups.values()), {
        "scanned_lines": len(text.splitlines()),
        "matched_lines": matched,
        "groups": len(groups),
        "ungrouped_lines": dropped,
        "evicted_groups": evicted,
    }


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False, openWorldHint=False
    )
)
async def filter_log(
    run_id: str, stream: str = "stderr", contains: str = "", question: str = ""
) -> dict:
    """Group saved logs; optional literal filter/question. Preserves late errors, counts, original line references. Timestamp variants share a group; omissions are explicit."""

    async def work():
        if stream not in store.STREAMS or len(contains) > 500:
            raise ValueError("Use stdout/stderr and a filter of at most 500 characters")
        text, partial = await asyncio.to_thread(store.stream_text, run_id, stream)
        groups, coverage = group_log(text, contains)
        ordered = sorted(
            groups,
            key=lambda x: (x["severity"], x["count"], x["last_line"]),
            reverse=True,
        )
        evidence = await choose(ordered, question)
        # Retain up to two highest-priority error groups even if Gemma overlooks them.
        mandatory = [x for x in ordered if x["severity"] == 2][:2]
        evidence["items"] = mandatory + [
            x for x in evidence["items"] if x not in mandatory
        ]
        evidence["items"] = evidence["items"][:6]
        evidence["omitted"] = len(groups) - len(evidence["items"])
        return {
            "id": run_id,
            "stream": stream,
            "coverage": {**coverage, "scan_truncated": partial},
            "evidence": evidence,
        }

    return await bounded(work())
