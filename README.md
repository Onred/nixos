# NixOS Configuration

Personal NixOS flake for host `nixos`.

## Notable Choices

- Disko-managed GPT/Btrfs layout
- Ephemeral root with explicit impermanence persistence
- Limine bootloader with Secure Boot support
- Latest upstream kernel
- NVIDIA open kernel modules on the `new_feature` branch
- Optional modules for Sunshine, VFIO/KVMFR virtualisation, local AI, and
  targeted local tweaks

## Customize Before Installing

- Edit imports in `configuration.nix`.
- Adjust modules under `modules/`.
- Review `modules/storage/disko-layout.nix` before installing to a new disk.
- Remove hardware-specific modules you do not need, such as `modules/nvidia.nix`
  or entries under `modules/tweaks/`.

The installer generates `hardware-configuration.nix` for the target machine.

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

The installer prompts for a target disk, then shows the selected disk layout
before the final confirmation.

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
