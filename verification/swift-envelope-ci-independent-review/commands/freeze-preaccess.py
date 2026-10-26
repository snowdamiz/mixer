#!/usr/bin/env python3
"""Seal only this lane's preaccess plan; never inspect or execute the candidate."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

REPO = Path(__file__).resolve().parents[3]
OWNED = REPO / "verification/swift-envelope-ci-independent-review"
SELECTION = "verification/swift-envelope-ci-root-review/implementation-selection.json"
PROPOSAL = "verification/swift-envelope-ci-contract/seal.json"
ACCEPTANCE = "verification/swift-ordered-retention-analyzer-envelope-root-review/absence-implementation-acceptance.json"
EXPECTED = {
    SELECTION: "33124b5e9b5c8534ea0e18fffe145cea770f704b2aa3618457ab50573d0f5474",
    PROPOSAL: "690894df6376ddf33067f9dda10493bc3aaf22151b8ac7935cba4389ba88b466",
    ACCEPTANCE: "38918f5916cd976965cd93c233606687bc78918c105aa9bcc91c02c2acda4ebf",
}


def info(relative):
    data = (REPO / relative).read_bytes()
    return {"path": relative, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def write(relative, value):
    path = REPO / relative
    if path.exists():
        raise RuntimeError("refusing to replace preaccess output: " + relative)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


at = datetime.now(timezone.utc).isoformat()
inputs = []
for relative, expected in EXPECTED.items():
    record = info(relative)
    if record["sha256"] != expected:
        raise RuntimeError("frozen binding mismatch: " + relative)
    inputs.append(record)
proposal = json.loads((REPO / PROPOSAL).read_text())
proposal_members = []
for selected in proposal["members"]:
    actual = info(selected["path"])
    if actual != selected:
        raise RuntimeError("proposal member mismatch: " + selected["path"])
    proposal_members.append(actual)
for relative in ("AGENTS.md", "mixer-product-plan.md", "PLAN.md"):
    inputs.append(info(relative))
plan_relative = "verification/swift-envelope-ci-independent-review/preaccess-control-plan.json"
plan = json.loads((REPO / plan_relative).read_text())
ids = [item["id"] for item in plan["controls"]]
if len(ids) != 40 or len(set(ids)) != 40 or plan["planned_control_count"] != 40:
    raise RuntimeError("incorrect independent plan inventory")
audit = {
    "schema": 1,
    "status": "preaccess-preparation-only-no-candidate-acceptance",
    "at": at,
    "command": "python3 -B verification/swift-envelope-ci-independent-review/commands/freeze-preaccess.py",
    "cwd": str(REPO),
    "python_executable": sys.executable,
    "python_version": sys.version,
    "git_version": git("--version"),
    "source_revision": git("rev-parse", "HEAD"),
    "committed_tree": git("rev-parse", "HEAD^{tree}"),
    "os": platform.system(),
    "os_release": platform.release(),
    "machine": platform.machine(),
    "binding_inputs": inputs,
    "proposal_members_verified": proposal_members,
    "proposal_member_count": len(proposal_members),
    "proposal_member_bytes": sum(item["bytes"] for item in proposal_members),
    "selected_originals_verified_in_this_preparation": False,
    "selected_originals_scope": "Root selection and frozen manifest are bound; no selected product source or fixture bytes were re-audited here.",
    "planned_control_count": 40,
    "candidate_access": {"runner": False, "tests": False, "pack": False, "implementation_receipts": False},
    "executed": {"candidate_compiler_or_binary": False, "candidate_tests": False, "model": False, "historical_collector": False, "native_runtime": False, "capture_or_UI": False, "unrelated_process_discovery": False},
    "scope": "Independent review preparation only; root admission and fresh correct-source host run remain required.",
    "storedPrefixValidated": False,
    "fullReplayAccepted": False,
    "semanticMetricsValid": False,
    "GA_qualified": False,
    "errors": [],
}
audit_relative = "verification/swift-envelope-ci-independent-review/preaccess-input-audit.json"
write(audit_relative, audit)
log_relative = "verification/swift-envelope-ci-independent-review/preaccess-freeze.stdout"
log = "Verified 3 frozen root/proposal/acceptance bindings, 11 proposal members, and 40 planned controls. No candidate access or execution.\n"
log_path = REPO / log_relative
if log_path.exists():
    raise RuntimeError("refusing to replace preparation log")
log_path.write_text(log, encoding="utf-8")
members = [info(relative) for relative in (
    "docs/swift-envelope-ci-independent-review.md",
    plan_relative,
    "verification/swift-envelope-ci-independent-review/commands/freeze-preaccess.py",
    audit_relative,
    log_relative,
)]
seal = {
    "schema": 1,
    "status": "frozen-preaccess-independent-plan-awaiting-root-candidate-admission",
    "at": at,
    "member_count": len(members),
    "total_bytes": sum(item["bytes"] for item in members),
    "members": members,
    "planned_control_count": 40,
    "candidate_reviewed": False,
    "candidate_executed": False,
    "candidate_accepted": False,
    "root_selection_sha256": EXPECTED[SELECTION],
    "proposal_seal_sha256": EXPECTED[PROPOSAL],
    "excluded": ["verification/swift-envelope-ci-independent-review/preaccess-seal.json", "verification/swift-envelope-ci-independent-review/preaccess-seal.sha256"],
    "storedPrefixValidated": False,
    "fullReplayAccepted": False,
    "semanticMetricsValid": False,
    "GA_qualified": False,
}
seal_relative = "verification/swift-envelope-ci-independent-review/preaccess-seal.json"
write(seal_relative, seal)
digest = info(seal_relative)["sha256"]
checksum_path = OWNED / "preaccess-seal.sha256"
if checksum_path.exists():
    raise RuntimeError("refusing to replace preparation checksum")
checksum_path.write_text(digest + "  " + seal_relative + "\n", encoding="utf-8")
print(log, end="")
print(json.dumps({"seal": seal_relative, "sha256": digest, "member_count": len(members), "total_bytes": seal["total_bytes"], "planned_controls": 40}, sort_keys=True))
