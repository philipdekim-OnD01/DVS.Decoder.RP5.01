# Event B — independent offline application

This Linux C++20/Python3 package reuses PR5's file reader, bounded queue, C++ decoder and renderer, and PR13's source/baseline interpretation. It does not change RAW2 A or implement restore/Switcher code. **Phase C HARD BLOCKED; `--device PHASE_C_BLOCKED`.**

Read main AGENTS, Issue15 latest body/comments and PROGRESS before resuming. B0–B5 checkpoints are recorded there. Do not repeat completed A/B analysis or native/mock suites to rebuild context.

## Build (no install)

Requirements: Linux with GCC C++20/pthreads, Python3, approved private SDK source, ext-family/tmpfs regular input. The public repository cannot supply the private SDK or sample. macOS native engine build is deliberately unsupported; the existing RP5 regular-file guard is retained. Browser Viewer/Node checks may run on macOS.

From this checkout, using a fresh private output path whose parent already exists:

```sh
python3 event-b/build.py --sdk PRIVATE_SDK --output /tmp/event-b-package-UNIQUE
/tmp/event-b-package-UNIQUE/bin/event-b info
```

The build makes a private SDK copy with the existing checked carry/EOF patch and compiles **EVENT_FILE_ONLY**: no V4L2 capture/service-check code. Artifacts are isolated under bin/config/share/runs/build; source/SDK/binary hashes and actual compiler command are in manifest.json. No sudo, global installation, systemd, startup script, I2C, driver, media or boot changes. The private build directory contains SDK source and must not be published. Compilation failure leaves that fresh private tree for diagnosis; retry in a new tree.

## Run and view

```sh
/tmp/event-b-package-UNIQUE/bin/event-b replay --file PRIVATE_APPROVED_EVENT_SAMPLE --name sample
/tmp/event-b-package-UNIQUE/bin/event-b serve --name sample --port 8767
```

Open **http://127.0.0.1:8767** on the same host. If running on Pi, use a separate user-owned SSH tunnel from the desktop (`ssh -N -L 8767:127.0.0.1:8767 philip@192.168.0.177`), then open the local URL. This is loopback file serving, not live camera capture. Stop the viewer server with Ctrl+C and stop only the owned tunnel afterward.

The 960×720 Viewer provides play/pause, frame seek, display fps, ON green/OFF red filters, per-frame timestamp/period/event counts and final file/queue/CPU/EOF metrics. Display fps is presentation speed, not sensor measurement. It loads completed frames after replay; no real-time sensor input. Images, frames.bin, metrics/status/logs remain private in package/runs/NAME. Browser size limit128MiB. Frame ABI is the recorded little-endian SDK SensorFrame16B/EventGroup6B; another ABI needs explicit format adaptation.

Optional config must be a fresh file **inside package/config**:

```json
{"queue_capacity":8,"decode_delay_us":0}
```

Use `replay ... --config PACKAGE/config/custom.json`. Exactly these integer keys are accepted; capacity1..32 and delay0..1000000µs. Bool/duplicate/extra keys and nonregular/symlink/oversized config are rejected before engine launch. O_PATH pins config without device/FIFO data opens. `decode_delay_us` is for offline backpressure/signal testing. Existing run names are never overwritten; names allow letters/digits/underscore/hyphen up to64 chars. Output always belongs to package/runs.

Exit0 means complete replay,1 means engine/runtime failure,2 means CLI/config/preflight/device refusal,130 means interrupted. status.json records actual engine exit and complete=false for interrupted/failed runs once an output directory exists; stdout/stderr logs are kept. Preflight rejection creates no run. `error=false` metrics alone do not imply completion: consult exit/status. SIGINT/SIGTERM are forwarded to the owned child. A terminal read-only regular file is required; missing/empty/symlink/special inputs fail closed (existing Linux guard also checks pinned inode/filesystem/drift).

## Evidence and new checks

New package native build + one approved-sample E2E: b1-native-build.json/b2-native-e2e.json. New Node render equivalence: b2-render-equivalence.json. Actual browser controls: b3-browser-review.json. New launcher config/status/signal tests: b4-runtime.json. The initial -Werror unused locals and config FIFO stall are recorded with corrections; failed staging trees were retained. No prior suite is recounted as new evidence.

For a **fresh** built package and exact approved source/sample, only when validating relevant changes:

```sh
python3 event-b/check_package.py --package PACKAGE --sample PRIVATE_SAMPLE --results PRIVATE_AGGREGATES.json
python3 event-b/check_runtime.py --package PACKAGE --results PRIVATE_RUNTIME.json
node event-b/check_viewer.mjs PACKAGE/runs/approved-sample
```

Checks create new test-owned run/config fixtures; use a fresh package for repeat runs. Node needs copied private results if reviewing on another host. Do not put sample/SDK/images/event traces/frames or private package binaries into public Git. Publish only reviewed aggregate evidence.

## Scope and limitations

The approved sample yields1557 completed frames and1469217 SDK-counted events (ON706157/OFF763060), unsynced830 as already explained in PR13. Completed frame payloads carry1468615 events; these counters cover different spans and the stream ends with one incomplete frame. No event-loss claim follows. Logical timestamp/coordinate rendering is not authentication of physical finger identity or sensor accuracy.

File/queue/Viewer integration is verified offline. **NOT TESTED:** this package's live CSI reception, physical coordinates/time/fingers, actual sensor loss, hardware switching or RAW2 restoration. Existing A is untouched. Future hardware work requires a separate explicit task/approval and Issue7 preflight; restore development is outside this Issue15 package.
