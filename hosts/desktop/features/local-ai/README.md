# Local AI

This module provides:

- Ollama with the declared local models
- Open WebUI on <http://127.0.0.1:8080>
- Qwen Code

Ollama models and Open WebUI data are persisted under `/var/lib/private`.

## Qwen

Run from a project terminal:

```console
qwen
```

## Checks

```console
systemctl status ollama-model-loader
systemctl status open-webui
ollama ps
```
