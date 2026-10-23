#!/usr/bin/env python3
"""Replay the old presentation with the new non-publishing lifetime regression."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BEFORE = "35a9a36c8837fd2dd3e491419b7965b6307cd6b9"
TEST = "nativeAttachmentChangesRevokeAuthorityWithoutPublishingIntoSwiftUIGraph"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location("presentation_driver", ROOT / "verification/guest-ui-presentation/verify.py")
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    snapshot = output / ".build/package"
    files = {}
    inputs = driver.OWNED + ["sdk/Package.swift"] + [str(p.relative_to(ROOT)) for p in (ROOT / "sdk/Sources").rglob("*") if p.is_file()]
    for relative in inputs:
        source = Path(relative)
        raw = (ROOT / source).read_bytes()
        if relative == driver.OWNED[0]:
            raw = subprocess.check_output(["git", "show", BEFORE + ":" + relative], cwd=ROOT)
        if relative.startswith("sdk/"):
            destination = snapshot / source
        else:
            section = "Sources" if "Sources" in source.parts else "Tests"
            target = "MixerCapabilityActivation" if section == "Sources" else "MixerCapabilityActivationTests"
            destination = snapshot / section / target / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        files[relative] = hashlib.sha256(raw).hexdigest()
    (snapshot / "Package.swift").write_text(driver.PACKAGE)
    command = ["swift", "test", "--package-path", str(snapshot), "--scratch-path", str(snapshot / "build"), "--jobs", "4", "--filter", TEST, "-Xswiftc", "-warnings-as-errors"]
    result = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=360)
    (output / "baseline.log").write_bytes(result.stdout)
    text = result.stdout.decode(errors="replace")
    reproduced = result.returncode != 0 and text.count("Expectation failed: publications == 0") == 5 and "Test run with 1 test in 1 suite failed" in text
    receipt = {"status": "old-source-regression-reproduced" if reproduced else "unexpected-result", "base_revision": BEFORE, "source_files": files, "argv": command, "exit_code": result.returncode, "output_sha256": hashlib.sha256(result.stdout).hexdigest(), "swift_version": subprocess.check_output(["swift", "--version"], text=True), "scope": "Five synchronous publications from native attachment callbacks reproduced on old production source; pinned CI separately observed the resulting SwiftUI teardown crash. This local run does not reproduce the OS-specific crash itself."}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    if not reproduced:
        raise SystemExit("Baseline did not reproduce the exact publication failures")


if __name__ == "__main__":
    main()
