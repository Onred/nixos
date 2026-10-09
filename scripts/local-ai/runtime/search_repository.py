"""Bounded project search with exact source coordinates and saved full matches."""

import asyncio
import json
import os
from mcp.types import ToolAnnotations
import artifact_store as store
import tool_config
from tool_config import mcp, bounded
from candidate_selection import choose, ranked_candidates
from diagnostic_context import excerpt, severity


def repository_scan(root, pattern, roots, regex=False):
    root = store.allowed_path(root, roots, directory=True)
    if not pattern or len(pattern.encode()) > 1000:
        raise ValueError("Supply a pattern of at most 1000 UTF-8 bytes")
    argv = ["rg", "--no-config", "--json", "--line-number", "--color", "never"]
    if not regex:
        argv.append("--fixed-strings")
    for name in sorted(store.BLOCKED):
        argv += ["--glob", f"!**/{name}/**"]
    argv += [
        "--glob",
        "!**/.env*",
        "--glob",
        "!**/*.pem",
        "--glob",
        "!**/*.key",
        "--",
        pattern,
        str(root),
    ]
    run = store.capture(
        argv, root, timeout=30, max_bytes=store.SCAN_BYTES, kind="repository-search"
    )
    text, partial = store.stream_text(run["id"], "stdout")
    entries = []
    malformed = matched = 0
    with (store.artifact_dir(run["id"]) / "matches").open(
        "x", encoding="utf-8"
    ) as saved:
        os.chmod(saved.name, 0o600)
        for line in text.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                malformed += 1
                continue
            if event.get("type") != "match":
                continue
            matched += 1
            data = event["data"]
            path = data.get("path", {}).get("text")
            content = data.get("lines", {}).get("text")
            if path is None or content is None:
                malformed += 1
                continue
            try:
                source = store.allowed_path(path, roots)
            except (ValueError, OSError):
                continue
            content = content.rstrip("\n")
            full = {"source": str(source), "line": data["line_number"], "text": content}
            # Store full lines, including text beyond excerpt clipping.
            saved.write(json.dumps(full, ensure_ascii=False) + "\n")
            short = excerpt(content)
            if short.get("clipped") and not regex:
                pos = content.casefold().find(pattern.casefold())
                if pos >= 900:
                    begin = max(0, pos - 150)
                    short = {
                        "text": content[begin : begin + 900],
                        "column": begin + 1,
                        "clipped": True,
                    }
            entries.append(
                {"source": str(source), "line": data["line_number"], **short}
            )
    return (
        run,
        entries,
        {
            "matching_lines": matched,
            "readable_matches": len(entries),
            "malformed_or_binary_records": malformed,
            "scan_truncated": partial or not run["capture_complete"],
        },
    )


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False, openWorldHint=False
    )
)
async def search_repository(
    root: str, pattern: str, question: str = "", regex: bool = False
) -> dict:
    """Search an allowed project using literal rg (optional regex). Small match sets return directly; questions select diverse evidence. Full matches are saved for read_artifact."""

    async def work():
        run, entries, coverage = await asyncio.to_thread(
            repository_scan, root, pattern, tool_config.ROOTS, regex
        )
        ok = run["exit_code"] in (0, 1) and run["capture_complete"]
        # Return relative paths once rooted, cutting repetitive path prefixes.
        for entry in entries:
            entry["source"] = os.path.relpath(entry["source"], root)
        evidence = await choose(entries, question)
        # Model selection cannot discard the strongest observed diagnostic matches.
        mandatory = [
            {k: v for k, v in item.items() if k != "id"}
            for item in ranked_candidates(entries, question)
            if severity(item["text"]) == 2
        ][:2]
        evidence["items"] = (
            mandatory + [item for item in evidence["items"] if item not in mandatory]
        )[:6]
        evidence["omitted"] = len(entries) - len(evidence["items"])
        if mandatory:
            evidence["retained_diagnostics"] = len(mandatory)
        result = {
            "status": "ok" if ok else "incomplete",
            "id": run["id"],
            "root": str(root),
            "coverage": coverage,
            "evidence": evidence,
        }
        if not ok:
            result["process"] = store.process_facts(run)
            result["error"] = store.stream_text(run["id"], "stderr")[0][:1000]
        return result

    return await bounded(work())
