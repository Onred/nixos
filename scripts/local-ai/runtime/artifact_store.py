"""Private bounded artifacts and deterministic process capture."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import tempfile
import time
import uuid

ARTIFACTS = (
    Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
    / "local-gemma"
    / "artifacts"
)
SCAN_BYTES = 8 * 1024 * 1024
BLOCKED = {".git", ".ssh", ".gnupg", ".codex", ".aws", "secrets"}
STREAMS = {"stdout", "stderr"}


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".pending-")
    try:
        with os.fdopen(fd, "w") as file:
            json.dump(value, file, ensure_ascii=False)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def new_artifact(kind):
    ARTIFACTS.mkdir(mode=0o700, parents=True, exist_ok=True)
    ident = uuid.uuid4().hex
    directory = ARTIFACTS / ident
    directory.mkdir(mode=0o700)
    return ident, directory


def artifact_dir(ident):
    if not re.fullmatch(r"[0-9a-f]{32}", ident):
        raise ValueError("Invalid artifact ID")
    directory = ARTIFACTS / ident
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Unknown artifact")
    return directory


def read_bytes(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as file:
        if not stat.S_ISREG(os.fstat(file.fileno()).st_mode):
            raise ValueError("Only regular files are supported")
        data = file.read(limit + 1)
    return data[:limit], len(data) > limit


def manifest(ident):
    data, partial = read_bytes(artifact_dir(ident) / "manifest.json", 128_000)
    if partial:
        raise ValueError("Oversized artifact manifest")
    return json.loads(data)


def allowed_path(name, roots, directory=False):
    requested = Path(name)
    if not requested.is_absolute():
        raise ValueError("Use an absolute project path")
    path = requested.resolve(strict=True)
    if not any(path.is_relative_to(root) for root in roots):
        raise ValueError("Path is outside configured project roots")
    if (
        BLOCKED.intersection(path.parts)
        or path.name.startswith(".env")
        or path.suffix in {".pem", ".key"}
    ):
        raise ValueError("Credential/configuration paths are excluded")
    if directory and not path.is_dir():
        raise ValueError("Expected a project directory")
    return path


def capture(
    argv, cwd, timeout=120, max_bytes=32 * 1024 * 1024, kind="command", report_path=None
):
    """Called by the shell wrapper, or with fixed read-only rg arguments by MCP."""
    if not argv or len(argv) > 256 or sum(len(x) for x in argv) > 32_000:
        raise ValueError("Supply a bounded, nonempty command argument list")
    if not 0 < timeout <= 86400 or not 1024 <= max_bytes <= 256 * 1024 * 1024:
        raise ValueError("Invalid timeout or output limit")
    cwd = Path(cwd).resolve(strict=True)
    ident, directory = new_artifact(kind)
    start = time.monotonic()
    record = {
        "id": ident,
        "kind": kind,
        "state": "running",
        "argv": argv,
        "cwd": str(cwd),
        "started_at": timestamp(),
        "exit_code": None,
        "signal": None,
        "timed_out": False,
        "output_limit_reached": False,
        "capture_complete": False,
        "duration_seconds": None,
        "streams": {},
        "report_requested": report_path,
    }
    write_json(directory / "manifest.json", record)
    process = None
    handles = {}
    counts = {s: 0 for s in STREAMS}
    digests = {s: hashlib.sha256() for s in STREAMS}
    selector = selectors.DefaultSelector()
    stop_at = None
    killed = False
    try:
        for stream in STREAMS:
            handles[stream] = (directory / stream).open("xb")
            os.chmod(directory / stream, 0o600)
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        for stream in STREAMS:
            pipe = getattr(process, stream)
            os.set_blocking(pipe.fileno(), False)
            selector.register(pipe, selectors.EVENT_READ, stream)
        while selector.get_map() or process.poll() is None:
            current = time.monotonic()
            if stop_at is None and current - start >= timeout:
                record["timed_out"] = True
                stop_at = current
            if stop_at is not None:
                if not killed:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    killed = True
                if current - stop_at > 2:
                    break
            for key, _ in selector.select(0.05):
                data = os.read(key.fileobj.fileno(), 65536)
                if not data:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                room = max_bytes - sum(counts.values())
                saved = data[:room]
                handles[key.data].write(saved)
                digests[key.data].update(saved)
                counts[key.data] += len(saved)
                if len(saved) < len(data):
                    record["output_limit_reached"] = True
                    if stop_at is None:
                        stop_at = current
        code = process.wait(timeout=3)
        record["exit_code"] = code if code >= 0 else None
        record["signal"] = -code if code < 0 else None
        record["capture_complete"] = (
            not record["timed_out"]
            and not record["output_limit_reached"]
            and not selector.get_map()
        )
    except (OSError, subprocess.SubprocessError, KeyboardInterrupt) as error:
        record["capture_error"] = str(error)[:500] or type(error).__name__
    finally:
        if process is not None:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
            for stream in STREAMS:
                getattr(process, stream).close()
        selector.close()
        for file in handles.values():
            file.close()
        record["state"] = "finished"
        record["finished_at"] = timestamp()
        record["duration_seconds"] = round(time.monotonic() - start, 3)
        record["streams"] = {
            s: {"bytes": counts[s], "sha256": digests[s].hexdigest()} for s in STREAMS
        }
        # Copy an explicitly requested report into this run; never infer that an old file belongs to it.
        if report_path:
            try:
                path = Path(report_path)
                if not path.is_absolute():
                    path = cwd / path
                data, partial = read_bytes(path, SCAN_BYTES)
                if partial:
                    raise ValueError("Validation report exceeds 8 MiB")
                (directory / "validation").write_bytes(data)
                os.chmod(directory / "validation", 0o600)
                record["report"] = {
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "source": str(path),
                    "freshness": "caller_must_verify",
                }
            except (OSError, ValueError) as error:
                record["report_error"] = str(error)[:500]
        write_json(directory / "manifest.json", record)
    return record


def process_facts(record):
    result = {key: record.get(key) for key in ("id", "exit_code", "capture_complete")}
    for key in (
        "signal",
        "timed_out",
        "output_limit_reached",
        "capture_error",
        "report_error",
    ):
        if record.get(key):
            result[key] = record[key]
    if record.get("state") != "finished":
        result["state"] = record.get("state")
    return result


def stream_text(ident, stream):
    if stream not in STREAMS | {"validation"}:
        raise ValueError("Use stdout, stderr, or validation")
    data, partial = read_bytes(artifact_dir(ident) / stream, SCAN_BYTES)
    return data.decode("utf-8", errors="replace"), partial
