# Helper Scripts

These scripts support configuration modules but live together so their purpose
and direct usage are easy to find.

## `extract-vfct-rom`

Extracts a PCI option ROM from the host firmware ACPI VFCT table:

```console
sudo extract-vfct-rom
```

Default output:

```console
/var/lib/vfio/amd-igpu-1002-13c0-vfct.rom
```

Use this when the guest needs a raw GPU ROM file. Impermanence bind-mounts
`/var/lib/vfio` from its durable backing directory under `/persist`.

## `patch-vfct-bdf`

Patches VFCT image headers so their bus/device/function values match the guest
PCI address assigned to the passed-through GPU:

```console
sudo cp /sys/firmware/acpi/tables/VFCT /var/lib/vfio/VFCT-host.dat
sudo patch-vfct-bdf --bus 07 --device 00 --function 00
```

Default output:

```console
/var/lib/vfio/VFCT-guest.dat
```

Use this only if the guest is given a VFCT ACPI table and needs the table's GPU
BDF values rewritten to match the guest PCI topology. The correct `--bus`,
`--device`, and `--function` values come from the guest VM's assigned PCI
address, not necessarily from the host address.

Both commands support `--list` for inspection and refuse to overwrite outputs
unless `--force` is passed.

## `sunshine-mode-switch.sh`

Switches a KDE output to the first available requested mode before Sunshine
starts streaming, then restores the previous mode afterward. The Sunshine
module packages this script with its output name and runtime dependencies, so
it is normally invoked through Sunshine's preparation commands rather than
directly.

## Steam

The Steam helpers live under `steam/`. `desktop-input.mjs` backs the
`steam-desktop-input` command packaged by `modules/gaming.nix`. It switches all
connected Steam-recognized controllers' Desktop configurations between their
current layouts and Steam's empty layout:

```console
steam-desktop-input off
steam-desktop-input on
steam-desktop-input toggle
steam-desktop-input status
```

The `off` command saves the current layout under
`$XDG_STATE_HOME/steam-desktop-input` (or `~/.local/state`), and `on` restores
that exact layout. Steam must be fully restarted once after the configuration
is first applied so its local UI debugging endpoint becomes available.

That endpoint listens only on localhost but is unauthenticated. Port 8080 is
reserved for it, so Open WebUI uses port 8081.

`desktop-input-watcher.py` provides a user-session D-Bus service, and
`desktop-input-focus/` contains the KWin script that reports each active window.
The watcher identifies Steam games from the window's desktop file or the
focused process's Steam environment, then runs `steam-desktop-input off` for
games and `steam-desktop-input on` everywhere else.

The service serializes focus changes, briefly debounces transitions away from
games, and restores desktop input when it stops. Its decisions are available
in the user journal:

```console
journalctl --user -u steam-desktop-input-watcher
```
