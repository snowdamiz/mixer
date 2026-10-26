#!/usr/bin/env python3
"""Freeze source-independent controls; never read the new candidate packet."""
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DOC = ROOT / "docs/swift-envelope-absent-state-behavior-review.md"
EXPECTED = {
    "verification/swift-ordered-retention-analyzer-envelope-root-review/implementation-accounting-addendum.json": "242b19079476ab4ee8437f4e7df04d8ebb584e899f7dab7bef537c8330f526dc",
    "verification/swift-ordered-retention-analyzer-envelope-root-review/correction-numeric-contract-selection.json": "199dfa75b024d04eeef28f2f40165115797a0bbb3d09a2405426172d8339867c",
    "verification/swift-ordered-retention-analyzer-envelope-root-review/final-correction-review-admission.json": "c45012695ad8c8d055d5c97dcb7af4bb9e72c6fb0965d82be788917341989d87",
    "verification/swift-analyzer-envelope-correction-behavior-review/final-review/finding-R2.json": "8ccca728cc7523b2f0622db35dea665327d5e8bc7179e21dca01818f6bd56098",
}
OTHER_INPUTS = [
    "AGENTS.md",
    "verification/swift-analyzer-envelope-correction-behavior-review/final-review.md",
    "verification/swift-analyzer-envelope-correction-behavior-review/final-review/coverage.json",
]


def digest(path):
    data = path.read_bytes()
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    contract = json.loads((OUT / "preaccess-contract.json").read_text())
    assert contract["status"] == "preaccess-frozen-candidate-unread-unselected"
    assert contract["readability"]["absent_lengths"] == [0, 32, 7731055]
    assert contract["absent"]["original_expected_debits"] == [0] * 10
    assert contract["absent"]["credits"] == [0, 1, 424, 425, 426]
    assert contract["readable_underfunding"]["credits_inclusive"] == [0, 424]
    assert contract["guard"]["requires_independent_accounting_then_root_selection"]
    for row in contract["public"]["paid_counter_vectors"]:
        assert row["debit"] == 534 * row["S"] + 47 * row["F"] + 425 * row["N"]
    assert len(contract["API"]["expected_negative"]) == 8
    assert len(contract["caller_debit_truth_table"]) == 16
    assert len({r["id"] for r in contract["caller_debit_truth_table"]}) == 16
    assert not contract["execution_state"]["candidate_source_accessed"]
    assert contract["execution_state"]["candidate_runtime_methods_executed"] == 0
    inputs = {p: digest(ROOT / p) for p in [*EXPECTED, *OTHER_INPUTS]}
    for path, expected in EXPECTED.items():
        assert inputs[path]["sha256"] == expected, path
    receipt = {
        "schema": 1,
        "at": datetime.now(timezone.utc).isoformat(),
        "command": [sys.executable, "-B", str(Path(__file__).resolve())],
        "python_version": sys.version,
        "platform": platform.platform(),
        "context_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "context_committed_tree": subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip(),
        "tree_scope": "committed context identity only; no claim that unread dirty candidate matches this tree",
        "inputs": inputs,
        "old_source_accessed": False,
        "new_candidate_accessed": False,
        "scope": "preaccess contract preparation and static self-consistency only; no candidate compile/runtime/API/native execution",
        "planned_caller_vectors": 16,
        "candidate_runtime_methods_executed": 0,
        "no_owned_runtime_children_started": True,
        "cleanup": "no runtime child, binary or fixture scratch created; preparation files retained",
    }
    write_json(OUT / "prep-receipt.json", receipt)
    output = {"status": "frozen-preaccess-only", "input_hashes_verified": len(EXPECTED), "named_inputs": len(inputs), "planned_caller_vectors": 16, "candidate_runtime_methods_executed": 0}
    write_json(OUT / "preparation.stdout.json", output)
    members = [DOC, OUT / "preaccess-contract.json", Path(__file__).resolve(), OUT / "prep-receipt.json", OUT / "preparation.stdout.json"]
    write_json(OUT / "preaccess-seal.json", {"schema": 1, "status": "frozen-before-new-candidate-access", "members": {str(p.relative_to(ROOT)): digest(p) for p in members}})
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
