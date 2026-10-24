#!/usr/bin/env python3
"""Seal the additive integration packet after actual terminal host outcomes."""
from pathlib import Path
import datetime
import sys
import integrate as i


def main():
    result = i.read(i.HERE / "host-result.json")
    cleanup = i.read(i.HERE / "cleanup.json")
    integration = i.read(i.HERE / "integration.json")
    assert result["focusedTestsPassed"] and result["focusedTests"] == 23
    assert result["clippyPassed"] and result["clippyExitCode"] == 0
    assert cleanup["removed"] and cleanup["holderCheckEmpty"]
    assert not Path(cleanup["scratch"]).exists()
    assert i.source_check() == i.read(i.HERE / "live-final-manifest.json")
    document = i.ROOT / "docs/swift-reactor-lifecycle-v3-integration.md"
    receipt = {
        "schema": "mixer.swift-lifecycle.live-v3-integration-receipt.1",
        "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "rootAcceptanceSHA256": i.ACCEPTANCE_SHA,
        "candidateClosure": i.CLOSURE,
        "sourceRevisionContext": integration["sourceRevisionContext"],
        "actualRevisionAtIntegration": integration["actualRevisionAtIntegration"],
        "scope": "Private experimental exact three-file integration; macOS arm64 synthetic host tests and required Swift-only Clippy",
        "scopeFiles": 132,
        "liveScopeEqualsAcceptedCandidate": True,
        "acceptedCandidateBytesChangedByThisLane": False,
        "selectedFileMutations": integration["exactSelectedChanges"],
        "retainedEvidence": {
            "runtimeFinalSealSHA256": i.FINAL_SEAL_SHA,
            "verifiedFinalPins": 978,
            "passedHostTestIdentityExecutions": 1602,
            "cargoCheckRows": 4,
            "qualifiedNodeOracleRows": 2,
            "targetsRemoved": 30,
            "matrixReexecuted": False,
        },
        "liveObservations": {
            "freshFocusedTests": 23,
            "focusedPassed": 23,
            "focusedFailed": 0,
            "focusedIgnored": 0,
            "swiftOnlyClippyWarningsDenied": True,
            "swiftOnlyClippyExitCode": 0,
            "freshOwnedTargets": 1,
            "ownedTargetsRemoved": 1,
            "logicalBytesRemoved": cleanup["logicalBytesRemoved"],
            "nativeInstancesCreated": 0,
            "qualifiedToolChecksBeforeAfterEachCommand": True,
            "sourceCheckedBeforeAfterEachCommand": True,
        },
        "fullPlannedSLRowsComplete": False,
        "pending": [
            "Complete original SL failure/checkpoint/budget/WASI permutations",
            "SL12 guest table mutation unsupported/unimplemented/unrun",
            "Real full 53 MB Swift reactor",
            "Public/signed execution and public lifecycle API",
            "Native simulator/emulator matrix and final physical-phone matrix",
            "Separate-repository FieldLog consuming immutable published packages",
            "Store/customer/operational and GA acceptance gates",
        ],
        "gitMutated": False,
        "sharedTrackersMutated": False,
        "frozenOtherLanesMutated": False,
        "document": {"path": str(document.relative_to(i.ROOT)), "sha256": i.digest(document)},
        "readOnlyReplayCommand": [sys.executable, "-B", "verification/swift-reactor-lifecycle-v3-integration/verify.py"],
        "rootAcceptanceAndGitRemainRootOwned": True,
    }
    i.save("receipt.json", receipt)
    files = {str(path.relative_to(i.HERE)): i.digest(path) for path in sorted(i.HERE.rglob("*")) if path.is_file() and path.name != "seal.json" and "__pycache__" not in path.parts}
    seal = {"schema": "mixer.swift-lifecycle.live-v3-integration-seal.1", "candidateClosure": i.CLOSURE, "rootAcceptanceSHA256": i.ACCEPTANCE_SHA, "retainedRuntimeFinalSealSHA256": i.FINAL_SEAL_SHA, "files": files, "packetClosureSHA256": i.sha(i.enc(files)), "document": receipt["document"], "fullPlannedSLRowsComplete": False}
    i.save("seal.json", seal)
    print(i.enc({"sealedFiles": len(files), "sealSHA256": i.digest(i.HERE / "seal.json"), "packetClosureSHA256": seal["packetClosureSHA256"]}).decode())


if __name__ == "__main__":
    main()
