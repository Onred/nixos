# Local AI

This module provides:

- Ollama with the declared local models
- Qwen Code
- A local web-search MCP command
- Optional Cline integration in `cline.nix`

Ollama models are persisted under `/var/lib/private/ollama`.

## Qwen

Run from a project terminal:

```console
qwen
```

## Cline

Install the Cline extension in VS Code, then import `modules/local-ai/cline.nix`
from `configuration.nix`.

Suggested settings:

- Provider: Ollama
- Base URL: `http://localhost:11434`
- Model: `qwen3.6:27b`
- Enable: Use Compact Prompt

## Checks

```console
systemctl status ollama-model-loader
ollama ps
```
