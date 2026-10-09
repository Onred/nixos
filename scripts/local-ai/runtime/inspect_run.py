"""Compact process status with error context, small-output passthrough and tails."""

import asyncio
from mcp.types import ToolAnnotations
from tool_config import mcp, bounded
import artifact_store as store
from diagnostic_context import diagnostic_lines, failure_context, excerpt
from candidate_selection import choose
from filter_log import group_log


def inspect(ident):
    record = store.manifest(ident)
    result = {"process": store.process_facts(record)}
    texts = {
        stream: store.stream_text(ident, stream) for stream in sorted(store.STREAMS)
    }
    if sum(len(value[0].encode()) for value in texts.values()) <= 1600 and not any(
        x[1] for x in texts.values()
    ):
        result["output"] = {stream: text for stream, (text, _) in texts.items() if text}
        return result
    diagnostics = {}
    for stream, (text, partial) in texts.items():
        if not text:
            continue
        report = diagnostic_lines(text, 4)
        contexts = failure_context(text)
        if contexts:
            report["context"] = contexts
            report.pop("excerpts", None)
        if record.get("exit_code") != 0 and not contexts:
            lines = text.splitlines()
            report["tail"] = [
                {"line": i + 1, **excerpt(lines[i], 600)}
                for i in range(max(0, len(lines) - 4), len(lines))
            ]
        report["scan_truncated"] = partial
        diagnostics[stream] = report
    result["diagnostics"] = diagnostics
    return result


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False, openWorldHint=False
    )
)
async def inspect_run(run_id: str, question: str = "") -> dict:
    """Inspect saved process status and failure context. Small output is returned directly. Optional question selects additional excerpts; use read_artifact for omitted data."""

    async def work():
        result = await asyncio.to_thread(inspect, run_id)
        if question and "output" not in result:
            entries = []
            for stream in sorted(store.STREAMS):
                text, _ = store.stream_text(run_id, stream)
                groups, _ = group_log(text)
                entries.extend({"stream": stream, **entry} for entry in groups)
            result["evidence"] = await choose(entries, question)
        return result

    return await bounded(work())
