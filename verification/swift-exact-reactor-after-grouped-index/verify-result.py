#!/usr/bin/env python3
"""Read-only final result verification; no compiler, guest, native or UI run."""
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CLOSURE = "3ffa1055e462be74c10ee9830bf891bbd196a896dfc7a66dc6befe2a6d9bb70f"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read(name):
    return json.loads((HERE / name).read_bytes())


def strict(text):
    def pairs(items):
        value = {}
        for key, item in items:
            assert key not in value, key
            value[key] = item
        return value
    return json.loads(text, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def main():
    seal = read("result-seal.json")
    actual = {str(path.relative_to(HERE)) for path in HERE.rglob("*")
              if path.is_file() and path.name != "result-seal.json"}
    assert actual == set(seal["files"]), "final inventory changed"
    for name, expected in seal["files"].items():
        assert sha(HERE / name) == expected, name
    for name, expected in seal["externalFiles"].items():
        assert sha(ROOT / name) == expected, name
    assert not (HERE / "owned-scratch").exists() and not (HERE / "bin/exact-tests").exists()
    with gzip.open(HERE / "bin/exact-tests.gz", "rb") as stream:
        executable = stream.read()
    binary_hash = hashlib.sha256(executable).hexdigest()
    prepared = read("prepared-seal.json")
    for name, expected in prepared["files"].items():
        assert (binary_hash if name == "bin/exact-tests" else sha(HERE / name)) == expected, name
    for name, expected in prepared["externalFiles"].items():
        assert sha(ROOT / name) == expected, name
    baseline = read("baseline-manifest.json")
    assert len(baseline) == 132 and sha(HERE / "baseline-manifest.json") == CLOSURE
    for name, expected in baseline.items():
        assert sha(HERE / "baseline" / name) == expected, name
    copied = read("copied-build-manifest.json")
    changed = [name for name in baseline if baseline[name] != copied[name]]
    assert changed == ["src/experimental_swift_reactor/lifecycle_tests.rs"]
    append = '\n// Isolated diagnostic only; baseline production bytes are unchanged.\ninclude!(' + json.dumps(str(HERE / "harness.rs")) + ');\n'
    assert hashlib.sha256((HERE / "baseline" / changed[0]).read_bytes() + append.encode()).hexdigest() == copied[changed[0]]
    binding = read("binding.json")
    for info in binding["inputs"]:
        assert sha(info["path"]) == info["sha256"], info["path"]
    assert sha(binding["target"]["path"]) == binding["target"]["sha256"]
    selected = read("root-selection.json")
    assert sha(ROOT / "verification/swift-exact-reactor-after-grouped-index-root-selection/execution.json") == sha(HERE / "root-selection.json") == "28465c0768a098eb34949beaebd6848ea9c4ee6c5690f6a17fce8b87357d674e"
    assert selected["exactCommandSelected"] and selected["baselineClosure"] == CLOSURE
    assert selected["binarySHA256"] == binary_hash and selected["binaryBytes"] == len(executable)
    assert selected["harnessSHA256"] == sha(HERE / "harness.rs")
    assert selected["driverSHA256"] == sha(HERE / "diagnostic.py")
    assert selected["inputBindingSHA256"] == sha(HERE / "binding.json")
    assert selected["preparedSealSHA256"] == sha(HERE / "prepared-seal.json")
    assert selected["preparedSelectionSHA256"] == sha(HERE / "prepared-selection.json")
    for name, expected in selected["boundEvidence"].items():
        assert sha(HERE / name) == expected, name
    commands = []
    for path in sorted((HERE / "commands").glob("*/receipt.json")):
        command = json.loads(path.read_bytes())
        assert command["processGroupEmpty"] and command["finalGroupObservation"]["state"] == "absent"
        assert command["rawStreamEOFConfirmed"] and command["signalSent"] == []
        assert command["toolsBefore"] == binding["compilerTools"]
        for field in ("sourceUnchanged", "toolsUnchanged", "allBoundInputsUnchanged", "harnessUnchanged", "driverUnchanged", "argvFilesUnchanged"):
            assert command[field], (path, field)
        for stream in ("stdout", "stderr"):
            assert sha(path.parent / stream) == command[stream]["sha256"]
        assert sha(path.parent / "harness.rs") == command["harnessSHA256"]
        assert sha(path.parent / "diagnostic.py") == command["driverSHA256"]
        for info in command["argvFileIdentities"]:
            digest = binary_hash if info["path"] == str(HERE / "bin/exact-tests") else sha(info["path"])
            assert digest == info["sha256"], info["path"]
        if path.parent.name != "target-once":
            assert command["passed"]
        commands.append(path.parent.name)
    assert commands == ["build-001", "control-001", "control-002", "driver-observation-controls", "list-001", "target-once"]
    command = read("commands/target-once/receipt.json")
    assert command["argv"] == selected["argv"] and command["timeoutSeconds"] == 170
    assert command["terminationGraceSeconds"] == command["killWaitSeconds"] == 5
    assert command["exitCode"] == 101 and not command["passed"] and not command["timedOut"]
    marker = read("target-attempt-started.json")
    assert marker["rootSelection"]["sha256"] == sha(HERE / "root-selection.json")
    early = read("commands/target-once/before-process-cleanup.json")
    assert early["failureEvidencePrecedesHostCleanup"] and early["exitCode"] == 101 and not early["timedOut"]
    assert early["stdout"]["sha256"] == command["stdout"]["sha256"]
    assert early["stderr"]["sha256"] == command["stderr"]["sha256"]
    result = read("target-once-result.json")
    events = read("target-once-events.json")
    raw_events = []
    for line in (HERE / "commands/target-once/stdout").read_text().splitlines():
        at = line.find("MIXER_EXACT ")
        if at >= 0:
            raw_events.append(strict(line[at + len("MIXER_EXACT "):]))
    assert raw_events == events
    def event(name):
        return next((row["payload"] for row in events if row["event"] == name), None)
    failures = [row for row in events if row["event"] in ("validation_failure", "adoption_failure", "construction_failure", "runtime_failure", "guest_output_failure", "phase_failed")]
    assert result["firstFailure"] == failures[0]
    assert result["targetAttempted"] and not result["commandPassed"] and not result["nativeParity"]
    assert result["phasesBegun"] == ["validation", "initialize", "corpus_1"]
    assert event("phase_reply") == "Initialized" and event("initialize")["lifecycle"] == "Ready"
    assert event("corpus_2") is None and event("diagnostic_execution_complete") is False
    for row in events:
        value = row["payload"]
        if isinstance(value, dict) and "stdout_hex" in value:
            for stream in ("stdout", "stderr"):
                raw = bytes.fromhex(value[stream + "_hex"])
                assert raw == b"" and value[stream] == ""
    classification = read("target-once-classification.json")
    assert classification["rawResultSHA256"] == sha(HERE / "target-once-result.json")
    assert classification["rawStderrSHA256"] == sha(HERE / "commands/target-once/stderr")
    first = result["firstFailure"]["payload"]
    assert classification["firstTypedFailure"] == first
    assert (first["resource"], first["function"], first["offset"], first["attempted"], first["limit"]) == ("CacheWork", 3416, 1077688, 64000001, 64000000)
    assert (first["stage"], first["kind"], first["code"]) == ("Cache", "WorkExhausted", "swift_run_work")
    assert first["at_failure"]["reservations"]["live_tickets"] == 85
    assert first["at_failure"]["reservations"]["peak_tickets"] == 86
    assert first["at_failure"]["instructions"] == 15753076
    assert first["at_failure"]["cache_work"] == 64000000
    assert all(event("final_failure")[key] == first[key] for key in first if key != "after_cleanup")
    final = event("final_cleanup_usage")
    assert all(value["current"] == 0 for value in final["reservations"].values() if isinstance(value, dict))
    assert final["reservations"]["live_tickets"] == 0 and all(value["current"] == 0 for value in final["live"].values())
    assert final["cleanup_invariant"] is None and event("cleanup_reservations_and_live_empty") is True
    assert event("cleanup_empty") is False and result["ownedCleanupEmpty"] is False
    counters = read("phase-counters.json")
    assert counters["sourceEventsSHA256"] == sha(HERE / "target-once-events.json")
    for row in counters["snapshots"]:
        original = event(row["event"])
        assert row["cache"] == original["cache"]
        assert row["reservations"] == original["usage"]["reservations"]
        assert row["live"] == original["usage"]["live"]
        assert row["work"] == {key: original["usage"][key] for key in row["work"]}
        assert row["lifecycle"] == original["lifecycle"] and row["memoryBytes"] == original["memory_bytes"]
    assert [row["event"] for row in counters["snapshots"]] == ["constructed", "initialize", "corpus_1"]
    prior = ROOT / "verification/swift-exact-reactor-after-resident-index"
    previous_events = json.loads((prior / "target-once-events.json").read_bytes())
    def previous_event(name):
        return next(row["payload"] for row in previous_events if row["event"] == name)
    compare = read("ownership-comparison.json")
    assert compare["priorResultSealSHA256"] == sha(prior / "result-seal.json") == "05d31bc936466d9dd6c2b21c411e30e75087396e6f6903a0e6fc597f401948fd"
    assert compare["priorEventsSHA256"] == sha(prior / "target-once-events.json")
    assert compare["currentEventsSHA256"] == sha(HERE / "target-once-events.json")
    assert [row["event"] for row in compare["snapshots"]] == ["constructed", "initialize"]
    work_keys = ["cache_work", "execution_work", "instruction_fuel", "instructions", "host_calls"]
    def ownership(value):
        reservations = value["usage"]["reservations"]
        return {"fixedCacheReservation":value["cache"]["fixed_reserved"], "liveTickets":reservations["live_tickets"], "peakTickets":reservations["peak_tickets"], "cacheCurrent":reservations["cache"]["current"], "constructionCurrent":reservations["construction"]["current"], "stateCurrent":reservations["state"]["current"], "combinedCurrent":reservations["combined"]["current"]}
    for row in compare["snapshots"]:
        old = previous_event(row["event"]); current = event(row["event"])
        assert old["usage"]["live"] == current["usage"]["live"] and old["memory_bytes"] == current["memory_bytes"]
        assert {key:old["usage"][key] for key in work_keys} == {key:current["usage"][key] for key in work_keys}
        assert {key:value for key,value in old["cache"].items() if key!="fixed_reserved"} == {key:value for key,value in current["cache"].items() if key!="fixed_reserved"}
        assert row["prior"] == ownership(old) and row["current"] == ownership(current)
        assert row["delta"] == {key:row["current"][key]-row["prior"][key] for key in row["prior"]}
        assert row["delta"]["liveTickets"] == -1 and row["delta"]["combinedCurrent"] == -1608
    for name in ("validation_budget", "run_budget", "wasi_budget", "wasi_grants"):
        assert event(name) == previous_event(name)
    consuming = read("consuming-cleanup-audit.json")
    assert consuming["sourceEventsSHA256"] == sha(HERE / "target-once-events.json")
    assert consuming["finalConsumingUsage"] == final
    assert consuming["finalFailureAfterCleanupSnapshot"] == event("final_failure")["after_cleanup"]
    assert consuming["finalLiveTickets"] == 0 and consuming["cleanupInvariant"] is None
    assert all(value == 0 for value in consuming["finalCurrentReservationCategories"].values())
    assert all(value == 0 for value in consuming["finalCurrentLiveCategories"].values())
    assert consuming["finalFailureAfterCleanupSnapshot"]["reservations"]["live_tickets"] == 3
    assert consuming["finalFailureAfterCleanupSnapshot"]["reservations"]["combined"]["current"] == 271168
    assert consuming["rawHarnessCleanupEmpty"] is False and consuming["rawDriverOwnedCleanupEmpty"] is False
    for name, digest in consuming["sourceBindings"].items():
        assert sha(HERE / name) == digest
    preselection = json.loads((ROOT / "verification/swift-exact-reactor-after-grouped-index-root-selection/preselection-failure.json").read_bytes())
    assert not preselection["guestStarted"] and not preselection["targetMarkerPresent"]
    assert preselection["dispatchExitCode"] == preselection["rootCheckExitCode"] == 1
    assert classification["preselectionDispatchesCountAsGuestAttempts"] is False
    assert classification["preselectionFailureReference"]["record"] == preselection
    assert classification["rootPreselectionCheckFailures"] == classification["rootRefusedPreselectionDispatches"] == 1
    assert len(list((HERE / "commands").glob("target-*"))) == 1
    cleanup_command = read("cleanup-command.json")
    assert cleanup_command["passed"] and cleanup_command["exitCode"] == 0 and not cleanup_command["timedOut"]
    assert cleanup_command["signalsSent"] == [] and cleanup_command["rawStreamEOFConfirmed"]
    assert cleanup_command["finalGroupObservation"]["state"] == "absent"
    for stream in ("stdout", "stderr"):
        assert sha(HERE / ("cleanup." + stream)) == cleanup_command[stream]["sha256"]
    pre_cleanup = read("pre-cleanup-audit.json")
    assert pre_cleanup["allOwnedGroupsAbsent"] and pre_cleanup["toolBinariesAndSysrootMatchRecordedBindings"]
    assert pre_cleanup["sourceBaselineAndBuildCopyMatchBindings"] and pre_cleanup["consumingCleanupCurrentReservationsLiveAndTicketsZero"]
    assert pre_cleanup["targetPID"] == pre_cleanup["targetProcessGroup"] == command["pid"]
    for row in pre_cleanup["ownedGroupObservations"]:
        assert row["observation"]["state"] == "absent" and row["streamEOF"]
    for row in pre_cleanup["holderChecks"]:
        assert row["exitCode"] == 1 and not row["pathIdentity"]["symlink"]
    for path in sorted((HERE / "commands").glob("*/receipt.json")):
        observed = json.loads(path.read_bytes())
        assert observed["baselineClosure"] == CLOSURE
        assert observed["sourceClosure"] == sha(HERE / "copied-build-manifest.json")
        assert json.loads((path.parent / "source-manifest.json").read_bytes()) == copied
    cleanup = read("cleanup.json")
    assert cleanup["removed"] and cleanup["holderExitCode"] == 1
    assert cleanup["retainedExecutable"]["uncompressed"]["sha256"] == binary_hash
    assert sha(HERE / "bin/exact-tests.gz") == cleanup["retainedExecutable"]["gzip"]["sha256"]
    assert all((HERE / (name + ".stdout")).read_bytes() == b"" and (HERE / (name + ".stderr")).read_bytes() == b"" for name in ("scratch-holders", "binary-holders"))
    receipt = read("result-receipt.json")
    assert receipt["firstFailure"] == result["firstFailure"] and receipt["targetAttempts"] == seal["targetAttempts"] == 1
    assert receipt["preparedInputsUnchanged"] and receipt["scratchRemoved"] and not receipt["gaAccepted"]
    assert receipt["cleanupCommandExecutions"] == 1 and receipt["rootPreselectionCheckFailures"] == receipt["rootRefusedPreselectionDispatches"] == 1
    assert receipt["preselectionDispatchesCountAsGuestAttempts"] is False and receipt["finalCleanupReservationsAndLiveEmpty"]
    assert receipt["targetChildExitCode"] == 101 and receipt["targetDriverExitCodeReportedByRoot"] == 1
    assert receipt["targetPID"] == receipt["targetProcessGroup"] == command["pid"]
    assert receipt["compilerTools"] == binding["compilerTools"]
    assert receipt["rootSelectionSHA256"] == sha(HERE / "root-selection.json")
    print(json.dumps({"integrityVerified": True, "sealedMembers": len(seal["files"]),
        "preparedMembersVerified": len(prepared["files"]), "preparedExecutableLosslesslyCompressed": True,
        "commands": commands, "targetAttempts": 1, "targetCommandPassed": False,
        "firstFailure": {key: first[key] for key in ("stage", "kind", "code", "resource", "function", "offset", "attempted", "limit")},
        "initializeCompleted": True, "nativeParity": False, "finalCleanupReservationsAndLiveEmpty": True,
        "ownedScratchRemoved": True, "gaAccepted": False}))


if __name__ == "__main__":
    main()
