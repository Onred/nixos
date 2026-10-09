"""Run a frontier-chosen command through the host shell's normal approval path."""

import argparse
import json
import os
from pathlib import Path

from artifact_store import capture, process_facts
from inspect_run import inspect
from validation_report import validation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--max-output-mib", type=int, default=32)
    parser.add_argument(
        "--facts-only",
        action="store_true",
        help="Return only process facts when a separate filtering tool will be used",
    )
    parser.add_argument(
        "--report",
        help="Explicit JUnit/pytest-json/Ruff report to snapshot after execution",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    argv = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not argv:
        parser.error("Supply a command after --")
    os.umask(0o077)
    record = capture(
        argv,
        args.cwd,
        args.timeout,
        args.max_output_mib * 1024 * 1024,
        report_path=args.report,
    )
    output = (
        {"process": process_facts(record)} if args.facts_only else inspect(record["id"])
    )
    try:
        parsed = {"format": None} if args.facts_only else validation(record["id"])
        if not args.facts_only and (parsed["format"] or record.get("report_requested")):
            output = parsed
    except Exception as error:
        output["validation_error"] = str(error)[:300]
    print(json.dumps(output, ensure_ascii=False, separators=(",", ":")))
    if record.get("timed_out"):
        return 124
    if record.get("output_limit_reached"):
        return 125
    if record.get("capture_error"):
        return 126
    return (
        record["exit_code"]
        if record["exit_code"] is not None
        else 128 + (record.get("signal") or 1)
    )


if __name__ == "__main__":
    raise SystemExit(main())
