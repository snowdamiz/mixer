"""Read-only review of the sealed harness's completed simulator attempt."""
import collections
import datetime
import hashlib
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PRODUCER = ROOT / "verification/apple-toggle-xctest-preparation"
RUN = PRODUCER / "runtime"
read = lambda path: json.loads(path.read_bytes())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()

selection = read(OUT / "selection.json")
for name, digest in selection["bindings"].items():
    assert sha(ROOT / name) == digest, name
lifecycle = read(RUN / "lifecycle.json")
assert lifecycle["cleanedUp"] and lifecycle["ownedDeviceAbsent"]
assert lifecycle["baselineStatesPreserved"] and lifecycle["ephemeralWorkspaceAbsent"]
assert all(row["passed"] for row in lifecycle["cleanupResults"])
assert not Path(lifecycle["ephemeralWorkspace"]["path"]).exists()
assert lifecycle["runtime"]["buildversion"] == "23F77"
assert lifecycle["verifiedHandoff"]["sealSHA256"] == selection["invocation"][-1]
assert lifecycle["beforeFrontends"] == lifecycle["afterFrontends"]

spec = importlib.util.spec_from_file_location("reviewed_xctest_oracle", PRODUCER / "oracle.py")
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)
actions = []
for path in sorted((RUN / "captures").glob("*-after-*.json")):
    after = read(path)
    actual = after["verdict"]
    before = read(path.with_name(path.name.replace("-after-", "-before-")))
    replay = oracle.verdict(actual["candidate"], actual["case"], actual["action"],
                            before["observation"], after["observation"],
                            before["signature"] != after["signature"])
    assert all(actual[key] == value for key, value in replay.items())
    assert actual["ownedSimulatorIdentity"]["udid"] == lifecycle["ownedSimulator"]
    trace = after["observation"].get("diagnosticTrace", [])
    previous = max((item["sequence"] for item in before["observation"].get("diagnosticTrace", [])), default=0)
    delta = [item for item in trace if item["sequence"] > previous]
    decisions = [item for item in delta if item["kind"] == "shouldBeginDecision"]
    begin = [item for item in delta if item["kind"] == "carrierTouchesBegan"]
    moves = [item for item in delta if item["kind"] == "carrierTouchesMoved"]
    if actual["case"] in {"ltr-on", "ltr-off", "rtl-on", "rtl-off"}:
        assert len(begin) == 1 and len(decisions) == 1
        decision = decisions[0]
        assert decision["isAuthoredPan"] and not decision["result"]
        assert decision["enabled"] and decision["inputAllowed"]
        earlier = [item for item in moves if item["sequence"] < decision["sequence"]]
        assert earlier
        displaced = earlier[-1]["locationInView"]["x"] - begin[0]["locationInView"]["x"]
        assert abs(displaced) >= 9 and abs(decision["translationInCarrier"]["x"]) < 6
    else:
        displaced = None
    actions.append({"case": actual["case"], "action": actual["action"],
                    "actionIndex": actual["actionIndex"], "passed": actual["passed"],
                    "failedPredicates": [key for key, value in actual["predicates"].items() if not value],
                    "nativeTraceCounts": dict(collections.Counter(item["kind"] for item in delta)),
                    "admissionDecisions": decisions,
                    "lastObservedHorizontalDisplacementBeforeAdmission": displaced,
                    "originalChecks": actual["originalChecks"]})

commands = read(RUN / "commands.json")
interrupted = [item for item in commands if item["kind"] == "command-interrupted"]
test_output = "\n".join(item.get("stdout", "") for item in commands)
test_methods = [{"method": name, "status": status, "seconds": float(seconds)}
                for name, status, seconds in re.findall(
                    r"Test Case '-\[MixerToggleUITests.ToggleUITests (\w+)\]' (passed|failed) \(([0-9.]+) seconds\)\.", test_output)]
summary_path = RUN / "runtime-verdict.json"
summary = read(summary_path) if summary_path.exists() else None
result = {
    "schema": 1,
    "status": "root-reviewed-native-input-and-failures-retained-not-carrier-acceptance",
    "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "sourceRevisionContext": selection["sourceRevisionContext"],
    "environment": "iPhone17Pro iOS26.5(23F77) simulator; immutable SDK26.5 apps",
    "actionEvaluations": len(actions),
    "passingActionEvaluations": sum(action["passed"] for action in actions),
    "actions": actions,
    "completeCaseSet": summary["completeCaseSet"] if summary else False,
    "xcodebuildExitCode": summary["xcodebuildExitCode"] if summary else interrupted[-1]["exitCode"] if interrupted else None,
    "bridgeFailures": summary["bridgeFailures"] if summary else None,
    "bridgeFailureEvidence": "Per-request bridge failures were not durably retained before the interrupted final summary; their precise reason is unavailable. XCTest retains invalidResponse for diagnostic-direct.",
    "xctestMethodsReported": test_methods,
    "testSuiteReportedFinishedBeforeCommandTimeout": "Test Suite 'All tests' failed at" in test_output and bool(interrupted),
    "sessionFailures": [item for item in commands if item["kind"] == "session-failure"],
    "ownedSimulator": lifecycle["ownedSimulator"],
    "cleanup": "Owned simulator deleted, ephemeral capability workspace removed, server/thread closed; baseline instances/frontend preserved.",
    "finding": "All four authored pans receive actual movement but reject native admission: observed displacement exceeds9pt while reported recognizer translation is below the authored6pt threshold. This identifies a measurement mismatch; no threshold or product contract changed by this review.",
    "carrierAccepted": False,
    "pending": ["Pan correction and native replay", "Complete direct diagnostic collection", "Full cancellation/no-change/keyboard matrix", "Compositor parity", "Physical VoiceOver/final matrix", "Live adapter integration", "External FieldLog release", "GA"],
    "bindings": {str(path.relative_to(ROOT)): sha(path) for path in sorted(RUN.rglob("*")) if path.is_file()},
}
for path in [Path(__file__), OUT / "selection.json", OUT / "diagnostic-direct-partial-observation.json", OUT / "diagnostic-direct-partial-capture.json"]:
    result["bindings"][str(path.relative_to(ROOT))] = sha(path)
(OUT / "runtime-review.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({key: value for key, value in result.items() if key not in {"actions", "bindings"}}, indent=2))
