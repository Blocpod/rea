#!/usr/bin/env python3
"""Compile a common 3D .cube file into bounded C80LUT v1; no dependencies."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shlex
import struct
import zlib

HEADER = struct.Struct("<8sHHI6iII")

def compile_cube(text, *, clip_output=False):
    size = None
    domain = {"DOMAIN_MIN": [0., 0., 0.], "DOMAIN_MAX": [1., 1., 1.]}
    seen = set()
    rows = []
    title = ""
    for line_number, line in enumerate(text.splitlines(), 1):
        try:
            fields = shlex.split(line, comments=True)
        except ValueError as error:
            raise ValueError(f"line {line_number}: {error}") from error
        if not fields:
            continue
        key = fields[0]
        if key in ("TITLE", "LUT_3D_SIZE", "DOMAIN_MIN", "DOMAIN_MAX"):
            if key in seen or rows:
                raise ValueError(f"line {line_number}: duplicate or late {key}")
            seen.add(key)
            if key == "TITLE":
                if len(fields) != 2:
                    raise ValueError(f"line {line_number}: TITLE requires one quoted string")
                title = fields[1]
            elif key == "LUT_3D_SIZE":
                if len(fields) != 2:
                    raise ValueError("LUT_3D_SIZE requires one integer")
                size = int(fields[1])
                if not 2 <= size <= 65:
                    raise ValueError("LUT_3D_SIZE must be 2..65")
            else:
                if len(fields) != 4:
                    raise ValueError(f"{key} requires three values")
                domain[key] = [float(v) for v in fields[1:]]
        else:
            if size is None:
                raise ValueError(f"line {line_number}: expected LUT_3D_SIZE before samples")
            if len(fields) != 3:
                raise ValueError(f"line {line_number}: expected three sample values; unsupported directive {key!r}")
            try:
                row = [float(v) for v in fields]
            except ValueError as error:
                raise ValueError(f"line {line_number}: unsupported directive or invalid sample") from error
            if not all(math.isfinite(v) for v in row):
                raise ValueError(f"line {line_number}: nonfinite sample")
            rows.append(row)
            if len(rows) > size**3:
                raise ValueError("too many samples")
    if size is None or len(rows) != size**3:
        raise ValueError("missing LUT_3D_SIZE or incorrect sample count")
    qdomain = []
    for key in ("DOMAIN_MIN", "DOMAIN_MAX"):
        if not all(math.isfinite(v) and -32768 <= v < 32768 for v in domain[key]):
            raise ValueError("input domain must be finite signed Q16.16")
        values = [round(v*65536) for v in domain[key]]
        if any(v < -(2**31) or v > 2**31-1 for v in values):
            raise ValueError("quantized domain out of range")
        qdomain.extend(values)
    if any(qdomain[i] >= qdomain[i+3] for i in range(3)):
        raise ValueError("domain maximum must exceed minimum after quantization")
    clipped = sum(v < 0 or v > 1 for row in rows for v in row)
    if clipped and not clip_output:
        raise ValueError("output outside 0..1; use --clip-output to explicitly clip")
    samples = [round(min(1., max(0., v))*65535) for row in rows for v in row]
    payload = struct.pack(f"<{len(samples)}H", *samples)
    header = HEADER.pack(b"C80LUT3\0", 1, size, 0, *qdomain, len(payload), zlib.crc32(payload))
    return header+payload, {"title": title, "dimension": size, "table_bytes":len(payload),
                            "blob_bytes":len(header)+len(payload), "clipped_components":clipped,
                            "domain_q16":qdomain, "order":"red fastest, then green, then blue"}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--clip-output", action="store_true")
    args = parser.parse_args()
    try:
        source = args.input.read_bytes()
        blob, info = compile_cube(source.decode("utf-8-sig"), clip_output=args.clip_output)
        info["source_sha256"] = hashlib.sha256(source).hexdigest()
        info["blob_sha256"] = hashlib.sha256(blob).hexdigest()
        info["color_space"] = "unspecified; caller must match LUT input encoding"
        with args.output.open("xb") as target:
            target.write(blob)
    except (ValueError, OSError, UnicodeError) as error:
        parser.exit(2, f"compile_cube: {error}\n")
    print(json.dumps(info, indent=2))

if __name__ == "__main__":
    main()
