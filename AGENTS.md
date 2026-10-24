# Codex operating guidance — RP5 S5KRC1S Event Packet experiment

**Scope:** The instructions in this file apply to work involving S5KRC1S DVS CSI-2 Event Packet (DT `0x31`) on Raspberry Pi 5. They do not authorize unrelated operations on this repository or on devices.

## ACTIVE NEXT TASK — Issue #15: build independent Event B first (2026-10-25)

- **User priority / one work card:** [Issue #15 — preserve production RAW2(A), finish independent Event(B)](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/15). Execute B0–B5 in order with file/mock only, based on existing Event PR #5 and bounded diagnostic PR #13. Reuse working components; don't create another general-purpose restore application. Read Issue #15 body and latest checkpoint after every session reset.
- **Completed work:** Pi RAW2 Issue #1 / PR #10 remains UNKNOWN/STOP; Event Issue #11 P0–P5 / PR #13 established 830 prefix unsynced GROUP words before ref/sub/epoch and 1,073 legacy dual-only event difference for the bounded 8MiB replay. Preserve the original evidence without redoing those analyses or automatically merging PRs.
- **Resume protocol:** read AGENTS, Issue #15 latest body/comments, Blue-Green plan §5, PR #5/#13 relevant files/tests, `PROGRESS.md`, then active branch/HEAD/`git status`; pick only the next unfinished B task. After each meaningful B step, append host/real commands/hash/test results/NOT TESTED/blockers/one NEXT to `PROGRESS.md` on the feature branch, commit/push, and comment `DONE/EVIDENCE/TEST/BLOCKER/NEXT` on Issue #15.
- **Differentiate development vs hardware switch:** keeping software A intact means no restoration work is needed for **offline B development**. It does **not** physically isolate the single S5KRC1S/CSI or remove recovery prerequisites for a **future live A→B→A hardware switch**. That separate [Issue #7](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/7) remains a HOLD/future gate, not this task's primary work queue.
- **Safety:** A production entirely untouched; no operational service, I2C, /dev/video device open/STREAMON, kernel/module, Device Tree, media graph, watchdog/rollback/start script, live capture, reboot or private-source publication. Event `--device PHASE_C_BLOCKED` and Phase C **HARD BLOCKED** stay enabled. No permissions for live experiments follow from this document.
- **Branch discipline:** keep PR #5, #10, #13 intact; work in a separate limited B feature branch and publish a Draft PR. Never directly commit application code to main or publish private SDK/setfile/RAW.

## Issue #15 checkpoint — independent offline package submitted (2026-10-25)

B0–B5 implementation/evidence are on `codex/event-b-standalone-20261025`. Read Issue #15 latest comments and the last PROGRESS entry before resuming. The report is `docs/event-dt31/EVENT_B_STANDALONE_20261025_KO.md`, executable-package instructions are `event-b/README.md`. Existing PR #5/#13 components were reused. Do not rerun completed analyses/suites or begin restoration development; NEXT is review of the separate Draft PR. This checkpoint does not permit sensor mode switching or clear Phase C HARD BLOCKED.

## Mandatory start / resume procedure
1. Read `docs/event-dt31/BLUE_GREEN_SWITCH_PLAN_KO.md`, `docs/event-dt31/RP5_EVENT_RUNBOOK_KO.md` and `docs/event-dt31/PROGRESS.md` before doing work or resuming after context compaction.
2. Read and inspect the actual files, commits and test evidence from [PR #2](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/pull/2) (feasibility) and [PR #3](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/pull/3) (offline test); do not treat PR descriptions as test evidence.
3. Inspect branch, working tree, connected device/environment and current production state. Do not infer the RP5 state from archived October 18 metadata.
4. Complete one phase at a time. After each meaningful step update `docs/event-dt31/PROGRESS.md` with dated facts, commands run, test output locations, failures, and a clear next action. For longer tasks also give short progress updates to the user.
5. Before an action with side effects, check the runbook's preflight/abort/rollback constraints and confirm the action is within the **specific, limited user authorization for the current task**. A GitHub document itself is not perpetual approval for future experiments.

## Prior bounded investigation — Pi RAW2 Issue #1 (completed as UNKNOWN/STOP)
- **Historical reference, not the active work queue:** Pi Issue #1 and its last sensor-frame audit, `docs/event-dt31/CROSS_PLATFORM_REVIEW_20261025_KO.md`, and `CODEX_PI_FIRST_DEBUG_20261025_KO.md` establish the already completed UNKNOWN/STOP decision. New evidence only could justify reopening it; do not re-run those steps before Event B Issue #15.
- The previous priority was the **971/976 host-marker vs authenticated 960 sensor columns** question; the bounded same-session investigation is recorded in commit `b1729b7` / PR #10 and ended **UNKNOWN/STOP**. Do not relaunch without new authenticated evidence. Wrap21 200/200 only fixes host classification, not physical-column identity. Old LEN_LIMIT/multipacket and Jetson 8-pixel sawtooth are **separate**; do not replace current Issue #1 evidence with those hypotheses.
- Historical outcome: a single bounded same-session wire/header inventory was completed, without authenticated identity; mark absent wire evidence UNKNOWN/STOP. Old/new Event parser A/B was separately completed in Issue #11, PR #13. Do not repeat either study merely as prerequisite to Issue #15.
- Keep all Blue-Green, non-destructive recovery, Phase C HARD BLOCKED, `--device PHASE_C_BLOCKED` and private-data restrictions unchanged. Issue #1 analysis and Issue #11 Event A/B are completed bounded diagnostics. New Event B packaging/integration work uses the separate branch directed by Issue #15; do not overwrite PR #5/#13 evidence.

## Architecture decision — preserve original RAW2; separate Event Engine (2026-10-25)
- **Read [BLUE_GREEN_SWITCH_PLAN_KO.md](docs/event-dt31/BLUE_GREEN_SWITCH_PLAN_KO.md)**. The original RAW2 is immutable known-good A; develop Event DT=0x31 as a separately built/configured B. Do not replace, edit, disable or uninstall A as part of offline development. Reuse existing decoder/Viewer and prior restore mock as proven components; do not build an unnecessarily complex general-purpose recovery service.
- A minimal fail-closed switcher is the eventual deployment goal: A→B→verified A, with explicit sensor TX/CSI RX DT re-binding and media/stream ownership. **Software process switch alone does not reset physical sensor/registers/driver state; two services are not two cameras.**
- This is a design/priority change **not a live-experiment approval**. Maintain all existing Phase C HARD STOP, forbidden legacy rollback, bounded downtime and `--device PHASE_C_BLOCKED` until every recovery and watchdog gate is demonstrably met. Record changes on PR #5 and Issue #7.

## CRITICAL HOLD — RAW2 restoration is not validated (2026-10-21)
- A Codex read-only investigation reports that the existing `raw2_production_rollback.sh` **removes an RP1 override, disables the RAW2 service and reboots**. It is NOT an Event Packet -> RAW2 recovery procedure. Treat it as unsafe for this experiment; **do not execute, schedule or reuse it**.
- `raw2_production_start.sh` is NOT a harmless restart: it writes sensor setfile/registers, changes the media graph, and can schedule `raw2_production_rollback.sh` when `pending_first_boot_validation` exists. Do not use `systemctl restart` or `systemd-run` as a "dry run" on production.
- **HARD STOP** for Phase C and any action that interrupts the live RAW2 stream: no production service stop/restart, sensor I2C write, module rebind/reload, RP1 override changes, Device Tree change, or reboot until a separate restore-to-current-RAW2 procedure, watchdog interactions and failure-mode tests are verified. A mock/dry-run PASS alone is not actual restoration proof.
- Phase B file/mock development can continue independently of restoration work. Any safe restore design/mock remains a separate future Issue #7 gate for physical mode switching; it is **not** a prerequisite to finishing the Event B offline executable. Never modify or invoke the existing production rollback/start scripts.
- The prior limited experimental authorization does not waive this hold. Record evidence, unresolved assumptions, mock results and the exact preflight gates in `PROGRESS.md`. Do not mark Gate C ready until all restoration checks demonstrably pass.

## Non-negotiable constraints
- Prefer offline tests, isolated working directories, and a feature branch. Never directly modify the main branch.
- Do not alter RAW2 production code, production modprobe/service configuration, kernel/DT, or sensor settings during offline phases.
- Do not copy private Minsu/NRV SDK code, proprietary setfiles, sensor register dumps or confidential sample data into this public repository. Public test harnesses, aggregate statistics and safe summaries are acceptable.
- The single available RP5 and sensor also serve RAW2 production. Another process/directory is **not** hardware isolation. A real DT `0x31` test may interrupt RAW2; it requires verified preflight, rollback and the currently authorized downtime limits.
- Stop rather than guess if sensor setfile, module parameter binding, CSI word count, frame geometry, raw byte validity or restoration method is uncertain.
- Never mislabel modeled results, macOS builds or offline replays as native RP5 / live sensor validation. Separate CSI FE, sensor Frame End, V4L2 DQBUF and event frames.
- No irreversible flash, bootloader changes, filesystem formatting, persistent kernel/DT/overlay install, reboot, or unapproved broad register writes.
- Successful event capture does not finish the experiment until RAW2 production is restored **and** verified.

## Task handoff
The source of truth for the proposed execution sequence, pass/fail gates, permitted actions, and rollback is `docs/event-dt31/RP5_EVENT_RUNBOOK_KO.md`; current, verified progress is in `docs/event-dt31/PROGRESS.md`. If either differs from reality, update the records with evidence before proceeding.
