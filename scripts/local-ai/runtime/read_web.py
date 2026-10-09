"""Read one public page and return focused source evidence."""

from mcp.types import ToolAnnotations
from tool_config import mcp, bounded
from web_retrieval import fetch_page
from evidence_selection import extract


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False, openWorldHint=True
    )
)
async def read_web(url: str, question: str, fresh: bool = False) -> dict:
    """Fetch one public HTML/text page for a focused question. Small pages return directly; Gemma selects exact passages from larger pages. Fresh bypasses page cache; check coverage."""

    async def work():
        page = await fetch_page(url, fresh)
        result = await extract([(page["url"], page["text"])], question)
        result["page"] = {key: value for key, value in page.items() if key != "text"}
        result["line_numbers"] = "Lines in extracted page text, not HTML source"
        return result

    return await bounded(work())
