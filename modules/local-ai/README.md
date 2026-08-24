# Local AI

These modules provide:

- Ollama with the declared local models
- Open WebUI on <http://127.0.0.1:8080>
- ComfyUI with CUDA acceleration on <http://127.0.0.1:8188>
- Ephemeral ComfyUI Private sessions on <http://127.0.0.1:8189>
- Qwen Code

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

Run from a project terminal:

```console
qwen
```

## Checks

```console
systemctl status ollama-model-loader
systemctl status open-webui
systemctl status comfyui
systemctl status comfyui-private
ollama ps
```
