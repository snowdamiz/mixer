#!/usr/bin/env python3
"""Classify and seal the already-collected single target outcome; no execution."""
import datetime
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read(name):
    return json.loads((HERE / name).read_bytes())


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    assert not (HERE / "result-seal.json").exists()
    assert not (HERE / "owned-scratch").exists() and not (HERE / "bin/exact-tests").exists()
    command = read("commands/target-once/receipt.json")
    result = read("target-once-result.json")
    cleanup = read("cleanup.json")
    selected = read("root-selection.json")
    assert sha(ROOT / "verification/swift-exact-reactor-after-resident-index-root-selection/execution.json") == sha(HERE / "root-selection.json") == "677beb7e3bb2751f0fc819f4e695dc22f576ffa027eb7b6bc6c7139b834599fb"
    prepared = read("prepared-seal.json")
    binding = read("binding.json")
    events = read("target-once-events.json")
    def event(name):
        return next((row["payload"] for row in events if row["event"] == name), None)
    with gzip.open(HERE / "bin/exact-tests.gz", "rb") as stream:
        executable = stream.read()
    assert hashlib.sha256(executable).hexdigest() == selected["binarySHA256"]
    for name, expected in prepared["files"].items():
        actual = hashlib.sha256(executable).hexdigest() if name == "bin/exact-tests" else sha(HERE / name)
        assert actual == expected, name
    for name, expected in prepared["externalFiles"].items():
        assert sha(ROOT / name) == expected, name
    assert command["argv"] == selected["argv"] and selected["maxTargetAttempts"] == 1
    assert command["processGroupEmpty"] and command["rawStreamEOFConfirmed"] and cleanup["removed"]
    assert command["exitCode"] == 101 and not command["timedOut"] and command["signalSent"] == []
    assert result["phasesBegun"] == ["validation", "initialize", "corpus_1"]
    first = result["firstFailure"]["payload"]
    assert (first["stage"], first["kind"], first["resource"], first["function"], first["offset"]) == ("Invocation", "ResourceExhausted", "TicketInventory", 79548, 15881589)
    assert first["attempted"] == 87 and first["limit"] == 86
    assert first["code"] == "swift_run_ticket_inventory"
    final = event("final_cleanup_usage")
    empty = all(value["current"] == 0 for value in final["reservations"].values() if isinstance(value, dict))
    empty = empty and final["reservations"]["live_tickets"] == 0 and all(value["current"] == 0 for value in final["live"].values())
    assert empty and final["cleanup_invariant"] is None and event("cleanup_reservations_and_live_empty") is True
    assert event("cleanup_empty") is False and result["ownedCleanupEmpty"] is False
    save("target-once-classification.json", {"schema": 1,
        "classification": "bounded-real-typed-ticket-inventory-failure-after-resident-index",
        "rawResultSHA256": sha(HERE / "target-once-result.json"),
        "rawStderrSHA256": sha(HERE / "commands/target-once/stderr"),
        "targetAttempts": 1, "retryAttempted": False, "initializeCompleted": event("phase_reply") == "Initialized",
        "corpus1Attempted": True, "corpus2Attempted": False, "firstTypedFailure": first,
        "historicalFailurePreservedInFinalFailure": all(event("final_failure")[key] == first[key] for key in first if key != "after_cleanup"),
        "consumingOwnerCleanupObserved": True, "finalCleanupReservationsAndLiveEmpty": empty,
        "finalCleanupInvariant": final["cleanup_invariant"], "rawHarnessCleanupEmpty": event("cleanup_empty"),
        "rawDriverOwnedCleanupEmpty": result["ownedCleanupEmpty"],
        "cleanupFlagExplanation": "The unchanged success-oriented cleanup_empty also requires no final failure. The original TicketInventory failure remains; the separate final consuming-cleanup usage and cleanup_reservations_and_live_empty show all current reservations, tickets and live counters zero.",
        "ticketInventoryPhaseObservation": {"phase": "corpus_1", "cursorStage": first["stage"],
            "function": first["function"], "sourceOffset": first["offset"],
            "liveTicketsAtFailure": first["at_failure"]["reservations"]["live_tickets"],
            "peakTicketsAtFailure": first["at_failure"]["reservations"]["peak_tickets"],
            "cacheEntriesAtFailure": first["at_failure"]["live"]["cache_entries"]["current"],
            "activePinsAtFailure": first["at_failure"]["live"]["active_pins"]["current"],
            "framesAtFailure": first["at_failure"]["live"]["frames"]["current"],
            "requestingTicketOwnerObserved": False,
            "scope": "unchanged observer identifies the invocation cursor and aggregate inventory; no per-ticket owner or requesting reservation identity was emitted"},
        "nativeParityObserved": False, "productionBaselineModifiedByDiagnostic": False,
        "budgetsChanged": False, "fullSLMatrixAccepted": False, "nativeSignedPublicAccepted": False, "gaAccepted": False})
    keys = ["cache_work", "execution_work", "instruction_fuel", "instructions", "host_calls"]
    snapshots = []
    for name in ("constructed", "initialize", "corpus_1"):
        value = event(name)
        snapshots.append({"event": name, "cache": value["cache"], "cacheEntries": value["usage"]["live"]["cache_entries"],
            "cacheReservation": value["usage"]["reservations"]["cache"],
            "work": {key: value["usage"][key] for key in keys}, "elapsedMicros": value["usage"]["elapsed_micros"]})
    increments = []
    for before, after in zip(snapshots, snapshots[1:]):
        increments.append({"from": before["event"], "to": after["event"],
            "cache": {key: after["cache"][key] - before["cache"][key] for key in after["cache"]},
            "work": {key: after["work"][key] - before["work"][key] for key in keys},
            "cacheEntriesCurrent": after["cacheEntries"]["current"] - before["cacheEntries"]["current"],
            "cacheReservationCurrent": after["cacheReservation"]["current"] - before["cacheReservation"]["current"],
            "elapsedMicros": after["elapsedMicros"] - before["elapsedMicros"]})
    save("phase-counters.json", {"schema": 1, "sourceEventsSHA256": sha(HERE / "target-once-events.json"),
        "scope": "direct snapshots and arithmetic intervals; corpus_1 is terminal after failure/drain, not the internal failure checkpoint",
        "snapshots": snapshots, "increments": increments})
    save("result-receipt.json", {"schema": 1, "status": "sealed-single-attempt-typed-ticket-inventory-failure",
        "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "sourceRevisionContext": binding["sourceRevisionContext"], "selectionRevisionContext": selected["selectionRevisionContext"],
        "baselineClosure": selected["baselineClosure"], "rootSelectionSHA256": sha(HERE / "root-selection.json"),
        "preparedSealSHA256": sha(HERE / "prepared-seal.json"), "preparedInputsUnchanged": True,
        "preparedExecutableRepresentation": "original byte-identical executable retained losslessly as bin/exact-tests.gz after owned cleanup",
        "harnessSHA256": selected["harnessSHA256"], "driverSHA256": selected["driverSHA256"], "binarySHA256": selected["binarySHA256"],
        "inputBindingSHA256": selected["inputBindingSHA256"], "target": binding["target"],
        "targetAttempts": 1, "exitCode": command["exitCode"], "durationSeconds": command["durationSeconds"],
        "timedOut": command["timedOut"], "signalsSent": command["signalSent"], "argv": command["argv"],
        "commandReceipt": "commands/target-once/receipt.json", "validationUsage": event("validation_usage"),
        "validationObservations": event("validation_observations"), "inputOverlap": event("input_overlap"),
        "initializeCompleted": True, "firstFailure": result["firstFailure"], "phasesBegun": result["phasesBegun"],
        "ticketInventoryPhaseObservation": read("target-once-classification.json")["ticketInventoryPhaseObservation"],
        "cleanupCommand": ["python3", "-B", str((HERE / "diagnostic.py").relative_to(ROOT)), "cleanup"],
        "cleanupCommandExitCode": 0, "cleanupStdoutSHA256": sha(HERE / "cleanup.stdout"),
        "cleanupStderrSHA256": sha(HERE / "cleanup.stderr"),
        "consumingOwnerCleanupObserved": True, "finalCleanupReservationsAndLiveEmpty": empty,
        "rawHarnessCleanupEmpty": event("cleanup_empty"), "rawDriverOwnedCleanupEmpty": result["ownedCleanupEmpty"],
        "finalCleanupUsage": final, "phaseCounters": read("phase-counters.json"),
        "processGroupEmpty": command["processGroupEmpty"], "rawStreamEOFConfirmed": command["rawStreamEOFConfirmed"],
        "scratchRemoved": cleanup["removed"], "logicalBytesRemoved": cleanup["logicalBytesRemoved"],
        "retainedExecutable": cleanup["retainedExecutable"],
        "hostChildHighWaterRSS": {"value": command["cumulativeChildrenMaxRSS"], "unit": "bytes on Darwin", "scope": command["maxRSSUnit"], "performanceAcceptance": False},
        "nativeParity": False, "productionBaselineModifiedByDiagnostic": False, "budgetWidened": False,
        "retryAttempted": False, "fullSLMatrixAccepted": False, "productionAccountingAccepted": False,
        "nativeSignedPublicAccepted": False, "performanceSizeMemoryAccepted": False,
        "fieldLogPublishedPackageQualified": False, "physicalPhonesAttempted": False, "gaAccepted": False})
    files = {str(path.relative_to(HERE)): sha(path) for path in sorted(HERE.rglob("*"))
             if path.is_file() and path.name != "result-seal.json"}
    external = {name: sha(ROOT / name) for name in (
        "docs/swift-exact-reactor-after-resident-index.md",
        "verification/swift-exact-reactor-after-resident-index-root-selection/execution.json")}
    external[str(Path(binding["target"]["path"]).relative_to(ROOT))] = binding["target"]["sha256"]
    save("result-seal.json", {"schema": 1, "status": "single-attempt-typed-ticket-inventory-failure",
        "targetAttempts": 1, "files": files, "externalFiles": external})
    print(json.dumps({"sealedMembers": len(files), "externalBindings": len(external),
        "resultSealSHA256": sha(HERE / "result-seal.json"), "firstTypedFailure": "TicketInventory",
        "finalCleanupReservationsAndLiveEmpty": empty, "scratchRemoved": True, "targetAttempts": 1, "gaAccepted": False}))


if __name__ == "__main__":
    main()
