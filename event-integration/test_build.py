"""Focused integration packaging checks; no old decoder/sample suites or device access."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("candidate_build", HERE / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class IntegrationPackaging(unittest.TestCase):
    def test_template_preserves_unknowns(self):
        profile = json.loads((HERE / "profile.json").read_text())
        self.assertEqual(build.validate_profile(profile), ["sensor_tx_setfile_sha256", "transport", "kernel_release"])

    def test_wrong_rx_dt_and_types_rejected(self):
        for dt in (42, True, "0x31", None):
            with self.subTest(dt=dt), self.assertRaises(ValueError):
                build.validate_profile({"receiver_dt": dt})

    def test_bad_profile_rejected_before_output_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.json"
            p.write_text('{"receiver_dt":42}')
            out = Path(tmp) / "out"
            with self.assertRaises(ValueError):
                build.stage(p, out)
            self.assertFalse(out.exists())

    def test_geometry_rejects_coordinate_dimensions_and_padding_underflow(self):
        profile = {"receiver_dt": 49, "transport": {
            "width": 960, "height": 720, "payload_bytes": 8192,
            "stride": 8192, "sizeimage": 1040384, "virtual_channel": 0}}
        with self.assertRaises(ValueError):
            build.validate_profile(profile)
        profile["transport"].update(width=8192, height=127, stride=8191)
        with self.assertRaises(ValueError):
            build.validate_profile(profile)

    def test_stage_exact_sources_no_subprocess_and_no_live_claim(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(build.subprocess, "run", side_effect=AssertionError("unexpected execution")):
            out, m = build.stage(HERE / "profile.json", Path(tmp) / "out")
            self.assertFalse(m["live_ready"])
            self.assertFalse(m["sensor_tx_applied"])
            self.assertEqual(m["native_build"], "NOT RUN")
            for name in build.SOURCES:
                self.assertEqual((out / "source" / name).read_bytes(), (build.ROOT / name).read_bytes())
            self.assertEqual(m["source_sha256"], {name: build.sha(build.ROOT / name) for name in build.SOURCES})
            self.assertIn("PHASE_C_BLOCKED", (out / "source/experiments/event-engine/engine.cpp").read_text())

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            out.mkdir()
            marker = out / "keep"
            marker.write_text("keep")
            with self.assertRaises(FileExistsError):
                build.stage(HERE / "profile.json", out)
            self.assertEqual(marker.read_text(), "keep")

    def test_source_checkout_output_rejected(self):
        with self.assertRaises(ValueError):
            build.stage(HERE / "profile.json", HERE / "never-create")
        self.assertFalse((HERE / "never-create").exists())

    def test_native_build_refused_on_macos(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(build.platform, "system", return_value="Darwin"), mock.patch.object(build.subprocess, "run") as run:
            out, manifest = build.stage(HERE / "profile.json", Path(tmp) / "out")
            with self.assertRaisesRegex(ValueError, "Linux"):
                build.compile_candidate(out, manifest, Path("unused"), Path("unused"))
            run.assert_not_called()
            self.assertEqual(json.loads((out / "manifest.json").read_text())["failure_stage"], "prerequisites")

    def fake_build_inputs(self, tmp, expected=None):
        root = Path(tmp)
        profile = json.loads((HERE / "profile.json").read_text())
        profile["kernel_release"] = expected
        path = root / "profile.json"
        path.write_text(json.dumps(profile))
        out, manifest = build.stage(path, root / "out")
        kernel = root / "kernel"
        (kernel / "include/config").mkdir(parents=True)
        (kernel / "include/config/kernel.release").write_text("6.12-test\n")
        (kernel / "Makefile").write_text("# inert test fixture\n")
        sdk = root / "sdk"
        sdk.mkdir()
        return out, manifest, sdk, kernel

    def test_kernel_mismatch_fails_before_sdk_and_compiler(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(build.platform, "system", return_value="Linux"), mock.patch.object(build.subprocess, "run") as run:
            out, manifest, sdk, kernel = self.fake_build_inputs(tmp, "6.99-other")
            with self.assertRaisesRegex(ValueError, "differs"):
                build.compile_candidate(out, manifest, sdk, kernel)
            result = json.loads((out / "manifest.json").read_text())
            self.assertEqual(result["failure_stage"], "kernel_identity")
            self.assertIs(result["kernel_profile_match"], False)
            run.assert_not_called()

    def test_sdk_prepare_failure_recorded_and_unknown_kernel_not_promoted(self):
        from types import SimpleNamespace
        fake = SimpleNamespace(FILES=(), prepare=mock.Mock(side_effect=RuntimeError("SDK patch anchor mismatch")))
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(build.platform, "system", return_value="Linux"), mock.patch.object(build.importlib.util, "module_from_spec", return_value=fake), mock.patch.object(build.importlib.util, "spec_from_file_location", return_value=SimpleNamespace(loader=SimpleNamespace(exec_module=lambda m: None))), mock.patch.object(build.subprocess, "run") as run:
            out, manifest, sdk, kernel = self.fake_build_inputs(tmp)
            with self.assertRaisesRegex(RuntimeError, "anchor"):
                build.compile_candidate(out, manifest, sdk, kernel)
            result = json.loads((out / "manifest.json").read_text())
            self.assertEqual(result["native_build"], "FAILED")
            self.assertEqual(result["failure_stage"], "sdk_prepare")
            self.assertEqual(result["kernel_profile_match"], "UNKNOWN")
            self.assertEqual(result["kernel_build_release"], "6.12-test")
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
