#!/usr/bin/env python3
"""Verify only the owned frozen preparation packet; no semantic tests."""
import hashlib
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[2]
owned = root / "verification/swift-semantic-adapter-contract-review"
freeze = owned / "preaccess"
seal_bytes = (freeze / "seal.json").read_bytes()
seal_hash = hashlib.sha256(seal_bytes).hexdigest()
expected = (freeze / "seal.sha256").read_text().split()[0]
if seal_hash != expected:
    raise SystemExit("seal mismatch")
seal = json.loads(seal_bytes)
for member in seal["members"]:
    data = (freeze / member["path"]).read_bytes()
    if len(data) != member["bytes"] or hashlib.sha256(data).hexdigest() != member["sha256"]:
        raise SystemExit(f"member mismatch: {member['path']}")
if len(seal["members"]) != seal["member_count"]:
    raise SystemExit("member count mismatch")
if sum(item["bytes"] for item in seal["members"]) != seal["total_bytes"]:
    raise SystemExit("byte total mismatch")
plan = root / "docs/swift-semantic-adapter-contract-review.md"
if plan.read_bytes() != (freeze / "plan.md").read_bytes():
    raise SystemExit("initial public plan differs from frozen plan")
checked = []
for relative in ("docs/swift-semantic-adapter-contract-review.md",
                 "verification/swift-semantic-adapter-contract-review/prepare_preaccess.py",
                 "verification/swift-semantic-adapter-contract-review/verify_preaccess.py"):
    argv = ["git", "diff", "--no-index", "--check", "/dev/null", relative]
    completed = subprocess.run(argv, cwd=root, capture_output=True, check=False)
    if completed.returncode not in (0, 1) or completed.stdout or completed.stderr:
        raise SystemExit(f"whitespace check failed: {relative}")
    checked.append({"argv": argv, "exit_code": completed.returncode,
                    "stdout": completed.stdout.decode(), "stderr": completed.stderr.decode()})
result = {"schema": 1, "scope": "preparation seal and whitespace bookkeeping only",
          "command": "python3 verification/swift-semantic-adapter-contract-review/verify_preaccess.py",
          "seal_sha256": seal_hash, "verified_members": seal["member_count"],
          "verified_bytes": seal["total_bytes"], "whitespace": checked,
          "candidate_access": "none", "tests_executed": 0,
          "product_workloads_executed": 0, "native_capture_processes_started_or_queried": False}
(owned / "preaccess-verification.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps(result, sort_keys=True))
