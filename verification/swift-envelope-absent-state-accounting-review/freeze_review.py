#!/usr/bin/env python3
"""Freeze completed offline review; all candidate artifacts remain read-only."""
from pathlib import Path
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
digest = lambda data: hashlib.sha256(data).hexdigest()
producer = ROOT / "verification/swift-envelope-absent-state-correction/proposal-1/seal.json"
producer_data = producer.read_bytes()
assert digest(producer_data) == "3da07ea9c308c9bee798cf7c891a8f9dfd2a170e85b43341c30caa38cdb9b04c"
for member in json.loads(producer_data)["members"]:
    data = (ROOT / member["path"]).read_bytes()
    assert len(data) == member["bytes"] and digest(data) == member["sha256"], member["path"]
prep = OWN / "preparation/seal.json"
assert digest(prep.read_bytes()) == "4bbf4fcd7ffeee393f2e79ffd7d549adda148da74d557cb99db4aa1a7feb3b35"
for member in json.loads(prep.read_bytes())["members"]:
    data = (ROOT / member["path"]).read_bytes()
    assert len(data) == member["bytes"] and digest(data) == member["sha256"], member["path"]
for input_file in json.loads((OWN / "preparation/receipt.json").read_text())["inputs"]:
    data = (ROOT / input_file["path"]).read_bytes()
    assert len(data) == input_file["bytes"] and digest(data) == input_file["sha256"], input_file["path"]
for path in OWN.rglob("*.json"):
    json.loads(path.read_text())
doc = ROOT / "docs/swift-envelope-absent-state-accounting-review.md"
assert all(line == line.rstrip() for line in doc.read_text().splitlines()), "trailing document whitespace"
audit = json.loads((OWN / "audit-1/receipt.json").read_text())
assert audit["passed"] == 352 and audit["failed"] == 0
head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
receipt = {
    "schema": 1,
    "at": datetime.now(timezone.utc).isoformat(),
    "status": "proposed-source-bounds-supported-root-ownership-selection-and-execution-pending",
    "command": "python3 verification/swift-envelope-absent-state-accounting-review/freeze_review.py",
    "tool": {"python": platform.python_version(), "executable": sys.executable},
    "source_revision_context": head,
    "producer_seal_sha256": digest(producer_data),
    "producer_member_count": 35,
    "producer_total_bytes": 205372,
    "producer_members_match_at_closure": True,
    "preparation_and_prior_input_identities_match_at_closure": True,
    "candidate_source_sha256": audit["candidate_source_sha256"],
    "parent_source_sha256": audit["parent_source_sha256"],
    "independent_source_pair_digest": audit["source_pair_digest"],
    "mechanical_source_checks": {"passed": 352, "failed": 0, "runtime_tests": False},
    "accounting": {"rows":121,"edges":108,"leaf":425,"W":24,"B":471,"G_proposed_amount":112,"T":42,"finish":47,"F":42,"validator_paths":[2,3,4,5],"guard_paths":[7,7,112]},
    "root_selection_required": "Amend existing G ownership to one terminal unpaid leaf among absent/invalid-spent/present-underfunded; caller W24 remains independently main-paid",
    "ownership_or_numeric_selection_by_reviewer": False,
    "candidate_compiled_or_executed": False,
    "behavior_product_release_or_GA_accepted": False,
    "failures_preserved": ["Original old-packet F1/R2 source failure remains referenced unchanged", "authoring-failure-1.json records rejected documentation patch before application"],
    "scope": "Independent offline review, standard-library hash/JSON/byte reconstruction and accounting arithmetic only. No candidate or producer script is imported/executed. No Rust compilation, native/UI/capture/device/process discovery or forbidden hosted path. Only assigned review document and own verification directory were written.",
    "pending": ["root G ownership selection", "new corrected candidate host behavior and regression controls", "fresh complete layouts and API controls", "native/device gates under pause", "all product/release/FieldLog/GA gates"]
}
(OWN / "final-review-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
closure = OWN / "closure"
closure.mkdir(exist_ok=False)
(closure / "stdout.txt").write_text("closure identity/JSON/whitespace checks passed; proposed source bounds supported; root ownership selection and execution pending\n")
(closure / "stderr.txt").write_bytes(b"")
members = []
paths = [doc] + sorted(p for p in OWN.rglob("*") if p.is_file() and p.name not in ["seal.json", "seal.sha256"])
# The preparation seal itself is an immutable input and remains a member.
paths.append(prep)
for path in sorted(set(paths)):
    assert not path.is_symlink()
    data = path.read_bytes()
    members.append({"path":str(path.relative_to(ROOT)),"bytes":len(data),"sha256":digest(data)})
seal = {
    "schema":1,
    "status":receipt["status"],
    "candidate_source_sha256":receipt["candidate_source_sha256"],
    "producer_seal_sha256":receipt["producer_seal_sha256"],
    "members":members,
    "member_count":len(members),
    "total_bytes":sum(m["bytes"] for m in members),
    "source_checks_passed":352,
    "source_checks_failed":0,
    "scope":receipt["scope"],
    "candidate_compiled_or_executed":False,
    "ownership_selected":False,
    "behavior_or_product_or_GA_accepted":False
}
(OWN / "seal.json").write_text(json.dumps(seal, indent=2, sort_keys=True) + "\n")
seal_hash = digest((OWN / "seal.json").read_bytes())
(OWN / "seal.sha256").write_text(seal_hash + "  seal.json\n")
print(json.dumps({"status":seal["status"],"seal_sha256":seal_hash,"member_count":len(members),"total_bytes":seal["total_bytes"]},sort_keys=True))
