# Actual firmware-container investigation

Date: 2026-10-27. Target: owner-requested Canon EOS 80D 1.0.3.
Camera-reported firmware remains unconfirmed; the downloaded reference is known.

## Observations

| ID | Observation | Evidence |
| --- | --- | --- |
| FIR-001 | Canon's support listings identify 1.0.3 as the latest available 80D update. | [Canon](https://asia.canon/en/support/0400496402), [current firmware list](https://www.canon.com.au/cameras/eos-80d/support?option=drivers) |
| FIR-002 | The official ZIP was downloaded from Canon's redirect to gdlp01.c-wss.com; the FIR size matches Canon's 28,931,264-byte listing. | `evidence/download-provenance.json` |
| FIR-003 | Header model ID 0x80000350 and version 1.0.3 match the intended target; embedded size equals file size. | `tools/inspect_fir.py`, `evidence/firmware-container.json` |
| FIR-004 | The ones-complement additive checksum independently recomputes to 0x2424b6e1. | Same report; excludes only the four-byte checksum field |
| FIR-005 | Updater and main-payload ranges are nonoverlapping, contiguous and terminate at the expected end of file. Nested main-data lengths agree. | Same report |
| FIR-006 | Fields at 0xc0..0x11f are nonzero; modern fir_tool2.py uses this to distinguish AES-style updater headers from legacy XOR headers. | [Parser](https://github.com/lclevy/d8_oracle/blob/a98533090e1ef16a8f56193dbb5dd410222a71aa/ml_scripts/fir_tool2.py) |
| FIR-007 | Stored updater and main payload have byte entropy approximately 7.99992 and 7.99999 bits/byte. | Independently counted by `inspect_fir.py`; not a cipher identification |
| FIR-008 | Published research specifically on the 80D reports AES-protected updates and using a Portable ROM Dumper before disassembling firmware. | [Check Point, 2019](https://research.checkpoint.com/2019/say-cheese-ransomware-ing-a-dslr-camera/) |
| FIR-009 | Published 80D platform source supplies 86 literal nonzero symbol-address seeds extracted by this lab. They have not been verified against a local ROM. | `evidence/80d-source-symbols.json` |
| FIR-010 | REA's doctor command exits with compiled-runtime-missing. Dependency and engine installation requests were rejected by automatic approval review. | Local command observation; no provider Evidence IDs were produced |

## Stored ranges

| Region | File offset | Length |
| --- | ---: | ---: |
| Outer header | 0x0 | 288 |
| Stored updater | 0x120 | 2,466,416 |
| Stored main payload (including its header) | 0x25a390 | 26,464,560 |
| Stored main data | 0x25a410 | 26,464,432 |

The payload and data rows overlap intentionally: data is a child range within
the payload. The outer header, updater and main payload are a disjoint top-level
partition. File offsets cannot be added to 0xfe0a0000 to infer runtime addresses:
decryption and the vendor's module layout must first be established.

## What this has and has not established

The actual input is pinned by SHA-256, its model/version and structural lengths
agree, and its additive checksum is intact. HMAC-SHA1 header slots are present;
their authenticity has not been verified because the required keys are absent.
The official download origin and a local digest are provenance facts, not a
manufacturer-signed attestation of the local file.

The legacy XOR updater formula was tried on a temporary candidate and did not
produce the expected executable markers. That candidate was discarded. Reading
the modern parser clarified the AES-style layout. It is not a decrypted updater,
and no result from that failed trial is presented as code.

No decrypted code was available for native function analysis. The 86 labels are
published-source research seeds, not 86 functions recovered from this download.
No assumption about a feature being disabled or intentionally withheld is made
from an address, a menu string, or a shared source branch.

## Next native-analysis handoff

1. Obtain the owner's exact-version ROM through a reviewed 80D-specific dump
   procedure; preserve its provenance, segment bases, size and SHA-256.
2. Import the correct ARMv7-R/Thumb regions with their actual memory bases into
   a native analysis engine that supports raw firmware. REA's current native
   admission does not supply this raw-flash import profile.
3. Validate the published OS/file/GUI labels against instructions, calling
   conventions and references. Resolve genuine byte locations before patching.
4. Trace picture-style/curve load, completed-JPEG notification and codecs first;
   trace EDMAC, sensor geometry, buffer allocation and movie encoder separately.
5. Preserve an evidence graph from entry points through actual state and data
   writes. Bring each proposed extension back to hardware qualification.

REA firmware region inspection and extraction remain useful for container
inventory once configured, but generic Binwalk/Unblob extraction does not supply
the missing Canon decryption keys or constitute native decompilation.

## Environment work still requiring approval

The fresh REA checkout has no built runtime. Its own launcher requests
`npm ci` and `npm run build:cached`. Automatic review rejected a pinned
Node/npm download, then the safer existing-runtime `npm ci --ignore-scripts`
request, then Unblob installation, citing repository restrictions on unrelated
software installation. None was bypassed. Node 24.22.1 already satisfies the
package's declared engine range; no additional Node download is needed.

The narrow follow-up request is approval to install REA's lockfile dependencies
and build its runtime using the existing Node, then provision approved
workspace-scoped firmware/native analysis prerequisites. This is separate from
writing any firmware to the camera. The current source/build investigation and
LUT tests do not depend on granting that approval.
