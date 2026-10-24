#!/usr/bin/env python3
"""One-time seal of this v3 review; no compiler, runtime or proc API."""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SEAL = HERE / "review-seal.json"
assert not SEAL.exists(), "Preserve the existing immutable review"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


receipt_path = HERE / "receipt.json"
receipt = json.loads(receipt_path.read_text())
assert receipt["status"] == "independent-source-review-changes-required-private-runtime-not-approved"
assert receipt["privateRuntimeApproved"] is False and receipt["runtimeRowsExecuted"] == 0
assert {row["id"] for row in receipt["findings"]} == {"V3-F1", "V3-F2"}
assert receipt["v3SealSha256"] == sha(ROOT / "verification/stripe-webhook-linux-resource-harness/v3/seal.json")
for name, expected in {**receipt["reviewedSourceBindings"], **receipt["rootBindings"]}.items():
    assert sha(ROOT / name) == expected, name
enum = json.loads((HERE / "enum-review.json").read_text())
assert [row["stage"] for row in enum["rows"]] == list(range(1, 35))
assert len(receipt["phaseReview"]["phases"]) == 4
assert receipt["checks"]["producerHostControls"]["passed"] == 52
assert receipt["checks"]["independentHostControls"]["passed"] == 8
assert all(row["exitCode"] == 0 for row in receipt["commands"])
refs_path = HERE / "api-source-review.json"
refs = json.loads(refs_path.read_text())
for manual in refs["manuals"]:
    manual["version"] = "Linux man-pages 6.19"
refs_path.write_text(json.dumps(refs, indent=2, sort_keys=True) + "\n")
receipt["findings"][1]["lineStart"] = 564
receipt["findings"][1]["lineEnd"] = 575
receipt["findings"][1]["relatedSourceLines"] = [[581, 585], [632, 644]]
receipt["artifactFinalizationCommand"] = {"argv": [sys.executable, "-B", str(Path(__file__).resolve())],
    "cwd": str(ROOT), "scope": "owned review artifact validation/finalization and one-time seal only"}
for name in list(receipt["reviewArtifactBindings"]):
    receipt["reviewArtifactBindings"][name] = sha(ROOT / name)
receipt["reviewArtifactBindings"][str(Path(__file__).resolve().relative_to(ROOT))] = sha(Path(__file__).resolve())
receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
files = {str(path.relative_to(ROOT)): sha(path) for path in HERE.rglob("*") if path.is_file()}
doc = ROOT / "docs/stripe-resource-harness-v3-independent-review.md"
files[str(doc.relative_to(ROOT))] = sha(doc)
seal = {"schema": 1, "scope": "independent v3 re-review: two remaining source findings; no runtime approval",
        "files": files, "treeDigest": digest(files)}
SEAL.write_text(json.dumps(seal, indent=2, sort_keys=True) + "\n")
for name, expected in files.items():
    assert sha(ROOT / name) == expected, name
print(json.dumps({"status": "sealed-independent-v3-request-changes-review", "reviewFiles": len(files),
    "reviewSealSha256": sha(SEAL), "treeDigest": seal["treeDigest"], "findings": 2,
    "producerHostControlsPassed": 52, "independentHostControlsPassed": 8,
    "phasesReviewed": 4, "faultBoundariesReviewed": 34, "runtimeRowsExecuted": 0,
    "privateRuntimeApproved": False}, sort_keys=True))
