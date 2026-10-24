#!/usr/bin/env python3
"""Replay public UIKit probe on one explicitly supplied simulator, never phones."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
OUT = ROOT / "evidence"
OUT.mkdir(exist_ok=True)
commands = []

def run(*args, check=True):
    start = time.time()
    result = subprocess.run(args, cwd=REPO, capture_output=True, text=True)
    commands.append({"argv": list(args), "exitCode": result.returncode,
                     "stdout": result.stdout, "stderr": result.stderr,
                     "startedUTC": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(start)),
                     "elapsedSeconds": round(time.time()-start, 4)})
    (OUT / "commands.json").write_text(json.dumps(commands, indent=2)+"\n")
    if check and result.returncode:
        raise RuntimeError(f"Command failed: {args!r}\n{result.stderr}")
    return result.stdout.strip()

def wait_stage(container, stage):
    for _ in range(100):
        marker = container / "Documents/stage.txt"
        if marker.exists() and marker.read_text() == stage:
            return
        time.sleep(0.1)
    raise RuntimeError(f"No completion marker for {stage}")

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

parser = argparse.ArgumentParser()
parser.add_argument("--simulator", required=True)
options = parser.parse_args()
simulator = options.simulator
inputs = [ROOT / "source/main.swift", ROOT / "source/Info.plist", Path(__file__),
          REPO / "AGENTS.md", REPO / "docs/ui-measured-appearance-v2-contract.md"]
source_lock = {"revision": run("git", "rev-parse", "HEAD"),
               "tree": run("git", "rev-parse", "HEAD^{tree}"),
               "dirtyPaths": run("git", "status", "--short"),
               "inputSHA256": {str(p.relative_to(REPO)): digest(p) for p in inputs}}
(OUT / "source-lock.json").write_text(json.dumps(source_lock, indent=2)+"\n")
run("xcodebuild", "-version")
run("xcrun", "swiftc", "--version")
sdk = run("xcrun", "--sdk", "iphonesimulator", "--show-sdk-path")
run("xcrun", "simctl", "list", "runtimes", "--json")
devices = json.loads(run("xcrun", "simctl", "list", "devices", "--json"))
matches = [(runtime, device) for runtime, values in devices["devices"].items()
           for device in values if device["udid"] == simulator]
if len(matches) != 1:
    raise RuntimeError("Explicit simulator is not uniquely present")
runtime, device = matches[0]
(OUT / "simulator.json").write_text(json.dumps({"runtimeIdentifier": runtime, "device": device}, indent=2)+"\n")
work = Path(tempfile.mkdtemp(prefix="mixer-field-paint-probe-"))
app = work / "MixerFieldPaintProbe.app"
app.mkdir()
shutil.copy2(ROOT / "source/Info.plist", app / "Info.plist")
run("xcrun", "swiftc", str(ROOT / "source/main.swift"), "-o", str(app / "MixerFieldPaintProbe"),
    "-target", "arm64-apple-ios17.0-simulator", "-sdk", sdk, "-framework", "UIKit")
run("codesign", "--force", "--sign", "-", str(app))
(OUT / "built-app.json").write_text(json.dumps({"deploymentTarget": "iOS 17.0 simulator",
    "binarySHA256": digest(app / "MixerFieldPaintProbe"), "plistSHA256": digest(app / "Info.plist")}, indent=2)+"\n")
if device["state"] != "Booted":
    run("xcrun", "simctl", "boot", simulator)
run("xcrun", "simctl", "bootstatus", simulator, "-b")
run("xcrun", "simctl", "install", simulator, str(app))
container = Path(run("xcrun", "simctl", "get_app_container", simulator, "dev.mixer.verification.fieldpaint", "data"))
for name in ["stage.txt", "command.txt", "observations.json"]:
    (container / "Documents" / name).unlink(missing_ok=True)
run("xcrun", "simctl", "launch", "--terminate-running-process", simulator, "dev.mixer.verification.fieldpaint")
wait_stage(container, "discovery")
run("xcrun", "simctl", "io", simulator, "screenshot", str(OUT / "discovery.png"))
stages = ["native-selection", "native-managed-tints", "native-caret-red", "native-selection-alpha128",
          "native-selection-opaque", "native-selection-clear", "install-selection",
          "reactivate-selection", "reinstall-selection", "authored-caret", "caret-alpha61", "caret-alpha128", "selection-alpha61",
          "selection-alpha128", "selection-clear", "selection-caret-green", "caret-green",
          "caret-clear", "marked-text", "restyle-marked", "reinstall-marked", "commit-marked", "delete-native", "disable"]
for stage in stages:
    (container / "Documents/command.txt").write_text(stage)
    commands.append({"operation": "writeProbeControlFile", "stage": stage,
                     "path": str(container / "Documents/command.txt")})
    (OUT / "commands.json").write_text(json.dumps(commands, indent=2)+"\n")
    wait_stage(container, stage)
    run("xcrun", "simctl", "io", simulator, "screenshot", str(OUT / (stage+".png")))
for path in (container / "Documents").glob("*"):
    shutil.copy2(path, OUT / path.name)
run("xcrun", "simctl", "terminate", simulator, "dev.mixer.verification.fieldpaint")
shutil.rmtree(work)
observations = json.loads((OUT / "observations.json").read_text())
summary = {"scope": "Actual installed simulator; iOS17 deployment compilation is separate from runtime qualification",
    "runtimeIdentifier": runtime, "publicInteractionFound": bool(observations[0]["after"].get("displayTextInputIsField")),
    "observedStages": [x["stage"] for x in observations],
    "physicalDeviceTested": False, "iOS17RuntimeTested": "iOS-17-" in runtime,
    "realKeyboardIMETested": False, "secureInputTested": False,
    "editingMenuTested": False, "voiceOverTested": False,
    "productIntegrationOrTransactionQualification": False}
(OUT / "result.json").write_text(json.dumps(summary, indent=2)+"\n")
print(json.dumps(summary, indent=2))
