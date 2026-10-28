#!/usr/bin/env python3
"""Read-only Canon 80D FIR v4 container inspection; no decryption or device I/O.

Field interpretation is cross-checked against Arm.Indy's GPL fir_tool2.py
and Laurent Clevy's Python 3 update. This original parser contains no keys,
vendor firmware bytes, or borrowed decoding tables.
"""

import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import struct

EXPECTED_SHA256 = "aa25b4c1a966b3611078ca86b348475dd676a1eabc6f74a0bdc308bc7b116f8c"
EXPECTED_SIZE = 28_931_264
MODEL = 0x80000350
MAX_SIZE = 128 * 1024 * 1024


def entropy(data):
    """Return Shannon byte entropy; this is not an encryption detector."""
    if not data:
        return 0.0
    return -sum((n / len(data)) * math.log2(n / len(data))
                for n in collections.Counter(data).values())


def inspect(data):
    """Validate container bounds/checksum and describe stored byte ranges."""
    if not 0x120 <= len(data) <= MAX_SIZE:
        raise ValueError("FIR size is outside the supported 0x120..128 MiB range")

    def u32(offset):
        if offset < 0 or offset + 4 > len(data):
            raise ValueError("32-bit field outside input")
        return struct.unpack_from("<I", data, offset)[0]

    def region(name, offset, size):
        if size <= 0 or offset < 0 or offset > len(data) - size:
            raise ValueError(f"{name} range extends outside input")
        value = data[offset:offset + size]
        return {"name": name, "offset": offset, "offset_hex": hex(offset),
                "length": size, "end_exclusive": offset + size,
                "sha256": hashlib.sha256(value).hexdigest(),
                "byte_entropy": entropy(value), "runtime_address": None}

    if u32(0) != MODEL:
        raise ValueError("model ID is not Canon EOS 80D (0x80000350)")
    if data[0x10:0x15] != b"1.0.3":
        raise ValueError("only the EOS 80D 1.0.3 v4 layout is supported")
    if u32(0x38) != len(data):
        raise ValueError("embedded file length differs from actual input")
    updater_header, updater, firmware = u32(0x24), u32(0x28), u32(0x30)
    if updater_header != 0xB0 or updater != 0x120:
        raise ValueError("unsupported updater header/data layout")
    if u32(0x2C) != 0xFFFFFFFF or u32(0x34) != 0xFFFFFFFF:
        raise ValueError("unexpected additional updater")
    if firmware < updater:
        raise ValueError("main payload precedes updater")
    updater_size, firmware_size = u32(updater_header), u32(0x64)
    if updater + updater_size != firmware or u32(0x60) != firmware:
        raise ValueError("updater/main ranges are inconsistent")
    if firmware + firmware_size != len(data):
        raise ValueError("main payload range does not end at EOF")
    # Check the internal payload header before reading its variable offsets.
    region("main-payload-header", firmware, 0x80)
    if u32(firmware + 8) != firmware_size:
        raise ValueError("nested firmware size differs from outer header")
    data_offset, data_size = u32(firmware + 4), u32(firmware + 0x10)
    if data_offset != 0x80 or data_offset + data_size != firmware_size:
        raise ValueError("unsupported nested payload range")
    if u32(firmware + 0x14) != data_size:
        raise ValueError("nested duplicate payload length differs")
    stored_checksum = u32(0x20)
    calculated_checksum = (~(sum(data[:0x20]) + sum(data[0x24:]))) & 0xFFFFFFFF
    if stored_checksum != calculated_checksum:
        raise ValueError("container additive checksum mismatch")
    digest = hashlib.sha256(data).hexdigest()
    aes_style_header = any(data[0xC0:0x120])
    return {
        "schema_version": 1,
        "model": "Canon EOS 80D", "model_id": hex(MODEL), "version": "1.0.3",
        "file_size": len(data), "sha256": digest,
        "matches_downloaded_official_reference": digest == EXPECTED_SHA256 and len(data) == EXPECTED_SIZE,
        "checksum": {"kind": "ones-complement sum of bytes excluding 0x20..0x23",
                     "stored": hex(stored_checksum), "calculated": hex(calculated_checksum), "valid": True},
        "updater_header_classification": "AES-style v4 header" if aes_style_header else "legacy XOR-style header",
        "classification_basis": "nonzero fields at 0xc0..0x11f; fir_tool2.py convention, not cryptographic verification",
        "authentication": {"hmac_sha1_present": {"updater": any(data[0x68:0x7C]),
                                                "main_payload": any(data[0x88:0x9C])},
                           "hmac_verified": False, "keys_available": False},
        "regions": [region("outer-header", 0, updater),
                    region("stored-updater", updater, updater_size),
                    region("stored-main-payload", firmware, firmware_size),
                    region("stored-main-data", firmware + data_offset, data_size)],
        "limitations": [
            "No payload decryption, disassembly, firmware re-signing, or hardware execution was performed.",
            "A valid additive checksum does not establish authenticity or camera compatibility.",
            "High entropy does not independently distinguish encryption from compression.",
            "Stored file offsets are not runtime memory addresses.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("firmware", type=Path)
    parser.add_argument("--require-official", action="store_true",
                        help="also require the exact official reference SHA-256")
    args = parser.parse_args()
    try:
        if args.firmware.stat().st_size > MAX_SIZE:
            raise ValueError("input exceeds 128 MiB")
        report = inspect(args.firmware.read_bytes())
        if args.require_official and not report["matches_downloaded_official_reference"]:
            raise ValueError("SHA-256 does not match downloaded official reference")
    except (OSError, ValueError) as error:
        parser.exit(2, f"inspect_fir: {error}\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
