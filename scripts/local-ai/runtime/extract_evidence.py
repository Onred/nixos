"""Extract evidence from explicitly allowed local files."""

import os
from pathlib import Path
import stat
from mcp.types import ToolAnnotations
import tool_config
from tool_config import mcp, MAX_FILE, BLOCKED_PARTS, bounded
from evidence_selection import extract


def file_text(name: str) -> tuple[str, str]:
    requested = Path(name)
    if not requested.is_absolute():
        raise ValueError("File paths must be absolute")
    path = requested.resolve(strict=True)
    if not any(path.is_relative_to(root) for root in tool_config.ROOTS):
        raise ValueError("File is outside configured project roots")
    if (
        BLOCKED_PARTS.intersection(path.parts)
        or path.name.startswith(".env")
        or path.suffix in {".pem", ".key"}
    ):
        raise ValueError("Credential/configuration paths are excluded")
    # Nonblocking open also avoids hanging on a FIFO if a file changes after resolution.
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("Only regular files are supported")
        data = stream.read(MAX_FILE + 1)
    if len(data) > MAX_FILE:
        raise ValueError(
            "File exceeds 512 KB; filter it into a smaller project file first"
        )
    if b"\0" in data:
        raise ValueError("Binary files are not supported")
    return str(path), data.decode("utf-8")


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False, openWorldHint=False
    )
)
async def extract_evidence(paths: list[str], question: str) -> dict:
    """Read 1–5 explicit files in allowed roots. Small inputs return directly; Gemma selects exact passages from larger inputs. Includes line/column references and partial coverage."""

    async def work():
        if not 1 <= len(paths) <= 5:
            raise ValueError("Supply 1–5 explicit file paths")
        return await extract([file_text(path) for path in paths], question)

    return await bounded(work())
