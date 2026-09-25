# Local AI

These modules provide:

- Ollama with the declared local models
- Open WebUI on <http://127.0.0.1:8081>
- ComfyUI with CUDA acceleration on <http://127.0.0.1:8188>
- Ephemeral ComfyUI Private sessions on <http://127.0.0.1:8189>
- Qwen Code
- Gemma evidence tools for Codex, with local SearXNG search and Chromium fallback

Ollama models and Open WebUI data are persisted under `/var/lib/private`.
ComfyUI data is persisted under `/var/lib/comfyui`. ComfyUI Manager installs
custom nodes and their Python packages into an isolated virtual environment in
that directory.

## ComfyUI

Use ComfyUI Manager's **Install Models** browser to download checkpoints and
supporting models without adding them to the Nix configuration. Pony V7 is not
downloaded automatically. Models, workflows, output, custom nodes, and Manager's
runtime state survive root resets. Manager keeps runtime-installed Python
dependencies inside `/var/lib/comfyui/.venv` rather than changing the system
Python environment.

## Chat models

The Codex MCP integration and post-restart checks are documented in
[`scripts/local-ai/README.md`](../../scripts/local-ai/README.md). Its tools use
Gemma only; Qwen remains available for direct heavy-use sessions.

Gemma 4 12B QAT (`gemma4:12b-it-qat`) is the everyday default with a 16K
context. Qwen3.8 27B (`qwen3.8:27b`) is available for heavier work with a 64K
context. Only one model is loaded at a time; Flash Attention and the Q8 context
cache remain enabled. Active generation still competes with games for GPU time.

After `nixos-rebuild switch --flake .#nixos`, the model loader downloads the
declared models and applies their context settings to the same local tags.
Synchronization removes undeclared models, including the previous Qwen models.
Manual `ollama pull` commands reset the local context customization; restart
`ollama-model-loader` to reapply it.

Open WebUI defaults to Gemma for new chats. If an existing saved preference
overrides that default, select Gemma in the model picker. Existing chats retain
their selections; explicit chat-level context settings can override model defaults.

The **ComfyUI Private** desktop entry starts a separate ComfyUI instance and a
dedicated Firefox private window. It shares the persistent models read-only,
but keeps its database, workflow state, inputs, outputs, logs, and browser
profile under `/run`. Closing the private window stops the service and removes
that session data. Images deliberately downloaded through Firefox remain, but
ComfyUI does not embed their prompt or workflow metadata.

ComfyUI and Ollama share the GPU. If an Ollama model is occupying VRAM, unload
it before generating an image:

```console
ollama stop MODEL
```

## Qwen

Run from a project terminal for Gemma, or select Qwen for heavier work:

```console
qwen
qwen --model qwen3.8:27b
```

## Checks

```console
systemctl status ollama-model-loader
systemctl status open-webui
systemctl status comfyui
systemctl status comfyui-private
ollama ps
```
