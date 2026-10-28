#!/usr/bin/env python3
"""Export published ML 80D symbols as analysis seeds, not binary discoveries."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

REVISION = "142472e95054d73640f50789ac0fd66325499d82"


def collect(root):
    revision = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if revision != REVISION:
        raise ValueError(f"expected ML commit {REVISION}; got {revision}")
    source = root / "platform/80D.103/stubs.S"
    raw = source.read_bytes()
    symbols = []
    for number, line in enumerate(raw.decode().splitlines(), 1):
        # Only literal hex mappings are included; don't evaluate C expressions.
        match = re.match(r"\s*(THUMB_FN|ARM_FN|NSTUB)\(\s*(0x[0-9a-fA-F]+)\s*,\s*([A-Za-z_][A-Za-z_0-9]*)\s*\)", line)
        if match:
            kind, address, name = match.groups()
            value = int(address, 16)
            if value == 0:
                continue
            symbols.append({"name": name, "address": value, "address_hex": hex(value),
                            "declaration_kind": kind, "source_line": number,
                            "verified_against_local_rom": False})
    return {"schema_version": 1, "model": "Canon EOS 80D", "firmware": "1.0.3",
            "source_repository": "https://github.com/reticulatedpines/magiclantern_simplified",
            "source_revision": revision, "source_path": "platform/80D.103/stubs.S",
            "source_sha256": hashlib.sha256(raw).hexdigest(), "symbols": symbols,
            "limitations": ["Published source mappings only; no local ROM was available to verify instructions.",
                            "Zero-address and expression-based declarations are omitted.",
                            "THUMB_FN is source-declared mode, not a disassembly finding."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("magic_lantern_checkout", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(collect(args.magic_lantern_checkout), indent=2))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(2, f"map_source_symbols: {error}\n")


if __name__ == "__main__":
    main()
