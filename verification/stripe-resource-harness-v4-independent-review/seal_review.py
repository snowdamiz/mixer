#!/usr/bin/env python3
"""One-time independent v4 review seal; no runtime, compiler or proc access."""
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


path = HERE / "receipt.json"
receipt = json.loads(path.read_text())
assert receipt["status"] == "independent-source-review-changes-required-private-runtime-not-approved"
assert receipt["privateRuntimeApproved"] is False and receipt["runtimeRowsExecuted"] == 0
assert [row["id"] for row in receipt["findings"]] == ["V4-F1"]
assert receipt["v4SealSha256"] == sha(ROOT / "verification/stripe-webhook-linux-resource-harness/v4/seal.json")
for name, expected in {**receipt["rootBindings"], **receipt["reviewedSourceBindings"]}.items():
    assert sha(ROOT / name) == expected, name
for item in (receipt["independentImmutableFixture"], receipt["priorPrimarySourceReference"]):
    assert sha(ROOT / item["path"]) == item["sha256"]
v4 = ROOT / "verification/stripe-webhook-linux-resource-harness/v4"
review_root = ROOT / "verification/stripe-webhook-resource-ingress-root-review"
sources = ("run.py", "linux_backend.py", "proc_inventory.py", "lifecycle.py", "role.exs", "fault_helper.c",
           "control_nif.c", "checkpoint.py", "signal-authority.json")
payload = {"v1Seal": "0af22f84b6129b781f7af970cafdc71bf208f86f63275e4584a79875ce1c7dfe",
    "v2Seal": sha(v4.parent / "v2/seal.json"), "v3Seal": sha(v4.parent / "v3/seal.json"),
    "sources": {name: sha(v4 / name) for name in sources},
    "amendmentSHA256": sha(review_root / "r14-r18-private-interface-amendment.json"),
    "signalAmendmentSHA256": sha(review_root / "r14-real-signal-amendment.json"),
    "repairSelectionSHA256": sha(review_root / "v2-cleanup-review-repair-selection.json"),
    "v4RepairSelectionSHA256": sha(review_root / "v3-cleanup-review-repair-selection.json")}
assert digest(payload) == receipt["harnessDigest"] == "64768849091ac048d91c2679303506a40b18633a5982cc8f25683ff7f2b117ec"
enum = json.loads((HERE / "enum-review.json").read_text())
assert [row["stage"] for row in enum["rows"]] == list(range(1, 35))
assert len(receipt["phaseReview"]["phases"]) == 4
assert all(row["exitCode"] == 0 for row in receipt["commands"])
assert receipt["checks"]["producerHostControls"]["passed"] == 66
assert receipt["checks"]["independentHostControls"]["passed"] == 4
receipt["findings"][0]["relatedSourceLines"] = [[169, 176], [118, 123]]
receipt["artifactFinalizationCommand"] = {"argv": [sys.executable, "-B", str(Path(__file__).resolve())],
    "cwd": str(ROOT), "scope": "owned review/schema/source-identity validation and one-time seal only"}
receipt["reviewArtifactBindings"][str(Path(__file__).resolve().relative_to(ROOT))] = sha(Path(__file__).resolve())
path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
files = {str(p.relative_to(ROOT)): sha(p) for p in HERE.rglob("*") if p.is_file()}
doc = ROOT / "docs/stripe-resource-harness-v4-independent-review.md"
files[str(doc.relative_to(ROOT))] = sha(doc)
seal = {"schema": 1, "scope": "independent v4 review: direct v3 repairs confirmed; partial descriptor evidence finding; no runtime approval",
        "files": files, "treeDigest": digest(files)}
SEAL.write_text(json.dumps(seal, indent=2, sort_keys=True) + "\n")
for name, expected in files.items():
    assert sha(ROOT / name) == expected, name
print(json.dumps({"status": "sealed-independent-v4-request-changes-review", "reviewFiles": len(files),
    "reviewSealSha256": sha(SEAL), "treeDigest": seal["treeDigest"], "findings": 1,
    "directV3RepairsConfirmed": 2, "producerHostControlsPassed": 66, "independentHostControlsPassed": 4,
    "phasesReviewed": 4, "faultBoundariesReviewed": 34, "runtimeRowsExecuted": 0,
    "privateRuntimeApproved": False}, sort_keys=True))
