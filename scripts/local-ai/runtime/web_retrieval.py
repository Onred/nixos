"""Bounded public-page fetching with destination checks and one browser fallback."""

import asyncio
import hashlib
import ipaddress
import os
import socket
from urllib.parse import urljoin, urlsplit
import httpx
from playwright.async_api import async_playwright
import trafilatura
from tool_config import (
    MAX_FETCH,
    MAX_TEXT,
    USER_AGENT,
    CHALLENGES,
    cache_get,
    cache_put,
    exclusive,
    now,
)


def public_url(url: str) -> str:
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Only public HTTP(S) URLs without credentials are allowed")
    if parsed.port not in {None, 80, 443}:
        raise ValueError("Only standard web ports are allowed")
    addresses = socket.getaddrinfo(
        parsed.hostname,
        parsed.port or (443 if parsed.scheme == "https" else 80),
        type=socket.SOCK_STREAM,
    )
    if not addresses or any(
        not ipaddress.ip_address(item[4][0]).is_global for item in addresses
    ):
        raise ValueError(
            "Local, private, and reserved network destinations are not allowed"
        )
    return url


async def check_url(url: str) -> str:
    return await asyncio.to_thread(public_url, url)


async def http_page(url: str) -> tuple[str, str, str]:
    async with httpx.AsyncClient(
        timeout=15, trust_env=False, headers={"User-Agent": USER_AGENT}
    ) as client:
        for _ in range(6):
            await check_url(url)
            async with client.stream("GET", url) as response:
                if response.is_redirect:
                    url = urljoin(url, response.headers["location"])
                    continue
                response.raise_for_status()
                mime = response.headers.get("content-type", "").lower()
                if not any(
                    value in mime
                    for value in ("text/html", "text/plain", "application/xhtml+xml")
                ):
                    raise ValueError("Only HTML and plain-text pages are supported")
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > MAX_FETCH:
                        raise ValueError("Page exceeds the 2 MB retrieval limit")
                return (
                    url,
                    data.decode(response.encoding or "utf-8", errors="replace"),
                    mime,
                )
    raise ValueError("Too many redirects")


async def browser_page(url: str) -> tuple[str, str]:
    executable = os.environ.get("LOCAL_GEMMA_BROWSER")
    if not executable:
        raise ValueError("Browser fallback is unavailable")
    await check_url(url)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            executable_path=executable, headless=True, chromium_sandbox=True
        )
        try:
            context = await browser.new_context(
                accept_downloads=False, service_workers="block"
            )
            requests = 0

            async def route_request(route):
                nonlocal requests
                requests += 1
                try:
                    if (
                        requests > 60
                        or route.request.method not in {"GET", "HEAD"}
                        or route.request.resource_type
                        in {"image", "media", "font", "websocket"}
                    ):
                        await route.abort()
                        return
                    await check_url(route.request.url)
                    await route.continue_()
                except (ValueError, OSError):
                    await route.abort()

            await context.route("**/*", route_request)
            page = await context.new_page()
            response = await page.goto(
                url, wait_until="domcontentloaded", timeout=20000
            )
            if response and response.status >= 400:
                raise ValueError(f"Browser access denied (HTTP {response.status})")
            await page.wait_for_timeout(1500)
            await check_url(page.url)
            content = await page.content()
            if len(content.encode()) > MAX_FETCH:
                raise ValueError("Rendered page exceeds the 2 MB limit")
            return page.url, content
        finally:
            await browser.close()


def readable(content: str, mime: str = "text/html") -> str:
    if any(marker in content[:20000].lower() for marker in CHALLENGES):
        raise ValueError(
            "Page is an access challenge; use another source or open it manually"
        )
    text = (
        content
        if "text/plain" in mime
        else trafilatura.extract(content, include_comments=False, include_tables=True)
    )
    if not text or len(text.strip()) < 100:
        raise ValueError("No substantive page text was available")
    return text


async def fetch_page(url: str, fresh: bool) -> dict:
    await check_url(url)
    key = "page:" + hashlib.sha256(url.encode()).hexdigest()
    cached = None if fresh else cache_get(key, 900)
    if cached:
        return {**cached, "cached": True}
    async with exclusive("web"):
        # Serialize retrievals across Codex sessions and avoid bursts to upstream sites.
        await asyncio.sleep(1)
        method = "http"
        try:
            final_url, content, mime = await http_page(url)
            text = readable(content, mime)
        except httpx.HTTPStatusError as error:
            if error.response.status_code in {401, 429}:
                raise ValueError(
                    f"Site denied access (HTTP {error.response.status_code}); do not retry automatically"
                ) from error
            if error.response.status_code != 403:
                raise
            method = "browser"
            final_url, content = await browser_page(url)
            text = readable(content)
        except ValueError as error:
            if not any(
                reason in str(error)
                for reason in ("No substantive", "access challenge")
            ):
                raise
            method = "browser"
            final_url, content = await browser_page(url)
            text = readable(content)
    data = {
        "url": final_url,
        "text": text[:MAX_TEXT],
        "truncated": len(text) > MAX_TEXT,
        "retrieved_at": now(),
        "method": method,
    }
    cache_put(key, data)
    return {**data, "cached": False}
