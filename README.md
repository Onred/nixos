# NixOS Configuration

Personal NixOS flake for the `nixos` system.

## Layout

- `flake.nix` defines editable machine values, inputs, the installer app, and
  the single NixOS output.
- `configuration.nix` is the NixOS entrypoint.
- `hardware-configuration.nix` contains generated hardware facts only.
- `modules/default.nix` is the explicit list of enabled system modules.
- `modules/packages.nix` contains general desktop, development, and gaming
  applications and packages.
- `scripts/` contains module helper scripts and their usage documentation.

The identity values passed to NixOS modules can also be passed to a future Home
Manager configuration under `home/`.

## Notable Choices

- Disko-managed GPT/Btrfs layout
- Ephemeral root with explicit impermanence persistence
- Limine bootloader with Secure Boot support
- Latest upstream kernel
- NVIDIA open kernel modules on the `new_feature` branch
- Modules for Sunshine, local AI, EVO4 audio, and VFIO/KVMFR GPU passthrough
- Cohesive modules for the system, hardware, KDE Plasma, applications, virtualisation, Disko, and Impermanence

## Customize Before Installing

- Edit the local system settings near the top of the `flake.nix` output block
  for the architecture, hostname, username, and full name.
- Edit imports in `modules/default.nix` to enable or disable capabilities.
- Adjust configuration under `modules/`.
- Review `modules/disko.nix` before installing to a new disk.
- Review `modules/hardware.nix` for system-specific devices and integrations.

The installer generates `hardware-configuration.nix` for the target system.

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
