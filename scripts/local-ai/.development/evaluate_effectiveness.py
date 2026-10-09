"""Effectiveness evaluation; generates isolated fixtures and makes up to four local selections.

Run with the packaged Python: evaluate_effectiveness.py --output /tmp/report-evaluation.json
Byte counts measure JSON tool responses plus capture facts, not model tokens.
CLI next_step text, schemas, tool arguments, transport and reasoning are excluded.
"""

import argparse
import asyncio
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
import artifact_store as reports
import tool_config
import gemma_client
import candidate_selection
import server


def size(value):
    return len(json.dumps(value, ensure_ascii=False).encode())


async def evaluate():
    rows = []
    with tempfile.TemporaryDirectory(prefix="report-efficacy-") as temp:
        root = Path(temp)
        reports.ARTIFACTS = root / "artifacts"
        selection_inputs = []

        async def selector(payload, question, instruction, limit):
            selection_inputs.append(payload)
            return await gemma_client.gemma_select(
                payload, question, instruction, limit
            )

        tool_config.ROOTS = [root, Path(__file__).resolve().parents[3]]
        candidate_selection.gemma_select = selector
        tools = {
            name: getattr(server, name)
            for name in (
                "inspect_run",
                "validation_report",
                "filter_log",
                "search_repository",
                "compare_reports",
                "read_artifact",
            )
        }

        def capture_text(text, exit_code=1):
            source = root / "input.txt"
            source.write_text(text)
            return reports.capture(
                [
                    sys.executable,
                    "-c",
                    "import pathlib,sys;sys.stderr.write(pathlib.Path(sys.argv[1]).read_text());sys.exit(int(sys.argv[2]))",
                    str(source),
                    str(exit_code),
                ],
                root,
            )

        async def measure(name, run, tool, args, expected, baseline=None, checks=None):
            raw = "".join(
                reports.stream_text(run["id"], stream)[0]
                for stream in sorted(reports.STREAMS)
            )
            selection_inputs.clear()
            start = time.monotonic()
            result = await tools[tool](**args)
            elapsed = time.monotonic() - start
            serialized = json.dumps(result, ensure_ascii=False)
            # Baseline is raw stdout/stderr, or normal rg path:line:text output.
            before = len((raw if baseline is None else baseline).encode())
            # Include wrapper facts because the frontier receives them before inspecting a run.
            overhead = (
                size(reports.process_facts(run)) if tool != "search_repository" else 0
            )
            after = size(result) + overhead
            row = {
                "case": name,
                "tool": tool,
                "raw_bytes": before,
                "returned_bytes_including_capture": after,
                "byte_reduction_percent": round((1 - after / max(1, before)) * 100, 1),
                "tool_seconds": round(elapsed, 3),
                "capture_seconds": run["duration_seconds"],
                "expected_facts": expected,
                "facts_returned": [fact for fact in expected if fact in serialized],
                "candidate_facts": [
                    fact for fact in expected if fact in json.dumps(selection_inputs)
                ],
                "selection": result.get("evidence", {}).get("selection"),
                "local_usage": result.get("evidence", {}).get("local_usage"),
                "checks": checks(result) if checks else {},
                "result": result,
            }
            rows.append(row)
            print(
                json.dumps({k: v for k, v in row.items() if k != "result"}), flush=True
            )
            return result

        # Repeated log messages with one distinctive late failure.
        text = (
            "INFO completed background synchronization\n" * 5000
            + "ERROR database connection refused at db.internal:5432\n"
        )
        run = capture_text(text)
        await measure(
            "repeated_log",
            run,
            "filter_log",
            {
                "run_id": run["id"],
                "question": "What database connection error occurred?",
            },
            ["connection refused at db.internal:5432"],
            checks=lambda x: {
                "repetition_count_correct": any(
                    item["count"] == 5000
                    and "background synchronization" in item["text"]
                    for item in x["evidence"]["items"]
                )
                and x["coverage"]["matched_lines"] == 5001
            },
        )

        # Real failing unittest execution, with enough passing test output to hide the failure.
        suite = root / "test_generated.py"
        suite.write_text(
            "import unittest\nclass Generated(unittest.TestCase):\n"
            + "".join(
                f"    def test_ok_{i:03d}(self): self.assertTrue(True)\n"
                for i in range(120)
            )
            + '    def test_broken(self): self.assertEqual("actual-payload", "EXPECTED-PAYLOAD-735")\n'
            + 'if __name__ == "__main__": unittest.main(verbosity=2)\n'
        )
        run = reports.capture([sys.executable, str(suite)], root)
        await measure(
            "real_unittest_failure",
            run,
            "validation_report",
            {"run_id": run["id"]},
            ["EXPECTED-PAYLOAD-735", "test_broken"],
            checks=lambda x: {
                "counts_correct": x["counts"]["total"] == 121
                and x["counts"]["failed"] == 1,
                "process_failure_retained": x["process"]["exit_code"] == 1,
            },
        )

        # Early warnings must not make an actual traceback disappear unnoticed.
        text = "".join(
            f"WARNING optional plugin {i} was not installed\n" for i in range(12)
        )
        text += 'Traceback (most recent call last):\n  File "worker.py", line 42, in load\nKeyError: REQUIRED_DATABASE_URL\n'
        run = capture_text(text)
        await measure(
            "warning_flood_then_traceback",
            run,
            "inspect_run",
            {"run_id": run["id"]},
            ["KeyError: REQUIRED_DATABASE_URL"],
        )
        await measure(
            "warning_flood_focused_question",
            run,
            "inspect_run",
            {"run_id": run["id"], "question": "Which exception terminated the worker?"},
            ["KeyError: REQUIRED_DATABASE_URL"],
        )

        # Timestamped logs defeat exact duplicate grouping and exceed its 5000-group limit.
        text = "".join(
            f"2026-09-29T12:{i // 60:03d}:{i % 60:02d} INFO scheduler heartbeat\n"
            for i in range(6000)
        )
        text += (
            "2026-09-29T14:00:00 ERROR database connection refused FINAL-CAUSE-942\n"
        )
        run = capture_text(text)
        await measure(
            "timestamped_log_over_group_cap",
            run,
            "filter_log",
            {
                "run_id": run["id"],
                "question": "Which database connection failure stopped the service?",
            },
            ["FINAL-CAUSE-942"],
            checks=lambda x: {
                "all_lines_accounted_for": x["coverage"]["ungrouped_lines"] == 0
                and x["coverage"]["matched_lines"] == 6001
            },
        )
        await measure(
            "timestamped_log_literal_followup",
            run,
            "filter_log",
            {"run_id": run["id"], "contains": "database"},
            ["FINAL-CAUSE-942"],
        )

        rows[-1]["prior_response_bytes"] = rows[-2]["returned_bytes_including_capture"]
        rows[-1]["total_returned_with_prior"] = (
            rows[-1]["returned_bytes_including_capture"]
            + rows[-1]["prior_response_bytes"]
        )
        rows[-1]["recovery_note"] = (
            "Literal database filter available in the original question; conservatively includes duplicate capture facts."
        )

        # Candidate preselection can discard a semantically relevant cause before Gemma sees it.
        project = root / "project"
        project.mkdir()
        (project / "config.txt").write_text(
            "".join(
                f"cache setting documentation example {i}: normal operation\n"
                for i in range(80)
            )
            + "cache backend unavailable: ECONNREFUSED 127.0.0.1:6379\n"
        )
        run = capture_text("", 0)
        baseline = "".join(
            f"{project}/config.txt:{i + 1}:{line}\n"
            for i, line in enumerate((project / "config.txt").read_text().splitlines())
        )
        await measure(
            "repository_lexical_decoys",
            run,
            "search_repository",
            {
                "root": str(project),
                "pattern": "cache",
                "question": "Which cache setting causes the service failure?",
            },
            ["ECONNREFUSED 127.0.0.1:6379"],
            baseline=baseline,
        )

        # Real repository query with an exact evidence question.
        repo = Path(__file__).resolve().parents[3]
        baseline = subprocess.run(
            [
                "rg",
                "--no-config",
                "--line-number",
                "--with-filename",
                "--fixed-strings",
                "--",
                "httpx.AsyncClient(timeout=",
                str(repo / "scripts/local-ai/runtime"),
            ],
            capture_output=True,
            check=True,
            text=True,
        ).stdout
        await measure(
            "real_repository_timeout_lookup",
            run,
            "search_repository",
            {
                "root": str(repo / "scripts/local-ai/runtime"),
                "pattern": "httpx.AsyncClient(timeout=",
                "question": "What timeout does gemma_select use for its Ollama request?",
            },
            ["httpx.AsyncClient(timeout=110"],
            baseline=baseline,
            checks=lambda x: {
                "original_source_returned": any(
                    item["source"].endswith("gemma_client.py")
                    and "httpx.AsyncClient(timeout=110" in item["text"]
                    for item in x["evidence"]["items"]
                )
            },
        )

        # Deterministic comparison must retain actual changes alongside repeated noise.
        left = capture_text(
            "INFO worker completed\n" * 3000 + "ERROR obsolete endpoint refused\n"
        )
        right = capture_text(
            "INFO worker completed\n" * 3000 + "ERROR new endpoint refused\n" * 3
        )
        await measure(
            "before_after_comparison",
            right,
            "compare_reports",
            {"before_id": left["id"], "after_id": right["id"]},
            ["obsolete endpoint refused", "new endpoint refused"],
            baseline=reports.stream_text(left["id"], "stderr")[0]
            + reports.stream_text(right["id"], "stderr")[0],
            checks=lambda x: {
                "new_error_count_correct": x["streams"]["stderr"]["added"][0]["count"]
                == 3,
                "old_error_removed": x["streams"]["stderr"]["removed"][0]["count"] == 1,
            },
        )

        rows[-1]["returned_bytes_including_capture"] += size(
            reports.process_facts(left)
        )
        rows[-1]["byte_reduction_percent"] = round(
            (1 - rows[-1]["returned_bytes_including_capture"] / rows[-1]["raw_bytes"])
            * 100,
            1,
        )

        # Small output incurs overhead: establishes where using this pipeline is counterproductive.
        run = capture_text("ok\n", 0)
        await measure(
            "tiny_output_overhead",
            run,
            "inspect_run",
            {"run_id": run["id"]},
            [],
            checks=lambda x: {"success_status_correct": x["process"]["exit_code"] == 0},
        )

        # Ordinary traceback recovery needs a bounded read. Include both responses in cost.
        run = capture_text(
            "WARNING optional plugin missing\n" * 10
            + "KeyError: RECOVERABLE_CAUSE_81\n"
        )
        initial = await tools["inspect_run"](run_id=run["id"])
        await measure(
            "bounded_followup_read",
            run,
            "read_artifact",
            {
                "run_id": run["id"],
                "stream": "stderr",
                "start_line": 7,
                "line_count": 40,
            },
            ["RECOVERABLE_CAUSE_81"],
        )
        rows[-1]["prior_response_bytes"] = size(initial)
        rows[-1]["total_returned_with_prior"] = rows[-1][
            "returned_bytes_including_capture"
        ] + size(initial)
        rows[-1]["recovery_note"] = (
            "Start line 7 follows the sixth reported warning; no oracle line lookup."
        )

        # Long lines remain clipped on every line-based read; test evidence beyond column 1000.
        run = capture_text(
            "context=" + "x" * 1800 + " HIDDEN_CAUSE_AFTER_COLUMN_1800\n"
        )
        await measure(
            "long_line_recovery_limit",
            run,
            "read_artifact",
            {"run_id": run["id"], "stream": "stderr", "start_line": 1, "line_count": 1},
            ["HIDDEN_CAUSE_AFTER_COLUMN_1800"],
            checks=lambda x: {"read_complete": not x["clipped"]},
        )
    return {
        "method": "Controlled fixtures plus real unittest failure and repository lookup; exact expected-fact recall, JSON response bytes, wall time. Not frontier-token measurements or a blinded production benchmark.",
        "rows": rows,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = asyncio.run(evaluate())
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
