#!/usr/bin/env python3
"""Seal the separate preaccess reconciliation without running Rust source."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
ORIGINAL = OUT.parent / "preaccess-seal.json"
EXPECTED_ORIGINAL = "e24d3bd09fd5bf07e5df86a03df2ca285eaea5837245666b3718c33b15fc56a4"
INPUTS = {
    "verification/swift-ordered-retention-analyzer-envelope-correction/src/envelope.rs": "7b8237abbaec492e595508eb7456dab38fbb0d92d8d3cd5a88184f7c1082b9d1",
    "verification/swift-ordered-retention-analyzer-envelope-root-review/implementation-accounting-addendum.json": "242b19079476ab4ee8437f4e7df04d8ebb584e899f7dab7bef537c8330f526dc",
    "verification/swift-ordered-retention-analyzer-envelope-root-review/correction-numeric-contract-selection.json": "199dfa75b024d04eeef28f2f40165115797a0bbb3d09a2405426172d8339867c",
}


def identity(path):
    b = path.read_bytes()
    return {"sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    assert identity(ORIGINAL)["sha256"] == EXPECTED_ORIGINAL
    original = json.loads(ORIGINAL.read_text())
    for name, expected in original["members"].items():
        assert identity(ROOT / name) == expected, name
    inputs = {name: identity(ROOT / name) for name in INPUTS}
    for name, expected in INPUTS.items():
        assert inputs[name]["sha256"] == expected, name
    supplement = json.loads((OUT / "contract-supplement.json").read_text())
    assert len(supplement["review_model_errors"]) == 4
    assert len(supplement["poststate_vectors"]) == 19
    assert len({r["id"] for r in supplement["poststate_vectors"]}) == 19
    assert not supplement["predicate_has_entry_budget"]
    assert not supplement["old_source_executed"]
    assert not supplement["new_candidate_accessed"]
    source = (ROOT / next(iter(INPUTS))).read_text().splitlines()
    line_ranges = [(99, 104), (127, 154), (253, 293), (298, 325)]
    ranges = []
    for first, last in line_ranges:
        data = ("\n".join(source[first-1:last]) + "\n").encode()
        ranges.append({"first": first, "last": last, "sha256": hashlib.sha256(data).hexdigest()})
    receipt = {
        "schema": 1,
        "at": datetime.now(timezone.utc).isoformat(),
        "command": [sys.executable, "-B", str(Path(__file__).resolve())],
        "python_version": sys.version,
        "context_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "context_committed_tree": subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip(),
        "tree_scope": "committed context identity, not unread candidate tree identity",
        "inputs": inputs,
        "old_source_inspected_ranges": ranges,
        "original_seal": identity(ORIGINAL),
        "original_members_verified_unchanged": len(original["members"]),
        "new_candidate_accessed": False,
        "source_executed": False,
        "candidate_runtime_methods_executed": 0,
        "scope": "old-source static reconciliation and artifact self-consistency; source-derived tables are not runtime passes",
        "native_capture_UI_process_discovery_started": False,
        "cleanup": "no compiled binary, runtime child or fixture scratch created; supplement retained",
    }
    write_json(OUT / "receipt.json", receipt)
    summary = {"status": "reconciled-preaccess-only", "original_members_unchanged": 5, "review_model_errors_preserved": 4, "poststate_vectors": 19, "candidate_runtime_methods_executed": 0}
    write_json(OUT / "preparation.stdout.json", summary)
    members = [OUT / n for n in ["supplement.md", "contract-supplement.json", "freeze_supplement.py", "receipt.json", "preparation.stdout.json"]]
    write_json(OUT / "seal.json", {"schema": 1, "status": "frozen-before-new-candidate-access", "original_seal_sha256": EXPECTED_ORIGINAL, "members": {str(p.relative_to(ROOT)): identity(p) for p in members}})
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
