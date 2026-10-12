# Validation — 2026-10-12 snapshot

- Running Raspberry Pi 5, aarch64 kernel 6.12.47+rpt-rpi-2712: installer --check passed (snapshot SHA-256, user UID/home, model, module vermagic).
- Separate temporary builds: s5krc1s_min.ko, rp1-cfe.ko, CAM0 overlay, C++ RAW2 producer all succeeded.
- Decoder regression: code counts, packet wrap, coordinate mapping and invalid-code preservation passed. RAM microbenchmark: reference 2082.82 µs/frame, optimized 501.001 µs/frame; not a sensor capture-rate benchmark.
- Five FrameSurface tests passed (polarity/ROI/flip, temporal decay, thin edges, hot pixels, dilation).
- Installer tests passed: snapshot integrity, idempotent boot settings preserving existing contents, restore existing/new files and virtualenv symlink.
- Staged payload hashes match every source file.
- Build warnings: harmless pre-existing _GNU_SOURCE redefinition.
- Live service was not reinstalled/restarted/rebooted during package validation. Fresh-SD installation and post-install boot remain untested.
