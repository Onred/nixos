import json
import re
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from mcp.server.fastmcp import FastMCP

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
def local_web_search(query: str, max_results: int = 8) -> str:
    """Search the web through the local SearXNG instance."""
    limit = max(1, min(max_results, 20))
    url = "http://127.0.0.1:8080/search?" + urlencode(
        {"q": query, "format": "json"}
    )

    try:
        with urlopen(url, timeout=30) as response:
            results = json.load(response).get("results", [])[:limit]
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        return f"Local web search failed: {error}"

    if not results:
        return "No results found."

    return "\n\n".join(
        f'{index}. {result.get("title", "Untitled")}\n'
        f'{result.get("url", "")}\n'
        f'{result.get("content", "")}'
        for index, result in enumerate(results, 1)
    )


@mcp.tool()
def fetch_web_page(url: str, max_characters: int = 20000) -> str:
    """Read an HTTP(S) documentation or web page as plain text."""
    parsed_url = urlparse(url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        return "Only complete HTTP(S) URLs are supported."

    character_limit = max(4000, min(max_characters, 40000))
    request = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (local-web-search/1.0)"},
    )

    try:
        with urlopen(request, timeout=30) as response:
            content_type = response.headers.get_content_type()
            charset = response.headers.get_content_charset() or "utf-8"
            final_url = response.geturl()
            body = response.read(2000001)
    except (HTTPError, URLError, TimeoutError, ValueError) as error:
        return f"Page fetch failed: {error}"

    if not (
        content_type.startswith("text/")
        or content_type in {"application/json", "application/xhtml+xml"}
    ):
        return f"Unsupported page content type: {content_type}"

    download_truncated = len(body) > 2000000
    decoded = body[:2000000].decode(charset, errors="replace")
    if content_type in {"text/html", "application/xhtml+xml"}:
        parser = PageTextParser()
        parser.feed(decoded)
        text = parser.text()
    else:
        text = decoded.strip()

    text_truncated = len(text) > character_limit
    text = text[:character_limit]
    truncation_note = (
        "\n\n[Content truncated.]" if download_truncated or text_truncated else ""
    )
    return f"Source: {final_url}\n\n{text}{truncation_note}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
