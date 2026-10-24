#!/usr/bin/env python3
"""Seal only this independent review after its host/source checks finish.

No runtime, compiler, socket, signal or live process API is used.
"""
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
assert len(receipt["findings"]) == 2
assert sha(ROOT / "verification/stripe-webhook-linux-resource-harness/v2/seal.json") == receipt["v2SealSha256"]
for name, expected in {**receipt["reviewedSourceBindings"], **receipt["rootAmendmentBindings"]}.items():
    assert sha(ROOT / name) == expected, name
enum = json.loads((HERE / "enum-review.json").read_text())
assert [row["stage"] for row in enum["rows"]] == list(range(1, 35))
assert len(receipt["phaseReview"]["phases"]) == 4
reproduced = json.loads((HERE / "source-defect-reproductions.json").read_text())
assert {row["finding"] for row in reproduced["findings"]} == {"F1", "F2"}
assert all(row["reproduced"] for row in reproduced["findings"])
receipt["phaseReview"]["validator"] = "verification/stripe-webhook-linux-resource-harness/v2/lifecycle.py:161"
receipt["findings"][0]["reproductionSourceLine"] = 41
receipt["findings"][1]["reproductionSourceLine"] = 74
receipt["artifactFinalizationCommand"] = {"argv": [sys.executable, "-B", str(Path(__file__).resolve())],
    "cwd": str(ROOT), "scope": "review artifact/schema/identity checks and one-time owned seal only"}
doc = ROOT / "docs/stripe-resource-harness-v2-independent-review.md"
receipt["reviewArtifactBindings"][str(doc.relative_to(ROOT))] = sha(doc)
receipt["reviewArtifactBindings"][str(Path(__file__).resolve().relative_to(ROOT))] = sha(Path(__file__).resolve())
receipt["officialSourceCheck"] = {"argv": ["python3", "-B", "-"],
    "tool": "urllib.request.urlopen/hashlib.sha256; bounded fixed URLs; bytes not retained",
    "output": "verification/stripe-resource-harness-v2-independent-review/official-source-reference-check.json"}
receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
files = {str(path.relative_to(ROOT)): sha(path) for path in HERE.rglob("*") if path.is_file()}
files[str(doc.relative_to(ROOT))] = sha(doc)
seal = {"schema": 1, "scope": "independent v2 source/contract/enum request-changes review; runtime not approved",
        "files": files, "treeDigest": digest(files)}
SEAL.write_text(json.dumps(seal, indent=2, sort_keys=True) + "\n")
for name, expected in files.items():
    assert sha(ROOT / name) == expected, name
print(json.dumps({"status": "sealed-independent-request-changes-review", "reviewFiles": len(files),
    "reviewSealSha256": sha(SEAL), "treeDigest": seal["treeDigest"], "findings": 2,
    "phasesReviewed": 4, "faultBoundariesReviewed": 34, "runtimeRowsExecuted": 0,
    "privateRuntimeApproved": False}, sort_keys=True))
