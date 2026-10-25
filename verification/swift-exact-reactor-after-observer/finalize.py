#!/usr/bin/env python3
"""Seal already-collected evidence; cannot build or execute a guest."""
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read(name):
    return json.loads((HERE / name).read_bytes())


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    assert not (HERE / "owned-scratch").exists()
    assert not (HERE / "bin/exact-tests").exists()
    command = read("commands/target-once/receipt.json")
    result = read("target-once-result.json")
    cleanup = read("cleanup.json")
    classification = read("target-once-classification.json")
    selected = read("root-selection.json")
    assert command["argv"] == selected["argv"] and selected["maxTargetAttempts"] == 1
    assert command["processGroupEmpty"] and cleanup["removed"]
    events = read("target-once-events.json")
    def event(name):
        return next((e["payload"] for e in events if e["event"] == name), None)
    save("receipt.json", {
        "schema": 1, "status": "sealed-single-attempt-typed-cache-work-failure",
        "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "sourceRevisionContext": read("binding.json")["sourceRevisionContext"],
        "selectedSourceRevisionContext": selected["sourceRevision"],
        "baselineClosure": selected["baselineClosure"],
        "rootSelectionSHA256": sha(HERE / "root-selection.json"),
        "harnessSHA256": selected["harnessSHA256"], "driverSHA256": selected["driverSHA256"],
        "binarySHA256": selected["binarySHA256"],
        "historicalPacket": read("binding.json")["historicalFailurePacket"],
        "target": read("binding.json")["target"],
        "targetAttempts": 1, "exitCode": command["exitCode"],
        "durationSeconds": command["durationSeconds"], "timedOut": command["timedOut"],
        "signalSent": command["signalSent"], "argv": command["argv"],
        "commandReceipt": "commands/target-once/receipt.json",
        "validationUsage": event("validation_usage"), "validationObservations": event("validation_observations"),
        "inputOverlap": event("input_overlap"), "initializeCompleted": classification["initializeCompleted"],
        "firstFailure": result["firstFailure"], "phasesBegun": result["phasesBegun"],
        "consumingOwnerCleanupObserved": classification["consumingOwnerCleanupObserved"],
        "finalCleanupReservationsAndLiveEmpty": classification["finalCleanupReservationsAndLiveEmpty"],
        "rawHarnessCleanupEmpty": classification["rawHarnessCleanupEmpty"],
        "rawDriverOwnedCleanupEmpty": result["ownedCleanupEmpty"],
        "cleanupClassification": "target-once-classification.json",
        "phaseCounters": read("phase-counters.json"),
        "finalCleanupUsage": event("final_cleanup_usage"),
        "processGroupEmpty": command["processGroupEmpty"], "scratchRemoved": cleanup["removed"],
        "logicalBytesRemoved": cleanup["logicalBytesRemoved"],
        "retainedExecutable": cleanup["retainedExecutable"],
        "hostChildHighWaterRSS": {"value": command["cumulativeChildrenMaxRSS"], "unit": "bytes on Darwin", "scope": command["maxRSSUnit"], "performanceAcceptance": False},
        "nativeParity": result["nativeParity"], "productionEngineChanged": False,
        "budgetWidened": False, "retryAttempted": False,
        "fullSLMatrixAccepted": False, "productionAccountingAccepted": False,
        "nativeSignedPublicAccepted": False, "performanceSizeMemoryAccepted": False,
        "fieldLogPublishedPackageQualified": False, "physicalPhonesAttempted": False,
        "gaAccepted": False})
    files = {str(p.relative_to(HERE)): sha(p) for p in sorted(HERE.rglob("*"))
             if p.is_file() and p.name != "seal.json"}
    external = {"docs/swift-exact-reactor-after-observer.md": sha(ROOT / "docs/swift-exact-reactor-after-observer.md"),
        "verification/swift-exact-reactor-diagnostic/seal.json": sha(ROOT / "verification/swift-exact-reactor-diagnostic/seal.json"),
        "verification/swift-exact-reactor-after-observer-root-selection/execution.json": sha(ROOT / "verification/swift-exact-reactor-after-observer-root-selection/execution.json"),
        str(Path(read("binding.json")["target"]["path"]).relative_to(ROOT)): read("binding.json")["target"]["sha256"]}
    save("seal.json", {"schema": 1, "status": "single-attempt-typed-cache-work-failure", "targetAttempts": 1,
         "files": files, "externalFiles": external})
    print(json.dumps({"sealedMembers": len(files), "externalBindings": len(external),
        "sealSHA256": sha(HERE / "seal.json"), "firstFailure": result["firstFailure"]["payload"]["resource"],
        "finalCleanupReservationsAndLiveEmpty": classification["finalCleanupReservationsAndLiveEmpty"], "gaAccepted": False}))


if __name__ == "__main__":
    main()
