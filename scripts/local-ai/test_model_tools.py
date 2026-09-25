import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import httpx
import tomlkit

import model_tools as tools
import register_codex


class EvidenceTests(unittest.TestCase):
    def test_exact_excerpts_and_invalid_ids(self):
        blocks, coverage = tools.candidates([("source", "first\nsecond\nthird\nfourth\nfifth")], "fifth")
        result = tools.selected_evidence('{"selected":[0,0]}', blocks)
        self.assertEqual(result, [{"source": "source", "start_line": 5, "end_line": 5, "text": "fifth"}])
        self.assertFalse(coverage["partial"])
        for selection in ([99], [-1], [True], ["0"], [0] * 5):
            with self.assertRaises(ValueError):
                tools.selected_evidence(json.dumps({"selected": selection}), blocks)

    def test_budget_and_partial_coverage(self):
        text = "\n".join(f"line {n} suspend " + "x" * 150 for n in range(200))
        blocks, coverage = tools.candidates([("log", text)], "suspend")
        self.assertTrue(coverage["partial"])
        self.assertLessEqual(sum(len(block["text"].encode()) + 80 for block in blocks), tools.INPUT_BYTES)

    def test_oversized_lines_reported(self):
        blocks, coverage = tools.candidates([("source", "x" * 2000)], "x")
        self.assertEqual(blocks, [])
        self.assertEqual(coverage["oversized_lines_skipped"], 1)

    def test_file_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            inside = root / "file.txt"
            inside.write_text("evidence")
            outside = Path(directory) / "outside.txt"
            outside.write_text("private")
            (root / "escape").symlink_to(outside)
            (root / ".env.local").write_text("secret")
            with patch.object(tools, "ROOTS", [root]):
                self.assertEqual(tools.file_text(str(inside))[1], "evidence")
                for path in (outside, root / "escape", root / ".env.local", root):
                    with self.assertRaises((ValueError, IsADirectoryError)):
                        tools.file_text(str(path))

    def test_url_boundaries(self):
        for url in ("file:///etc/passwd", "http://user:password@example.com", "https://example.com:444"):
            with self.assertRaises(ValueError):
                tools.public_url(url)
        for address in ("127.0.0.1", "10.0.0.1", "169.254.169.254", "::1"):
            with patch.object(socket, "getaddrinfo", return_value=[(0, 0, 0, "", (address, 80))]):
                with self.assertRaises(ValueError):
                    tools.public_url("http://example.com")

    def test_cache_bounded(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(tools, "CACHE", Path(directory)):
            for index in range(105):
                tools.cache_put(str(index), {"number": index})
            self.assertIsNone(tools.cache_get("0", 900))
            self.assertEqual(tools.cache_get("104", 900), {"number": 104})
            self.assertIsNone(tools.cache_get("104", -1))


class AsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_ollama_selection_and_busy_model(self):
        actual_client = httpx.AsyncClient
        calls = []
        active = []

        def response(request):
            if request.url.path == "/api/ps":
                return httpx.Response(200, json={"models": active})
            calls.append(json.loads(request.content))
            return httpx.Response(200, json={"message": {"content": '{"selected":[0]}'}, "prompt_eval_count": 100, "eval_count": 8})

        def client(**kwargs):
            return actual_client(**kwargs, transport=httpx.MockTransport(response))

        with tempfile.TemporaryDirectory() as directory, patch.object(tools, "CACHE", Path(directory)), patch.object(tools.httpx, "AsyncClient", side_effect=client):
            result = await tools.extract([("source", "actual evidence")], "evidence")
            self.assertEqual(result["evidence"][0]["text"], "actual evidence")
            self.assertEqual(calls[0]["model"], "gemma4:12b-it-qat")
            self.assertFalse(calls[0]["think"])
            active.append({"name": "qwen3.8:27b"})
            with self.assertRaisesRegex(ValueError, "will not evict"):
                await tools.extract([("source", "actual evidence")], "evidence")
            self.assertEqual(len(calls), 1)

    async def test_concurrent_lock_fails_fast(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(tools, "CACHE", Path(directory)):
            async with tools.exclusive("gemma"):
                with self.assertRaisesRegex(ValueError, "busy"):
                    async with tools.exclusive("gemma"):
                        pass

    async def test_http_redirect_rechecks_destination(self):
        actual_client = httpx.AsyncClient
        checks = []

        async def check(url):
            checks.append(url)
            if "127.0.0.1" in url:
                raise ValueError("private address")

        def client(**kwargs):
            return actual_client(**kwargs, transport=httpx.MockTransport(lambda _: httpx.Response(302, headers={"location": "http://127.0.0.1/private"})))

        with patch.object(tools, "check_url", side_effect=check), patch.object(tools.httpx, "AsyncClient", side_effect=client):
            with self.assertRaisesRegex(ValueError, "private"):
                await tools.http_page("https://example.com")
        self.assertEqual(len(checks), 2)

    async def test_browser_fallback_once_and_no_retry_for_rate_limit(self):
        response = httpx.Response(403, request=httpx.Request("GET", "https://example.com"))
        error = httpx.HTTPStatusError("forbidden", request=response.request, response=response)
        browser = AsyncMock(return_value=("https://example.com", "<html><body><article><h1>Source</h1><p>" + "Useful source content. " * 40 + "</p></article></body></html>"))
        with tempfile.TemporaryDirectory() as directory, patch.object(tools, "CACHE", Path(directory)), patch.object(tools, "check_url", new=AsyncMock()), patch.object(tools, "http_page", new=AsyncMock(side_effect=error)), patch.object(tools, "browser_page", new=browser):
            result = await tools.fetch_page("https://example.com", True)
            self.assertEqual(result["method"], "browser")
            self.assertEqual(browser.await_count, 1)
            response.status_code = 429
            with self.assertRaisesRegex(ValueError, "429"):
                await tools.fetch_page("https://example.com", True)
            self.assertEqual(browser.await_count, 1)

    async def test_tool_schema_and_safe_errors(self):
        advertised = await tools.mcp.list_tools()
        self.assertEqual({tool.name for tool in advertised}, {"search_web", "read_web", "extract_evidence"})
        self.assertTrue(all(tool.annotations.readOnlyHint for tool in advertised))
        result = await tools.extract_evidence([], "question")
        self.assertEqual(result["status"], "unavailable")


class RegistrationTests(unittest.TestCase):
    def test_merge_preserves_user_settings_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = '# personal\nmodel = "gpt-6-astra"\n[mcp_servers.docs]\nurl = "https://example.com"\n'
            (root / "config.toml").write_text(original)
            (root / "AGENTS.md").write_text("# My instructions\nKeep these.\n")
            managed = '[mcp_servers.local_gemma]\ncommand = "/nix/store/test/bin/local-model-tools"\n'
            register_codex.register(root, managed, "Use evidence tools.")
            first = (root / "config.toml").read_text()
            first_agents = (root / "AGENTS.md").read_text()
            register_codex.register(root, managed, "Use evidence tools.")
            self.assertEqual((root / "config.toml").read_text(), first)
            self.assertEqual((root / "AGENTS.md").read_text(), first_agents)
            parsed = tomlkit.parse(first)
            self.assertEqual(parsed["model"], "gpt-6-astra")
            self.assertIn("docs", parsed["mcp_servers"])
            self.assertIn("Keep these.", first_agents)
            self.assertEqual((root / "config.toml.before-local-gemma").read_text(), original)
            self.assertEqual((root / "config.toml").stat().st_mode & 0o777, 0o600)

    def test_broken_guidance_leaves_config_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config.toml").write_text('model = "original"\n')
            (root / "AGENTS.md").write_text(register_codex.START)
            with self.assertRaises(ValueError):
                register_codex.register(root, '[mcp_servers.local_gemma]\ncommand="x"', "guidance")
            self.assertEqual((root / "config.toml").read_text(), 'model = "original"\n')

    def test_symlink_managed_config_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config.toml").symlink_to(root / "elsewhere")
            with self.assertRaises(ValueError):
                register_codex.register(root, '[mcp_servers.local_gemma]\ncommand="x"', "guidance")
            self.assertTrue((root / "config.toml").is_symlink())


if __name__ == "__main__":
    unittest.main()
