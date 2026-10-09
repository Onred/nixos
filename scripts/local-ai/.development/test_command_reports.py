import sys
from pathlib import Path

sys.path[:0] = [
    str(Path(__file__).resolve().parents[1] / "runtime"),
    str(Path(__file__).resolve().parents[1]),
]
"""Regression tests for execution facts, parser honesty, and bounded evidence."""
import asyncio
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest.mock import patch, AsyncMock

import artifact_store as r
import inspect_run as inspection
import read_artifact as reader
import validation_report as validation
import filter_log as logs
import compare_reports as comparison
import search_repository as repository
import candidate_selection as selection


class ReportsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.mock = patch.object(r, "ARTIFACTS", self.root / "artifacts")
        self.mock.start()

    def tearDown(self):
        self.mock.stop()
        self.temp.cleanup()

    def run_code(self, code, **kwargs):
        return r.capture([sys.executable, "-c", code], self.root, **kwargs)

    def report(self, text, **kwargs):
        return self.run_code("print(" + repr(text) + ")", **kwargs)["id"]

    def structured(self, text):
        path = self.root / "report"
        path.write_text(text)
        return self.run_code("pass", report_path=str(path))["id"]

    def test_exit_and_streams(self):
        run = self.run_code(
            'import sys; print("out"); print("error: broken",file=sys.stderr);sys.exit(7)'
        )
        self.assertEqual(run["exit_code"], 7)
        self.assertTrue(run["capture_complete"])
        self.assertIn(
            "error: broken", inspection.inspect(run["id"])["output"]["stderr"]
        )
        self.assertEqual(
            reader.read_slice(run["id"], "stdout")["lines"][0]["text"], "out"
        )
        self.assertEqual(
            (r.artifact_dir(run["id"]) / "stdout").stat().st_mode & 0o777, 0o600
        )

    def test_missing_command(self):
        run = r.capture(["/nonexistent/command"], self.root)
        self.assertIn("capture_error", run)
        self.assertIsNone(run["exit_code"])
        self.assertFalse(run["capture_complete"])

    def test_signal(self):
        run = self.run_code("import os,signal;os.kill(os.getpid(),signal.SIGTERM)")
        self.assertEqual(run["signal"], signal.SIGTERM)
        self.assertIsNone(run["exit_code"])

    def test_timeout_kills_descendants(self):
        marker = self.root / "descendant-survived"
        code = (
            'import subprocess,sys,time;subprocess.Popen([sys.executable,"-c",'
            + repr(
                "import time,pathlib;time.sleep(.8);pathlib.Path("
                + repr(str(marker))
                + ").touch()"
            )
            + "]);time.sleep(5)"
        )
        run = self.run_code(code, timeout=0.15)
        self.assertTrue(run["timed_out"])
        self.assertFalse(run["capture_complete"])
        import time

        time.sleep(0.9)
        self.assertFalse(marker.exists())

    def test_output_bound(self):
        run = self.run_code(
            'import os\nwhile True: os.write(1,b"x"*65536)', max_bytes=1024
        )
        self.assertTrue(run["output_limit_reached"])
        self.assertEqual(sum(x["bytes"] for x in run["streams"].values()), 1024)
        self.assertLess(run["duration_seconds"], 5)

    def test_artifact_access_and_long_lines(self):
        ident = self.run_code("print('x' * 100000); print('last')")["id"]
        value = reader.read_slice(ident, "stdout", 1, 2)
        self.assertTrue(value["clipped"])
        self.assertEqual(value["lines"][1], {"line": 2, "text": "last"})
        with self.assertRaises(ValueError):
            reader.read_slice("../../etc/passwd", "stdout")
        path = r.artifact_dir(ident) / "stderr"
        path.unlink()
        path.symlink_to("/etc/passwd")
        with self.assertRaises(OSError):
            r.stream_text(ident, "stderr")
        path.unlink()
        os.mkfifo(path)
        with self.assertRaises(ValueError):
            r.stream_text(ident, "stderr")

    def test_unknown_is_not_pass(self):
        self.assertEqual(
            validation.validation(self.report("All good"))["outcome"], "unknown"
        )

    def test_pytest_console(self):
        parsed = validation.validation(
            self.report(
                "================== 3 passed, 1 skipped in 0.03s =================="
            )
        )
        self.assertEqual(parsed["counts"]["total"], 4)
        self.assertEqual(parsed["outcome"], "passed")
        self.assertEqual(
            validation.validation(self.report("=== 2 failed in 0.03s ==="))["outcome"],
            "failed",
        )
        self.assertEqual(
            validation.validation(self.report("=== 2 xfailed in 0.03s ==="))["outcome"],
            "completed_without_passes",
        )

    def test_unittest_console(self):
        parsed = validation.validation(
            self.report("Ran 3 tests in 0.013s\n\nOK (skipped=1)")
        )
        self.assertEqual(parsed["counts"]["passed"], 2)
        self.assertEqual(parsed["outcome"], "passed")
        self.assertEqual(
            validation.validation(self.report("Ran 0 tests in 0.013s\n\nOK"))[
                "outcome"
            ],
            "no_tests",
        )
        self.assertEqual(
            validation.validation(
                self.report("Ran 1 test in 0.013s\n\nFAILED (unexpected successes=1)")
            )["outcome"],
            "failed",
        )

    def test_junit_provisional_counts(self):
        parsed = validation.validation(
            self.structured(
                '<testsuites><testsuite><testcase name="a"/><testcase name="b"><skipped/></testcase><testcase name="c"><failure message="bad">detail</failure></testcase></testsuite></testsuites>'
            )
        )
        self.assertEqual(
            parsed["counts"],
            {"passed": 1, "failed": 1, "errors": 0, "skipped": 1, "total": 3},
        )
        self.assertEqual(parsed["outcome"], "failed")
        self.assertTrue(parsed["outcome_provisional"])
        self.assertIn("detail", parsed["failures"][0]["message"])
        with self.assertRaises(ValueError):
            validation.validation(self.structured("<!DOCTYPE x><testsuite/>"))

    def test_json_and_missing_report(self):
        self.assertEqual(
            validation.validation(self.structured("[]"))["outcome"], "passed"
        )
        parsed = validation.validation(
            self.structured(
                json.dumps([{"code": "F401", "message": "unused", "filename": "x.py"}])
            )
        )
        self.assertEqual(parsed["issue_count"], 1)
        self.assertEqual(parsed["outcome"], "issues_found")
        parsed = validation.validation(
            self.structured(
                json.dumps({"summary": {"passed": 2, "total": 1}, "tests": []})
            )
        )
        self.assertEqual(parsed["outcome"], "inconsistent_report")
        parsed = validation.validation(
            self.run_code("pass", report_path="missing")["id"]
        )
        self.assertEqual(parsed["outcome"], "report_missing")
        with self.assertRaises(ValueError):
            validation.validation(self.structured('{"invented":true}'))

    def test_group_and_compare(self):
        groups, coverage = logs.group_log("error 1\nerror 1\nerror 2\ninfo")
        self.assertEqual(groups[0]["count"], 2)
        self.assertEqual(coverage["groups"], 3)
        a, b = self.report("error 1\nerror 1"), self.report("error 1\nerror 2")
        diff = comparison.compare(a, b)["streams"]["stdout"]
        self.assertEqual(diff["added"], [{"text": "error 2", "count": 1}])
        self.assertEqual(diff["removed"], [{"text": "error 1", "count": 1}])

    def test_repository_scope_and_no_config(self):
        project = self.root / "project"
        project.mkdir()
        (project / "a.py").write_text("needle[\nneedle2\n")
        (project / "secret.key").write_text("needle[\n")
        (project / "secrets").mkdir()
        (project / "secrets" / "private").write_text("needle[\n")
        (self.root / "outside").write_text("needle[\n")
        (project / "link").symlink_to(self.root / "outside")
        config = self.root / "rgconfig"
        config.write_text("--follow\n--hidden\n")
        with patch.dict(os.environ, {"RIPGREP_CONFIG_PATH": str(config)}):
            run, entries, coverage = repository.repository_scan(
                str(project), "needle[", [project]
            )
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["line"], 1)
        self.assertEqual(entries[0]["text"], "needle[")
        self.assertTrue(run["capture_complete"])
        run, entries, _ = repository.repository_scan(str(project), "absent", [project])
        self.assertEqual(run["exit_code"], 1)
        self.assertEqual(entries, [])
        run, _, _ = repository.repository_scan(str(project), "[", [project], regex=True)
        self.assertEqual(run["exit_code"], 2)
        with self.assertRaises(ValueError):
            repository.repository_scan(str(self.root), "needle", [project])

    def test_selection_and_unavailable(self):
        entries = [{"text": f"line {i}"} for i in range(50)]
        selector = AsyncMock(
            return_value={"selected": [1, 3], "local_usage": {"model": "test"}}
        )
        selected = asyncio.run(selection.choose(entries, "line", selector))
        self.assertEqual(len(selected["items"]), 2)
        self.assertTrue(all(x in entries for x in selected["items"]))
        self.assertEqual(selected["coverage"]["considered"], 30)
        self.assertEqual(selected["omitted"], 48)
        selector = AsyncMock(side_effect=RuntimeError("busy"))
        selected = asyncio.run(selection.choose(entries, "line", selector))
        self.assertEqual(selected["selection"], "unavailable")
        self.assertEqual(len(selected["items"]), 6)
        self.assertTrue(all(x in entries for x in selected["items"]))
        selector.reset_mock()
        asyncio.run(selection.choose(entries[:2], "line", selector))
        selector.assert_not_called()


if __name__ == "__main__":
    unittest.main()
