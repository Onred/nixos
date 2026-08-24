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
