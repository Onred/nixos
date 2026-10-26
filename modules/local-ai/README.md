# Local AI

The configuration uses three ordinary modules, without custom runtime scripts:

- `strata.nix`: the official Strata CUDA container, started by llama-swap when a request arrives at `127.0.0.1:8082`.
- `opencode.nix`: OpenCode's local model and the official Brave Search MCP server.
- `dictation.nix`: CPU Whisper dictation in your Plasma session.

`default.nix` imports those modules. Edit `models.nix` to change the Qwen selection/context/output limit or the pinned Whisper download. OpenCode's input budget is calculated from context minus output. Qwen's family, quantization and server name remain explicit; Strata supplies the corresponding model download metadata. Whisper is pinned by revision and checksum.

## Model and memory

Qwen3.8 Flash Next **IQ3_XXS**, 65,536-token context, one concurrent request. OpenCode reserves 16,384 tokens for output and advertises 49,152 tokens of input.

`vram-reserve-mib=4564` asks Strata to leave 4,564 MiB free on the 24,564 MiB card, targeting at most approximately 20,000 MiB for inference. This is an engine allocation policy, not a driver-enforced VRAM quota; other GPU users and runtime overhead affect the actual allocation.

`resident-experts=true` keeps the experts not resident on the GPU in RAM rather than retaining a full duplicate. The container has a **36 GiB RAM limit and no additional swap allowance**, leaving roughly 12 GiB for the desktop after reserving another 12 GiB for the VM. The limit protects host memory, but is not proof the model fits: confirm peak usage with your real workload. If it runs out of memory, try a 32K context first and update OpenCode's limits to match.

llama-swap starts the container on demand and requests shutdown after **120 seconds without active requests**. Shutdown can take additional time; the container has a 120-second grace period. Model files remain in `/var/lib/strata` for reuse.

Strata follows `latest-cuda13` with `--pull=always`: each container start checks the registry for a newer image. Brave MCP follows npm's `@latest` when its process starts. Neither updates a running process. These applications can change independently of a NixOS rebuild, and rolling back NixOS does not pin them to an earlier release. Strata startup requires registry access even when an image is cached. Nix-managed packages still update only when you update the flake inputs and rebuild; no automatic system upgrade is configured.

The first request pulls the image and downloads/prepares the selected model; allow roughly **120 GB of disk space** and a potentially long first start. Model loading on later requests is still a cold start, not instantaneous.

The API binds only to localhost. `strata-local-only` is a public local placeholder shared between the client and container, not a secret suitable for remote access. Brave searches leave the machine; inference and dictation are local.

## First use

1. Add the new files to Git before a Git-based flake rebuild. Build and switch normally, then log out and in so the session environment and `ydotool` group take effect.
2. Obtain a [Brave Search API key](https://api-dashboard.search.brave.com/). Create `~/.config/opencode` with mode `0700`, put the key alone in `~/.config/opencode/brave-api-key`, and set that file to mode `0600`. Do not put the key in this repository or in a Nix string.
3. Run `opencode`. The model is `strata/qwen-flash`; its first request triggers Strata startup. Brave MCP is resolved by `npx` using `@latest`. Brave will report a connection error until its key file exists; restart OpenCode after creating it.
4. In Plasma's shortcut settings, add/select the **Dictation** application and assign a shortcut such as **Meta+Alt+Space**. If adding a command directly, use `voxtype record toggle`. Focus the OpenCode prompt, press once to record, and press again to transcribe and type. Review the text before pressing Enter.

Whisper's multilingual `small` model is fetched during the Nix build. It uses four CPU threads, loads on demand, and unloads after transcription. Voxtype uses your default microphone. If typing fails, it falls back to the clipboard. It does not require membership in the keyboard-reading `input` group; `ydotool` supplies virtual keyboard output.

## Checks

```console
systemctl status llama-swap
systemctl --user status voxtype
opencode mcp list
curl http://127.0.0.1:8082/v1/models
sudo docker stats strata-qwen
nvidia-smi
```

The model list alone does not load the model. After a real prompt finishes, leave it idle and confirm that `sudo docker ps` no longer lists `strata-qwen`. Check RAM/VRAM with the VM running before relying on the chosen budget.

The NixOS system build, llama-swap configuration validation, OpenCode configuration parsing, and Voxtype configuration parsing passed. Live Strata inference, idle shutdown, microphone input, and Brave search still need runtime checks after activation; privileged Docker access and the Brave key were not available during configuration.

Restic currently includes `/persist`, so the persisted model/container files will also enter backups. No backup exclusions were added as part of this setup.

References: [Strata containers](https://github.com/Niko1221/Strata/blob/v0.2.3/docs/DOCKER.md), [Strata memory modes](https://github.com/Niko1221/Strata/blob/main/docs/MODELS.md), [llama-swap configuration](https://github.com/mostlygeek/llama-swap/blob/main/docs/config.example.yaml), [OpenCode MCP](https://opencode.ai/docs/mcp-servers/), [Brave MCP](https://github.com/brave/brave-search-mcp-server), [Voxtype](https://github.com/peteonrails/voxtype/blob/v1.1.0/docs/USER_MANUAL.md).
