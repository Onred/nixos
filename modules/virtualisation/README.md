# VFIO helpers

This module includes two manual VFCT helpers for AMD iGPU passthrough. They are
installed as commands when the virtualisation module is imported.

## `extract-vfct-rom`

Extracts a PCI option ROM from the host firmware ACPI VFCT table:

```console
sudo extract-vfct-rom
```

Default output:

```console
/persist/vfio/amd-igpu-1002-13c0-vfct.rom
```

Use this when the guest needs a raw GPU ROM file.

## `patch-vfct-bdf`

Patches VFCT image headers so their bus/device/function values match the guest
PCI address assigned to the passed-through GPU:

```console
sudo cp /sys/firmware/acpi/tables/VFCT /persist/vfio/VFCT-host.dat
sudo patch-vfct-bdf --bus 07 --device 00 --function 00
```

Default output:

```console
/persist/vfio/VFCT-guest.dat
```

Use this only if the guest is given a VFCT ACPI table and needs the table's GPU
BDF values rewritten to match the guest PCI topology. The correct `--bus`,
`--device`, and `--function` values come from the guest VM's assigned PCI
address, not necessarily from the host address.

Both commands support `--list` for inspection and refuse to overwrite outputs
unless `--force` is passed.
