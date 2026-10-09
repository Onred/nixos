"""Deterministic validation counts and bounded failure evidence."""

import json
import re
import xml.etree.ElementTree as ET
from artifact_store import manifest, process_facts, stream_text, STREAMS
from diagnostic_context import failure_context, ANSI
from tool_config import mcp
import asyncio
from mcp.types import ToolAnnotations


def validation(ident, format="auto"):
    record = manifest(ident)
    result = {
        "process": process_facts(record),
        "format": None,
        "counts": None,
        "failures": [],
        "outcome": "unknown",
    }
    counts = None
    details = []
    partial = False
    console_failed = False
    if "report" in record:
        text, partial = stream_text(ident, "validation")
        result["report"] = {k: record["report"][k] for k in ("source", "freshness")}
        fmt = (
            ("junit" if text.lstrip().startswith("<") else "json")
            if format == "auto"
            else format
        )
        if fmt == "junit":
            if re.search(r"<!\s*(DOCTYPE|ENTITY)", text, re.I):
                raise ValueError("XML DTD/entity declarations are not supported")
            root = ET.fromstring(text)
            if root.tag.rsplit("}", 1)[-1] not in {"testsuite", "testsuites"}:
                raise ValueError("Expected a JUnit testsuite or testsuites root")
            cases = [x for x in root.iter() if x.tag.rsplit("}", 1)[-1] == "testcase"]
            counts = {
                "passed": 0,
                "failed": 0,
                "errors": 0,
                "skipped": 0,
                "total": len(cases),
            }
            for case in cases:
                children = {x.tag.rsplit("}", 1)[-1]: x for x in case}
                status = next(
                    (key for key in ("error", "failure", "skipped") if key in children),
                    None,
                )
                counts[
                    {
                        "error": "errors",
                        "failure": "failed",
                        "skipped": "skipped",
                        None: "passed",
                    }[status]
                ] += 1
                if status in {"error", "failure"}:
                    child = children[status]
                    details.append(
                        {
                            "name": (
                                case.get("classname", "") + ":" + case.get("name", "")
                            )[:500],
                            "message": (
                                child.get("message", "") + "\n" + (child.text or "")
                            )[:800],
                        }
                    )
            result["format"] = "junit"
        elif fmt in {"json", "pytest-json", "ruff-json"}:
            data = json.loads(text)
            if isinstance(data, list) and all(
                isinstance(x, dict) and {"code", "message", "filename"} <= x.keys()
                for x in data
            ):
                result["format"] = "ruff-json"
                result["issue_count"] = len(data)
                details = [
                    {
                        "name": f"{x['filename']}:{x.get('location', {}).get('row', '?')} [{x['code']}]"[
                            :500
                        ],
                        "message": str(x["message"])[:800],
                    }
                    for x in data
                ]
            elif (
                isinstance(data, dict)
                and isinstance(data.get("summary"), dict)
                and isinstance(data.get("tests"), list)
            ):
                summary = data["summary"]
                counts = {
                    k: int(summary.get(k, 0))
                    for k in (
                        "passed",
                        "failed",
                        "skipped",
                        "total",
                        "xfailed",
                        "xpassed",
                    )
                }
                counts["errors"] = int(summary.get("error", 0))
                result["format"] = "pytest-json"
                for test in data["tests"]:
                    if test.get("outcome") in {"failed", "error"}:
                        details.append(
                            {
                                "name": str(test.get("nodeid", ""))[:500],
                                "message": str(
                                    test.get("call", test.get("setup", {})).get(
                                        "longrepr", ""
                                    )
                                )[:800],
                            }
                        )
            else:
                raise ValueError(
                    "Unsupported validation JSON; use JUnit, pytest-json-report, or Ruff JSON"
                )
        else:
            raise ValueError(
                "Supported formats: auto, junit, json, pytest-json, ruff-json"
            )
    elif record.get("report_requested"):
        result["outcome"] = "report_missing"
        return result
    else:
        texts = [stream_text(ident, stream) for stream in sorted(STREAMS)]
        text = "\n".join(x[0] for x in texts)
        partial = any(x[1] for x in texts)
        # Match final pytest/unittest summary lines only, not arbitrary mentions of pass/fail.
        summaries = re.findall(
            r"^(?:=+ )?(.+?) in [\d.]+s(?: \([^\n]*\))?(?: =+)?$",
            ANSI.sub("", text),
            re.M,
        )
        if summaries:
            pairs = re.findall(
                r"(\d+) (passed|failed|skipped|error|errors|xfailed|xpassed|deselected)\b",
                summaries[-1],
            )
            if pairs:
                counts = {
                    k: 0
                    for k in (
                        "passed",
                        "failed",
                        "errors",
                        "skipped",
                        "xfailed",
                        "xpassed",
                        "deselected",
                    )
                }
                for number, key in pairs:
                    counts["errors" if key == "error" else key] += int(number)
                counts["total"] = sum(v for k, v in counts.items() if k != "deselected")
                result["format"] = "pytest-console"
        match = re.search(
            r"^Ran (\d+) tests? in [\d.]+s\s+\n(OK|FAILED)(?: \(([^\n]*)\))?",
            text,
            re.M,
        )
        if counts is None and match:
            console_failed = match[2] == "FAILED"
            counts = {
                "total": int(match[1]),
                "failed": 0,
                "errors": 0,
                "skipped": 0,
                "xfailed": 0,
                "xpassed": 0,
            }
            for key, value in re.findall(
                r"(failures|errors|skipped|expected failures|unexpected successes)=(\d+)",
                match[3] or "",
            ):
                counts[
                    {
                        "failures": "failed",
                        "expected failures": "xfailed",
                        "unexpected successes": "xpassed",
                    }.get(key, key)
                ] = int(value)
            counts["passed"] = counts["total"] - sum(
                v for k, v in counts.items() if k != "total"
            )
            result["format"] = "unittest-console"
        # Pair unittest failure headers with their assertion/traceback block.
        blocks = re.findall(
            r"^(?:FAIL|ERROR): ([^\n]+)\n(.*?)(?=^={10,}|^Ran \d+ tests? in |\Z)",
            text,
            re.M | re.S,
        )
        for name, body in blocks:
            body = body.strip().strip("-").strip()
            if len(body) > 1400:
                body = body[:500] + "\n[context omitted]\n" + body[-800:]
            details.append({"name": name[:300], "message": body})
        if not details:
            details = failure_context(text, limit=4, budget=3000)
        if not counts and not details and len(text.encode()) <= 1200:
            result["output"] = text.strip()

    result["counts"] = counts
    result["failures"] = details[:4]
    result["omitted_failures"] = max(0, len(details) - 4)
    result["scan_truncated"] = partial
    success = (
        record.get("state") == "finished"
        and record.get("exit_code") == 0
        and record.get("capture_complete")
    )
    if not success:
        result["outcome"] = "process_failed_or_incomplete"
    elif partial:
        result["outcome"] = "incomplete_report"
    elif counts is not None:
        if (
            any(v < 0 for v in counts.values())
            or sum(v for k, v in counts.items() if k not in {"total", "deselected"})
            != counts["total"]
        ):
            result["outcome"] = "inconsistent_report"
        elif console_failed or counts.get("failed", 0) or counts.get("errors", 0):
            result["outcome"] = "failed"
        elif not counts["total"]:
            result["outcome"] = "no_tests"
        elif counts["skipped"] == counts["total"]:
            result["outcome"] = "all_skipped"
        elif not counts.get("passed", 0):
            result["outcome"] = "completed_without_passes"
        else:
            result["outcome"] = "passed"
    elif result["format"] == "ruff-json":
        result["outcome"] = "issues_found" if result["issue_count"] else "passed"
    if "report" in record:
        result["outcome_provisional"] = True
        result["warning"] = (
            "Explicit report was snapshotted after the command; verify it was produced by this run."
        )
    return result


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False, openWorldHint=False
    )
)
async def validation_report(run_id: str, format: str = "auto") -> dict:
    """Parse saved JUnit/pytest/Ruff/unittest reports with counts and actual failures. Unknown formats stay unknown; structured snapshots are provisional. No model inference."""
    try:
        return await asyncio.to_thread(validation, run_id, format)
    except Exception as error:
        result = {"status": "unavailable", "error": str(error)[:300]}
        try:
            result["process"] = process_facts(manifest(run_id))
        except (ValueError, OSError):
            pass
        return result
