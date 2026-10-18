# Strata

`modules/strata.nix` is independent of the existing local-AI modules. It uses
Strata's official Dockerfile with NVIDIA GPU access and starts on demand.
The first start builds the engine for the RTX 4090, downloads and prepares
Qwen3.8-Flash-Next IQ2_XS, then serves Strata's own chat interface and APIs.
Allow substantial time and SSD space for the image, model files and prepared
weights. Later starts reuse them from persisted storage.

After applying the NixOS configuration, free the GPU from any loaded Ollama
model before testing Strata. Stopping Ollama temporarily is one option:

```console
sudo systemctl stop ollama
sudo systemctl start --no-block docker-strata
journalctl -fu strata-image -u docker-strata
```

Open <http://127.0.0.1:8082> when the model finishes loading. The
OpenAI-compatible base URL is `http://127.0.0.1:8082/v1`; use `/v1/models` to
check the model ID. The endpoint is local only. This does not change Open WebUI,
Qwen Code, or the existing evidence tools.

For terminal work, run `codex-local` from the project directory after applying
the configuration. Plain `codex` continues using its normal configuration.
The local launcher supplies matching model metadata, the real 32K context
limit, earlier conversation compaction, and conventional terminal/editing
tools. It excludes apps, plugins, subagents and the inherited Gemma/OpenAI-docs
MCP integrations to keep the first request within that limit. Global and
project `AGENTS.md` guidance still applies. The metadata catalog is generated
from the same packaged CLI used by the launcher.

```console
cd ~/nixos
codex-local
```

```console
sudo systemctl stop docker-strata
sudo systemctl start ollama
```

To try a larger quantization later, change `environment.MODEL` in the module to
`IQ3_XXS` or `IQ3_S`, rebuild, and restart `docker-strata`. Each model has its own
prepared files; previous models remain on disk. Start with IQ2_XS to leave room
for the desktop and other applications. The upstream defaults provide 32K
context and disable vision; the image includes the vision encoder for later
use. Changing context or vision for an already prepared model also requires
upstream's `REINSTALL=1` setup pass; see the installation guide.

The Strata version and source hash live together in the module. Updating them
builds a new image on its next start. Model data is in `/var/lib/strata` and
Docker's image/cache storage is persisted under `/var/lib/docker` and
`/var/lib/containerd`.

Upstream: [Strata](https://github.com/Niko1221/Strata),
[installation](https://github.com/Niko1221/Strata/blob/main/docs/INSTALL.md),
[model guidance](https://github.com/Niko1221/Strata/blob/main/docs/MODELS.md).
