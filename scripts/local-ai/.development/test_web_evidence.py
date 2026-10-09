import sys
from pathlib import Path

sys.path[:0] = [
    str(Path(__file__).resolve().parents[1] / "runtime"),
    str(Path(__file__).resolve().parents[1]),
]
import json
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import httpx
import tomlkit

import asyncio
import server  # noqa: F401 -- registers every tool for schema checks
import tool_config as config
import evidence_selection as evidence
import web_retrieval as web
import search_web as search
import extract_evidence as files
import register_codex


class EvidenceTests(unittest.TestCase):
    def test_exact_excerpts_and_invalid_ids(self):
        blocks, coverage = evidence.candidates(
            [("source", "first\nsecond\nthird\nfourth\nfifth")], "fifth"
        )
        result = evidence.selected_evidence('{"selected":[0,0]}', blocks)
        self.assertEqual(
            result,
            [{"source": "source", "start_line": 5, "end_line": 5, "text": "fifth"}],
        )
        self.assertFalse(coverage["partial"])
        for selection in ([99], [-1], [True], ["0"], [0] * 5):
            with self.assertRaises(ValueError):
                evidence.selected_evidence(json.dumps({"selected": selection}), blocks)

    def test_budget_and_partial_coverage(self):
        text = "\n".join(f"line {n} suspend " + "x" * 150 for n in range(200))
        blocks, coverage = evidence.candidates([("log", text)], "suspend")
        self.assertTrue(coverage["partial"])
        self.assertLessEqual(
            sum(len(block["text"].encode()) + 80 for block in blocks),
            config.INPUT_BYTES,
        )

    def test_oversized_lines_reported(self):
        blocks, coverage = evidence.candidates([("source", "x" * 2000)], "x")
        self.assertTrue(blocks)
        self.assertEqual(coverage["long_lines_split"], 1)
        self.assertFalse(coverage["partial"])

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
            with patch.object(config, "ROOTS", [root]):
                self.assertEqual(files.file_text(str(inside))[1], "evidence")
                for path in (outside, root / "escape", root / ".env.local", root):
                    with self.assertRaises((ValueError, IsADirectoryError)):
                        files.file_text(str(path))

    def test_url_boundaries(self):
        for url in (
            "file:///etc/passwd",
            "http://user:password@example.com",
            "https://example.com:444",
        ):
            with self.assertRaises(ValueError):
                web.public_url(url)
        for address in ("127.0.0.1", "10.0.0.1", "169.254.169.254", "::1"):
            with patch.object(
                socket, "getaddrinfo", return_value=[(0, 0, 0, "", (address, 80))]
            ):
                with self.assertRaises(ValueError):
                    web.public_url("http://example.com")

    def test_google_challenge_is_not_evidence(self):
        content = (
            "<html><body><p>Our systems have detected unusual traffic from your computer network.</p>"
            + "Please solve the CAPTCHA. " * 20
            + "</body></html>"
        )
        with self.assertRaisesRegex(ValueError, "access challenge"):
            web.readable(content)

    def test_cache_bounded(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(config, "CACHE", Path(directory)),
        ):
            for index in range(105):
                config.cache_put(str(index), {"number": index})
            self.assertIsNone(config.cache_get("0", 900))
            self.assertEqual(config.cache_get("104", 900), {"number": 104})
            self.assertIsNone(config.cache_get("104", -1))


class AsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_ollama_selection_and_busy_model(self):
        actual_client = httpx.AsyncClient
        calls = []
        active = []

        def response(request):
            if request.url.path == "/api/ps":
                return httpx.Response(200, json={"models": active})
            calls.append(json.loads(request.content))
            return httpx.Response(
                200,
                json={
                    "message": {"content": '{"selected":[0]}'},
                    "prompt_eval_count": 100,
                    "eval_count": 8,
                },
            )

        def client(**kwargs):
            return actual_client(**kwargs, transport=httpx.MockTransport(response))

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(config, "CACHE", Path(directory)),
            patch.object(httpx, "AsyncClient", side_effect=client),
        ):
            result = await evidence.extract(
                [("source", "actual evidence\n" + "x" * 2000)], "evidence"
            )
            self.assertIn("actual evidence", result["evidence"][0]["text"])
            self.assertEqual(calls[0]["model"], "gemma4:12b-it-qat")
            self.assertFalse(calls[0]["think"])
            active.append({"name": "qwen3.8:27b"})
            with self.assertRaisesRegex(ValueError, "will not evict"):
                await evidence.extract(
                    [("source", "actual evidence\n" + "x" * 2000)], "evidence"
                )
            self.assertEqual(len(calls), 1)

    async def test_concurrent_lock_fails_fast(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(config, "CACHE", Path(directory)),
        ):
            async with config.exclusive("gemma"):
                with self.assertRaisesRegex(ValueError, "busy"):
                    async with config.exclusive("gemma"):
                        pass

    async def test_http_redirect_rechecks_destination(self):
        actual_client = httpx.AsyncClient
        checks = []

        async def check(url):
            checks.append(url)
            if "127.0.0.1" in url:
                raise ValueError("private address")

        def client(**kwargs):
            return actual_client(
                **kwargs,
                transport=httpx.MockTransport(
                    lambda _: httpx.Response(
                        302, headers={"location": "http://127.0.0.1/private"}
                    )
                ),
            )

        with (
            patch.object(web, "check_url", side_effect=check),
            patch.object(httpx, "AsyncClient", side_effect=client),
        ):
            with self.assertRaisesRegex(ValueError, "private"):
                await web.http_page("https://example.com")
        self.assertEqual(len(checks), 2)

    async def test_browser_fallback_once_and_no_retry_for_rate_limit(self):
        response = httpx.Response(
            403, request=httpx.Request("GET", "https://example.com")
        )
        error = httpx.HTTPStatusError(
            "forbidden", request=response.request, response=response
        )
        browser = AsyncMock(
            return_value=(
                "https://example.com",
                "<html><body><article><h1>Source</h1><p>"
                + "Useful source content. " * 40
                + "</p></article></body></html>",
            )
        )
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(config, "CACHE", Path(directory)),
            patch.object(web, "check_url", new=AsyncMock()),
            patch.object(web, "http_page", new=AsyncMock(side_effect=error)),
            patch.object(web, "browser_page", new=browser),
        ):
            result = await web.fetch_page("https://example.com", True)
            self.assertEqual(result["method"], "browser")
            self.assertEqual(browser.await_count, 1)
            response.status_code = 429
            with self.assertRaisesRegex(ValueError, "429"):
                await web.fetch_page("https://example.com", True)
            self.assertEqual(browser.await_count, 1)

    async def test_tool_schema_and_safe_errors(self):
        advertised = await config.mcp.list_tools()
        self.assertEqual(
            {tool.name for tool in advertised},
            {
                "search_web",
                "read_web",
                "extract_evidence",
                "inspect_run",
                "validation_report",
                "filter_log",
                "search_repository",
                "compare_reports",
                "read_artifact",
            },
        )
        self.assertTrue(all(tool.annotations.readOnlyHint for tool in advertised))
        result = await files.extract_evidence([], "question")
        self.assertEqual(result["status"], "unavailable")


class SearchTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        cache = patch.object(config, "CACHE", Path(directory.name))
        cache.start()
        self.addCleanup(cache.stop)
        self.items = [
            {
                "url": "https://sites.google.com/new",
                "title": "Google Sites",
                "content": "Create a website",
                "engines": ["bing"],
            },
            {
                "url": "https://docs.example.com/audio",
                "title": "Audio timing",
                "content": "Configure timer scheduling",
                "engines": ["brave"],
            },
        ]
        self.failures = [["duckduckgo", "CAPTCHA"]]
        self.selection = [1]
        self.models = []
        self.calls = []
        self.requests = []
        actual_client = httpx.AsyncClient

        def response(request):
            if request.url.path == "/search":
                self.requests.append(request)
                return httpx.Response(
                    200,
                    json={"results": self.items, "unresponsive_engines": self.failures},
                )
            if request.url.path == "/api/ps":
                return httpx.Response(200, json={"models": self.models})
            self.calls.append(json.loads(request.content))
            return httpx.Response(
                200,
                json={
                    "message": {"content": json.dumps({"selected": self.selection})},
                    "prompt_eval_count": 200,
                    "eval_count": 9,
                },
            )

        client = patch.object(
            httpx,
            "AsyncClient",
            side_effect=lambda **kw: actual_client(
                **kw, transport=httpx.MockTransport(response)
            ),
        )
        client.start()
        self.addCleanup(client.stop)
        sleep = patch.object(asyncio, "sleep", new=AsyncMock())
        sleep.start()
        self.addCleanup(sleep.stop)

    async def test_search_uses_gemma_and_preserves_selected_source(self):
        result = await search.search_web("audio timer scheduling", fresh=True)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["model"], config.MODEL)
        self.assertEqual(result["local_usage"]["input_tokens"], 200)
        self.assertEqual(result["results"][0]["url"], self.items[1]["url"])
        self.assertEqual(result["results"][0]["snippet"], self.items[1]["content"])
        self.assertEqual(result["results"][0]["engines"], ["brave"])
        self.assertTrue(result["degraded"])
        self.assertEqual(result["failed_engines"], self.failures)
        self.assertEqual(result["coverage"]["considered"], 2)
        self.assertEqual(result["coverage"]["returned"], 1)
        self.assertEqual(self.calls[0]["model"], config.MODEL)
        self.assertFalse(self.calls[0]["think"])

    async def test_domain_filter_includes_subdomains_not_lookalikes(self):
        self.items += [
            {"url": "https://example.com.evil.test/audio"},
            {"url": "https://notexample.com/audio"},
            {"url": "https://example.com/audio"},
        ]
        self.selection = [0, 1]
        result = await search.search_web("audio", domains=["EXAMPLE.COM."])
        self.assertEqual(result["domains"], ["example.com"])
        self.assertEqual(result["coverage"]["domain_rejected"], 3)
        self.assertEqual(len(result["results"]), 2)
        self.assertEqual(self.requests[0].url.params["q"], "site:example.com audio")

    async def test_site_operator_is_enforced_locally(self):
        self.selection = [0]
        result = await search.search_web("site:example.com audio")
        self.assertEqual(result["results"][0]["url"], self.items[1]["url"])
        self.assertEqual(result["coverage"]["domain_rejected"], 1)

    async def test_malformed_query_and_domains_fail_before_search(self):
        for query, domains in [
            ("site.example.com audio", None),
            ("audio", ["https://example.com"]),
            ("audio", ["example.com/path"]),
            ("site:example.com audio", ["example.com"]),
            ("", None),
        ]:
            result = await search.search_web(query, domains=domains)
            self.assertEqual(result["status"], "unavailable")
        self.assertEqual(self.requests, [])

    async def test_no_relevant_results_is_not_success(self):
        self.selection = []
        result = await search.search_web("unrelated topic")
        self.assertEqual(result["status"], "no_relevant_results")
        self.assertEqual(result["results"], [])
        self.assertEqual(len(self.calls), 1)

    async def test_no_candidates_skips_inference_and_keeps_failures(self):
        result = await search.search_web("audio", domains=["missing.test"])
        self.assertEqual(result["status"], "upstream_unavailable")
        self.assertIn("SearXNG", result["next_step"])
        self.assertIsNone(result["local_usage"])
        self.assertTrue(result["degraded"])
        self.assertEqual(self.calls, [])

    async def test_transport_failure_preserves_scope_and_reports_limitation(self):
        # Replace the existing mock factory only for the SearXNG request.
        with patch.object(httpx, "AsyncClient") as factory:
            client = factory.return_value.__aenter__.return_value
            client.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
            result = await search.search_web("audio", domains=["example.com"])
        self.assertEqual(result["status"], "upstream_unavailable")
        self.assertEqual(result["domains"], ["example.com"])
        self.assertEqual(result["failed_engines"][0][0], "searxng")
        self.assertIn("SearXNG", result["next_step"])
        self.assertEqual(self.calls, [])

    async def test_busy_model_never_returns_unfiltered_results(self):
        self.models = [{"name": "another-model"}]
        result = await search.search_web("audio")
        self.assertEqual(result["status"], "unavailable")
        self.assertIn("will not evict", result["error"])
        self.assertNotIn("results", result)
        self.assertEqual(self.calls, [])

    async def test_invalid_model_ids_never_return_results(self):
        for selection in ([999], [True], ["0"], [0] * 6):
            self.selection = selection
            result = await search.search_web("audio", fresh=True)
            self.assertEqual(result["status"], "unavailable")
            self.assertNotIn("results", result)

    async def test_cached_selection_avoids_inference_and_fresh_bypasses(self):
        first = await search.search_web("audio")
        cached = await search.search_web("audio")
        self.assertFalse(first["cached"])
        self.assertTrue(cached["cached"])
        self.assertEqual(cached["results"], first["results"])
        self.assertEqual(len(self.calls), 1)
        await search.search_web("audio", fresh=True)
        self.assertEqual(len(self.calls), 2)

    async def test_old_unfiltered_cache_is_not_reused(self):
        import hashlib

        config.cache_put(
            "search:" + hashlib.sha256(b"audio").hexdigest(), {"results": self.items}
        )
        result = await search.search_web("audio")
        self.assertFalse(result["cached"])
        self.assertEqual(len(self.calls), 1)

    def test_candidate_count_and_byte_bounds(self):
        items = [
            {"url": f"https://example.com/{index}", "content": "x" * 600}
            for index in range(100)
        ]
        candidates, coverage = search.search_candidates(items, [])
        self.assertLessEqual(len(candidates), 20)
        self.assertLessEqual(coverage["candidate_bytes"], config.INPUT_BYTES)
        self.assertTrue(coverage["partial"])
        self.assertTrue(all(len(item["snippet"]) <= 450 for item in candidates))
        self.assertEqual(
            [item["id"] for item in candidates], list(range(len(candidates)))
        )

    def test_unsafe_duplicate_and_malformed_links_are_omitted(self):
        items = [
            {"url": url}
            for url in [
                "javascript:alert(1)",
                "https://user:password@example.com",
                "https://[broken",
                "https://example.com",
                "https://example.com",
            ]
        ]
        candidates, _ = search.search_candidates(items, [])
        self.assertEqual([item["url"] for item in candidates], ["https://example.com"])


@unittest.skipUnless(
    os.environ.get("LOCAL_GEMMA_LIVE_TESTS") == "1", "Opt-in live local Gemma inference"
)
class LiveGemmaTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_gemma_filters_search_candidates(self):
        # Controlled search fixture, real Ollama inference; no upstream search requests.
        items = [
            {
                "url": f"https://example.com/unrelated/{index}",
                "title": title,
                "content": "An unrelated page about " + title,
                "engines": ["fixture"],
            }
            for index, title in enumerate(
                [
                    "Google Sites website builder",
                    "Audio equipment store",
                    "Weather forecast",
                    "Pizza recipes",
                    "Gardening tips",
                    "Computer monitors",
                    "Camera reviews",
                    "Linux wallpaper gallery",
                    "Video game releases",
                    "Travel photography",
                ]
            )
        ]
        relevant = {
            "url": "https://pipewire.pages.freedesktop.org/wireplumber/daemon/configuration/priorities.html",
            "title": "WirePlumber node priorities",
            "content": "A saved user default sink selection outranks priority.session on subsequent starts.",
            "engines": ["fixture"],
        }
        items.insert(6, relevant)
        actual_client = httpx.AsyncClient
        original_get = actual_client.get

        async def get(client, url, **kwargs):
            if url == config.SEARX:
                return httpx.Response(
                    200, request=httpx.Request("GET", url), json={"results": items}
                )
            return await original_get(client, url, **kwargs)

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(config, "CACHE", Path(directory)),
            patch.object(actual_client, "get", new=get),
        ):
            result = await search.search_web(
                "WirePlumber saved default sink versus priority.session", fresh=True
            )
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual([item["url"] for item in result["results"]], [relevant["url"]])
        self.assertGreater(result["local_usage"]["input_tokens"], 0)
        self.assertLess(
            result["coverage"]["result_bytes"], result["coverage"]["candidate_bytes"]
        )
        print(
            "Live Gemma search selection:",
            json.dumps(
                {"coverage": result["coverage"], "local_usage": result["local_usage"]}
            ),
        )


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
            self.assertEqual(
                (root / "config.toml.before-local-gemma").read_text(), original
            )
            self.assertEqual((root / "config.toml").stat().st_mode & 0o777, 0o600)

    def test_broken_guidance_leaves_config_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config.toml").write_text('model = "original"\n')
            (root / "AGENTS.md").write_text(register_codex.START)
            with self.assertRaises(ValueError):
                register_codex.register(
                    root, '[mcp_servers.local_gemma]\ncommand="x"', "guidance"
                )
            self.assertEqual((root / "config.toml").read_text(), 'model = "original"\n')

    def test_symlink_managed_config_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config.toml").symlink_to(root / "elsewhere")
            with self.assertRaises(ValueError):
                register_codex.register(
                    root, '[mcp_servers.local_gemma]\ncommand="x"', "guidance"
                )
            self.assertTrue((root / "config.toml").is_symlink())


if __name__ == "__main__":
    unittest.main()
