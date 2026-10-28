# Canon EOS 80D extension lab

This is the first reproducible research and implementation milestone for a
custom 80D extension project. It contains a read-only firmware-container
inspector, published-source symbol seeds, a camera-specific imaging investigation,
and a portable 3D LUT engine with host-side tests.

**No camera executable is provided. Nothing here has been installed or tested
on a physical 80D. Higher-resolution recording, real-time LUT preview, and
in-camera JPEG processing remain integration work.**

## Firmware baseline

Canon's current support listings identify **1.0.3** as the latest 80D firmware.
The official update was downloaded and inspected on 2026-10-27.

- [Official support listing](https://asia.canon/en/support/0400496402)
- [Official ZIP](https://gdlp01.c-wss.com/gds/4/0400004964/01/eos80d-v103-win.zip)
- Firmware: `80D00103.FIR`, **28,931,264 bytes**
- SHA-256: `aa25b4c1a966b3611078ca86b348475dd676a1eabc6f74a0bdc308bc7b116f8c`
- Model ID: `0x80000350`; embedded version: `1.0.3`
- Whole-file additive checksum: `0x2424b6e1`, independently recomputed and matched.

The model/version and checksum were read from the actual official file. Its
updater starts at file offset `0x120`; the main stored payload starts at
`0x25a390`. These are file locations, not runtime addresses.

The v4 updater header matches the AES-style layout documented by the modern
`fir_tool2.py` parser. The payloads have near-uniform byte distributions; this
alone does not identify a cipher. Independent historical 80D research confirms
that the update uses AES and describes obtaining a ROM dump to analyze code.
We have **not** decrypted this download, verified its HMAC, recovered a ROM,
or decompiled the main camera application.

See [container evidence](evidence/firmware-container.json),
[download provenance](evidence/download-provenance.json), and
[firmware investigation](docs/firmware-investigation.md).

## Run the offline work

Python 3 and a C99 host compiler are enough for the original tools in this lab.
They do not install dependencies, communicate with a camera, or modify a FIR.
Download Canon's official ZIP yourself and extract the FIR outside this repo.

```sh
python examples/canon80d/tools/inspect_fir.py /absolute/path/80D00103.FIR --require-official
python -m unittest discover -s examples/canon80d/tests -v
make -C examples/canon80d/lut test
```

To regenerate the source symbol seeds from the exact upstream revision:

```sh
python examples/canon80d/tools/map_source_symbols.py /absolute/path/to/magiclantern
```

The [LUT README](lut/README.md) documents `.cube` compilation, host rendering,
precision, storage, and remaining camera integration. A LUT needs an explicit
input encoding: an S-Log-to-709 or LogC transform does not become an accurate
80D camera match when applied directly to an ordinary Canon JPEG.

## Investigation tracks

| Track | Current evidence | Next implementation or measurement |
| --- | --- | --- |
| Portable film/look pipeline | Tested host-side `.cube` compiler and C LUT interpolation | Camera ABI, JPEG codec/file completion, allocation and timing |
| Native Picture Styles | Published 80D properties and style controls | Exact-version binary trace and round-trip camera tests |
| LiveView look preview | Published YUV buffers and compositor symbols | Read-only frame snapshot, stride/ownership, private-buffer preview |
| RAW capture | Important EDMAC/register routines are no-op source stubs | Resolve and validate each primitive against a local ROM |
| 2K / cropped RAW | Bandwidth estimates and shared crop code; no 80D mode proven | Baseline frame capture, sensor timing and real SD throughput |
| 4K | No proven 80D high-resolution encoder path | Trace sensor/encoder support; investigate compression, burst and low-fps paths |
| Other shooting aids | Existing OS, task, GUI, file I/O and property mappings | Validate diagnostics and original capture/playback before integration |

The [imaging report](docs/imaging-research.md) links each finding to pinned
upstream source and contains exact bandwidth calculations. For example,
uncompressed 3840x2160 10-bit Bayer at 24 fps is **248.83 MB/s** before overhead.
That exceeds the standard UHS-I bus ceiling of 104 MB/s. It rules out that
particular continuous uncompressed SD path, not compressed 4K or every higher
resolution experiment. A mode below the bus ceiling is not thereby proven.

## REA execution status

This investigation uses the workflow and contracts in `Blocpod/rea` commit
`37fcea78cecbeeadd869e9a3d77dd133ed264a0a` and its
`skill-src/reverse-engineer-anything/SKILL.md`.

Running `node scripts/rea.mjs doctor --client codex --json` reported the compiled
runtime missing. Automatic approval review rejected installing locked npm
dependencies and Unblob, citing repository installation restrictions. No REA
engine report, Ghidra session, Binwalk scan or Unblob extraction was obtained.
The evidence in this lab comes from its explicitly named original Python tools,
host C executable, published source inspection and primary documentation.

REA's current firmware adapter delegates to Binwalk 3.1.x / Unblob 26.6.x and
does not offer a raw-flash Ghidra load profile. Once its runtime is available,
use the actual firmware commands, retain their full output and limitations,
and select a supported decrypted/native child for native analysis. An archive
scan cannot itself decrypt this Canon update.

## Hardware milestone

The next code-analysis input is an exact-version **ROM dump from the owner's
80D**, obtained through a reviewed model-specific procedure. Before presenting
any camera-side build for installation, verify the camera's displayed version,
the boot/recovery procedure, ABI and instruction addresses, file/GUI behavior,
available RAM and card throughput. This lab does not supply an updater or a
flash command.

## Source and data boundaries

Original lab tools are MIT-licensed under the repository license; the portable
LUT implementation also carries its own MIT notice. Published Magic Lantern
symbols are referenced as source evidence; no ML binary or vendored GPL source
is included. Canon firmware, decoded candidate bytes, proprietary LUTs, camera
images and analysis databases remain outside git. Branded camera or film
matches require suitable reference measurements and licensed source profiles.
