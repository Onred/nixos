"""Regression and held-out cases for retained evidence and compact output."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
import asyncio
import json
import tempfile
import unittest
from unittest.mock import patch, AsyncMock
import artifact_store as store
import filter_log
import inspect_run
import read_artifact
import validation_report
import candidate_selection
import evidence_selection
import compare_reports


class EffectivenessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patch = patch.object(store, "ARTIFACTS", self.root / "artifacts")
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def record(self, text, code=1):
        source = self.root / "fixture"
        source.write_text(text)
        return store.capture(
            [
                sys.executable,
                "-c",
                "import pathlib,sys;sys.stderr.write(pathlib.Path(sys.argv[1]).read_text());sys.exit(int(sys.argv[2]))",
                str(source),
                str(code),
            ],
            self.root,
        )["id"]

    def test_warning_flood_preserves_exception_context(self):
        text = (
            "WARNING deprecated extension\n" * 300
            + 'Traceback (most recent call last):\n  File "worker.py", line 81\nValueError: malformed profile beta\n'
        )
        report = inspect_run.inspect(self.record(text))
        self.assertIn("malformed profile beta", json.dumps(report))
        self.assertIn("worker.py", json.dumps(report))
        self.assertLess(len(json.dumps(report)), len(text) // 2)

    def test_timestamp_groups_keep_late_error(self):
        text = (
            "".join(
                f"2026-09-29T12:00:00.{i:06d} INFO still alive\n" for i in range(8000)
            )
            + "2026-09-29T13:00:00 ERROR disk quota exceeded\n"
        )
        groups, coverage = filter_log.group_log(text)
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]["count"], 8000)
        self.assertEqual(coverage["ungrouped_lines"], 0)
        self.assertIn("disk quota exceeded", groups[1]["text"])

    def test_unique_groups_keep_late_error(self):
        text = (
            "".join(f"INFO completed item {i}\n" for i in range(8000))
            + "ERROR permission denied /build/output\n"
        )
        groups, coverage = filter_log.group_log(text)
        self.assertIn("permission denied", json.dumps(groups[-1]))
        self.assertGreater(coverage["ungrouped_lines"], 0)

    def test_candidates_preserve_late_cause(self):
        entries = [
            {"source": "docs", "text": f"cache setting guide example {i}"}
            for i in range(100)
        ]
        cause = {
            "source": "daemon",
            "text": "cache backend: ECONNREFUSED 127.0.0.1:6379",
        }
        entries.insert(65, cause)
        candidates = candidate_selection.ranked_candidates(
            entries, "Which cache setting causes failure?"
        )
        self.assertTrue(any(x["text"] == cause["text"] for x in candidates))
        self.assertLessEqual(len(candidates), 30)
        self.assertLessEqual(len(json.dumps(candidates).encode()), 12000)

    def test_assertion_and_name_retained(self):
        text = (
            "test_ok ... ok\n" * 200
            + "FAIL: test_save (TestCache.test_save)\n"
            + "-" * 70
            + '\nTraceback (most recent call last):\n  File "test_cache.py", line 32\nAssertionError: 7 != 9\n\nRan 201 tests in 0.020s\n\nFAILED (failures=1)\n'
        )
        report = validation_report.validation(self.record(text))
        self.assertEqual(report["counts"]["failed"], 1)
        self.assertIn("test_save", json.dumps(report["failures"]))
        self.assertIn("7 != 9", json.dumps(report["failures"]))
        self.assertLess(len(json.dumps(report)), len(text) // 2)

    def test_quiet_pytest_supported(self):
        value = validation_report.validation(self.record("...\n3 passed in 0.04s\n", 0))
        self.assertEqual(value["counts"]["passed"], 3)
        self.assertEqual(value["outcome"], "passed")

    def test_long_line_byte_recovery(self):
        ident = self.record("x" * 9000 + " ROOT_CAUSE_AFTER_9000\n")
        first = read_artifact.read_slice(ident, "stderr", lines=1)
        self.assertTrue(first["clipped"])
        second = read_artifact.read_slice(
            ident, "stderr", byte_offset=first["lines"][0]["next_byte"]
        )
        self.assertIn("ROOT_CAUSE_AFTER_9000", second["text"])
        self.assertTrue(second["eof"])

    def test_timestamp_comparison_ignores_clock_only_change(self):
        a = self.record("2026-09-29T01:00:00 ERROR timeout 42\n")
        b = self.record("2026-09-29T02:00:00 ERROR timeout 42\n")
        diff = compare_reports.compare(a, b)["streams"]["stderr"]
        self.assertEqual(diff["added_groups"], 0)
        self.assertEqual(diff["removed_groups"], 0)

    def test_small_output_and_document_bypass_inference(self):
        result = inspect_run.inspect(self.record("ok\n", 0))
        self.assertEqual(result["output"]["stderr"], "ok\n")
        self.assertLess(len(json.dumps(result)), 200)
        model = AsyncMock(side_effect=AssertionError("Should not run"))
        with patch.object(evidence_selection, "gemma_select", model):
            result = asyncio.run(
                evidence_selection.extract([("config", "setting = 9")], "setting")
            )
        self.assertEqual(result["selection"], "direct")
        model.assert_not_called()

    def test_repository_keeps_diagnostic_when_model_selects_nothing(self):
        import search_repository
        import tool_config

        project = self.root / "project"
        project.mkdir()
        (project / "cache.txt").write_text(
            "".join(f"cache documentation example {i}\n" for i in range(80))
            + "cache: ECONNREFUSED backend\n"
        )
        model = AsyncMock(
            return_value={
                "selected": [],
                "local_usage": {"input_tokens": 1, "output_tokens": 1},
            }
        )
        with (
            patch.object(tool_config, "ROOTS", [project]),
            patch.object(candidate_selection, "gemma_select", model),
        ):
            result = asyncio.run(
                search_repository.search_repository(
                    str(project), "cache", "What caused the cache failure?"
                )
            )
        self.assertIn("ECONNREFUSED backend", json.dumps(result["evidence"]["items"]))
        self.assertEqual(result["evidence"]["retained_diagnostics"], 1)

    def test_long_document_line_not_discarded(self):
        text = "a" * 8000 + " explicit_default = 19"
        blocks, coverage = evidence_selection.candidates(
            [("manual", text)], "explicit_default"
        )
        self.assertTrue(any("explicit_default = 19" in b["text"] for b in blocks))
        self.assertEqual(coverage["long_lines_split"], 1)
        for block in blocks:
            start = block.get("start_column", 1) - 1
            self.assertEqual(text[start : start + len(block["text"])], block["text"])


if __name__ == "__main__":
    unittest.main()
