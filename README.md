# NixOS Configuration

Personal multi-host NixOS flake. The current desktop remains available as
`.#nixos`.

## Notable Choices

- Disko-managed GPT/Btrfs layout
- Ephemeral root with explicit impermanence persistence
- Limine bootloader with Secure Boot support
- Latest upstream kernel
- NVIDIA open kernel modules on the `new_feature` branch
- Desktop-local features for Sunshine and VFIO/KVMFR GPU passthrough
- Optional profiles/modules for virtualisation, local AI, and targeted local tweaks

## Customize Before Installing

- Edit `config.nix` for user identity and per-host names.
- Edit host imports in `hosts/desktop/default.nix`.
- Adjust reusable bundles under `profiles/` and feature modules under `modules/`.
- Review `modules/storage/disko-layout.nix` before installing to a new disk.
- Remove hardware-specific modules you do not need, such as `modules/nvidia.nix`
  or entries under `modules/tweaks/`.

The installer generates the selected host's `hardware-configuration.nix`.

## Install

From GitHub:

```console
sudo nix --extra-experimental-features "nix-command flakes" run \
  'github:Onred/nixos#install'
```

From a customized checkout:

```console
sudo nix --extra-experimental-features "nix-command flakes" run \
  'path:.#install'
```

The installer prompts for an install target and target disk, then shows the
selected disk layout before the final confirmation.

After install, enroll Secure Boot keys with `sbctl` before enabling Secure Boot
in firmware.

## Apply Config

From `/home/onred/nixos`:

```console
sudo nixos-rebuild build --flake .#nixos
sudo nixos-rebuild switch --flake .#nixos
```

For bootloader or early-boot changes:

```console
sudo nixos-rebuild boot --flake .#nixos
sudo reboot
```
