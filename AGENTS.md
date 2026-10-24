# Codex operating guidance — RP5 S5KRC1S Event Packet experiment

**Scope:** The instructions in this file apply to work involving S5KRC1S DVS CSI-2 Event Packet (DT `0x31`) on Raspberry Pi 5. They do not authorize unrelated operations on this repository or on devices.

## ACTIVE NEXT TASK — GitHub Issue #11 (2026-10-25)

- **Single task source:** [Issue #11 — Event 32-bit offline A/B / unsynced_groups=830](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/11). Its P0–P5 checklist, latest comments and evidence links are the authoritative next-work queue. The instruction in this file to study earlier Pi Issue #1 remains required for provenance, **not** permission to repeat completed 971/976 analysis.
- **Resume/compaction protocol:** before work, read this AGENTS.md, Issue #11 latest body/comments, `docs/event-dt31/PROGRESS.md`, the active branch/HEAD/`git status`, and the last completed checkpoint. Work only on the next unchecked task; do not replay already-verified suites merely to rebuild context.
- **Persistent checkpoint:** after each meaningful P0–P5 unit, append actual date/host/commands/results/sha/FAIL/NOT TESTED/NEXT to PROGRESS.md on the dedicated feature branch, commit and push, and post a short `DONE / EVIDENCE / TEST / BLOCKER / NEXT` comment on Issue #11. Stop and log blockers rather than switching goals.
- **Current safety:** Pi RAW2 Issue #1 remains **UNKNOWN/STOP** after commit `b1729b7` / Draft PR #10; no authenticated same-session wire/header evidence, no proof of physical 5-column loss. Event Phase C **HARD BLOCKED**, `--device PHASE_C_BLOCKED`. Only offline/file/mock Event diagnostics are in scope. No hardware authorization is implied by this issue or documentation.
- **Branch policy:** keep PR #5 original experiments and PR #10 RAW2 provenance intact. Develop Event A/B on its own branch and report via a separate Draft PR. Never directly modify `main`; proprietary source/samples/raw files must not enter public Git.

## Mandatory start / resume procedure
1. Read `docs/event-dt31/BLUE_GREEN_SWITCH_PLAN_KO.md`, `docs/event-dt31/RP5_EVENT_RUNBOOK_KO.md` and `docs/event-dt31/PROGRESS.md` before doing work or resuming after context compaction.
2. Read and inspect the actual files, commits and test evidence from [PR #2](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/pull/2) (feasibility) and [PR #3](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/pull/3) (offline test); do not treat PR descriptions as test evidence.
3. Inspect branch, working tree, connected device/environment and current production state. Do not infer the RP5 state from archived October 18 metadata.
4. Complete one phase at a time. After each meaningful step update `docs/event-dt31/PROGRESS.md` with dated facts, commands run, test output locations, failures, and a clear next action. For longer tasks also give short progress updates to the user.
5. Before an action with side effects, check the runbook's preflight/abort/rollback constraints and confirm the action is within the **specific, limited user authorization for the current task**. A GitHub document itself is not perpetual approval for future experiments.

## Prior bounded investigation — Pi RAW2 Issue #1 (completed as UNKNOWN/STOP)
- Before another Event/restore development cycle, read [Pi Issue #1](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/1) and its **last independent sensor-frame audit**, then `docs/event-dt31/CROSS_PLATFORM_REVIEW_20261025_KO.md` and **separate Codex task** `docs/event-dt31/CODEX_PI_FIRST_DEBUG_20261025_KO.md`.
- The previous priority was the **971/976 host-marker vs authenticated 960 sensor columns** question; the bounded same-session investigation is recorded in commit `b1729b7` / PR #10 and ended **UNKNOWN/STOP**. Do not relaunch without new authenticated evidence. Wrap21 200/200 only fixes host classification, not physical-column identity. Old LEN_LIMIT/multipacket and Jetson 8-pixel sawtooth are **separate**; do not replace current Issue #1 evidence with those hypotheses.
- Work *offline and read-only*, inspect only existing same-session wire/header evidence once; label absent evidence UNKNOWN/STOP, never invent +5 columns or patch production decoder. Then compare the old/new Event decoders and boundary statistics offline using Jetson diagnostic **methods**, not proprietary source or hardware-specific configuration.
- Keep all Blue-Green, non-destructive recovery, Phase C HARD BLOCKED, `--device PHASE_C_BLOCKED` and private-data restrictions unchanged. Use an Issue #1 analysis branch; do not overwrite PR #5 evidence.

## Architecture decision — preserve original RAW2; separate Event Engine (2026-10-25)
- **Read [BLUE_GREEN_SWITCH_PLAN_KO.md](docs/event-dt31/BLUE_GREEN_SWITCH_PLAN_KO.md)**. The original RAW2 is immutable known-good A; develop Event DT=0x31 as a separately built/configured B. Do not replace, edit, disable or uninstall A as part of offline development. Reuse existing decoder/Viewer and prior restore mock as proven components; do not build an unnecessarily complex general-purpose recovery service.
- A minimal fail-closed switcher is the eventual deployment goal: A→B→verified A, with explicit sensor TX/CSI RX DT re-binding and media/stream ownership. **Software process switch alone does not reset physical sensor/registers/driver state; two services are not two cameras.**
- This is a design/priority change **not a live-experiment approval**. Maintain all existing Phase C HARD STOP, forbidden legacy rollback, bounded downtime and `--device PHASE_C_BLOCKED` until every recovery and watchdog gate is demonstrably met. Record changes on PR #5 and Issue #7.

## CRITICAL HOLD — RAW2 restoration is not validated (2026-10-21)
- A Codex read-only investigation reports that the existing `raw2_production_rollback.sh` **removes an RP1 override, disables the RAW2 service and reboots**. It is NOT an Event Packet -> RAW2 recovery procedure. Treat it as unsafe for this experiment; **do not execute, schedule or reuse it**.
- `raw2_production_start.sh` is NOT a harmless restart: it writes sensor setfile/registers, changes the media graph, and can schedule `raw2_production_rollback.sh` when `pending_first_boot_validation` exists. Do not use `systemctl restart` or `systemd-run` as a "dry run" on production.
- **HARD STOP** for Phase C and any action that interrupts the live RAW2 stream: no production service stop/restart, sensor I2C write, module rebind/reload, RP1 override changes, Device Tree change, or reboot until a separate restore-to-current-RAW2 procedure, watchdog interactions and failure-mode tests are verified. A mock/dry-run PASS alone is not actual restoration proof.
- Phase B file/mock tests and read-only inspection may continue. Prepare an independent restore *design/script* in a separate experimental workspace; never modify or run the current rollback script. Inspect pending-first-boot and all timers/services read-only, and ensure they cannot invoke the destructive rollback during the proposed restoration.
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
