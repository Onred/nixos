#!/usr/bin/env bash
set -euo pipefail

if (( EUID != 0 )); then
  echo 'Run this installer with sudo.' >&2
  exit 1
fi

# shellcheck source=/dev/null
source /etc/os-release
if [[ "${ID:-}" != debian || "${VERSION_CODENAME:-}" != trixie ]]; then
  echo 'This installer requires Debian / Raspberry Pi OS Trixie.' >&2
  exit 1
fi

if [[ "$(dpkg --print-architecture)" != arm64 ]]; then
  echo 'This installer requires the 64-bit ARM OS.' >&2
  exit 1
fi

install -d -m 0755 /usr/share/keyrings
curl --fail --silent --show-error \
  https://pkgs.tailscale.com/stable/debian/trixie.noarmor.gpg \
  -o /usr/share/keyrings/tailscale-archive-keyring.gpg
curl --fail --silent --show-error \
  https://pkgs.tailscale.com/stable/debian/trixie.tailscale-keyring.list \
  -o /etc/apt/sources.list.d/tailscale.list

apt-get update
apt-get full-upgrade -y
apt-get install -y tailscale tailscale-archive-keyring docker.io docker-compose

printf '%s\n' 'net.ipv4.ip_forward = 1' > /etc/sysctl.d/99-tailscale.conf
sysctl -p /etc/sysctl.d/99-tailscale.conf

install -d -m 0755 /opt/upsnap
install -m 0644 "$(dirname "$0")/upsnap-compose.yaml" /opt/upsnap/compose.yaml
systemctl enable --now tailscaled docker
docker compose -f /opt/upsnap/compose.yaml up -d

echo 'Installation complete. Next: sudo tailscale up --advertise-routes=10.44.0.0/16'
