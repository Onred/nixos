#!/usr/bin/env python3
import argparse
import os
import struct
import sys


ACPI_HEADER_SIZE = 36
VFCT_IMAGE_HEADER_SIZE = 28
DEFAULT_SOURCE = "/persist/vfio/VFCT-host.dat"
DEFAULT_OUTPUT = "/persist/vfio/VFCT-guest.dat"


def parse_hex_byte(value):
    value = value.lower().removeprefix("0x")
    parsed = int(value, 16)
    if parsed < 0 or parsed > 0xff:
        raise argparse.ArgumentTypeError(f"{value} is outside byte range")
    return parsed


def acpi_checksum(blob):
    return sum(blob) & 0xff


def fix_acpi_checksum(blob):
    blob[9] = 0
    blob[9] = (-sum(blob)) & 0xff


def read_vfct_image_headers(blob):
    if len(blob) < ACPI_HEADER_SIZE + 0x28:
        raise ValueError("VFCT table is too short")
    if blob[:4] != b"VFCT":
        raise ValueError("input does not start with a VFCT ACPI signature")

    table_length = struct.unpack_from("<I", blob, 4)[0]
    if table_length != len(blob):
        raise ValueError(
            f"ACPI length field is {table_length}, but file length is {len(blob)}"
        )

    image_offset = struct.unpack_from("<I", blob, ACPI_HEADER_SIZE + 0x10)[0]
    headers = []

    while image_offset:
        header_offset = image_offset
        rom_offset = header_offset + VFCT_IMAGE_HEADER_SIZE
        if rom_offset > len(blob):
            raise ValueError(f"VFCT image header at 0x{header_offset:x} is truncated")

        bus, device, function = struct.unpack_from("<III", blob, header_offset)
        vendor_id, device_id = struct.unpack_from("<HH", blob, header_offset + 0x0c)
        subsystem_vendor_id, subsystem_id = struct.unpack_from(
            "<HH", blob, header_offset + 0x10
        )
        revision = struct.unpack_from("<I", blob, header_offset + 0x14)[0]
        image_length = struct.unpack_from("<I", blob, header_offset + 0x18)[0]

        if image_length == 0 or rom_offset + image_length > len(blob):
            raise ValueError(f"invalid image length at 0x{header_offset:x}")
        if blob[rom_offset : rom_offset + 2] != b"\x55\xaa":
            raise ValueError(f"VFCT image at 0x{rom_offset:x} is missing ROM signature")

        headers.append(
            {
                "header_offset": header_offset,
                "rom_offset": rom_offset,
                "bus": bus,
                "device": device,
                "function": function,
                "vendor_id": vendor_id,
                "device_id": device_id,
                "subsystem_vendor_id": subsystem_vendor_id,
                "subsystem_id": subsystem_id,
                "revision": revision,
                "image_length": image_length,
            }
        )

        next_offset = rom_offset + image_length
        if next_offset >= len(blob):
            break
        if next_offset + VFCT_IMAGE_HEADER_SIZE > len(blob):
            break
        next_rom_offset = next_offset + VFCT_IMAGE_HEADER_SIZE
        if blob[next_rom_offset : next_rom_offset + 2] != b"\x55\xaa":
            break
        image_offset = next_offset

    return headers


def print_header(header):
    print(
        "vfct_image: header=0x{header_offset:x} rom=0x{rom_offset:x} "
        "bdf={bus:02x}:{device:02x}.{function:x} "
        "vendor={vendor_id:04x} device={device_id:04x} "
        "subsystem={subsystem_vendor_id:04x}:{subsystem_id:04x} "
        "revision=0x{revision:x} image_length={image_length}".format(**header)
    )


def main():
    parser = argparse.ArgumentParser(
        description="Patch AMD VFCT image headers to match a guest PCI BDF."
    )
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--bus", type=parse_hex_byte)
    parser.add_argument("--device", default="00", type=parse_hex_byte)
    parser.add_argument("--function", default="00", type=parse_hex_byte)
    parser.add_argument("--vendor-id", default="1002", type=lambda value: int(value, 16))
    parser.add_argument("--device-id", default="13c0", type=lambda value: int(value, 16))
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--list", action="store_true", help="list VFCT image headers only")
    args = parser.parse_args()

    with open(args.source, "rb") as source:
        blob = bytearray(source.read())

    headers = read_vfct_image_headers(blob)
    if not headers:
        print(f"no VFCT image headers found in {args.source}", file=sys.stderr)
        return 1

    if args.list:
        print(f"source: {args.source}")
        print(f"acpi_checksum=0x{acpi_checksum(blob):02x}")
        for header in headers:
            print_header(header)
        return 0

    if args.bus is None:
        parser.error("--bus is required unless --list is used")

    matches = [
        header
        for header in headers
        if header["vendor_id"] == args.vendor_id and header["device_id"] == args.device_id
    ]
    if not matches:
        print(
            f"no VFCT image header for {args.vendor_id:04x}:{args.device_id:04x}",
            file=sys.stderr,
        )
        for header in headers:
            print_header(header)
        return 1

    if os.path.exists(args.output) and not args.force:
        print(f"refusing to overwrite existing file: {args.output}", file=sys.stderr)
        return 1

    for header in matches:
        struct.pack_into("<III", blob, header["header_offset"], args.bus, args.device, args.function)

    fix_acpi_checksum(blob)

    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(args.output, "wb") as output:
        output.write(blob)

    print(f"source: {args.source}")
    print(f"output: {args.output}")
    print(f"patched_headers={len(matches)}")
    print(f"acpi_checksum=0x{acpi_checksum(blob):02x}")
    for header in read_vfct_image_headers(blob):
        print_header(header)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
