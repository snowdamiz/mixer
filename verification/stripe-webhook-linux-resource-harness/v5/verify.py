#!/usr/bin/env python3
"""Read-only v5 source/evidence checks; no Linux compiler, role or namespace."""
import argparse
import json
from pathlib import Path

import checkpoint
import lifecycle as life
import run as candidate
from author import source_table

HERE = Path(__file__).resolve().parent
ROOT = checkpoint.ROOT
base = candidate.base


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--seal", action="store_true")
    args = parser.parse_args()
    checkpoint.verify()
    if args.seal:
        assert not list(HERE.glob(".owned-scratch-*"))
        files = {str(p.relative_to(ROOT)): base.sha(p) for p in HERE.rglob("*") if p.is_file() and p != HERE / "seal.json"}
        for p in (candidate.AMENDMENT, candidate.SIGNAL_AMENDMENT, candidate.REPAIR_SELECTION, candidate.V4_REPAIR_SELECTION, candidate.V5_REPAIR_SELECTION,
                  checkpoint.PACKET / "v2/seal.json", ROOT / "verification/stripe-resource-harness-v2-independent-review/review-seal.json",
                  checkpoint.PACKET / "v3/seal.json", ROOT / "verification/stripe-resource-harness-v3-independent-review/review-seal.json",
                  checkpoint.PACKET / "v4/seal.json", ROOT / "verification/stripe-resource-harness-v4-independent-review/review-seal.json",
                  checkpoint.PACKET / "checkpoints/v1.tar", checkpoint.PACKET / "checkpoints/v1.json",
                  checkpoint.PACKET / "checkpoints/v1-seal.json"):
            files[str(p.relative_to(ROOT))] = base.sha(p)
        (HERE / "seal.json").write_text(json.dumps({"schema": 1, "scope": "v5 immediate sanitized descriptor observation repair; independent revised review and Linux unverified",
            "files": files, "treeDigest": base.digest(files)}, indent=2, sort_keys=True) + "\n")
    seal = base.load(HERE / "seal.json")
    assert seal["schema"] == 1 and seal["treeDigest"] == base.digest(seal["files"])
    actual = {str(p.relative_to(ROOT)) for p in HERE.rglob("*") if p.is_file() and p != HERE / "seal.json"}
    expected = {name for name in seal["files"] if name.startswith(str(HERE.relative_to(ROOT)) + "/")}
    assert actual == expected
    for name, expected_sha in seal["files"].items():
        path = ROOT / name
        assert path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(ROOT)
        assert base.sha(path) == expected_sha, name
    receipt = base.load(HERE / "authoring-receipt.json")
    assert receipt["status"] == "passed-host-controls-only-linux-runtime-unavailable"
    assert receipt["hostTests"] == {"run": 82, "passed": 82, "failed": 0, "errors": 0, "skipped": 0}
    assert receipt["runtimeRowsExecuted"] == 0 and receipt["tools"]["LinuxCOrNIFOrBEAMCompiled"] is False
    assert receipt["harnessDigest"] == candidate.harness_digest()
    assert receipt["implementationComplete"] is False and receipt["gaAccepted"] is False
    assert receipt["independentImplementationAndEnumReview"] == "pending"
    assert receipt["repairSelectionSha256"] == candidate.REPAIR_SELECTION_SHA
    assert receipt["v4RepairSelectionSha256"] == candidate.V4_REPAIR_SELECTION_SHA
    assert receipt["v5RepairSelectionSha256"] == candidate.V5_REPAIR_SELECTION_SHA
    assert receipt["repairHostControls"] == 16 and receipt["inheritedHostControls"] == 66
    for name in ("control_nif.c", "fault_helper.c", "role.exs", "signal-authority.json"):
        assert (HERE / name).read_bytes() == (checkpoint.PACKET / "v2" / name).read_bytes()
    for name, expected_sha in receipt["sourceInputs"].items():
        assert base.sha(HERE / name) == expected_sha
    assert base.load(HERE / "contract-table.json") == source_table()
    assert len(life.BOUNDARIES) == 34 and len(life.PHASES) == 4
    assert base.digest(candidate.fault_table()) == base.load(checkpoint.PACKET / "v2/contract-table.json")["faultEnumDigest"]
    assert life.ROW_WALL_NS == 120_000_000_000 and life.SUITE_WALL_NS == 900_000_000_000
    assert life.STOP_GRACE_NS == 2_000_000_000 and life.DISPOSAL_NS == 2_500_000_000
    assert not list(HERE.glob(".owned-scratch-*"))
    if args.live:
        candidate.check_amendment()
        base.profile(base.CONTRACT / "profile.json")
        base.source_inputs()
    print(json.dumps({"status": "passed-v5-source-host-evidence-only", "live": args.live,
        "sealedFiles": len(seal["files"]), "hostControlsPassed": 82,
        "sourcePhaseFixtures": 4, "sourceFaultBoundaries": 34, "runtimeRowsExecuted": 0,
        "LinuxCompileAndRuntimeAccepted": False, "independentReview": "pending", "gaAccepted": False}))


if __name__ == "__main__":
    main()
