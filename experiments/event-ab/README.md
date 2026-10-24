# Issue11 offline A/B (no hardware)

Read main AGENTS, Issue11 latest body/comments, PROGRESS and the last checkpoint before resuming. P0–P4 evidence is complete; do not rerun previous suites just to rebuild context. RAW2 Issue1 remains UNKNOWN/STOP. Phase C HARD BLOCKED; these tools have no device capture backend.

Private inputs are **not** provided by Git. P0 pins the approved 8MiB word stream, deployed legacy sources and SDK decoder source hashes. Legacy sources lack a Git history; historical binary equivalence is UNKNOWN. Do not substitute different sources silently. Private source/sample/frames/event/control traces must remain outside the public checkout.

On the recorded macOS arm64 / Apple clang21 host, with exact pinned sources already available privately:

```sh
python3 experiments/event-ab/build.py --sdk PRIVATE_SDK --legacy PRIVATE_LEGACY --work NEW_PRIVATE_BUILD
python3 experiments/event-ab/run_ab.py --work NEW_PRIVATE_BUILD --sample APPROVED_EVENT_SAMPLE --results PUBLIC_AGGREGATES.json
python3 experiments/event-ab/classify_unsynced.py --sample APPROVED_EVENT_SAMPLE --work NEW_PRIVATE_BUILD --results PUBLIC_UNSYNCED.json
python3 experiments/event-ab/test_observer.py --work NEW_PRIVATE_BUILD --results PUBLIC_SYNTHETIC.json
```

`build.py` requires a fresh work/sdk destination, calls existing `prepare_core.py` and adds checked observation hooks only to that private copy. The hook records byte offsets before every word and logical events at the actual SDK acceptance point, before CID0 completed-frame filtering; an RAII guard records actual unsynced counter increments plus pre-word context. Prefix event counts therefore compare SDK statistics, not just completed-frame payloads. Native private source files are not regenerated from a Python model. Trace bridge is little-endian in the recorded environment; do not treat its binary event format as portable to arbitrary hosts.

The legacy wrapper invokes actual `decode_batch` for each 4B word. It sets 960×720, one frame slot, gen4 CID, hold_cycles0, strict frame-end, same-group=false, and explicit reference-b3-only true/false. These are reproducible algorithm-comparison conditions, not a claim to reproduce old production settings. Reference forcibly uses B3 as ON; dual uses both masks. Suppression is disabled. Event timestamp_ns0 is a host-input placeholder, not sensor time. Legacy EOF has no explicit finalize; the fixed sample is word-aligned.

For timestamp field verification, rerun **only** the legacy observation required for the newly logged controls, then reuse the SDK output from A/B:

```sh
AB_TRACE_PREFIX=NEW_PRIVATE_BUILD/dual-time NEW_PRIVATE_BUILD/legacy APPROVED_EVENT_SAMPLE dual
python3 experiments/event-ab/compare_timestamps.py --work NEW_PRIVATE_BUILD --results PUBLIC_TIMESTAMP.json
```

Complete frames are read using the recorded SDK ABI: SensorFrame16B / EventGroup6B. Last incomplete frame has no completed output and is excluded. Build pins/commands and aggregate output SHA are evidence; raw traces and frame contents must not be committed. The initial test expected-offset and ABI-stride mistakes and corrections are recorded in the report.

Result: all830 SDK unsynced increments occur at file offsets4..5732 with valid X but missing ref/sub/epoch. Their exact offset set equals dual-versus-SDK differences;1073 extra dual events account for the difference. Column-orphan0 is a different metric, not a contradiction. Timestamp1557 paired fields agree. Physical time/coordinates, original V4L2/CSI boundaries, prefix provenance, actual wire loss, other SDK/sensor revisions and live restoration remain UNKNOWN/NOT TESTED. No production decoder patch was justified or applied. See `docs/event-dt31/EVENT_OFFLINE_AB_20261025_KO.md` and Issue11 for the authoritative checkpoint.
