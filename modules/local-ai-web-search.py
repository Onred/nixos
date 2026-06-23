import asyncio
import logging
import re
from html.parser import HTMLParser
from urllib.parse import urlencode, urlparse

import httpx

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING)

mcp = FastMCP("Local web search")


class PageTextParser(HTMLParser):
    block_tags = {
        "article",
        "aside",
        "blockquote",
        "br",
        "dd",
        "div",
        "dl",
        "dt",
        "figcaption",
        "figure",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "td",
        "th",
        "tr",
        "ul",
    }
    ignored_tags = {"script", "style", "svg", "template"}

    def __init__(self):
        super().__init__()
        self.chunks = []
        self.ignored_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.ignored_tags:
            self.ignored_depth += 1
        elif not self.ignored_depth and tag in self.block_tags:
            self.chunks.append("\n")

    def handle_endtag(self, tag):
        if tag in self.ignored_tags and self.ignored_depth:
            self.ignored_depth -= 1
        elif not self.ignored_depth and tag in self.block_tags:
            self.chunks.append("\n")

    def handle_data(self, data):
        if not self.ignored_depth:
            self.chunks.append(data)

    def text(self):
        text = "".join(self.chunks)
        text = re.sub(r"[ \t]+", " ", text)
        return re.sub(r"\n\s*\n+", "\n\n", text).strip()


@mcp.tool()
async def local_web_search(query: str, max_results: int = 8) -> str:
    """Search the web through the local SearXNG instance."""
    limit = max(1, min(max_results, 20))
    url = "http://127.0.0.1:8080/search?" + urlencode(
        {"q": query, "format": "json"}
    )

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()
            results = response.json().get("results", [])[:limit]
    except Exception as exc:
        return f"Local web search failed: {exc}"

    if not results:
        return "No results found."

    return "\n\n".join(
        f'{index}. {result.get("title", "Untitled")}\n'
        f'{result.get("url", "")}\n'
        f'{result.get("content", "")}'
        for index, result in enumerate(results, 1)
    )


@mcp.tool()
async def fetch_web_page(url: str, max_characters: int = 20000) -> str:
    """Read an HTTP(S) documentation or web page as plain text."""
    parsed_url = urlparse(url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        return "Only complete HTTP(S) URLs are supported."

    character_limit = max(4000, min(max_characters, 40000))

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (local-web-search/1.0)"},
                follow_redirects=True,
            )
            content_type = response.headers.get("content-type", "")
            charset = (
                response.charset
                if hasattr(response, "charset")
                else _extract_charset(content_type)
                or "utf-8"
            )
            final_url = str(response.url)
            body = response.read()[:2000000]
    except Exception as exc:
        return f"Page fetch failed: {exc}"

    if not (
        content_type.startswith("text/")
        or content_type in {"application/json", "application/xhtml+xml"}
    ):
        return f"Unsupported page content type: {content_type}"

    download_truncated = len(body) > 2000000
    decoded = body.decode(charset, errors="replace")
    if content_type in {"text/html", "application/xhtml+xml"}:
        parser = PageTextParser()
        parser.feed(decoded)
        text = parser.text()
    else:
        text = decoded.strip()

    text_truncated = len(text) > character_limit
    text = text[:character_limit]
    if len(text) < 300:
        return (
            f"Source: {final_url}\n\n"
            "This page returned very little readable text. It may be a JavaScript app, "
            "an empty page, or a page that blocks simple fetches. Do not retry this "
            "same URL; use another search result or a direct documentation page."
            f"\n\n{text}"
        )
    truncation_note = (
        "\n\n[Content truncated.]" if download_truncated or text_truncated else ""
    )
    return f"Source: {final_url}\n\n{text}{truncation_note}"


def _extract_charset(content_type: str) -> str | None:
    for part in content_type.split(";"):
        part = part.strip()
        if part.lower().startswith("charset="):
            return part.split("=", 1)[1].strip().strip('"')
    return None


if __name__ == "__main__":
    asyncio.run(mcp.run(transport="stdio"))
