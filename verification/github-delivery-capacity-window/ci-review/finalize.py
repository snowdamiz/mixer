#!/usr/bin/env python3
"""Build separate local and publishable evidence seals from the reviewed packet."""
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name):
    return json.loads((HERE / name).read_text())


def save(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def record(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main():
    review, receipt, snapshot, inventory = [load(n) for n in ("review.json", "receipt.json", "final-snapshot.json", "artifact-inventory.json")]
    arms = []
    for arm in review["arms"]:
        usage, failure, geometry = arm["finalUsage"], arm["firstFailure"], arm["geometry"]["plan"]
        arms.append({
            "name": arm["arm"], "sourceSHA256": arm["sourceSHA256"], "finiteTestsPassed": arm["finitePassed"], "harnessTestsPassed": arm["harnessPassed"],
            "conservativeCombinedBytes": geometry["conservative_combined"], "combinedHeadroomBytes": 268435456 - geometry["conservative_combined"],
            "firstFailure": {k: failure[k] for k in ("kind", "code", "stage", "resource", "deadline_origin", "function", "offset")},
            "failureElapsedMicros": failure["at_failure"]["elapsed_micros"],
            "phaseOrder": arm["phaseOrder"], "completedOriginalCorpora": arm["nativeEqualPhases"],
            "firstCorpusAllElevenFieldsMatched": arm["nativeEqualPhases"] == ["corpus_1"],
            "secondCorpusEntered": "corpus_2" in arm["phaseOrder"], "secondCorpusCompleted": "corpus_2" in arm["nativeEqualPhases"],
            "hostFeasibilityAccepted": arm["hostFeasibility"],
            "finalCounters": {k: usage[k] for k in ("instructions", "instruction_fuel", "cache_work", "execution_work", "host_calls", "elapsed_micros", "deadline_overshoot_micros")},
            "peakFrames": usage["live"]["frames"]["peak"], "peakPins": usage["live"]["active_pins"]["peak"],
            "peakCombinedLogicalBytes": usage["reservations"]["combined"]["peak"],
            "allFinalCurrentReservationsLiveCountersAndTicketsZero": arm["allFinalCurrentResourcesAndTicketsZero"],
        })
    summary = {
        "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "Sanitized actual CI diagnostic evidence. Raw artifact, log and detailed review remain local. No production default, native, OTA, published external FieldLog or GA acceptance.",
        "run": {"id": review["run"], "url": "https://github.com/snowdamiz/mixer/actions/runs/40788458735", "attempt": 1, "head": review["head"], "tree": review["tree"], "conclusion": snapshot["capacity"]["conclusion"], "profile": "capacity-window-v1"},
        "ordinaryPush": {"id": 40788454624, "url": "https://github.com/snowdamiz/mixer/actions/runs/40788454624", "conclusion": snapshot["ordinary"]["conclusion"], "jobs": [{"name": j["name"], "conclusion": j["conclusion"]} for j in snapshot["ordinary"]["jobs"]]},
        "artifact": {**review["artifact"], "files": inventory["fileCount"]},
        "review": {"offlineChecks": receipt["checksPassed"], "allPassed": review["allChecksPassed"], "sourceSHA256": record(HERE / "review.py")["sha256"], "receiptSHA256": record(HERE / "receipt.json")["sha256"], "sourcePacketsAllSealedMembersVerified": True, "workloadAndAllOriginalInputBindingsVerified": True, "rawClassificationGeometryAndSourcesReproduced": True, "reviewerBookkeepingCorrectionRetained": True},
        "sharedBounds": {"frames": 128, "activePins": 128, "combinedBytes": 268435456, "cacheWork": 4000000000, "instructionFuel": 2000000000, "executionWork": 16000000000, "runtimeDeadlineMilliseconds": 600000, "wasiDeadlineMilliseconds": 600000, "capacityOnlyBetweenArmFactor": True},
        "arms": arms, "fullAttemptsClosed": 2, "fullAttemptsRemaining": 0,
        "bothFiniteGeometryAndHarnessPreparationsBeforeAnyFull": True, "allElevenRemoteCommandsReapedAndOwnedGroupsAbsent": True,
        "remoteOutputClosureEvidence": "Regular-file contexts closed after wait4 child reaping and group absence; exact final hashes verified. Frozen driver has no explicit pipe EOF flag.",
        "ownedScratchRemoved": review["cleanup"]["ownedScratchRemoved"], "allOriginalFailuresPreserved": True, "allAttributionValid": True,
        "matchedObservedCounterCursorPrefixes": [p["instructions"] for p in review["pairedPrefixes"] if p["observedCountersAndCursorMatched"]],
        "unmatchedObservedCounterCursorPrefixes": [p["instructions"] for p in review["pairedPrefixes"] if not p["observedCountersAndCursorMatched"]],
        "retainedBaseline": {"run": 40779075333, "reviewSealSHA256": review["retainedBaseline"]["reviewSealSHA256"], "originalCacheWorkFailurePreserved": True, "dense256MatchedObservedPrefixes": [p["instructions"] for p in review["retainedBaseline"]["matchedObservedPrefixes"] if p["observedCountersAndCursorMatched"]]},
        "decision": "Accept closed diagnostic campaign: both arms now complete the first original eleven-field corpus and enter the second; both stop at the unchanged cumulative Runtime deadline during corpus_2. Full two-corpus host feasibility remains unproved.",
        "endpointTimingClaim": False, "productionDefaultOrGAAccepted": False, "newLocalCompilerGuestNativeUICaptureRuns": 0,
        "measurementLimits": ["One sequential sample per arm. Matched observed counters and cursor do not establish identical host entropy or all guest state.", "After 250M observed counters/cursors diverge; later elapsed, final debit and final progress observations do not establish a paired speedup or causal capacity effect.", "Work credits are not CPU time; logical reservations are not process RSS. CI executable hashes are reported manifests, not retained executable bytes rehashed by this reviewer."],
    }
    save("sanitized-summary.json", summary)
    publishable = {"sanitized-summary.json": record(HERE / "sanitized-summary.json")}
    save("sanitized-seal.json", {"schema": 1, "scope": "Only this sanitized summary is eligible for root publication selection. Raw local packet excluded.", "files": publishable, "filesCount": len(publishable), "totalBytes": sum(r["bytes"] for r in publishable.values()), "run": review["run"], "head": review["head"], "tree": review["tree"]})
    files = {str(p.relative_to(HERE)): record(p) for p in sorted(HERE.rglob("*")) if p.is_file() and p.name != "seal.json"}
    save("seal.json", {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "scope": "Local actual CI evidence packet only; raw archive and log must not be published. Separate sanitized-seal.json binds the publication candidate.", "files": files, "filesCount": len(files), "totalBytes": sum(r["bytes"] for r in files.values()), "run": review["run"], "head": review["head"], "tree": review["tree"]})
    print(json.dumps({"localSeal": record(HERE / "seal.json"), "sanitizedSeal": record(HERE / "sanitized-seal.json"), "summary": record(HERE / "sanitized-summary.json"), "files": len(files), "checks": receipt["checksPassed"]}))


if __name__ == "__main__":
    main()
