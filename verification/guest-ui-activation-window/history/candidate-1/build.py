#!/usr/bin/env python3
"""Build, but never launch, the signed public Mac window verification app."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OWNER_RECEIPT = ROOT / "verification/guest-ui-activation/candidate-4/receipt.json"
BUILD = HERE / ".build/candidate-1"
APP = BUILD / "MixerSignedGuestUI.app"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    BUILD.mkdir(parents=True, exist_ok=True)
    owner = json.loads(OWNER_RECEIPT.read_text())
    assert owner["status"] == "Snapshot integration tests passed for debug, release, tsan"
    source = Path(owner["source"])
    products = Path(owner["artifacts"]["debug"]["dylib"]["path"]).parent
    dylib = products / "libMixerCapabilityActivationGuestUI.dylib"
    assert sha(dylib) == owner["artifacts"]["debug"]["dylib"]["sha256"]
    receipt = {"status": "building; app has not been launched", "built_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
               "owner_receipt": str(OWNER_RECEIPT.relative_to(ROOT)), "owner_receipt_sha256": sha(OWNER_RECEIPT),
               "linked_dylib": {"path": str(dylib), "sha256": sha(dylib)}, "fixture_copies": {}, "commands": [],
               "scope": "Build-only handoff. Original Mac application harness uses public signed runtime open/download/start/screen/recovery/close APIs and exact test-only signer/bytecode fixture copies. No launch, UI automation, native receipt, health, storage outcome or qualification claimed by this build."}
    copied = HERE / "FixtureCopies"
    copied.mkdir(exist_ok=True)
    for name in ["GuestUISignedFixture.swift", "GuestUISignedProgram.swift"]:
        relative = "capability-activation/Tests/MixerCapabilityActivationTests/" + name
        original = source / relative
        assert sha(original) == owner["source_files"][relative]
        destination = copied / name
        shutil.copyfile(original, destination)
        receipt["fixture_copies"][relative] = {"copy": str(destination.relative_to(ROOT)), "sha256": sha(destination)}
    for section in ["MacOS", "Frameworks", "Resources/Fixtures"]:
        (APP / "Contents" / section).mkdir(parents=True, exist_ok=True)
    fixture_directory = source / "capability-activation/Tests/MixerCapabilityActivationTests/Fixtures"
    # The root snapshot deliberately reuses its original immutable test bundle.
    fixture_root = Path(next(row["environment"]["MIXER_COLD_START_TEST_BUNDLE"] for row in owner["commands"] if row["name"] == "debug-tests"))
    if not fixture_directory.exists():
        fixture_directory = fixture_root / "Contents/Resources/Fixtures"
    receipt["resource_fixtures"] = {}
    for original in sorted(fixture_directory.glob("*.json")):
        destination = APP / "Contents/Resources/Fixtures" / original.name
        shutil.copyfile(original, destination)
        receipt["resource_fixtures"][str(original)] = {"sha256": sha(original), "destination": str(destination)}
    assert len(receipt["resource_fixtures"]) >= 6
    library_copy = APP / "Contents/Frameworks" / dylib.name
    shutil.copyfile(dylib, library_copy)
    assert sha(library_copy) == sha(dylib)
    info = {"CFBundleIdentifier": "dev.mixer.signed-guest-ui-verification", "CFBundleName": "Mixer Signed Guest UI",
            "CFBundleExecutable": "MixerSignedGuestUI", "CFBundlePackageType": "APPL", "NSPrincipalClass": "NSApplication",
            "LSMinimumSystemVersion": "14.0", "MixerHarnessEvidenceDirectory": str(HERE)}
    info_path = APP / "Contents/Info.plist"
    info_path.write_bytes(plistlib.dumps(info, sort_keys=True))
    original_command = next(row["command"] for row in owner["commands"] if row["name"] == "debug-test-link")
    prefix = original_command[:original_command.index("-emit-library")]
    executable = APP / "Contents/MacOS/MixerSignedGuestUI"
    inputs = sorted((HERE / "Sources").glob("*.swift")) + sorted(copied.glob("*.swift"))
    receipt["harness_sources"] = {str(path.relative_to(ROOT)): sha(path) for path in inputs + [Path(__file__)]}
    env = dict(os.environ, DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer")

    def run(name, argv):
        started = time.monotonic()
        result = subprocess.run([str(x) for x in argv], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log = HERE / (name + ".log")
        attempt = 1
        while log.exists():
            attempt += 1
            log = HERE / (name + "-attempt-" + str(attempt) + ".log")
        log.write_bytes(result.stdout)
        receipt["commands"].append({"name": name, "command": [str(x) for x in argv], "cwd": str(ROOT),
                                    "developer_dir": env["DEVELOPER_DIR"], "exit_code": result.returncode,
                                    "elapsed_seconds": time.monotonic() - started, "log": str(log.relative_to(ROOT)), "log_sha256": sha(log)})
        (HERE / "build-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        assert result.returncode == 0, name + " failed; retained output"
        return result.stdout.decode(errors="replace")

    run("compiler-version", ["xcrun", "swiftc", "--version"])
    run("compile", prefix + ["-module-name", "MixerSignedGuestUIWindowHarness", "-L", str(products),
        "-lMixerCapabilityActivationGuestUI", "-Xlinker", "-rpath", "-Xlinker", "@executable_path/../Frameworks",
        "-o", str(executable)] + inputs)
    run("linked-libraries", ["otool", "-L", executable])
    run("codesign", ["codesign", "--force", "--sign", "-", APP])
    run("codesign-verify", ["codesign", "--verify", "--deep", "--strict", APP])
    # Preserve the original already-ad-hoc-signed dylib byte for byte. Signing
    # the outer app does not re-sign its nested immutable library.
    assert sha(library_copy) == sha(dylib)
    receipt.update(status="Build and ad-hoc signature verified; app not launched", app=str(APP), executable=str(executable),
                   executable_sha256=sha(executable), bundled_dylib_sha256=sha(library_copy), info_plist_sha256=sha(info_path),
                   launch_arguments=["--output", str(HERE / "runs/cua-1/progress.json"), "--run-root", str(HERE / "runs/cua-1/data")])
    assert receipt["harness_sources"] == {str(path.relative_to(ROOT)): sha(path) for path in inputs + [Path(__file__)]}
    (HERE / "build-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"app": str(APP), "executable": str(executable), "arguments": receipt["launch_arguments"],
                      "receipt_sha256": sha(HERE / "build-receipt.json")}, indent=2))


if __name__ == "__main__":
    main()
