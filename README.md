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
- `modules/strata.nix` is the standalone Strata/Qwen Flash setup; see
  [usage](scripts/strata.md).
- [TODO.md](TODO.md) records unfinished remote-access and streaming work.

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

## Remote Access

The proposed family access route is Tailscale, with an always-on Raspberry Pi
providing a subnet route and a packaged wake service. This PC remains a normal
LAN host. The relay is a Raspberry Pi 4 Model B Rev 1.4 running 64-bit Trixie
from a 16GB microSD. Tailscale and UpSnap are installed and running. The LAN
route is approved and relay key expiry is disabled; client setup and actual
sleep/wake tests remain. Its current LAN
address is `10.44.203.34`; its stable Tailscale address is `100.83.111.120`.
Moving to another port on the same LAN can change DHCP without changing that
Tailscale address. A move to a different VLAN/subnet needs routing and wake
reachability checked again. The deployment files are documented in
[`scripts/README.md`](scripts/README.md#pi-wake-relay).
Reserve `10.44.15.86` for Ethernet MAC `34:5a:60:c2:aa:61` in UniFi so client
bookmarks and Moonlight's saved host remain valid.

Install the current Raspberry Pi OS Lite (64-bit) with Raspberry Pi Imager.
Set hostname `relay`, username `onred`, the US keyboard layout, and enable SSH
during image customisation. Use Ethernet. Imager can run temporarily on this
NixOS PC with:

```console
env XDG_CACHE_HOME=/tmp/nix-cache nix shell --inputs-from . nixpkgs#rpi-imager -c bash -c 'sudo env XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR" WAYLAND_DISPLAY="$WAYLAND_DISPLAY" QT_QPA_PLATFORM=wayland "$(command -v rpi-imager)"'
```

After flashing and booting the Pi, connect with `ssh onred@relay.local` (or its
DHCP address). UpSnap is at `http://100.83.111.120:8090` from a connected
Tailscale client, or `http://relay.local:8090` on the LAN. The VPN alone does not
wake the PC.

The Pi should advertise `10.44.0.0/16` as a Tailscale subnet route, approved in
the admin console. Keep the default subnet-router SNAT so this PC receives
connections through its existing Ethernet firewall rules. Do not select an
exit node: ordinary internet traffic should keep its normal route.

For the family's mostly iPhone clients, configure Tailscale's VPN On Demand
with Cellular and Wi-Fi both set to Always. Keeping it connected at home makes
the relay's stable Tailscale address usable everywhere; ordinary internet keeps
its normal route with no exit node. Disable key expiry for trusted enrolled
devices to avoid periodic renewal prompts. These client settings and access
permissions still need setup.

Router WireGuard remains an alternative if the gateway has a reachable public
IP. It needs no Pi subnet route: import each client's UniFi configuration and
use `AllowedIPs = 10.44.0.0/16` for split routing. Leave the client's DNS setting
empty to retain normal DNS, or include its VPN DNS server in `AllowedIPs`.

| Service | Private address | Desktop login required |
| --- | --- | --- |
| Open WebUI | `http://10.44.15.86:8080` | No |
| SSH | `ssh onred@10.44.15.86` | No |
| Sunshine | Add `10.44.15.86` in Moonlight and pair once | Plasma logs in automatically |

Open WebUI retains its no-sign-in behavior on the trusted LAN/VPN. Its local
shortcut still uses port 8081. The remote socket on port 8080 forwards each
connection using packaged systemd and socat commands and holds an idle/sleep
inhibitor for that connection. A connected browser tab can keep the PC awake;
closing it releases the inhibitor. Ollama's API remains local. Safari can save
the remote WebUI address to the home screen; browser features requiring HTTPS,
such as microphone access, need a separate HTTPS setup.

Plasma logs in automatically, allowing Sunshine to start after reboot
without a local login. Locking follows the user's normal Plasma lock timer.
Streaming creates KDE's `Virtual-Sunshine` output,
disables `HDMI-A-1`, and uses KWin capture with NVIDIA NVENC. The Steam TV and
Steam Deck profiles use 1440p/120 Hz and 1080p/60 Hz respectively. The virtual
output supports SDR, not HDR. Quitting the Moonlight application removes the
virtual output and restores HDMI; merely disconnecting can leave Sunshine's
application session running. Sleep is inhibited while the virtual monitor
service is active. Reboot/login and client streaming still require an actual
end-to-end test after applying the configuration.

NetworkManager enables magic-packet Wake-on-LAN. After applying the config and
rebooting, inspect the actual hardware setting with:

```console
env XDG_CACHE_HOME=/tmp/nix-cache nix shell --inputs-from . nixpkgs#ethtool \
  -c sudo ethtool enp6s0
```

Look for `Supports Wake-on` containing `g` and `Wake-on: g`. Firmware must also
allow the Ethernet/PCIe device to wake the machine. Test sleep/wake from another
LAN device before relying on it remotely. WireGuard is routed and does not
carry LAN broadcasts automatically: an always-on sender at home must send the
packet to this MAC. This gateway has no installed wake utility, including
BusyBox's `ether-wake` applet. Keep the gateway on supported UniFi configuration;
do not install router packages or add Python wake scripts. Remote wake still
needs a supported UniFi feature or a packaged sender on an always-on LAN device.

Jellyfin is not currently enabled. It can run as a system service independently
of Plasma when added; its media directories and activity/sleep policy need to
be chosen first. Router VPN access alone does not prevent any service from
being interrupted by sleep.

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

## Swap

`modules/disko.nix` defines a 64 GiB swapfile in a dedicated `/swap` Btrfs
subvolume, created automatically on fresh installations. It is outside the
configured backup paths and the root-reset mechanism. Hibernation resume is
not configured.

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
