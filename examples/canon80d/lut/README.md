# Canon 80D LUT engine prototype

An original, portable C99 color-processing core and standard-library Python
compiler for common 3D `.cube` LUTs. This code has been tested on the host.
It is **not installed in the camera**, does not change firmware, and does not
establish that the 80D can process live video at any particular rate.

## Build and use

```sh
make test
python3 tools/compile_cube.py examples/warm_soft.cube build/warm_soft.c80lut
./build/c80-grade build/warm_soft.c80lut input.ppm build/output.ppm
make bench
```

The host reads binary P6 PPM with maximum 255 or 65535; 16-bit PPM samples use
the standard big-endian encoding. It preserves dimensions and bit depth.
Output paths must not exist. A malformed raster or I/O failure may leave a
partial newly-created host output, which must be discarded. Original inputs
are read only. The compiler also creates outputs exclusively.

`tools/generate_examples.py` regenerates the two sample LUTs. `identity` is a
calibration fixture; `warm_soft` is an original synthetic creative look.
Neither reproduces a named film stock, sensor, camera, or manufacturer profile.
The compiler's JSON output includes the source and compiled-blob SHA-256 digests.

## Accepted LUTs and color limits

The compiler accepts `TITLE`, one `LUT_3D_SIZE` from 2 through 65, optional
`DOMAIN_MIN`/`DOMAIN_MAX`, and exactly size-cubed RGB samples. Samples are ordered
with red changing fastest, then green, then blue. Comments use `#` and titles
may be quoted. Unknown directives, 1D shapers, combined 1D+3D LUTs, missing or
extra samples, duplicate or late directives, infinities, and NaNs are rejected.

An output component outside 0..1 is rejected unless `--clip-output` explicitly
requests clipping; the compiler reports the number of affected components.
This fixed output range means some HDR or scene-linear LUTs lose information
under clipping. Converting such a LUT correctly needs an explicit color-space
and transfer-function pipeline, not simply this flag.

Input and output are normalized RGB represented by integers from 0 to 65535.
The engine does not decode log curves, transform gamuts, debayer RAW, convert
YCbCr, apply white balance, or infer a LUT's intended input color space.
A LUT made for S-Log3/S-Gamut3.Cine, for example, must receive that encoding or
be transformed offline to the actual input encoding. Camera-brand labels do
not make a LUT correct for a Canon JPEG or live-view buffer.

Domain limits are signed Q16.16 values. The compiler rejects limits that are
nonfinite, out of range, or collapse after quantization. Each input is mapped
to that channel's domain and clamped at the endpoints. Table outputs are
normalized unsigned 16-bit values. Trilinear interpolation uses Q16 fractions
and rounds at each linear interpolation. The hot path uses integer operations
only, including 64-bit division for coordinates; ARM may need compiler runtime
helpers. No per-pixel allocations occur. Initialization validates the blob and
decodes it into caller-owned storage. Do not overlap input blob and table storage.

Quantization introduces small errors. The nonlinear end-to-end reference test
allows at most 4/65535 error against independently weighted floating-point
interpolation; it passes on 2,008 random and boundary pixels including a
nondefault domain. A 65-cube identity can differ by one 16-bit unit. These are
test-set results, not a universal error proof or a camera color-match claim.

## Memory and work budgets

| Dimension | Table bytes | Blob bytes |
| --- | ---: | ---: |
| 17 | 29,478 | 29,526 |
| 33 | 215,622 | 215,670 |
| 65 | 1,647,750 | 1,647,798 |

The C core has a small context, caller-owned table, and constant-size stack
temporaries. It samples eight grid corners and performs 21 scalar linear
interpolations for each RGB pixel. A 1920×1080 RGB8 frame alone is 6,220,800
bytes; 24 fps touches 149,299,200 input bytes/s before output and conversion.
Processing a scanline or tiles avoids retaining another complete RGB frame.
LUT table size, processing throughput, and memory traffic are separate limits.

`make bench` reports host CPU time for 2,073,600 synthetic pixels and a checksum.
That result does not predict DIGIC 6 speed, DMA access, display latency, RAW
recording performance, power draw, or thermal behavior.

## Binary format: C80LUT v1

All multibyte blob values use little endian. The 48-byte header is followed by
exactly `dimension^3 * 3` unsigned 16-bit sample values. No trailing data is
accepted. The initializer validates bounds and the payload CRC before use.

| Byte offset | Field |
| --- | --- |
| 0 | Eight bytes `C80LUT3` plus NUL |
| 8 | uint16 version = 1 |
| 10 | uint16 dimension, 2..65 |
| 12 | uint32 flags = 0 |
| 16 | Three int32 Q16.16 domain minima |
| 28 | Three int32 Q16.16 domain maxima |
| 40 | uint32 payload bytes |
| 44 | uint32 IEEE CRC-32 of payload, matching Python zlib.crc32 |
| 48 | RGB table, red fastest |

CRC detects accidental payload corruption; it is not a signature. The header
is structurally validated but is not covered by this payload CRC.

## Camera integration remains to be built and tested

1. Establish the exact 80D firmware revision and working extension loader.
2. Identify an RGB buffer or an explicit YCbCr-to-RGB adapter and its ownership.
3. Allocate a bounded table and scanline/tile scratch through known camera APIs.
4. Load a validated LUT outside the render/recording hot path.
5. Verify the LUT offline against real 80D files, then on saved-image processing.
6. Measure on hardware before attempting live preview or a recording path.

Changing a preview does not establish that the saved JPEG or movie contains the
look. Applying a transform to a JPEG preview is not processing original sensor
data. No camera hooks, boot-flag changes, firmware patches or flasher are included.

## License

Original project source and synthetic samples are MIT licensed; see LICENSE.
User-supplied LUTs retain their own licensing and usage requirements.
