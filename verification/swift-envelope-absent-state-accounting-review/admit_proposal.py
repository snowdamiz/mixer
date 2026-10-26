#!/usr/bin/env python3
"""Independent hash admission only. Never imports or executes proposal code."""
from pathlib import Path
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent / "admission-1"
OWN.mkdir(exist_ok=False)
seal_path = ROOT / "verification/swift-envelope-absent-state-correction/proposal-1/seal.json"
seal_bytes = seal_path.read_bytes()
expected_seal = "3da07ea9c308c9bee798cf7c891a8f9dfd2a170e85b43341c30caa38cdb9b04c"
digest = lambda data: hashlib.sha256(data).hexdigest()
results = []
assert digest(seal_bytes) == expected_seal, "explicit handoff seal mismatch"
seal = json.loads(seal_bytes)
names = set()
for member in seal["members"]:
    name = member["path"]
    assert name not in names and not Path(name).is_absolute() and ".." not in Path(name).parts, name
    names.add(name)
    path = ROOT / name
    assert not path.is_symlink() and path.is_file(), name
    data = path.read_bytes()
    result = {"path": name, "bytes": len(data), "sha256": digest(data), "matches": len(data) == member["bytes"] and digest(data) == member["sha256"]}
    results.append(result)
assert len(results) == seal["member_count"] == 35
assert sum(r["bytes"] for r in results) == seal["total_bytes"] == 205372
assert all(r["matches"] for r in results), "proposal member drift"
prep = ROOT / "verification/swift-envelope-absent-state-accounting-review/preparation/seal.json"
assert digest(prep.read_bytes()) == "4bbf4fcd7ffeee393f2e79ffd7d549adda148da74d557cb99db4aa1a7feb3b35"
for member in json.loads(prep.read_bytes())["members"]:
    data = (ROOT / member["path"]).read_bytes()
    assert len(data) == member["bytes"] and digest(data) == member["sha256"], "preparation member drift"
head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
receipt = {
    "schema": 1, "at": datetime.now(timezone.utc).isoformat(), "status": "all-handoff-members-match",
    "command": "python3 verification/swift-envelope-absent-state-accounting-review/admit_proposal.py",
    "tool": {"python": platform.python_version(), "executable": sys.executable},
    "source_revision_context": head, "seal_path": str(seal_path.relative_to(ROOT)), "seal_sha256": digest(seal_bytes),
    "member_count": len(results), "total_bytes": sum(r["bytes"] for r in results), "members": results,
    "source_tree_sha256_from_admitted_seal": seal["source_tree_sha256"],
    "preparation_freeze_matches": True,
    "candidate_source_sha256": seal["candidate_source_sha256"], "parent_source_sha256": seal["parent_source_sha256"],
    "scope": "Independent standard-library hash and size admission only. Candidate source is read as bytes for hashing, never imported, compiled or executed. No producer script is executed. Explicit producer frozen handoff preceded this command.",
    "acceptance": {"ownership_selection": False, "numeric_selection": False, "accounting": False, "behavior": False, "product": False, "GA": False}
}
(OWN / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
summary = json.dumps({"status": receipt["status"], "seal_sha256": receipt["seal_sha256"], "member_count": len(results), "total_bytes": receipt["total_bytes"]}, sort_keys=True) + "\n"
(OWN / "stdout.txt").write_text(summary)
(OWN / "stderr.txt").write_bytes(b"")
print(summary, end="")
