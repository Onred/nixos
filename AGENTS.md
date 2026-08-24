# Codex Project Guidance

Personal NixOS configuration for host `nixos`.

## Core Rules

- Do not change `system.stateVersion = "26.05"`.
- Keep flake inputs pinned unless the task is explicitly about updating them.
- Track every local file referenced by the flake; prefer relative repository
  paths over `/etc/nixos` paths.
- Never commit passwords, tokens, private keys, recovery material, or secrets.
- Keep changes small, direct, and aligned with the existing module structure.
- Prefer NixOS/module defaults; add options only for explicit requirements,
  necessary hardware facts, or required integrations.
- Keep comments sparse; explain non-obvious constraints, not ordinary settings.
- In Nix `''...''` strings, escape shell `$` as `''$`. Use `${nixExpr}` only
  for intentional Nix interpolation.
- Prefer `pkgs.writeShellApplication` with `runtimeInputs` for shell tools.

## Layout Notes

- `hardware-configuration.nix` contains generated hardware facts only.
- `configuration.nix` is the single NixOS entrypoint imported by the flake.
- `modules/default.nix` owns the explicit list of enabled capabilities.
- `modules/system.nix` owns baseline system, user, and boot configuration.
- `modules/hardware.nix` owns manually maintained device-specific settings.
- `modules/packages.nix` owns general applications and package lists.
- `modules/impermanence.nix` owns baseline persistence and root reset.
- Feature-specific persistence should live with the feature module.
- Module helper scripts and their documentation live under `scripts/`.
- Complex multi-module capabilities may use a directory under `modules/`.

## Validation

- Prefer validating with:

```console
env XDG_CACHE_HOME=/tmp/nix-cache nix build .#nixosConfigurations.nixos.config.system.build.toplevel --no-link
```

- Tell the user when a change still needs `nixos-rebuild switch`, `boot`, or a
  reboot to take effect.
