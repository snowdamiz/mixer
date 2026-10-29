#!/usr/bin/env python3
"""Seal source/data packet metadata after successful guarded controls."""
from offline_guard import install
install()

import json
import sys
from datetime import datetime, timezone

import prepare

HERE, ROOT = prepare.HERE, prepare.ROOT


def main():
    manifest = json.loads((HERE / "manifest.json").read_text())
    pure = json.loads((HERE / "pure-result.json").read_text())
    assert pure["passed"] == 12 and not pure["failed"] and not pure["errors"]
    assert pure["candidateTreeSHA256"] == manifest["candidateTreeSHA256"]
    receipt = {
        "schema": 1, "at": datetime.now(timezone.utc).isoformat(),
        "decision": "Source-only candidate prepared; independent source review and fresh hosted format/lint/regression remain pending",
        "ownership": "verification/swift-pin-bitmap-lint-correction/ only",
        "currentRevisionParentSupplied": prepare.REVISION,
        "baselineTreeSHA256": prepare.BASELINE_TREE,
        "priorCandidateTreeSHA256": manifest["priorCandidateTreeSHA256"],
        "formattedCandidateTreeSHA256": prepare.FORMATTED_TREE,
        "candidateTreeSHA256": manifest["candidateTreeSHA256"],
        "sourceMembers": 136, "overlays": len(manifest["overlayPaths"]),
        "actualDiagnosticUnion": {"baseline": 50, "candidate": 46, "shared": 45, "baselineOnly": 5, "candidateOnly": 1, "union": 51, "paths": 13, "categories": 16, "semanticAttribution": False, "exhaustive": False},
        "directlyDependentMechanicalCallsite": manifest["directCompatibilityDependency"],
        "commands": [{"command": "python3 -B verification/swift-pin-bitmap-lint-correction/prepare.py", "exit": 0, "pythonVersion": sys.version, "stdout": "local/prepare.stdout", "stdoutBinding": prepare.row(HERE / "local/prepare.stdout")},
                     {"command": pure["command"], "exit": 0, "pythonVersion": sys.version, "result": "pure-result.json", "stdout": "local/pure-controls.stdout", "stderr": "local/pure-controls.stderr", "stdoutBinding": prepare.row(HERE / "local/pure-controls.stdout"), "stderrBinding": prepare.row(HERE / "local/pure-controls.stderr")},
                     {"command": "python3 -B verification/swift-pin-bitmap-lint-correction/finalize.py", "exit": 0, "pythonVersion": sys.version}],
        "pureControls": {k: pure[k] for k in ("passed", "failed", "errors", "skipped", "assertions", "guardInstalledBeforeImplementationImports")},
        "APIAvailability": {"declaredMSRV": None, "declaredRustVersion": False, "newAPIHighWaterMark": "1.88.0", "observedSupportedHostCompilerBaseline": "1.98.1", "actualDiagnosticCompiler": "1.99.0", "lowerMSRVQualificationClaimed": False},
        "canonicalEdited": False, "frozenPacketsEdited": False, "runnerWorkflowEdited": False, "newDispatchSelected": False,
        "RustCargoRustfmtClippySwiftElixirCompilerProductRuntimeRuns": 0,
        "nativeUICaptureRuns": 0, "GitGhDeliveryDispatchActions": 0,
        "realNestedProcessesSessionsGroupsSignalsWaitsSockets": 0,
        "heldProcessesProbed": False, "ownedInstancesStarted": 0,
        "rawCIArtifactsRemainLocal": True,
        "preparationFailureHistory": "preparation-history.json",
        "sourceTestInventory": {"testMethods": sum(v["tests"] for v in pure["inventories"]["preservedSourceInventories"].values()), "assertionMacros": sum(sum(v["assertions"].values()) for v in pure["inventories"]["preservedSourceInventories"].values()), "errorLiterals": sum(v["preservedErrorLiterals"] for v in pure["inventories"]["preservedSourceInventories"].values())},
        "cleanup": "No owned runtime, child, socket, simulator, emulator or capture instance started. Only this source/data packet remains.",
        "publicSignedOTAFieldLogGAQualified": False,
        "pending": pure["pending"],
    }
    prepare.save(HERE / "receipt.json", receipt)
    members = {str(p.relative_to(HERE)): prepare.row(p) for p in sorted(HERE.rglob("*")) if p.is_file() and p.name != "seal.json" and "local" not in p.relative_to(HERE).parts}
    prepare.save(HERE / "seal.json", {"schema": 1, "scope": "Frozen source-only lint candidate; remote execution unselected", "candidateTreeSHA256": manifest["candidateTreeSHA256"], "files": members, "treeSHA256": prepare.closure(members), "rawLogsLocalOnly": True})
    print(json.dumps({"packetMembers": len(members), "candidateTreeSHA256": manifest["candidateTreeSHA256"], "sealSHA256": prepare.row(HERE / "seal.json")["sha256"]}))


if __name__ == "__main__":
    main()
