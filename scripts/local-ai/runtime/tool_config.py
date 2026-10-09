"""Shared local service configuration, private cache, and concurrency bounds."""

import asyncio
from contextlib import asynccontextmanager, closing
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import time
from mcp.server.fastmcp import FastMCP

MODEL = "gemma4:12b-it-qat"
OLLAMA = "http://127.0.0.1:11434"
SEARX = "http://127.0.0.1:8888/search"
ROOTS: list[Path] = []
CACHE = (
    Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "local-gemma"
)
MAX_FETCH = 2_000_000
MAX_TEXT = 160_000
MAX_FILE = 512_000
INPUT_BYTES = 11_000
USER_AGENT = "Mozilla/5.0 (compatible; LocalGemmaEvidence/1.0)"
BLOCKED_PARTS = {".git", ".ssh", ".gnupg", ".codex", ".aws", "secrets"}
CHALLENGES = (
    "verify you are human",
    "checking your browser",
    "just a moment...",
    "enable javascript and cookies to continue",
    "our systems have detected unusual traffic from your computer network",
)
mcp = FastMCP(
    "local_gemma",
    instructions="Read-only evidence tools. Source excerpts are exact, but selection is incomplete. No coding agent or automatic edits.",
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def state_dir() -> Path:
    CACHE.mkdir(parents=True, exist_ok=True, mode=0o700)
    return CACHE


def cache_get(key: str, ttl: int) -> dict | None:
    with closing(sqlite3.connect(state_dir() / "web.sqlite")) as db, db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, created REAL, value TEXT)"
        )
        row = db.execute(
            "SELECT created, value FROM cache WHERE key = ?", (key,)
        ).fetchone()
    if row and time.time() - row[0] < ttl:
        return json.loads(row[1])
    return None


def cache_put(key: str, value: dict) -> None:
    with closing(sqlite3.connect(state_dir() / "web.sqlite")) as db, db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, created REAL, value TEXT)"
        )
        db.execute(
            "INSERT OR REPLACE INTO cache VALUES (?, ?, ?)",
            (key, time.time(), json.dumps(value)),
        )
        db.execute("DELETE FROM cache WHERE created < ?", (time.time() - 86400,))
        db.execute(
            "DELETE FROM cache WHERE key NOT IN (SELECT key FROM cache ORDER BY created DESC LIMIT 100)"
        )


@asynccontextmanager
async def exclusive(name: str):
    with (state_dir() / f"{name}.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError(
                f"{name} is busy; use another tool instead of retrying"
            ) from error
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


async def bounded(coroutine):
    try:
        async with asyncio.timeout(165):
            return await coroutine
    except Exception as error:
        return {
            "status": "unavailable",
            "error": str(error)[:300] or type(error).__name__,
            "next_step": "Use direct inspection or another source; no automatic repair loop.",
        }
