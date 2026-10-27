#!/usr/bin/env python3
"""Stage or compile an isolated Event integration candidate; never install/run it."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "drivers/sensor/s5krc1s_min.c", "drivers/sensor/Makefile",
    "experiments/event-engine/engine.cpp",
    "experiments/event-engine/v4l2_capture.hpp",
    "experiments/event-engine/packet.hpp",
    "experiments/event-engine/regular_input.hpp",
    "experiments/event-offline/prepare_core.py",
    "event-b/index.html", "event-b/viewer.js",
    "event-integration/build.py",
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_profile(profile):
    if type(profile) is not dict or type(profile.get("receiver_dt")) is not int or profile["receiver_dt"] != 0x31:
        raise ValueError("receiver_dt must be integer 49 (0x31)")
    digest = profile.get("sensor_tx_setfile_sha256")
    if digest is not None and (not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)):
        raise ValueError("setfile digest must be SHA256 or null")
    transport = profile.get("transport")
    if transport is not None:
        fields = ("width", "height", "payload_bytes", "stride", "sizeimage", "virtual_channel")
        if type(transport) is not dict or set(transport) != set(fields):
            raise ValueError("transport must contain exactly " + ", ".join(fields))
        if any(type(transport[k]) is not int for k in fields):
            raise ValueError("transport fields must be integers")
        w, h = transport["width"], transport["height"]
        if not (8192 <= w <= 8256 and 126 <= h <= 160):
            raise ValueError("transport outside current sensor driver bounds")
        if transport["payload_bytes"] <= 0 or transport["payload_bytes"] > transport["stride"]:
            raise ValueError("invalid payload/stride")
        if transport["stride"] < w or transport["sizeimage"] < transport["stride"] * h:
            raise ValueError("invalid GREY stride/sizeimage")
        if transport["virtual_channel"] != 0:
            raise ValueError("current sensor descriptor requires virtual channel 0")
    kernel = profile.get("kernel_release")
    if kernel is not None and (not isinstance(kernel, str) or not re.fullmatch(r"[A-Za-z0-9._+-]+", kernel)):
        raise ValueError("invalid kernel_release")
    return [key for key in ("sensor_tx_setfile_sha256", "transport", "kernel_release") if profile.get(key) is None]


def stage(profile_path, output):
    profile = json.loads(profile_path.read_text())
    missing = validate_profile(profile)
    output = output.absolute()
    resolved = output.resolve()
    if resolved == ROOT or ROOT in resolved.parents:
        raise ValueError("output must be outside the source checkout")
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    for name in SOURCES:
        dest = output / "source" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, dest)
    (output / "profile.json").write_text(json.dumps(profile, indent=2) + "\n")
    # Inert example, not installed into /etc. No sensor register values are generated.
    (output / "receiver.conf.example").write_text("options s5krc1s_min csi2_dt=0x31\n")
    manifest = {
        "package": "Event integration candidate", "stage": "SOURCE_STAGED",
        "phase_c": "HARD BLOCKED", "live_ready": False,
        "sensor_tx_applied": False, "hardware_accessed": False,
        "profile_missing": missing, "profile_sha256": sha(output / "profile.json"),
        "profile_validation": "shape/bounds only; no sensor or packet authentication",
        "source_sha256": {name: sha(output / "source" / name) for name in SOURCES},
        "host": {"system": os.uname().sysname, "release": os.uname().release,
                 "machine": os.uname().machine}, "native_build": "NOT RUN",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return output, manifest


def compile_candidate(output, manifest, sdk, kernel_build):
    manifest["native_build"] = "IN_PROGRESS"
    step = "prerequisites"
    try:
        if platform.system() != "Linux":
            raise ValueError("native integration build requires Linux; no macOS hardware claim")
        if not sdk.is_dir() or not (kernel_build / "Makefile").is_file():
            raise ValueError("private SDK and prepared target kernel build tree are required")
        step = "kernel_identity"
        release_file = kernel_build / "include/config/kernel.release"
        release = release_file.read_text().strip()
        if not re.fullmatch(r"[A-Za-z0-9._+-]+", release):
            raise ValueError("prepared kernel release is missing or malformed")
        profile = json.loads((output / "profile.json").read_text())
        expected = profile.get("kernel_release")
        manifest["kernel_build_release"] = release
        manifest["kernel_release_sha256"] = sha(release_file)
        manifest["kernel_makefile_sha256"] = sha(kernel_build / "Makefile")
        manifest["kernel_profile_match"] = "UNKNOWN" if expected is None else (expected == release)
        manifest["running_board_kernel_match"] = "NOT VERIFIED"
        if expected is not None and expected != release:
            raise ValueError("profile kernel_release differs from target build tree")
        step = "sdk_prepare"
        core = output / "source/experiments/event-offline/prepare_core.py"
        spec = importlib.util.spec_from_file_location("integration_prepare_core", core)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        private = output / "private-sdk"
        manifest["private_sdk_input_sha256"] = {
            str(p.relative_to(sdk)): sha(p)
            for p in sorted((sdk / "include").rglob("*")) if p.is_file()
        }
        manifest["private_sdk_input_sha256"].update({"src/" + n: sha(sdk / "src" / n) for n in module.FILES})
        module.prepare(sdk, private)
        manifest["private_sdk_prepared_sha256"] = {
            str(p.relative_to(private)): sha(p) for p in sorted(private.rglob("*")) if p.is_file()
        }
        engine = output / "source/experiments/event-engine/engine.cpp"
        binary = output / "event-integration-engine"
        # Compile the existing adapter as well; engine's unconditional live block remains.
        compiler = os.environ.get("CXX", "g++")
        commands = [
            [compiler, "-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror", "-pthread",
             "-I" + str(private / "include"), str(engine),
             *[str(private / "src" / n) for n in module.FILES], "-o", str(binary)],
            ["make", "-C", str(kernel_build.resolve()),
             "M=" + str(output / "source/drivers/sensor"), "modules"],
        ]
        manifest["build_commands"] = commands
        step = "compiler_identity"
        manifest["compiler_version"] = subprocess.check_output([compiler, "--version"], text=True).splitlines()[0]
        for i, command in enumerate(commands):
            step = "engine_compile" if i == 0 else "module_compile"
            with (output / ("build-" + str(i) + ".log")).open("w") as log:
                subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        step = "output_hashes"
        manifest["binary_sha256"] = sha(binary)
        manifest["module_sha256"] = sha(output / "source/drivers/sensor/s5krc1s_min.ko")
        manifest["native_build"] = "COMPILED_NOT_EXECUTED"
        manifest["v4l2_adapter_compiled"] = True
    except (Exception, KeyboardInterrupt) as error:
        manifest["native_build"] = "FAILED"
        manifest["failure_stage"] = step
        manifest["failure_type"] = type(error).__name__
        raise
    finally:
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=Path(__file__).with_name("profile.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage-only", action="store_true")
    parser.add_argument("--sdk", type=Path)
    parser.add_argument("--kernel-build", type=Path)
    args = parser.parse_args()
    if not args.stage_only and (args.sdk is None or args.kernel_build is None):
        parser.error("build requires --sdk and --kernel-build; use --stage-only to preserve sources")
    try:
        output, manifest = stage(args.profile, args.output)
        if not args.stage_only:
            compile_candidate(output, manifest, args.sdk.resolve(), args.kernel_build.resolve())
        print(json.dumps(manifest, indent=2))
    except (ValueError, RuntimeError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
