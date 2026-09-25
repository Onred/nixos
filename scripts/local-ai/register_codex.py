"""Merge the Nix-owned MCP entry and guidance without replacing user settings."""

import argparse
import os
from pathlib import Path
import tempfile

import tomlkit

START = "<!-- BEGIN NIX LOCAL GEMMA -->"
END = "<!-- END NIX LOCAL GEMMA -->"


def write_updated(path: Path, text: str) -> None:
    if path.is_symlink():
        raise ValueError(f"Refusing to replace symlink: {path}")
    old = path.read_text() if path.exists() else None
    if old == text:
        return
    if old is not None:
        backup = path.with_name(path.name + ".before-local-gemma")
        try:
            fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, "w") as stream:
                stream.write(old)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".local-gemma-")
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def register(directory: Path, config: str, guidance: str) -> None:
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    config_path = directory / "config.toml"
    agents_path = directory / "AGENTS.md"
    if config_path.is_symlink() or agents_path.is_symlink():
        raise ValueError("Codex configuration is symlink-managed; merge local_gemma there instead")
    current = tomlkit.parse(config_path.read_text() if config_path.exists() else "")
    managed = tomlkit.parse(config)
    if "mcp_servers" not in current:
        current["mcp_servers"] = tomlkit.table()
    current["mcp_servers"]["local_gemma"] = managed["mcp_servers"]["local_gemma"]

    instructions = agents_path.read_text() if agents_path.exists() else ""
    block = f"{START}\n{guidance.strip()}\n{END}"
    if START in instructions or END in instructions:
        if instructions.count(START) != 1 or instructions.count(END) != 1:
            raise ValueError("Malformed local Gemma guidance markers")
        begin, finish = instructions.index(START), instructions.index(END)
        if finish < begin:
            raise ValueError("Reversed local Gemma guidance markers")
        instructions = instructions[:begin] + block + instructions[finish + len(END):]
    else:
        instructions = instructions.rstrip() + "\n\n" + block + "\n"
    write_updated(config_path, tomlkit.dumps(current))
    write_updated(agents_path, instructions)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--guidance", type=Path, required=True)
    args = parser.parse_args()
    register(args.directory, args.config.read_text(), args.guidance.read_text())
