# Issue #7 readiness harness — NO-GO

This extends the preserved 17/22/24-case evidence. It does not implement a live recovery backend. `production_ready` stays false and engine `--device` stays blocked.

## Reproducible software checks

```sh
python3 test_readiness.py --results /tmp/readiness.json
```

Final 33 cases pass on macOS and Pi with matching source SHA256. The suite uses synthetic temporary bundle payloads, never private SDK/setfiles/register dumps. It checks externally pinned manifest/file hashes, required roles, saved-register syntax, DT/geometry, unsafe paths/symlinks, marker flips at startup stages, concurrent installer/start/restart, file drift, forged prior success, real local watchdog processes, malformed cancellation and lock/signal handling. No hardware backend exists. Python tests are not ASan tests.

The bundle validator pins a manifest digest supplied **outside** the bundle, uses descriptor-relative O_NOFOLLOW reads and revalidates before/after startup stages. Readonly fixture permissions are tamper-evident through hashing, not a claim of root-proof immutability. Actual private snapshot sealing is NOT DONE; see the private bundle design.

## Genuine isolated systemd tests

On the authorized Pi only, with a fresh `/tmp` work path:

```sh
python3 systemd_sandbox_gate.py --work /tmp/dvs-watchdog-gate-UNIQUE
```

This creates only newly named `rp5-dvs-rdy-*` transient units; it never starts/stops/restarts RAW2 or legacy watchdogs. Worker user is philip with ProtectSystem=strict, ProtectHome, PrivateDevices/Network, NoNewPrivileges, closed device policy, only its own tmp writable, and CPU/memory/runtime limits. It writes a NOOP result marker, not a restore action. Final five cases: expiry, authorized sandbox cancellation, invalid token, invalid JSON token type, systemd runtime cap. Captured effective properties/cgroups/source pins and manager timeout journal are evidence. `--collect` removes the finished units; none remain.

Initial strict-sandbox failure is retained: tempfile.gettempdir attempted write probes outside the writable case directory. The worker was fixed without relaxing protection. During review, cancellation with a non-string token was hardened to remain alive until timeout instead of raising AttributeError.

```sh
python3 test_ssh_exit.py --work /tmp/dvs-watchdog-ssh-exit-UNIQUE --results /tmp/ssh-exit.json
```

This closes only a test-owned SSH client after arming a fresh harmless unit, then opens a new query session. The result is initially absent, later written by a PID1-owned worker in a distinct systemd cgroup. It proves this process/session-exit case; it does not test network outage, sshd restart, every logind policy, or actual hardware restoration. It requires the public scripts staged at the authorized Pi's `/tmp/dvs-readiness-20261022/readiness/` path. It is not a general-purpose remote command executor.

## File guard changes

`../event-engine/regular_input.hpp` pins a Linux O_PATH inode, rejects nonregular/symlink and non ext-family/tmpfs filesystems, and opens only the verified inode for read. It checks size/mtime drift. This closes the plain-ifstream file-mode bypass, while the unconditional `--device` refusal remains. New C++ type tests (7) and engine guard cases (6) passed on Pi ASan/UBSan. Acquisition changed, so the approved sample output was rechecked: 1557 frames/1469217 events and prior hash match. Original decoder suites were not rerun. Private derived output was not committed.

## Evidence and scope

Use `*-final.json`, `rp5-watchdog-ssh-exit-20261022-v3.json`, `rp5-file-types-20261022-v2.json` and `rp5-engine-fileguard-20261022-v2.json` for final results. Earlier 31/32-case and worker revisions remain historical artifacts, not extra coverage counts. Final worker hash in systemd/SSH ready records matches the local/Pi final source. `read_inventory.py` only reads current configuration, module metadata, graph, timer/service state, stored register shape, executable identity and metrics; it never invokes I2C.

See `docs/event-dt31/READINESS_20261022_KO.md` and `PRIVATE_BUNDLE_SPEC_KO.md` for the NO-GO matrix and remaining real-hardware gates. No GitHub Actions hardware job is enabled by these files.
