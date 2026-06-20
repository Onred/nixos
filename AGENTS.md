# Codex project guidance

This repository defines the NixOS installation for the host `nixos`.

## Goals

- Keep the complete, reproducible system configuration in Git.
- Target the current AMD/NVIDIA desktop. Generalizing the repository for other
  machines is out of scope until the user explicitly requests it.
- Migrate to a minimal Nix flake before adding impermanence.
- Install onto a clear disk with a Btrfs layout designed for an ephemeral root.
- Do not support or preserve the current installation layout; this repository
  describes the desired fresh system.
- Use `nix-community/impermanence` to declare state retained across boots.
- Use Disko to declare and reproduce the target GPT and Btrfs layout.
- Keep `/home` persistent initially; user impermanence can be a later change.

## Current system

- Architecture: `x86_64-linux`
- Hostname: `nixos`
- Time zone: `Asia/Tokyo`
- Desktop: KDE Plasma 6 with SDDM
- GPU: NVIDIA using the open kernel modules
- Boot loader: Limine with Secure Boot enabled
- The repository's target layout is authoritative; existing on-disk UUIDs and
  mounts are not part of the desired configuration.

## Decisions and constraints

- The target disk is assumed to be clear. Repartitioning and reinstalling are
  expected; preserving current user data is not required.
- Keep `system.stateVersion = "26.05"`. Do not change it during upgrades or a
  reinstall unless the user explicitly decides to do so.
- Keep `linuxPackages_latest`: the user prefers the latest upstream kernel for
  potential gaming improvements. CachyOS may be explored later without adding
  Chaotic Nyx unless it proves necessary.
- Secure Boot is recoverable by disabling it in firmware. Persist its signing
  keys for convenience, but never commit private keys to Git.
- The intended persistent Btrfs subvolumes are `/nix`, `/persist`, and initially
  `/home`. The root subvolume should be reset or recreated during boot.
- `modules/extra-disks.nix` optionally automounts the existing ext4 filesystem
  labeled `data` at `/mnt/data`. It is not managed or formatted by Disko.
- The machine contains two identical Samsung 980 PRO 2 TB drives. The intended
  NixOS disk has serial `S6B0NL0W144498J`; its identity must be verified from
  the installer before any destructive Disko operation.
- Keep `modules/hardware-configuration.nix` limited to detected hardware facts. Disko
  is the only source of partition and filesystem declarations.
- The installer must require an explicit `/dev/disk/by-id` target, display its
  model, serial, and current layout, and require `YES` before Disko.
- Generate `modules/hardware-configuration.nix` during installation with
  `nixos-generate-config --show-hardware-config --no-filesystems`.
- Before first boot, install a real `master` branch clone at
  `/home/onred/nixos`, overlay its generated hardware configuration, and retain
  the generated `/etc/nixos` tree as a separate recovery snapshot.

## Working conventions

- Keep flake inputs pinned in `flake.lock`.
- Track every local file referenced by the flake, including assets such as the
  Limine wallpaper. Prefer relative repository paths over `/etc/nixos` paths.
- Never commit passwords, tokens, private keys, recovery material, or secrets.
- Keep changes small and build the configuration before activating it.
- Batch validation at feature-complete milestones instead of asking for builds
  after every small edit.
- Prefer NixOS and module defaults. Add an option only when it expresses an
  explicit user requirement, necessary hardware fact, or required integration;
  avoid speculative tuning and redundant default values.
- Keep the configuration direct and simple. Do not proactively split files,
  introduce abstractions, or refactor working configuration. Suggest a
  refactoring when it has a concrete benefit, then wait for the user to direct
  or approve it.
- Prefer straightforward solutions for realistic failure modes over defensive
  machinery for implausible edge cases.
- Keep code comments sparse and short. Comment only non-obvious constraints.
- When the user reports a defect while continuing implementation work, make the
  corresponding code changes unless they explicitly request diagnosis only.
- Do not combine the initial flake migration with filesystem or impermanence
  changes; preserve a simple rollback point between milestones.
- Record newly discovered persistence requirements in both the Nix module and
  the recovery documentation where appropriate.
- Do not create Git commits automatically or bundle commits with implementation
  work. Suggest a commit only when a feature or milestone is complete and
  tested, then wait for the user's explicit confirmation before committing.
- Never run Disko in a destructive mode without showing the resolved target
  device to the user and receiving explicit confirmation immediately before it.
- Do not run Nix builds, `nixos-rebuild`, activation commands, or runtime tests.
  When validation is needed, give the user the exact commands to run and wait
  for them to report the results.

## Planned sequence

1. Publish the current `master` branch and make it the default branch of the
   existing `Onred/nixos` GitHub repository while preserving old `main`.
2. Review and test the complete fresh-install configuration.
3. Install onto the clear target disk.
4. Verify multiple reboot cycles before making `/home` selective or ephemeral.

## Verification

Before switching to a changed flake configuration, run:

```console
sudo nixos-rebuild build --flake .#nixos
```

Use `switch` only after a successful build. For boot-critical, filesystem, or
impermanence changes, prefer `boot` followed by a controlled reboot so the
previous generation remains an easy fallback.
