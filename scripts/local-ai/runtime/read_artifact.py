"""Read saved evidence by lines, literal filter, or byte offset for long lines."""

import asyncio
import os
import stat
from mcp.types import ToolAnnotations
from tool_config import mcp, bounded
from artifact_store import artifact_dir


def read_slice(ident, stream, start=1, lines=40, byte_offset=None, contains=""):
    if stream not in {"stdout", "stderr", "validation", "matches"}:
        raise ValueError("Unknown stream")
    if start < 1 or not 1 <= lines <= 100 or len(contains) > 500:
        raise ValueError("Invalid slice bounds")
    if byte_offset is not None and byte_offset < 0:
        raise ValueError("Invalid byte offset")
    fd = os.open(
        artifact_dir(ident) / stream, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    )
    with os.fdopen(fd, "rb") as file:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("Only regular files are supported")
        if byte_offset is not None:
            file.seek(byte_offset)
            data = file.read(8000)
            end = file.tell()
            return {
                "id": ident,
                "stream": stream,
                "byte_offset": byte_offset,
                "text": data.decode("utf-8", errors="replace"),
                "next_byte": end,
                "eof": end >= os.fstat(fd).st_size,
            }
        selected = []
        used = 0
        number = 0
        clipped = False
        while file.tell() < 256 * 1024 * 1024:
            offset = file.tell()
            raw = file.readline(65537)
            if not raw:
                break
            number += 1
            # Drain the remainder without splitting a long line into fake source lines.
            if not raw.endswith(b"\n") and len(raw) > 65536:
                while file.tell() < 256 * 1024 * 1024:
                    more = file.readline(65537)
                    if not more or more.endswith(b"\n"):
                        break
            if number < start:
                continue
            if (
                contains
                and contains.casefold()
                not in raw.decode("utf-8", errors="replace").casefold()
            ):
                continue
            take = min(2000, 8000 - used)
            data = raw[:take]
            value = data.decode("utf-8", errors="replace").rstrip("\n")
            truncated = len(raw) > take
            selected.append(
                {
                    "line": number,
                    "text": value,
                    **(
                        {
                            "clipped": True,
                            "byte_offset": offset,
                            "next_byte": offset + len(data),
                        }
                        if truncated
                        else {}
                    ),
                }
            )
            used += len(data)
            clipped |= truncated
            if len(selected) >= lines or used >= 8000:
                break
        return {
            "id": ident,
            "stream": stream,
            "lines": selected,
            "next_line": number + 1,
            "clipped": clipped,
            "next_byte": file.tell(),
            "eof": file.tell() >= os.fstat(fd).st_size,
        }


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False, openWorldHint=False
    )
)
async def read_artifact(
    run_id: str,
    stream: str = "stdout",
    start_line: int = 1,
    line_count: int = 40,
    byte_offset: int | None = None,
    contains: str = "",
) -> dict:
    """Read saved output: up to 100 lines/8 KB. Optional literal contains filter. For clipped long lines, use returned next_byte as byte_offset; no command rerun."""
    return await bounded(
        asyncio.to_thread(
            read_slice, run_id, stream, start_line, line_count, byte_offset, contains
        )
    )
