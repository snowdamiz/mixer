#!/usr/bin/env python3
"""Resume only the preserved metadata-output harness error; never rerun passed checks."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("qualification", ROOT / "compiler/qualification_support.py")
helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
name = "runtime-identity-2026-10-22"
output, work = ROOT / "verification" / name, ROOT / "verification/local" / name
path = output / "receipt.json"
original = path.read_bytes(); receipt = json.loads(original)
if receipt["status"] != "failed" or receipt["error"] != "Expecting value: line 1 column 1 (char 0)":
    raise SystemExit("Not the exact recorded metadata-output harness error")
if any(command["exitCode"] != 0 or command["name"].startswith("ios-simulator-") for command in receipt["commands"]):
    raise SystemExit("A required prior command failed, or simulator was already attempted")
for command in receipt["commands"]:
    for stream in ["stdout", "stderr"]:
        if helper.digest(output / command[stream]["path"]) != command[stream]["sha256"]:
            raise SystemExit("Prior command output changed")
source, simulator = work / "source", work / "simulator"
for file, digest in receipt["sourceFiles"].items():
    if helper.digest(source / file) != digest:
        raise SystemExit("Frozen source changed")
prepared = json.loads((simulator / "prepared.json").read_text())
if prepared["source_revision"] != receipt["sourceRevision"]:
    raise SystemExit("Simulator revision mismatch")
for file, digest in prepared["files"].items():
    if helper.digest(simulator / file) != digest:
        raise SystemExit("Prepared simulator input changed")
(output / "initial-harness-failure.json").write_bytes(original)
receipt["priorHarnessFailure"] = dict(path="initial-harness-failure.json", sha256=hashlib.sha256(original).hexdigest(),
    explanation="Preparer prints project path; runner incorrectly parsed it as JSON. Corrected runner reads prepared.json. Prior successful checks/source identities verified and retained.")
receipt["continuationSHA256"] = helper.digest(Path(__file__))
receipt["correctedRunnerSHA256"] = helper.digest(ROOT / "verification/tools/qualify-runtime-identity.py")
receipt["simulatorPreparation"] = prepared
receipt["preparerSHA256"] = helper.digest(ROOT / "verification/tools/prepare-ios-updater.py")
recorder = helper.CommandRecorder(output, receipt["commands"], ROOT)
env = helper.clean_environment()
result = simulator / "result.xcresult"
try:
    recorder.run("ios-simulator-tests", ["/usr/bin/xcodebuild", "-project", simulator / "app/UpdaterHost.xcodeproj", "-scheme", "UpdaterHost", "-configuration", "Debug", "-destination", "platform=iOS Simulator,id=463F0C3C-63BC-42C4-A17C-0908C07D341D", "-derivedDataPath", simulator / "build", "-resultBundlePath", result, "CODE_SIGNING_ALLOWED=NO", "test"], env=env, timeout=600)
    summary = json.loads(recorder.run("ios-simulator-summary", ["/usr/bin/xcrun", "xcresulttool", "get", "test-results", "summary", "--path", result, "--format", "json"], env=env))
    receipt["simulatorSummary"] = summary
    if summary.get("failedTests") != 0 or summary.get("skippedTests") != 0 or summary.get("testFailures"):
        raise ValueError("Simulator failed or skipped")
    if any(helper.digest(source / file) != digest for file, digest in receipt["sourceFiles"].items()):
        raise ValueError("Frozen source changed")
    receipt["sourceUnchangedAfterChecks"] = True
    receipt["status"] = "passed scoped host, simulator and cross-compilation"
    receipt.pop("error", None)
except Exception as error:
    receipt["status"] = "failed"; receipt["error"] = str(error)
    raise
finally:
    receipt["completedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    path.write_text(json.dumps(receipt, indent=2) + "\n")
