#!/usr/bin/env python3
"""Freeze the review plan from an explicit accepted-input allowlist only.

This is evidence packaging, not a product/model/test runner. Candidate paths
are deliberately absent from every filesystem operation.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OWNED = ROOT / "verification/swift-semantic-adapter-contract-review"
FREEZE = OWNED / "preaccess"
INPUTS = (
    "AGENTS.md",
    "mixer-product-plan.md",
    "docs/swift-envelope-ci-acceptance.md",
    "docs/swift-ordered-retention-analyzer-review.md",
    "docs/swift-ordered-retention-analyzer-fsm-contract-review.md",
    "verification/swift-envelope-ci-pack/source/library/analyzer.rs",
    "verification/swift-envelope-ci-pack/source/library/envelope.rs",
    "verification/swift-envelope-ci-pack/api/positive.rs",
    "verification/swift-envelope-ci-pack/inventories/proposed-layout.json",
    "verification/swift-envelope-ci-pack/provenance/contract-seal.json",
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    # Refuse overwriting an earlier freeze; later phases must use new packets.
    FREEZE.mkdir(parents=True, exist_ok=False)
    commands = []
    for name, command in (
        ("revision", ["git", "rev-parse", "HEAD"]),
        ("git-version", ["git", "--version"]),
        ("python-version", [sys.executable, "--version"]),
    ):
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, check=False)
        (FREEZE / f"{name}.stdout").write_bytes(completed.stdout)
        (FREEZE / f"{name}.stderr").write_bytes(completed.stderr)
        commands.append({"argv": command, "cwd": str(ROOT), "exit_code": completed.returncode,
                         "stdout": f"{name}.stdout", "stderr": f"{name}.stderr"})
        if completed.returncode:
            raise SystemExit(f"preparation command failed: {name}")
    inputs = []
    for relative in INPUTS:
        source = ROOT / relative
        data = source.read_bytes()
        destination = FREEZE / "accepted-inputs" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        inputs.append({"path": relative, "bytes": len(data), "sha256": digest(data),
                       "snapshot": str(destination.relative_to(FREEZE))})
    plan_source = ROOT / "docs/swift-semantic-adapter-contract-review.md"
    plan = plan_source.read_bytes()
    (FREEZE / "plan.md").write_bytes(plan)
    shutil.copyfile(__file__, FREEZE / "prepare_preaccess.py.txt")
    write_json(FREEZE / "commands.json", commands)
    write_json(FREEZE / "accepted-input-manifest.json", inputs)
    canonical = "".join(f"{item['sha256']} {item['bytes']} {item['path']}\n" for item in inputs).encode()
    write_json(FREEZE / "receipt.json", {
        "schema": 1,
        "phase": "pre-access independent source-contract plan only",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": (FREEZE / "revision.stdout").read_text().strip(),
        "accepted_input_tree_sha256": digest(canonical),
        "accepted_input_tree_algorithm": "sha256 of allowlist-order lines: sha256 SPACE bytes SPACE path LF",
        "accepted_input_count": len(inputs),
        "plan_sha256": digest(plan),
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "command": "python3 verification/swift-semantic-adapter-contract-review/prepare_preaccess.py",
        "candidate_access": {"enumerated": False, "hashed": False, "read": False},
        "executed_tests": 0,
        "product_or_native_workloads_executed": 0,
        "source_only_contract_review_executed": False,
        "root_authorization_for_candidate_access": "awaiting frozen seal and explicit access authorization",
        "scope": "C01-C10 frozen independently from accepted source documents and ordinary source pack; no implementation acceptance",
        "native_capture_processes_started_or_queried": False,
        "cleanup": "No disposable instance, native process or build scratch created; synchronous read-only children reaped.",
        "pending": ["candidate source-contract review", "root implementation selection", "future independent executable controls", "actual Rust 1.98.1 CI artifact qualification", "all real authority and semantic validity", "native/device and release/GA gates"],
    })
    members = []
    for path in sorted(FREEZE.rglob("*")):
        if path.is_file():
            data = path.read_bytes()
            members.append({"path": str(path.relative_to(FREEZE)), "bytes": len(data), "sha256": digest(data)})
    seal = {"schema": 1, "scope": "immutable pre-access independent review plan",
            "excluded": ["seal.json", "seal.sha256"],
            "member_count": len(members), "total_bytes": sum(item["bytes"] for item in members),
            "members": members}
    write_json(FREEZE / "seal.json", seal)
    seal_hash = digest((FREEZE / "seal.json").read_bytes())
    (FREEZE / "seal.sha256").write_text(f"{seal_hash}  seal.json\n")
    print(json.dumps({"seal_sha256": seal_hash, "member_count": seal["member_count"],
                      "total_bytes": seal["total_bytes"], "plan_sha256": digest(plan),
                      "accepted_input_tree_sha256": digest(canonical),
                      "candidate_access": "none", "tests_executed": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
