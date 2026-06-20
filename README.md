# NixOS configuration

Fresh NixOS desktop installation using flakes, Disko, and impermanence.

## Included

- NixOS 26.05 on `x86_64` UEFI systems
- KDE Plasma 6 with SDDM
- Latest upstream kernel
- NVIDIA open kernel modules
- Limine with Secure Boot signing
- NetworkManager, Bluetooth, PipeWire, and CUPS
- Steam, Firefox, Neovim, VS Code, Discord, and basic system tools
- Btrfs with ephemeral `/` and persistent `/nix`, `/persist`, and `/home`
- Automatic hardware detection and password setup during installation

NVIDIA is explicitly enabled. For another GPU, clone the repository and remove
the NVIDIA options from the **Graphics and desktop** section of
`configuration.nix`. Secure Boot may remain disabled in firmware if it is not
wanted.

## Installation

Boot the NixOS live environment and connect to the network.

### 1. Identify the target disk

List physical disks and their stable identifiers:

```console
lsblk -d -o NAME,PATH,SIZE,MODEL,SERIAL,TRAN
ls -l /dev/disk/by-id/
```

Choose a whole-disk identifier matching the intended model and serial. Do not
use an entry ending in `-part1`, `-part2`, or another partition suffix.

```console
DISK='/dev/disk/by-id/REPLACE_WITH_THE_VERIFIED_DISK_ID'
```

Resolve and inspect it before continuing:

```console
readlink -f "$DISK"
lsblk -o NAME,PATH,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS,MODEL,SERIAL \
  "$(readlink -f "$DISK")"
```

Confirm that the model, size, serial, existing partitions, and resolved device
are correct. The selected disk will be completely erased. Do not select the
installer USB or a disk containing data you want to keep. The original
machine's identifier is retained only as a footnote.[^this-machine]

### 2. Install

Install the published configuration directly from GitHub:

```console
sudo nix --extra-experimental-features "nix-command flakes" run \
  'github:Onred/nixos#install' -- --disk "$DISK"
```

To review or modify the configuration first:

```console
git clone --branch master https://github.com/Onred/nixos.git
cd nixos
sudo nix --extra-experimental-features "nix-command flakes" run \
  'path:.#install' -- --disk "$DISK"
```

The installer verifies the disk again, displays its current layout, requires
`YES`, prompts twice for the `onred` password, generates hardware configuration,
partitions the disk, and installs NixOS.

After installation:

- `/home/onred/nixos` is the working Git repository.
- `/etc/nixos` is a recovery snapshot from installation.
- Secure Boot keys are stored persistently under `/var/lib/sbctl`.

Leave Secure Boot disabled for the first boot. Enroll the generated keys before
enabling it in firmware. First check the current state:

```console
sudo sbctl status
```

The firmware must be in Setup Mode. If it is not, clear or reset the Secure Boot
keys from the firmware settings, then boot NixOS again. Enroll the current keys
while retaining the Microsoft certificates needed by some firmware and hardware:

```console
sudo sbctl enroll-keys --microsoft
sudo sbctl status
sudo sbctl verify
```

After enrollment succeeds and the boot files verify as signed, reboot into the
firmware settings and enable Secure Boot.

## Rebuilding

From `/home/onred/nixos`:

```console
sudo nixos-rebuild build --flake .#nixos
sudo nixos-rebuild switch --flake .#nixos
```

For boot, filesystem, or impermanence changes:

```console
sudo nixos-rebuild boot --flake .#nixos
sudo reboot
```

[^this-machine]: After verifying serial `S6B0NL0W144498J`, the original machine
    can use: `sudo nix --extra-experimental-features "nix-command flakes" run 'github:Onred/nixos#install' -- --disk '/dev/disk/by-id/nvme-Samsung_SSD_980_PRO_2TB_S6B0NL0W144498J'`
