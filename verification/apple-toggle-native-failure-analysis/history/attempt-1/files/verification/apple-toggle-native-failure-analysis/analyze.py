#!/usr/bin/env python3
"""Read-only evidence analysis. No subprocess, native, Git, or network calls."""
import hashlib
import json
import pathlib

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


manifest = read(BASE / "evidence-manifest.json")
for entry in manifest["files"]:
    if "snapshot" in entry:
        assert sha(ROOT / entry["snapshot"]) == entry["sha256"], entry["snapshot"]
    if not entry["source"].startswith("https:"):
        assert sha(pathlib.Path(entry["source"]) if entry["source"].startswith("/") else ROOT / entry["source"]) == entry["sha256"], entry["source"]

root_review = read(BASE / "observed/root-review-receipt.json")
for name, digest in root_review["bindings"].items():
    assert sha(ROOT / name) == digest, name


def capture(name):
    return read(BASE / "observed" / (name + ".json"))["observations"]


programmatic = capture("self-tests")
failures = [check["name"] for check in programmatic["checks"] if check["pass"] is False]
assert len(programmatic["checks"]) == 12 and failures == ["UIKit primary activation selects and emits once", "UIButton accessibility activation selects and emits once"]
assert programmatic["state"]["eventValues"] == [False, False]
assert not programmatic["state"]["isOn"] and programmatic["state"]["beginCount"] == 0
assert [e["state"]["isOn"] for e in programmatic["events"] if e["reason"] == "primaryAccepted"] == [False, False]

on, off, element = [capture(name)["state"] for name in ["native-tap-on", "native-tap-off", "native-element-click"]]
assert on["isOn"] and not off["isOn"] and element["isOn"]
for before, after in [(on, off), (off, element)]:
    assert after["primaryCount"] == before["primaryCount"] + 1
    assert after["eventCount"] == before["eventCount"] + 1
assert element["accessibilityActivationCount"] == off["accessibilityActivationCount"] + 1
assert element["beginCount"] == off["beginCount"] + 1
horizontal, vertical = [capture(name)["state"] for name in ["ltr-forward", "vertical-probe"]]
assert horizontal["panAcceptedCount"] == vertical["panAcceptedCount"] == 0
assert horizontal["panState"] == vertical["panState"] == 5
assert horizontal["continueCount"] == vertical["continueCount"] == 0
assert horizontal["primaryCount"] == element["primaryCount"] + 1
assert vertical["scrollOffsetY"] == 0 and vertical["eventCount"] == horizontal["eventCount"]
held, released = [capture(name)["state"] for name in ["native-held-press-held", "native-held-release"]]
assert held["tracking"] and held["highlighted"] and held["authoredPressed"]
assert not released["tracking"] and not released["highlighted"]
assert released["eventCount"] == held["eventCount"] + 1
life = read(BASE / "observed/lifecycle.json")
assert life["cleanedUp"] and life["ownedDeviceAbsent"] and life["frontend"]["ownedFrontendAbsent"] and life["preservedExistingDeviceIDsAndStates"]

original = ROOT / "verification/apple-authored-toggle-contract/candidate-2-directional-pan/source"
diagnostic = BASE / "diagnostic-candidate/source"
comparator = BASE / "sdk26-comparator/source"
for path in original.rglob("*"):
    if path.is_file():
        relative = path.relative_to(original)
        assert sha(path) == sha(comparator / relative), relative
        if str(relative).startswith("sdk/") or relative.name in {"AppearanceNativePathsV2.swift", "TogglePanPolicy.swift"}:
            assert sha(path) == sha(diagnostic / relative), relative
carrier = "Prototype/AuthoredToggleCarrier.swift"
def draw_region(path):
    return path.read_text().split("    override func draw(", 1)[1].split("\n}\n", 1)[0]
assert draw_region(original / carrier) == draw_region(diagnostic / carrier)
oracle = read(BASE / "diagnostic-candidate/oracle-receipt.json")
assert oracle["passed"] and oracle["checkCount"] == 17
host = read(BASE / "host-checks.json")
assert host["exitCode"] == 0 and "Ran 40 tests" in host["stderr"]
for folder in ["diagnostic-candidate", "sdk26-comparator"]:
    receipt = read(BASE / folder / "receipt.json")
    assert not receipt["nativeExecuted"] and not receipt["nativeQualification"]

print(json.dumps({"status": "bounded-failure-analysis-and-crosscompiled-handoff-only", "rootRuntimeBoundFiles": len(root_review["bindings"]), "originalProgrammaticChecks": {"total": 12, "failed": failures, "secondDeselectionPassIsVacuous": True}, "originalNativeInput": {"coordinateTaps": "observed in both directions", "simulatorElementActivation": "observed; activation override plus touch tracking", "panAndScroll": "unqualified; missing intermediate-delivery/admission telemetry", "pressedState": "observed", "pressedCompositorPixels": "unqualified"}, "diagnosticHostOracleChecksPassed": 17, "mockedHandoffGuardsPassed": 40, "comparatorSourceMatchesAllOriginalFiles": True, "diagnosticAuthoredDrawingAndPanPolicyUnchanged": True, "newNativeExecution": False, "carrierAcceptance": False, "productionAdapterAcceptance": False}, indent=2))
