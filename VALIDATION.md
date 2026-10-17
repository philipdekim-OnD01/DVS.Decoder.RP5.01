# Final running snapshot — 2026-10-18

The source of truth is the Pi's running `dvs-raw2-production.service`, captured without restarting, reinstalling, or rebooting it.

- `/proc/<producer PID>/exe`, installed `raw2_producer`, trace/shadow source build, and a fresh isolated rebuild of this repository all have SHA-256 `5c2a88249aca8c3e3af0e0c3ec6ad772cad902ef215bc531a635f9c7af16776b`.
- The source originally left beside the installed binary was stale. Its bytes are preserved in `metadata/installed-stale-producer.cpp`; the payload contains the source matching the live executable and all three required headers. `metadata/source-provenance.json` records the original paths and hashes.
- Isolated Raspberry Pi 5 build: both kernel modules, CAM0 overlay, current RAW2 producer succeeded. The build preserves the original translation-unit filename because that filename is retained in ELF symbols.
- C++ checks passed: RAW2 code counts/wrap/coordinates/invalid preservation; embedded alignment and discontinuities; Jetson display/denoise/persistence/input immutability; boundary histogram; trace wrap 11+10 and bounded ring; real production JSON writer/schema.
- All five Python FrameSurface checks passed. Installer checks cover integrity, boot-setting idempotence, file/venv recovery, and full drop-in directory backup/recovery.
- Installer preflight and staged-payload verification are performed against the final release archive; full clean-SD installation and boot remain untested.
- Live end-to-end check: service active; HTTP index and JavaScript 200; WebSocket stats report producer active and IPC connected; binary video received; capture frame counter advances. See `metadata/live-health-20261018.json`.
- The health check's instantaneous sample was capture 1190.395 buffers/s, web 58.97 frames/s, HDMI 59.97 frames/s. The initial snapshot sample was different; these are individual samples, not a sustained-rate guarantee.
- Existing cumulative RAW2 alignment rejects remain visible in the captured metrics. Preserving the current working version does not claim to fix those input-boundary issues.

`metadata/build-validation-20261018.txt` contains the build/test output. Driver bytes are unchanged from the previous snapshot; active display and diagnostic service overrides are now included in installation and rollback.
