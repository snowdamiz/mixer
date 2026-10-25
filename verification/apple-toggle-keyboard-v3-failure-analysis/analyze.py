"""Bounded offline extraction of already retained V3 evidence; no selected-code imports."""
import datetime
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
EXEC = "verification/apple-toggle-keyboard-full-case-v3-execution/"
PREP = "verification/apple-toggle-keyboard-full-case-preparation-v3/"
RUNTIME = PREP + "runtime/"
APP = "verification/apple-toggle-keyboard-focus-v9-preparation/source/Prototype/"
EXPECTED_SEAL = "7baff6c525359b0647caa2808d0fa73b7d1e8cc54146408d904570eabd80e3b7"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(name):
    return json.loads((ROOT / name).read_bytes())


seal_bytes = (ROOT / (EXEC + "packet-seal.json")).read_bytes()
assert digest(seal_bytes) == EXPECTED_SEAL
seal = json.loads(seal_bytes)
selected = read(EXEC + "inputs-before.json")
names = [
    "AGENTS.md", "mixer-product-plan.md",
    "docs/apple-toggle-keyboard-full-case-v3-runtime.md",
    EXEC + "packet-seal.json", EXEC + "original-exception.json",
    EXEC + "console-observations.json", EXEC + "attempt-started.json",
    EXEC + "input-reconciliation.json",
    "verification/apple-toggle-keyboard-full-case-root-review/v3-runtime/acceptance.json",
    PREP + "harness/UITests/ToggleUITests.swift",
    PREP + "inputs/runtime/verification/apple-toggle-keyboard-focus/keyboard_oracle.py",
    PREP + "inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/keyboard_oracle.py",
    PREP + "inputs/runtime/verification/apple-toggle-keyboard-focus/keyboard_bridge.py",
    PREP + "inputs/runtime/verification/apple-toggle-pan-origin-correction/harness.py",
    PREP + "composition.py", PREP + "orchestration.py", PREP + "attachment_export.py",
    PREP + "test_keyboard.py", PREP + "provenance.json",
    APP + "main.swift", APP + "AuthoredToggleCarrier.swift", APP + "DiagnosticTrace.swift",
    RUNTIME + "commands.json", RUNTIME + "captures/0001-begin.json",
    RUNTIME + "captures/0001-command-2.json", RUNTIME + "captures/0001-before-1.json",
    RUNTIME + "captures/0001-after-1.json", RUNTIME + "captures/0001-keyboard-witness-1.json",
    RUNTIME + "captures/bridge-summary.json", RUNTIME + "attachment-export.json",
    RUNTIME + "runtime-verdict.json", RUNTIME + "lifecycle.json",
]
inputs = {}
for name in names:
    path = ROOT / name
    data = path.read_bytes()
    record = {"sha256": digest(data), "bytes": len(data), "mode": path.stat().st_mode & 0o777}
    expected = seal["files"].get(name) or selected.get(name)
    if expected is not None:
        assert all(record[key] == expected[key] for key in ("sha256", "bytes", "mode")), name
    record["binding"] = "execution-seal" if name in seal["files"] else "selected-input" if name in selected else "current-read-only-context"
    inputs[name] = record

witness = read(RUNTIME + "captures/0001-keyboard-witness-1.json")["witness"]
before = read(RUNTIME + "captures/0001-before-1.json")["observation"]
captured = read(RUNTIME + "captures/0001-after-1.json")
after, verdict = captured["observation"], captured["verdict"]
focus = lambda snap: [name for name, value in snap["elements"].items() if value["hasFocus"]]
assert focus(witness["before"]) == ["authored-toggle"]
assert focus(witness["after"]) == []
assert before["state"]["focused"] is True and after["state"]["focused"] is False
assert witness["before"]["appForeground"] is witness["after"]["appForeground"] is True
assert [name for name, value in verdict["predicates"].items() if value is not True] == ["actualNativeFocusTraversal"]
new_events = after["events"][len(before["events"]):]
assert [event["reason"] for event in new_events] == ["focus"] * 3
assert [event["state"]["focused"] for event in new_events] == [False, True, False]
assert after["diagnosticTrace"] == before["diagnosticTrace"]
commands = read(RUNTIME + "commands.json")
test_commands = [event for event in commands if event.get("argv", [None])[0] == "/Applications/Xcode_26.6.app/Contents/Developer/usr/bin/xcodebuild"]
assert len(test_commands) == 1
command = test_commands[0]
assert command["kind"] == "command-interrupted" and command["failureType"] == "TimeoutExpired" and command["exitCode"] == -15
assert 600 <= command["elapsedSeconds"] < 609
console = command["stdout"].splitlines()
suite_line = next(line for line in console if "Test Suite 'Selected tests' failed at" in line)
assert console[-1].strip() == "Executed 7 tests, with 7 failures (6 unexpected) in 35.506 (35.525) seconds"
assert command["stdout"].count("Prior application case must complete before next begin") == 5
assert command["stderr"].endswith("** BUILD INTERRUPTED **\n")
exports = [event for event in commands if "xcresulttool" in " ".join(event.get("argv", []))]
assert len(exports) == 5 and all(event["exitCode"] == 64 and "Info.plist" in event["stderr"] for event in exports)
life = read(RUNTIME + "lifecycle.json")
assert len(life["cleanupResults"]) == 5 and all(value["passed"] is True for value in life["cleanupResults"])
attachment = read(RUNTIME + "attachment-export.json")
assert attachment["passed"] is False and attachment["files"] == {}
runtime_files = [name for name in seal["files"] if name.startswith(RUNTIME)]
runtime_media = [name for name in runtime_files if pathlib.Path(name).suffix in {".png", ".txt"}]
assert len(runtime_files) == 881
assert all("/settings-" in name for name in runtime_media)
result = {
    "schema": "mixer.apple-toggle.keyboard-v3-failure-analysis.1",
    "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "scope": "Offline source and immutable retained evidence only; no native/device/process inventory, compiler, build, network, server, Git, UI or screen capture commands; selected runtime modules were not imported.",
    "inheritedAnalysisRevision": "69d1672a",
    "inheritedRunRevision": seal["sourceRevision"],
    "executionSealSHA256": EXPECTED_SEAL,
    "pythonVersion": sys.version,
    "pythonExecutable": sys.executable,
    "pythonExecutableSHA256": digest(pathlib.Path(sys.executable).resolve().read_bytes()),
    "argv": [sys.executable, "-B", str(OUT / "analyze.py")],
    "analysisSourceSHA256": digest(pathlib.Path(__file__).read_bytes()),
    "analyzedInputTreeSHA256": digest(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()),
    "inputs": inputs,
    "facts": {
        "firstCase": witness["case"], "phase": witness["phase"], "key": witness["key"],
        "fixedFocusedBefore": focus(witness["before"]), "fixedFocusedAfter": focus(witness["after"]),
        "failedPredicates": [name for name, value in verdict["predicates"].items() if value is not True],
        "pairedFocusDisagreement": verdict["pairedFocusDisagreement"],
        "nativeAppFocusEventDelta": [{"sequence": event["sequence"], "uptime": event["uptime"], "focused": event["state"]["focused"]} for event in new_events],
        "keyStartedUptime": witness["startedUptime"], "keyFinishedUptime": witness["finishedUptime"],
        "afterCollectionFinishedUptime": witness["after"]["uptime"],
        "afterCollectionEndMinusKeyReturnSeconds": witness["after"]["uptime"] - witness["finishedUptime"],
        "snapshotIsAtomic": False, "perRowFocusObservationTimesRetained": False,
        "acquisitionWaitsForFocusSettling": False,
        "fullAppAXOrScreenshotRetained": False,
        "sealedRuntimeFiles": len(runtime_files),
        "sealedRuntimeAXTextAndPNGFiles": runtime_media,
        "consoleSelectedSuiteTerminalLine": suite_line,
        "testCommandElapsedSeconds": command["elapsedSeconds"], "interruptionRecordedUTC": command["utc"],
        "testCommandExitCode": command["exitCode"], "wrapperExitCode": 1,
        "exportAttempts": len(exports), "officialMethods": 0, "cleanupPasses": 5,
    },
    "conclusion": "Confirmed mechanism: real native toggle-focus departure plus no focused member observed in the three-ID witness makes the unchanged traversal predicate fail; the failed cursor then refuses five begins. Destination and reason for departure are not retained. The post-suite xcodebuild/session stall is separate, with no retained stack or teardown state to identify its blocker.",
    "notEstablished": ["legitimate focus destination outside fixed IDs", "global absence of focus", "product native focus defect", "specific focus-settling race", "keyboard command mapping error", "specific cause of post-suite Xcode stall"],
    "nativeAccepted": False, "gaAccepted": False, "physicalPhones": "disconnected-deferred",
}
(OUT / "analysis.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps({"status": "offline-analysis-controls-passed", "boundInputs": len(inputs), "analyzedInputTreeSHA256": result["analyzedInputTreeSHA256"], "failedPredicates": result["facts"]["failedPredicates"], "nativeAccepted": False, "gaAccepted": False}, sort_keys=True))
