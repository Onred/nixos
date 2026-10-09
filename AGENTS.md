# Codex Project Guidance

Personal NixOS configuration for host `nixos`.

## Core Rules

- Keep configured flake inputs current. `flake.lock` records the resolved
  snapshot; the user's routine update script advances it automatically.
- The user prefers a stable NixOS release channel with the newest available
  package variants within that channel, such as `pkgs.linuxPackages_latest`
  and NVIDIA's `latest` branch from the main package set. Choosing a stable
  channel does not imply a preference for LTS packages or older driver branches.
- Answer package version, branch resolution, and default questions assuming
  the configured inputs have advanced to their latest available snapshots.
  Use a refreshed candidate lock for read-only checks. State the revision
  checked and disclose any fallback to an older lock. Use historical snapshots
  only when the user asks about them.
- Inspect GUI package versions through store paths or package metadata instead
  of launching GUI executables for version checks. Sandboxed GUI processes can
  abort and trigger desktop crash notifications.
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
- Do not change `system.stateVersion` unless doing a major channel upgrade.
  It is ok to advance this version during a channel migration as long as
  it does not cause breakage.

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

## Git Workflow

- **`sync git`** is the user's short trigger for this full workflow: checkpoint
  all current configuration work, push `dev`, use the GitHub Action to preserve
  its history, squash into `master`, push `master`, and realign `dev`.
  Equivalent requests to commit, checkpoint, sync branches, squash, or prepare
  the repository for the next task also mean this workflow. This is standing
  authorization for its Git operations; do not ask for confirmation again.
- Work on `dev`. Review the worktree before staging; commit the requested
  changes and preserve unrelated work. When asked to checkpoint all current
  configuration work, include all relevant tracked and untracked files.
- Use clear, specific commit messages that explain the change and its purpose.
  Split independent changes into meaningful commits when useful; keep related
  changes together. The final `master` squash message should describe the
  combined result and include a body when needed to explain scope or validation.
- Fetch the remote branch tips before updating them. Do not overwrite remote
  changes or rewrite `master`.
- Keep `Archive dev history` at `.github/workflows/archive-dev-history.yml`;
  GitHub Actions does not discover workflow files in a root `workflows/` folder.
- Before squash-merging or otherwise rewriting `dev`, record its exact tip with
  `tip=$(git rev-parse dev)`, push `dev`, and wait for the `Archive dev history`
  GitHub Actions workflow.
- Explicitly fetch the remote archive into `origin/dev-history` before
  checking: `git fetch origin dev-history:refs/remotes/origin/dev-history`.
  Verify it with `git merge-base --is-ancestor "$tip" origin/dev-history`.
  Do not rewrite or force-push `dev` unless that check succeeds; report a
  failed archive run instead.
- Squash `dev` into `master`, commit the result, and push `master` normally.
  Verify that its tree matches the archived `dev` tip.
- With a clean worktree and verified archive, realign `dev` to `master` and
  push it with an explicit `--force-with-lease` against the recorded remote
  `dev` tip. Wait for the archive workflow again and verify the new tip.
- Fast-forward the local `dev-history` branch to the fetched archive, preserving
  any local-only history. Finish on `dev` with `master` and `dev` synchronized
  locally and remotely, and report the squash commit and archive verification.

## Validation

- Refresh flake inputs before validation builds so checks use the latest
  available snapshots of the configured channels. Report the revisions validated.
- Prefer validating with:

```console
env XDG_CACHE_HOME=/tmp/nix-cache nix flake update
env XDG_CACHE_HOME=/tmp/nix-cache nix build .#nixosConfigurations.nixos.config.system.build.toplevel --no-link
```

- Tell the user when a change still needs `nixos-rebuild switch`, `boot`, or a
  reboot to take effect.
