#!/usr/bin/env python3
"""Verify retained API37 development evidence without running a native device."""
import hashlib
import json
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LANE = HERE.parent
CANDIDATE = LANE / "candidate-16"
LIFECYCLE = ROOT / "verification/native-testing-resume-2026-10-24/android-candidate-16-lifecycle"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    receipt = json.loads((CANDIDATE / "receipt.json").read_text())
    assert receipt["status"] == "passed-compile-and-native-emulator"
    assert receipt["sourceUnchanged"] and receipt["error"] is None
    assert receipt["target"]["ro.kernel.qemu"] == "1"
    assert receipt["target"]["ro.build.version.sdk"] == "37"
    assert receipt["native"]["checks"] == 570
    seal = json.loads((CANDIDATE / "artifact-seal.json").read_text())
    for name, expected in seal.items():
        assert digest(CANDIDATE / name) == expected, name
    for name, expected in receipt["sourceManifest"].items():
        assert digest(CANDIDATE / "inputs" / name) == expected, name
        if name.startswith("native/android/"):
            assert digest(ROOT / name) == expected, name
    source_digest = hashlib.sha256(json.dumps(receipt["sourceManifest"], sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()
    assert source_digest == receipt["sourceClosureSHA256"]
    previous = json.loads((LANE / "headless-section-4/receipt.json").read_text())
    native_sources = [n for n in receipt["sourceManifest"] if n.startswith("native/android/")]
    assert len(native_sources) == 12
    for name in native_sources:
        assert previous["sourceManifest"][name] == receipt["sourceManifest"][name], name
    for command in receipt["commands"]:
        assert command["exitCode"] == 0, command["name"]
        assert digest(ROOT / command["output"]) == command["sha256"], command["name"]
    counts = {"native-instrumentation": 570, "baseline-first-native": 120,
              "baseline-last-native": 120, "button-insets-native": 14}
    for name, count in counts.items():
        output = (CANDIDATE / (name + ".log")).read_text()
        assert f"INSTRUMENTATION_RESULT: checks={count}\n" in output
        assert "INSTRUMENTATION_RESULT: status=passed\n" in output
        assert "INSTRUMENTATION_CODE: 0\n" in output
    for name in ("noncanonical", "oversized", "unselected-resource", "unselected-font",
                 "invalid-unselected-theme"):
        output = (CANDIDATE / (name + "-native-capture.log")).read_text()
        assert "INSTRUMENTATION_RESULT: status=passed\n" in output
        assert "INSTRUMENTATION_CODE: 0\n" in output
    captures = []
    for name in ("all-ten", "paired", "inset", "sections-ltr", "sections-rtl",
                 "baseline-first-ltr", "baseline-first-rtl", "baseline-last-ltr", "baseline-last-rtl"):
        capture = json.loads((CANDIDATE / (name + "-capture.json")).read_text())
        current = [a for a in capture["attempts"] if a["current"]]
        assert current and len(capture["attempts"]) <= 3
        for attempt in current:
            assert attempt["windowInkIntersectionOverUnion"] >= 0.75
            assert attempt["compositorInkIntersectionOverUnion"] >= 0.75
        captures.append(name)
    with tarfile.open(HERE / "built-artifacts.tar.gz", "r:gz") as archive:
        assert set(archive.getnames()) == set(receipt["artifacts"])
        for name, expected in receipt["artifacts"].items():
            assert hashlib.sha256(archive.extractfile(name).read()).hexdigest() == expected, name
    lifecycle = json.loads((LIFECYCLE / "receipt.json").read_text())
    assert lifecycle["status"] == "qualified" and lifecycle["cleanup"] == "stopped"
    assert lifecycle["error"] is None
    assert digest(LIFECYCLE.parent / "run-android.py") == lifecycle["collectorSHA256"]
    for command in lifecycle["commands"]:
        assert digest(LIFECYCLE / command["log"]) == command["sha256"], command["name"]
        if command["name"] in ("owned-process-after-cleanup", "port-after-5586", "port-after-5587"):
            assert command["exitCode"] == 1
    print(json.dumps({"status": "passed", "nativeAssertions": counts,
                      "negativeInstallations": 5, "currentCaptureScenes": captures,
                      "unchangedNativeSources": len(native_sources), "commands": len(receipt["commands"]),
                      "retainedBuiltArtifacts": len(receipt["artifacts"]), "cleanup": "stopped",
                      "scope": "API37 private consumer development slice; no physical, cross-platform parity, ordinary engine join or GA acceptance."}, indent=2))


if __name__ == "__main__":
    main()
