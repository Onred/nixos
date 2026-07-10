# NixOS Configuration

Personal multi-host NixOS flake. The current desktop remains available as
`.#nixos`.

## Notable Choices

- Disko-managed GPT/Btrfs layout
- Ephemeral root with explicit impermanence persistence
- Limine bootloader with Secure Boot support
- Latest upstream kernel
- NVIDIA open kernel modules on the `new_feature` branch
- Desktop-local features for Sunshine, local AI, EVO4 audio, and VFIO/KVMFR GPU passthrough
- Shared modules for boot, desktop, development, gaming, virtualisation, NVIDIA, Disko, and Impermanence

## Customize Before Installing

- Edit `config.nix` for user identity and per-host names.
- Edit host imports in `hosts/desktop/default.nix`.
- Adjust shared modules under `modules/` and host-specific features under
  `hosts/`.
- Review `modules/disko.nix` before installing to a new disk.
- Remove hardware-specific imports you do not need, such as `modules/nvidia.nix`
  or desktop features under `hosts/desktop/features/`.

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
