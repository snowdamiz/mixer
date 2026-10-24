#!/usr/bin/env python3
"""Seal only independent review-owned files after checking the observed verdict."""

import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DOCUMENT = ROOT / "docs/hosted-build-lifecycle-independent-review.md"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


results = json.loads((HERE / "results.json").read_text())
assert results["result"] == "pure_review_passed_root_acceptance_pending"
assert results["producer_suite"]["exit_code"] == 0
assert results["producer_suite"]["counts"] == {"tests": 21, "failures": 0}
assert results["independent_controls"]["exit_code"] == 0
assert results["independent_controls"]["counts"] == {"tests": 10, "failures": 0}
assert results["all_producer_handoff_files_unchanged_after_review"] is True
assert results["snapshot_and_review_inputs_unchanged_during_tests"] is True
assert results["metadata_correction"]["tests_rerun"] is False
acceptance = json.loads((HERE / "source-acceptance.json").read_text())
producer_seal = ROOT / "verification/hosted-build-lifecycle/handoff-manifest.json"
assert sha(producer_seal) == results["producer_seal_sha256"]
for name, expected in acceptance["producer_files_verified"].items():
    assert sha(ROOT / name) == expected["sha256"]
for name, expected in acceptance["snapshot_sha256"].items():
    assert sha(HERE / "accepted-source" / name) == expected
assert not list(HERE.rglob("*.pyc")), "remove reviewer-owned bytecode before sealing"
paths = sorted(p for p in HERE.rglob("*") if p.is_file() and p.name not in ["review-manifest.json", "review-manifest.sha256"])
paths.append(DOCUMENT)
entries = {str(p.relative_to(ROOT)): {"sha256": sha(p), "size_bytes": p.stat().st_size} for p in sorted(paths)}
manifest = {
    "schema": "mixer.hosted-build-lifecycle.independent-review-seal.v1",
    "created_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "verdict": "sealed_pure_component_review_passed_root_acceptance_pending",
    "producer_seal_sha256": results["producer_seal_sha256"],
    "tested_source_tree_sha256": results["tested_source_tree_sha256"],
    "owned_review_files_frozen": True,
    "files": entries,
}
destination = HERE / "review-manifest.json"
destination.write_text(json.dumps(manifest, indent=2) + "\n")
digest = sha(destination)
(HERE / "review-manifest.sha256").write_text(f"{digest}  {destination.relative_to(ROOT)}\n")
print(json.dumps({"seal_sha256": digest, "file_count": len(entries), "verdict": manifest["verdict"]}, indent=2))
