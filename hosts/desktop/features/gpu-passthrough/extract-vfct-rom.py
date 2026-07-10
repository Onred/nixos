#!/usr/bin/env python3
import argparse
import os
import struct
import sys


DEFAULT_SOURCE = "/sys/firmware/acpi/tables/VFCT"
DEFAULT_OUTPUT = "/persist/vfio/amd-igpu-1002-13c0-vfct.rom"


def parse_hex_id(value):
    value = value.lower().removeprefix("0x")
    return int(value, 16)


def checksum(data):
    return sum(data) & 0xff


def parse_rom_chain(blob, start):
    images = []
    offset = start

    while offset + 0x1c <= len(blob):
        if blob[offset : offset + 2] != b"\x55\xaa":
            raise ValueError(f"missing ROM signature at 0x{offset:x}")

        pcir_pointer = struct.unpack_from("<H", blob, offset + 0x18)[0]
        pcir = offset + pcir_pointer
        if pcir + 0x18 > len(blob) or blob[pcir : pcir + 4] != b"PCIR":
            raise ValueError(f"missing PCIR record for ROM at 0x{offset:x}")

        vendor_id, device_id = struct.unpack_from("<HH", blob, pcir + 0x04)
        image_blocks = struct.unpack_from("<H", blob, pcir + 0x10)[0]
        code_type = blob[pcir + 0x14]
        indicator = blob[pcir + 0x15]
        image_size = image_blocks * 512

        if image_size == 0 or offset + image_size > len(blob):
            raise ValueError(f"invalid image size at 0x{offset:x}")

        image = blob[offset : offset + image_size]
        images.append(
            {
                "offset": offset,
                "size": image_size,
                "vendor_id": vendor_id,
                "device_id": device_id,
                "code_type": code_type,
                "indicator": indicator,
                "checksum": checksum(image),
            }
        )

        offset += image_size
        if indicator & 0x80:
            break

    if not images:
        raise ValueError(f"no ROM images at 0x{start:x}")

    total_size = sum(image["size"] for image in images)
    return images, blob[start : start + total_size]


def find_roms(blob, vendor_id, device_id):
    results = []
    start = 0

    while True:
        offset = blob.find(b"\x55\xaa", start)
        if offset < 0:
            break

        try:
            images, rom = parse_rom_chain(blob, offset)
        except ValueError:
            start = offset + 1
            continue

        if any(
            image["vendor_id"] == vendor_id and image["device_id"] == device_id
            for image in images
        ):
            results.append((offset, images, rom))

        start = offset + 1

    return results


def find_all_roms(blob):
    results = []
    start = 0

    while True:
        offset = blob.find(b"\x55\xaa", start)
        if offset < 0:
            break

        try:
            images, rom = parse_rom_chain(blob, offset)
        except ValueError:
            start = offset + 1
            continue

        results.append((offset, images, rom))
        start = offset + 1

    return results


def print_rom(offset, images, rom):
    print(f"vfct_offset: 0x{offset:x}")
    print(f"rom_size: {len(rom)}")
    for index, image in enumerate(images):
        print(
            "image_{index}: offset=0x{offset:x} size={size} "
            "vendor={vendor_id:04x} device={device_id:04x} "
            "code_type=0x{code_type:02x} indicator=0x{indicator:02x} "
            "checksum=0x{checksum:02x}".format(index=index, **image)
        )


def main():
    parser = argparse.ArgumentParser(
        description="Extract an AMD GPU PCI option ROM from the ACPI VFCT table."
    )
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--vendor-id", default="1002", type=parse_hex_id)
    parser.add_argument("--device-id", default="13c0", type=parse_hex_id)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--list", action="store_true", help="list ROM candidates only")
    args = parser.parse_args()

    with open(args.source, "rb") as source:
        blob = source.read()

    if args.list:
        candidates = find_all_roms(blob)
        if not candidates:
            print(f"no ROM candidates found in {args.source}", file=sys.stderr)
            return 1
        for candidate in candidates:
            print_rom(*candidate)
        return 0

    matches = find_roms(blob, args.vendor_id, args.device_id)
    if not matches:
        print(
            f"no matching ROM for {args.vendor_id:04x}:{args.device_id:04x} in {args.source}",
            file=sys.stderr,
        )
        candidates = find_all_roms(blob)
        if candidates:
            print("ROM candidates found:", file=sys.stderr)
            for candidate in candidates:
                print_rom(*candidate)
        return 1

    if len(matches) > 1:
        print(f"found {len(matches)} matching ROMs; using the first match", file=sys.stderr)

    offset, images, rom = matches[0]
    if os.path.exists(args.output) and not args.force:
        print(f"refusing to overwrite existing file: {args.output}", file=sys.stderr)
        return 1

    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(args.output, "wb") as output:
        output.write(rom)

    print(f"source: {args.source}")
    print(f"output: {args.output}")
    print_rom(offset, images, rom)

    if any(image["checksum"] != 0 for image in images):
        print("warning: one or more ROM image checksums are non-zero", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
