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
- Latest stable kernel from the main nixpkgs input
- NVIDIA open kernel modules on the `latest` branch
- Modules for Sunshine, local AI, EVO4 audio, and VFIO/KVMFR GPU passthrough
- Cohesive modules for the system, hardware, KDE Plasma, applications, virtualisation, Disko, and Impermanence

## Package Channels

The main `nixpkgs` input temporarily uses `nixos-unstable` ahead of 26.11.
Both nixpkgs inputs currently lock the same revision. After the 26.11 package
freeze, change only `nixpkgs.url` to `nixpkgs/nixos-26.11` and run
`nix flake update nixpkgs`.

Codex uses `nixpkgs-unstable` because access to new models can require a newer
client. Update it independently with `nix flake update nixpkgs-unstable`.

The kernel uses `pkgs.linuxPackages_latest` from the main package set. NVIDIA,
CUDA, local AI applications, and Faugus Launcher also use the main package set
and will follow it onto 26.11.
Add another unstable override only if the stable version stops working with
a required external service or model. Watch Qwen Code for provider compatibility
changes; new features alone are not a reason to switch channels.

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
