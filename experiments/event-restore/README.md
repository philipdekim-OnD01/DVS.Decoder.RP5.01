# Restore-to-current-RAW2 — offline candidate

This is a **dry-run/mock-only** restore controller, not an operational recovery tool. It deliberately has no live backend, shell runner, I2C, module or systemd API. `--apply-live` is unsupported. Phase C remains BLOCKED even when every mock passes. Never invoke the existing production rollback/start/validate scripts as a test.

Read-only plan using a previously collected aggregate inventory:

```sh
python3 restore_current_raw2.py --dry-run evidence/rp5-readonly-inventory-20261021.json
```

Expected exit **2** means hardware restoration remains blocked; JSON lists observations, pinned file/module/parameter checks and unresolved gates. This mode prints a plan and does not change files or hardware. Hash matches are facts about the observed files, not proof of the loaded driver descriptor or current sensor registers.

Fault simulation (only temporary fixture JSON files are changed):

```sh
python3 test_restore.py --results /tmp/restore-results.json
```

Final suite: 24 cases on macOS and Pi. It covers success, idempotence, sensor restore failure, service start failure, stalled/error/visual checks, missing watchdog, hash/kernel/enable-state drift, pending marker and timer conflicts/races, deadline injection, an exiting mock SSH client with a separate worker, lock contention, dry-run immutability, absence of live mode, rejection of production roots, and current baseline hash/DT checks.

The independent-worker test uses local subprocess sessions; it does **not** disconnect real SSH or prove systemd/logind cgroup survival. `watchdog_armed` is a fake state flag, not a live daemon. Injected timeout is not a timing guarantee. Restoring `sensor_profile='raw2'` in JSON is not restoring real registers. All production effects count zero.

`--mock-worker TEMP_ROOT` requires a sentinel and a fixture under the OS temp directory; production roots and symlinked fixture files are rejected. The controller performs only a fixed sequence of logical actions. It cannot execute command strings from an inventory. Failure leaves the fake watchdog armed, marks manual intervention, preserves evidence and never falls back to deletion, disable, reboot or a legacy rollback.

See [restore design](../../docs/event-dt31/RESTORE_PLAN_KO.md) for the actual call graph, target baseline, what the mock proves and hardware blockers. Earlier 21-case results are retained as historical evidence; `*-v2-*` files are the final 24-case results. Private register values and setfile contents are excluded.
