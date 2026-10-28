# Canon 80D imaging and recording investigation

Source revision: `142472e95054d73640f50789ac0fd66325499d82` in Magic Lantern `dev`. Date: 2026-10-27.

Scope: offline source inspection and theoretical arithmetic. No physical camera, runtime capture, firmware build, or camera qualification was performed by this worker. These findings can guide implementation; none establishes a new working camera mode.

## Findings

The existing 80D port is a useful OS/UI/file-I/O foothold. Its raw-video blockers are concrete: important DMA/register operations are stubs, MVR constants are placeholders, SRM support is unqualified, and the required recorder/crop modules are hidden. The missing operations have to be reverse engineered and verified before enabling features. A compiling build would not establish imaging functionality.

| Evidence | Observation | Source |
| --- | --- | --- |
| IMG-001 | 80D build target is firmware 1.0.3, ARMv7-R Thumb, with boot-d678.o. | [platform/80D.103/Makefile:1](https://github.com/reticulatedpines/magiclantern_simplified/blob/142472e95054d73640f50789ac0fd66325499d82/platform/80D.103/Makefile#L1) |
| IMG-002 | EDMAC setup, routing, start/abort and callbacks are no-op overrides; engine writes are no-ops; shamem_read returns zero. | [platform/80D.103/function_overrides.c:112](https://github.com/reticulatedpines/magiclantern_simplified/blob/142472e95054d73640f50789ac0fd66325499d82/platform/80D.103/function_overrides.c#L112) |
| IMG-003 | 80D MVR recording constants are explicitly marked junk; HD DMA address is zero. | [platform/80D.103/consts.h:78](https://github.com/reticulatedpines/magiclantern_simplified/blob/142472e95054d73640f50789ac0fd66325499d82/platform/80D.103/consts.h#L78) |
| IMG-004 | State-object hooks disabled and programmatic image capture explicitly marked not working. | [platform/80D.103/features.h:26](https://github.com/reticulatedpines/magiclantern_simplified/blob/142472e95054d73640f50789ac0fd66325499d82/platform/80D.103/features.h#L26) |
| IMG-005 | SRM memory pool support is marked untested; required buffer size not found. | [platform/80D.103/internals.h:17](https://github.com/reticulatedpines/magiclantern_simplified/blob/142472e95054d73640f50789ac0fd66325499d82/platform/80D.103/internals.h#L17) |
| IMG-006 | Only bench and file_man are included; raw recording and crop modules are hidden. | [platform/80D.103/modules.hidden:1](https://github.com/reticulatedpines/magiclantern_simplified/blob/142472e95054d73640f50789ac0fd66325499d82/platform/80D.103/modules.hidden#L1) |
| IMG-007 | Picture-style selection/settings are whitelisted; MVR recording property handlers are denied. | [platform/80D.103/property_whitelist.h:28](https://github.com/reticulatedpines/magiclantern_simplified/blob/142472e95054d73640f50789ac0fd66325499d82/platform/80D.103/property_whitelist.h#L28) |
| IMG-008 | The 80D uses 11 picture styles. Shared picture style struct exposes contrast/sharpness/saturation/color tone plus fineness/threshold. | [src/picstyle.c:97](https://github.com/reticulatedpines/magiclantern_simplified/blob/142472e95054d73640f50789ac0fd66325499d82/src/picstyle.c#L97) |
| IMG-009 | MLV Lite disables lossless compression when DIGIC generation is not 5. | [modules/raw_video/mlv_lite/mlv_lite.c:4551](https://github.com/reticulatedpines/magiclantern_simplified/blob/142472e95054d73640f50789ac0fd66325499d82/modules/raw_video/mlv_lite/mlv_lite.c#L4551) |
| IMG-010 | The current crop-rec camera-init branches cover 5D3/EOSM/700D/650D/100D/6D and contain no 80D path. | [modules/crop_rec/crop_rec.c:1939](https://github.com/reticulatedpines/magiclantern_simplified/blob/142472e95054d73640f50789ac0fd66325499d82/modules/crop_rec/crop_rec.c#L1939) |
| IMG-011 | 80D stores mapped YUV LiveView buffers and Ximr compositor symbols. | [platform/80D.103/consts.h:68](https://github.com/reticulatedpines/magiclantern_simplified/blob/142472e95054d73640f50789ac0fd66325499d82/platform/80D.103/consts.h#L68) |
| IMG-012 | File create/open/read/write/size/rename/delete and GUI/task primitives have recovered addresses. | [platform/80D.103/stubs.S:40](https://github.com/reticulatedpines/magiclantern_simplified/blob/142472e95054d73640f50789ac0fd66325499d82/platform/80D.103/stubs.S#L40) |
| IMG-013 | 80D calibration matrix exists in shared raw code. | [src/raw.c:404](https://github.com/reticulatedpines/magiclantern_simplified/blob/142472e95054d73640f50789ac0fd66325499d82/src/raw.c#L404) |
| IMG-014 | Frame rate base clock is copied from 700D. | [src/fps-engio.c:282](https://github.com/reticulatedpines/magiclantern_simplified/blob/142472e95054d73640f50789ac0fd66325499d82/src/fps-engio.c#L282) |
| IMG-015 | Shared raw backend uses EDMAC geometry/buffer detection; 80D does not enable CONFIG_RAW_LIVEVIEW or CONFIG_RAW_PHOTO in its platform files. | [src/raw.c:695](https://github.com/reticulatedpines/magiclantern_simplified/blob/142472e95054d73640f50789ac0fd66325499d82/src/raw.c#L695) |

## Color and film-look route

1. **Native picture-style control**: use the recovered, whitelisted selection/settings surface to establish readback and round-trip behavior. This is useful but only adjusts six existing parameters; it does not reproduce a full 3D LUT. Imported Canon Picture Styles are a different file format and need their own analysis.
2. **Asynchronous post-shot look engine**: discover completed new JPEG/CR2 files using known file-I/O primitives; decode a JPEG, apply a shared integer LUT engine, encode a separate JPEG. Start from user-supplied reference images and keep original files. This avoids solving RAW DMA first, but needs proven file completion, available RAM, task scheduling and codec throughput. Full RAW development is a later path with its own memory/compute costs.
3. **Live preview**: mapped YUV display buffers and compositor symbols are plausible entry points. First capture and inspect a frame with correct stride and ownership; then test a reduced-resolution private-buffer preview. Editing a display surface is not evidence the look reaches saved files. Arbitrary frame-synchronous filtering lacks the 80D state-object integration currently disabled.
4. **Native JPEG/ISP hook**: find actual curve/matrix/3D table load paths in the binary and compare them with Canon picture-style loading. This could be much faster than CPU pixel processing, but no such arbitrary LUT hook is established by the inspected source.

A 17³ RGB16 table is 29,478 bytes, 33³ is 215,622 bytes, and 65³ is 1,647,750 bytes. Those sizes are practical reference points; they do not establish CPU interpolation throughput, available safe RAM, or frame rate. A larger table also cannot recreate another camera's sensor spectral response, noise, lens characteristics, and scene-dependent ISP processing; camera-matching presets need an explicit input color space and measured targets.

## Higher resolution: known capability and missing evidence

Canon's [80D specifications](https://asia.canon/en/support/6200320100) document 6000×4000 stills, 14-bit RAW and UHS-I media. Factory video is up to 1920×1080 with frame rates depending on format. A still sensor delivering 24 MP does not prove 24 MP at video rate. The readout mode, sensor timing, DMA routing, buffers, processing and output path are separate constraints.

Calculated uncompressed Bayer payload at **24 fps**, decimal MB/s:

| Geometry | 10-bit | 12-bit | 14-bit |
| --- | ---: | ---: | ---: |
| 1920×1080 | 62.21 | 74.65 | 87.09 |
| 2560×1080 | 82.94 | 99.53 | 116.12 |
| 2560×1440 | 110.59 | 132.71 | 154.83 |
| 3072×1024 | 94.37 | 113.25 | 132.12 |
| 3840×2160 | 248.83 | 298.60 | 348.36 |
| 6000×4000 | 720.00 | 864.00 | 1008.00 |

Formula: width × height × bits per pixel ÷ 8 × fps. Excludes optical-black rows/columns, pitch alignment, metadata, file-system overhead, audio and buffer-copy cost. Actual Canon RAW may need a wider/taller source frame.

The [SD Association](https://www.sdcard.org/developers/sd-standard-overview/bus-speed-default-speed-high-speed-uhs-sd-express/) specifies a standard UHS-I bus ceiling of 104 MB/s; it explicitly distinguishes that from sustained writing speed. The 80D's actual write speed is unmeasured here. Standard-path continuous uncompressed UHD RAW at 24 fps requires at least 248.83 MB/s even at 10-bit, so that mode cannot fit the standard UHS-I ceiling. That arithmetic does **not** rule out compressed video, short buffered bursts, a narrower/taller crop, lower fps, or time-lapse. Conversely, a payload below 104 MB/s does not prove that any such candidate mode works.

The existing MLV Lite code disables lossless compression outside DIGIC 5; an 80D/DIGIC 6 codec port is new work. Existing crop_rec init code has no 80D branch. There is no source evidence here for a working 80D 4K encoder or larger sensor crop mode. The generic raw sampling assumptions must not be promoted to 80D sensor measurements.

## Next experiments with explicit pass criteria

1. Pin input firmware hash and source revision; map exported update sections to runtime addresses. Cross-check recovered 80D OS/file/GUI addresses against the actual binary before using them.
2. Build a diagnostic-only extension; validate start/stop, menu return, original capture/playback and log flush. Use existing recovery procedure and exact-version boot code. No sensor or flash writes are needed for this milestone.
3. Export bounded read-only display/frame snapshots and timestamps, then validate format/stride and frame cadence on a computer. Identify capture completion and RAW-buffer ownership. Replace one missing primitive at a time with exact-version code and tests.
4. Measure SD throughput with existing bench module using expendable test files and known card; record allocation size, filesystem, card model, minimum sustained throughput, latencies and readback digests. Do not infer speed from card packaging.
5. Run host LUT engine against identity/ramp/color patches and independent reference interpolation; integrate one post-shot JPEG path and compare camera-produced output with host output. Evaluate memory, file completion, time per photo and recovery after interruption.
6. Establish unmodified RAW-frame capture at an existing sensor mode before changing crop geometry. Validate frame hashes, metadata, black levels, Bayer order, dropped frames and stop behavior.
7. Capture sensor register/timing sets for stock movie/photo/5×/10× modes. Trace them to actual sensor input and encoder output; investigate geometry and timing only after the baseline agrees with observations.
8. Implement candidates one at a time: low-fps RAW, crop geometry, reduced bit depth, then compression/encoder work. Publish measured limits rather than a maximum-resolution claim based on menus or a single frame.

## Build details

The target uses Cortex-R4 / ARMv7-R Thumb (`platform/80D.103/Makefile:17`). Existing build defaults to `arm-none-eabi-*` (`Makefile.globals:16`). This worker did not compile a camera image. Host-side LUT tests and mocks cannot qualify a camera executable.
