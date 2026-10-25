#!/usr/bin/env python3
"""Read-only sealed packet integrity check; no compiler, guest, native or UI run."""
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CLOSURE = "f2682c6a2fd6f6e74bd00a2394ff32b704aa1e2ed3d2373ef95cdee29fa7eb2c"
EXPECTED = {"codableRoundTrip": True, "committedEntries": 1, "completionBasisPoints": 5000,
    "emptyTitleRejected": True, "pendingChanges": 1503, "reordered": True,
    "repeatedCommitRejected": True, "reportIncludesEntry": True, "status": "passed",
    "taskCount": 1000, "unicodePreserved": True}


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def strict(text):
    def pairs(items):
        result = {}
        for key, value in items:
            assert key not in result, key
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=pairs, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def raw_events(path):
    result = []
    for line in Path(path).read_text().splitlines():
        at = line.find("MIXER_EXACT ")
        if at >= 0:
            result.append(strict(line[at + len("MIXER_EXACT "):]))
    return result


def main():
    seal = read(HERE / "seal.json")
    actual = {str(p.relative_to(HERE)) for p in HERE.rglob("*") if p.is_file() and p.name != "seal.json"}
    assert actual == set(seal["files"]), "sealed member inventory changed"
    for name, expected in seal["files"].items():
        assert sha(HERE / name) == expected, name
    for name, expected in seal["externalFiles"].items():
        assert sha(ROOT / name) == expected, name
    assert not (HERE / "owned-scratch").exists()
    assert not (HERE / "bin/exact-tests").exists()
    baseline = read(HERE / "baseline-manifest.json")
    assert len(baseline) == 132
    assert hashlib.sha256((json.dumps(baseline, indent=2, sort_keys=True) + "\n").encode()).hexdigest() == CLOSURE
    for name, expected in baseline.items():
        assert sha(HERE / "baseline" / name) == expected, name
    copied = read(HERE / "copied-build-manifest.json")
    changed = [name for name in baseline if baseline[name] != copied[name]]
    assert changed == ["src/experimental_swift_reactor/lifecycle_tests.rs"]
    test = changed[0]
    append = '\n// Isolated diagnostic only; baseline production bytes are unchanged.\ninclude!(' + json.dumps(str(HERE / "harness.rs")) + ');\n'
    assert hashlib.sha256((HERE / "baseline" / test).read_bytes() + append.encode()).hexdigest() == copied[test]
    binding = read(HERE / "binding.json")
    assert binding["baselineClosure"] == CLOSURE
    for info in binding["inputs"]:
        assert sha(info["path"]) == info["sha256"], info["path"]
    assert sha(binding["target"]["path"]) == binding["target"]["sha256"]
    binary = read(HERE / "binary.json")
    with gzip.open(HERE / "bin/exact-tests.gz", "rb") as stream:
        assert hashlib.sha256(stream.read()).hexdigest() == binary["retained"]["sha256"]
    selected = read(HERE / "root-selection.json")
    assert selected["exactCommandSelected"] and selected["baselineClosure"] == CLOSURE
    assert selected["binarySHA256"] == binary["retained"]["sha256"]
    assert selected["harnessSHA256"] == sha(HERE / "harness.rs") == binary["harnessSHA256"]
    assert selected["driverSHA256"] == sha(HERE / "diagnostic.py")
    for name, expected in selected["boundEvidence"].items():
        assert sha(HERE / name) == expected, name
    commands = []
    for path in sorted((HERE / "commands").glob("*/receipt.json")):
        command = read(path)
        assert command["processGroupEmpty"] and command["finalGroupObservation"]["state"] == "absent"
        for field in ("sourceUnchanged", "toolsUnchanged", "allBoundInputsUnchanged", "harnessUnchanged", "driverUnchanged", "argvFilesUnchanged"):
            assert command[field], (path, field)
        for stream in ("stdout", "stderr"):
            assert sha(path.parent / stream) == command[stream]["sha256"]
        assert sha(path.parent / "harness.rs") == command["harnessSHA256"]
        assert sha(path.parent / "diagnostic.py") == command["driverSHA256"]
        for info in command["argvFileIdentities"]:
            if info["path"] == str(HERE / "bin/exact-tests"):
                assert info["sha256"] == binary["retained"]["sha256"]
            elif Path(info["path"]).name == "test_driver.py":
                assert sha(path.parent / "test_driver.py") == info["sha256"]
            else:
                assert sha(info["path"]) == info["sha256"]
        assert command["exitCode"] is not None
        if path.parent.name != "target-once":
            assert command["passed"]
        elif not command["passed"]:
            early = read(path.parent / "before-process-cleanup.json")
            assert early["failureEvidencePrecedesHostCleanup"]
        commands.append(path.parent.name)
    attempt = read(HERE / "commands/target-once/receipt.json")
    marker = read(HERE / "target-attempt-started.json")
    assert attempt["argv"] == selected["argv"] and attempt["timeoutSeconds"] == 170
    assert attempt["terminationGraceSeconds"] == attempt["killWaitSeconds"] == 5
    assert marker["rootSelection"]["sha256"] == sha(HERE / "root-selection.json")
    result = read(HERE / "target-once-result.json")
    events = read(HERE / "target-once-events.json")
    assert raw_events(HERE / "commands/target-once/stdout") == events
    assert result["commandPassed"] == attempt["passed"]
    assert result["targetAttempted"] is True
    for flag in ("fullSLMatrixAccepted", "productionAccountingAccepted", "nativeSignedPublicAccepted", "performanceSizeMemoryAccepted", "GAaccepted"):
        assert result[flag] is False
    failures = [e for e in events if e["event"] in ("validation_failure", "adoption_failure", "construction_failure", "runtime_failure", "guest_output_failure", "phase_failed")]
    assert result["firstFailure"] == (failures[0] if failures else None)
    if result["nativeParity"]:
        calls = [e["payload"] for e in events if e["event"] in ("corpus_1", "corpus_2")]
        assert result["diagnosticCompleted"] and len(calls) == 2
        previous = ""
        for call in calls:
            output = call["stdout"]
            assert output.startswith(previous)
            value = strict(output[len(previous):])
            assert set(value) == set(EXPECTED) and len(value) == 11
            assert all(type(value[k]) is type(EXPECTED[k]) and value[k] == EXPECTED[k] for k in EXPECTED)
            previous = output
    for event in events:
        payload = event["payload"]
        if isinstance(payload, dict) and "stdout_hex" in payload:
            for stream in ("stdout", "stderr"):
                encoded = bytes.fromhex(payload[stream + "_hex"])
                try:
                    decoded = encoded.decode("utf-8", errors="strict")
                except UnicodeDecodeError:
                    decoded = None
                assert payload[stream] == decoded
    classification = read(HERE / "target-once-classification.json")
    assert classification["rawResultSHA256"] == sha(HERE / "target-once-result.json")
    assert classification["rawStderrSHA256"] == sha(HERE / "commands/target-once/stderr")
    assert classification["firstTypedFailure"] == result["firstFailure"]["payload"]
    final_usage = next(e["payload"] for e in events if e["event"] == "final_cleanup_usage")
    assert all(v["current"] == 0 for v in final_usage["reservations"].values() if isinstance(v, dict))
    assert final_usage["reservations"]["live_tickets"] == 0
    assert all(v["current"] == 0 for v in final_usage["live"].values())
    assert final_usage["cleanup_invariant"] is None
    assert classification["finalCleanupReservationsAndLiveEmpty"] is True
    assert classification["rawHarnessCleanupEmpty"] is False and result["ownedCleanupEmpty"] is False
    assert any(e["event"] == "cleanup_reservations_and_live_empty" and e["payload"] is True for e in events)
    counters = read(HERE / "phase-counters.json")
    assert counters["sourceEventsSHA256"] == sha(HERE / "target-once-events.json")
    for row in counters["snapshots"]:
        original = next(e["payload"] for e in events if e["event"] == row["event"])
        assert row["cache"] == original["cache"]
        assert row["cacheEntries"] == original["usage"]["live"]["cache_entries"]
        assert row["cacheReservation"] == original["usage"]["reservations"]["cache"]
        assert row["work"] == {k: original["usage"][k] for k in row["work"]}
        assert row["elapsedMicros"] == original["usage"]["elapsed_micros"]
    for prev, cur, delta in zip(counters["snapshots"], counters["snapshots"][1:], counters["increments"]):
        assert delta["from"] == prev["event"] and delta["to"] == cur["event"]
        for category in ("cache", "work"):
            assert delta[category] == {k: cur[category][k] - prev[category][k] for k in cur[category]}
        assert delta["cacheEntriesCurrent"] == cur["cacheEntries"]["current"] - prev["cacheEntries"]["current"]
        assert delta["cacheReservationCurrent"] == cur["cacheReservation"]["current"] - prev["cacheReservation"]["current"]
        assert delta["elapsedMicros"] == cur["elapsedMicros"] - prev["elapsedMicros"]
    cleanup = read(HERE / "cleanup.json")
    assert cleanup["removed"] and cleanup["holderExitCode"] == 1
    assert seal["targetAttempts"] == 1
    print(json.dumps({"integrityVerified": True, "sealedMembers": len(seal["files"]),
        "commands": commands, "targetCommandPassed": result["commandPassed"],
        "nativeParity": result["nativeParity"], "firstFailure": result["firstFailure"],
        "ownedCleanupEmpty": result["ownedCleanupEmpty"], "ownedScratchRemoved": True,
        "GAaccepted": False}))


if __name__ == "__main__":
    main()
