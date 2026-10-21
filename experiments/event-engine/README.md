# Phase B experimental event engine

Linux C++20 capture worker + bounded byte queue + decoding on main thread. File mode blocks on full queue; device mode drops oldest with explicit discontinuity. Public harness links private Minsu SDK core from an isolated patched copy. No production source or configuration is modified.

Run the **file-only** gate on Pi:

```
python3 gate_b.py /tmp/dvs-event-phase-a-20261021/sdk /tmp/dvs-event-phase-a-20261021/sample.bin /tmp/dvs-event-gate-b-UNIQUE
```

It builds `engine`, tests real sample decoding, a capacity-one slow consumer, SIGTERM/resource shutdown and missing input. It records final CPU, queue, byte/buffer/event rates, decoder counters and raw V4L2 buffer logs. File rates are replay throughput, never sensor performance. CSI counters remain null when not measured. The native compiler/sanitizer and mock results are recorded in PROGRESS.md.

The 960×720 PPM snapshot is updated every 100 decoded frames and at completion. `viewer.html` reads it into a canvas; gate copies it into each successful output directory as index.html. For local browsing, serve that output directory on loopback and use SSH forwarding. Viewer is intentionally separate from capture. Final metrics appear only when the engine stops; it is not yet a live telemetry dashboard.

Device mode is a gated adapter, **not permission to capture**. It requires `--device PATH EXPECTED_BUS WIDTH HEIGHT OUTDIR 10 --armed`, inactive production (systemctl status exit 3), exact `rp1-cfe`/`rp1-cfe-csi2_ch0` identity + expected bus, GREY negotiation, sane MMAP/bytesused bounds, and a fresh output directory. It caps reception at 10 seconds and releases STREAMOFF/MMAP/fd on exceptions. An external verified rollback watchdog and all runbook preflight remain mandatory. Do not run on a production device before Gate C preflight. Source compiles in file gate, but ioctl behavior has not been exercised by file mode.


Actual Gate B results (Pi GCC14.2): release and ASan/UBSan file tests PASS; output hash matches Gate A. Capacity8 normal and capacity1/2ms-delay consumers both decode 1,557 frames / 1,469,217 events without queue drops. Independent input-word counter sees 1,558 CID0 Frame End words. EOF reports 1 incomplete frame and 0 partial bytes. Unsynchronized groups=830; these are not mislabeled as zero drops or valid output events. SIGTERM stops within the 5s test bound; missing input fails cleanly; active production refuses live mode before device open. Queue unit tests cover live drop discontinuity propagation and blocked-producer wakeup on shutdown. Viewer canvas rendering was visually checked using a private temporary image, which is not committed. Temporary review server was stopped.

No real V4L2 ioctl, CSI diagnostics, physical Viewer/HDMI output or live capture was tested. The strict device identity/negotiation and cleanup code is compiled but still requires fault-injection/ioctl and actual hardware verification before being treated as validated behavior. `sequence_gaps` counts gap incidents, not estimated missing buffers. File buffer rates include rendering/file-output overhead and are not hardware capacity measurements. CPU percent uses process CPU divided by wall time and can exceed 100% across threads. `--sanitize` selects native AddressSanitizer/UndefinedBehaviorSanitizer; see aggregate evidence JSON. Phase C is STOP on recovery preflight; see docs/event-dt31/RECOVERY_PREFLIGHT_KO.md.


## Hard hold update

`--device` is now unconditionally refused with `PHASE_C_BLOCKED` before any systemctl/device/output operation. The previous service-inactive guard is not an authorization route. Only file/mock use is allowed. `v4l2_mock_test.cpp` replaces every adapter OS operation and covers 22 ASan/UBSan cases on Pi, including partial setup cleanup and invalid input. These complement the preserved earlier file/queue/Viewer evidence; they do not validate real device behavior. Empty buffers and zero request geometry are rejected; capability string comparisons are bounded. See new mock and hard-hold evidence JSON.


## File-input boundary (2026-10-22)

Plain ifstream acquisition was replaced with `RegularInput`. Linux O_PATH pins the inode without activating a device data file; type/filesystem checks precede the read open through the pinned proc fd. Only regular ext-family/tmpfs files are accepted. Symlinks, FIFOs, directories and kernel virtual files are refused and file size/mtime changes abort replay. This is an intentional RP5 experiment constraint; copy approved samples to an ordinary experimental filesystem rather than weakening it. New7 type/drift and6 engine/CLI guard cases passed on Pi ASan/UBSan. The changed acquisition path preserved the approved sample hash. --device remains unconditionally BLOCKED.
