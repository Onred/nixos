# Local AI

This module provides:

- Ollama with the declared local models
- Qwen Code
- A local web-search MCP command

Ollama models are persisted under `/var/lib/private/ollama`.

## Qwen

Run from a project terminal:

```console
qwen
```

## Checks

```console
systemctl status ollama-model-loader
ollama ps
```
