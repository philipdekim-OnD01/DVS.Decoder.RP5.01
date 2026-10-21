# Event decoder offline experiment — 2026-10-21

Approved scope: isolated C++ core build and file replay. No Pi connection, device open, sensor register changes, service actions, kernel/DT installation or reboot. This is the first Phase 3 increment; V4L2 threads, viewer, live metrics and hardware validation remain unimplemented.

## Reproduce

Requires Python 3, a C++20 `clang++`, the privately supplied extracted SDK and decompressed sample. Run from this directory:

```sh
python3 verify.py /path/to/nrv-dvs-jetson/sdk /path/to/sample.bin --results results.json
```

`verify.py` copies the supplied SDK into a temporary directory, builds only decoder/source/pipe and their public wrappers, and supplies empty visibility macros in a generated export header. It excludes device/stream, register controls, Jetson drivers and boot scripts. The original SDK is never modified. A temporary patched variant stores partial 4-byte words across calls and clears carry when upstream reports discontinuity. Patch anchors are checked before replacement. Private source, binaries and sample are not committed. Temporary executables are removed on exit; the build is reproducible through this command.

## Actual results

Host: macOS Darwin arm64, Apple clang 21.0.0. Both original and patched C++ cores built successfully with C++20/O2/pthread. This is **not** a Raspberry Pi native build or a complete SDK build.

8,388,608-byte sample SHA256: `962925dfaf87fcd1a16d04cd6e122d32558527b543f39acc2803926f2fc897b3`.

| Variant | Input chunk bytes | Output complete frames | Decoded events | invalid / unknown / frame gaps |
|---|---:|---:|---:|---|
| Original | 1,048,576 | 1,557 | 1,469,217 | 0 / 0 / 0 |
| Original | 4,093 | 0 | 142,541 | 222,451 / 960,107 / 385 |
| Carry fix | 1,048,576; 4,093; 4; 1 | 1,557 each | 1,469,217 each | 0 / 0 / 0 each |

All four fixed outputs match the aligned original byte-for-byte by SHA256 `e15a8a75899f6352725e0a4fbcd73f537acd1496fda6ae8ac25cd17903be1798`. The script checks both output hashes and semantic counters (excluding intentionally differing input buffer counts). Events are SDK statistics including CID0+CID1, not necessarily all rendered CID0 events. The prior PR's 1,558 frame-ending-word count is a different measure from 1,557 complete frames emitted by this SDK; this experiment does not explain or validate every sample boundary.

## Limits and next steps

This proves sample chunk-boundary invariance after the carry fix, not full protocol correctness or live DT 0x31 reception. Synthetic malformed input, timestamp wrap, frame-count wrap, discontinuity/reset, randomized splits and explicit truncated EOF accounting still need tests. Partial words at EOF remain silently unreported by the SDK; the carry fix does not yet expose that counter. Raw struct output includes ABI layout and is a same-host comparison artifact, not a portable recording format. No throughput, CPU, zero-loss, sensor fps or RP5 success claim is made.

Next: complete these parser tests and design the bounded capture/decode pipeline and 960×720 viewer. Hardware work requires separate approval and isolation from production at `philip@192.168.0.177`.

## Phase A continuation (2026-10-21)

`phase_a.py SDK SAMPLE RESULTS_JSON` builds the temporary patched core with `g++` (override `CXX`) and runs 17 protocol/chunk regressions. It adds explicit partial-word/incomplete-frame EOF counters, gap injection and seeded randomized splitting. `evidence/local-regressions-20261021.json` is the actual **macOS** regression evidence. Native Pi execution is pending the blocked private SDK/sample transfer; see PROGRESS.md. No hardware gate has passed.
