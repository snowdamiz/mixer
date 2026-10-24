#!/usr/bin/env python3
"""One-time source/host-method review seal; never a runtime authorization."""
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
assert receipt["status"] == "independent-source-and-host-method-review-approved-runtime-unverified"
assert receipt["findings"] == [] and receipt["sourceAndHostMethodApproved"] is True
assert receipt["privateRuntimeApproved"] is False and receipt["runtimeAuthorizationReceiptIssued"] is False
assert receipt["runtimeRowsExecuted"] == 0 and receipt["LinuxRuntimeAccepted"] is False
v5 = ROOT / "verification/stripe-webhook-linux-resource-harness/v5"
assert sha(v5 / "seal.json") == receipt["v5SealSha256"]
for name, expected in {**receipt["rootBindings"], **receipt["reviewedSourceBindings"]}.items():
    assert sha(ROOT / name) == expected, name
fixture = receipt["independentImmutableFixture"]
assert sha(ROOT / fixture["path"]) == fixture["sha256"]
review_root = ROOT / "verification/stripe-webhook-resource-ingress-root-review"
sources = ("run.py", "linux_backend.py", "proc_inventory.py", "lifecycle.py", "role.exs", "fault_helper.c",
           "control_nif.c", "checkpoint.py", "signal-authority.json")
payload = {"v1Seal": "0af22f84b6129b781f7af970cafdc71bf208f86f63275e4584a79875ce1c7dfe",
    "v2Seal": sha(v5.parent / "v2/seal.json"), "v3Seal": sha(v5.parent / "v3/seal.json"), "v4Seal": sha(v5.parent / "v4/seal.json"),
    "sources": {name: sha(v5 / name) for name in sources},
    "amendmentSHA256": sha(review_root / "r14-r18-private-interface-amendment.json"),
    "signalAmendmentSHA256": sha(review_root / "r14-real-signal-amendment.json"),
    "repairSelectionSHA256": sha(review_root / "v2-cleanup-review-repair-selection.json"),
    "v4RepairSelectionSHA256": sha(review_root / "v3-cleanup-review-repair-selection.json"),
    "v5RepairSelectionSHA256": sha(review_root / "v4-partial-descriptor-repair-selection.json")}
assert digest(payload) == receipt["harnessDigest"] == "9459d8fadeaaeda3f5c15971c7c3bce65bc71f87eca1d75dbe1d5c923b532b68"
enum = json.loads((HERE / "enum-review.json").read_text())
assert [r["stage"] for r in enum["rows"]] == list(range(1, 35))
assert len(receipt["phaseReview"]["phases"]) == 4
assert all(r["exitCode"] == 0 for r in receipt["commands"])
assert receipt["checks"]["producerHostControls"]["passed"] == 82
assert receipt["checks"]["independentHostControls"]["passed"] == 8
command_path = HERE / "command-receipt.json"
command = json.loads(command_path.read_text())
command["producerOrPreviousReviewBytesChanged"] = command.pop("allProducerAndPreviousReviewBytesChanged")
command_path.write_text(json.dumps(command, indent=2, sort_keys=True) + "\n")
receipt["artifactFinalizationCommand"] = {"argv": [sys.executable, "-B", str(Path(__file__).resolve())],
    "cwd": str(ROOT), "scope": "owned review/schema/source-identity validation and one-time seal only"}
for name in receipt["reviewArtifactBindings"]:
    receipt["reviewArtifactBindings"][name] = sha(ROOT / name)
receipt["reviewArtifactBindings"][str(Path(__file__).resolve().relative_to(ROOT))] = sha(Path(__file__).resolve())
receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
files = {str(p.relative_to(ROOT)): sha(p) for p in HERE.rglob("*") if p.is_file()}
doc = ROOT / "docs/stripe-resource-harness-v5-independent-review.md"
files[str(doc.relative_to(ROOT))] = sha(doc)
seal = {"schema": 1, "scope": "independent v5 source/host-method review approved; no runtime authorization or qualification",
        "files": files, "treeDigest": digest(files)}
SEAL.write_text(json.dumps(seal, indent=2, sort_keys=True) + "\n")
for name, expected in files.items():
    assert sha(ROOT / name) == expected, name
print(json.dumps({"status": "sealed-independent-v5-source-host-method-approved-runtime-unverified", "reviewFiles": len(files),
    "reviewSealSha256": sha(SEAL), "treeDigest": seal["treeDigest"], "findings": 0,
    "producerHostControlsPassed": 82, "independentHostControlsPassed": 8,
    "phasesReviewed": 4, "faultBoundariesReviewed": 34, "runtimeRowsExecuted": 0,
    "sourceAndHostMethodApproved": True, "privateRuntimeApproved": False}, sort_keys=True))
