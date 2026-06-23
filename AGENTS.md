# Codex project guidance

NixOS installation for host `nixos` on an AMD/NVIDIA desktop.

## System facts

- Architecture: `x86_64-linux`, hostname: `nixos`, timezone: `Asia/Tokyo`
- Desktop: KDE Plasma 6 with SDDM
- GPU: NVIDIA open kernel modules
- Bootloader: Limine with Secure Boot
- `system.stateVersion = "26.05"` — do not change
- Kernel: `linuxPackages_latest`

## Storage layout

- Target disk: Samsung 980 PRO 2 TB, serial `S6B0NL0W144498J`
- Disko manages GPT/Btrfs layout; `hardware-configuration.nix` holds only
  detected hardware facts (no filesystem declarations)
- Persistent Btrfs subvolumes: `/nix`, `/persist`, `/home`
- Root subvolume is reset on boot
- `modules/extra-disks.nix` automounts ext4 volume labeled `data` at
  `/mnt/data` (not managed by Disko)
- Secure Boot signing keys persisted for convenience; never commit private
  keys to Git

## Working conventions

- Keep flake inputs pinned in `flake.lock`
- Track every local file referenced by the flake; prefer relative repository
  paths over `/etc/nixos` paths
- Never commit passwords, tokens, private keys, recovery material, or secrets
- Keep changes small; batch validation at feature-complete milestones
- Prefer NixOS and module defaults; add options only for explicit
  requirements, necessary hardware facts, or required integrations
- Keep configuration direct and simple; no proactive refactoring
- Keep code comments sparse; comment only non-obvious constraints
- Fix defects immediately unless asked for diagnosis only
- Record persistence requirements in both the Nix module and recovery docs
- Suggest commits only when a feature or milestone is complete and tested;
  wait for explicit confirmation
- Never run Disko destructively without showing the target device and
  receiving explicit confirmation
- Before destructive disk operations, verify the target disk by `/dev/disk/by-id`,
  model, serial, and current layout
- For boot-critical, filesystem, or impermanence changes, prefer
  `nixos-rebuild boot` after a successful build
- Never include branch names in commit messages
- Use local web search routinely to verify information is current, especially
  for code, APIs, model availability, and documentation
- Prefer local/free solutions over cloud APIs

## Verification

Ask the user to run:

```console
sudo nixos-rebuild build --flake ~/nixos/.#nixos
```
