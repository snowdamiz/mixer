#!/usr/bin/env python3
"""Freeze only allowlisted immutable inputs and validate this behavioral plan.

No corrected source, operation proposal, compiler or analyzer is accessed/run.
The git/rg child commands are read-only identity probes with bounded deadlines.
"""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
DOC = ROOT / "docs/swift-analyzer-envelope-correction-behavior-review.md"
OLD = "verification/swift-ordered-retention-analyzer-envelope-review/"
SELECT = "verification/swift-ordered-retention-analyzer-envelope-root-review/"
INPUTS = [
    SELECT + name for name in (
        "interface-selection.json",
        "implementation-accounting-addendum.json",
        "leaf-accounting-reconciliation-selection.json",
        "revision-selection.json",
        "copy-unit-clarification.json",
    )
] + [
    "docs/swift-ordered-retention-analyzer-envelope-review.md",
    OLD + "seal.json",
    OLD + "vector-plan.json",
    OLD + "selected-interface-map.json",
    OLD + "final-receipt.json",
    OLD + "private_boundary_tests.rs",
    OLD + "proposal-review-2/frozen-proposal.md",
    OLD + "implementation-review-1/finding-R1.json",
    OLD + "implementation-review-1/frozen-final-receipt.json",
    OLD + "implementation-review-1/public/run-2/receipt.json",
    OLD + "implementation-review-1/private/run-2/receipt.json",
    OLD + "implementation-review-1/private/run-1/receipt.json",
    OLD + "implementation-review-1/api-probes/run-1/receipt.json",
    OLD + "preparation/run-3/accepted-inputs/docs/swift-ordered-retention-analyzer-fsm-contract.md",
    OLD + "preparation/run-3/accepted-inputs/docs/swift-ordered-retention-analyzer-library.md",
]
PINNED = {
    SELECT + "interface-selection.json": "3058c7a0c3dfed57842014874db94b8014c6e8beee4386cce6478b6615634e64",
    SELECT + "implementation-accounting-addendum.json": "242b19079476ab4ee8437f4e7df04d8ebb584e899f7dab7bef537c8330f526dc",
    OLD + "seal.json": "03c1986c3a19ae6464ac96cabe7743f6a562118bcb4a05689026df0de2165476",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def identity(label: str, argv: list[str]) -> dict:
    result = subprocess.run(
        argv, cwd=ROOT, capture_output=True, timeout=10, check=True,
        start_new_session=True,
    )
    stdout = OWN / "commands" / (label + ".stdout")
    stderr = OWN / "commands" / (label + ".stderr")
    stdout.parent.mkdir(parents=True, exist_ok=True)
    stdout.write_bytes(result.stdout)
    stderr.write_bytes(result.stderr)
    return {
        "argv": argv,
        "cwd": str(ROOT),
        "timeout_seconds": 10,
        "returncode": result.returncode,
        "stdout": str(stdout.relative_to(ROOT)),
        "stderr": str(stderr.relative_to(ROOT)),
        "stdout_sha256": sha(result.stdout),
        "stderr_sha256": sha(result.stderr),
        "scope": "read-only tool/revision identity; no process discovery",
    }


def main() -> None:
    if (OWN / "seal.json").exists():
        raise SystemExit("Baseline already frozen; preserve it and use a separate amendment")
    commands = [
        identity("revision", ["git", "rev-parse", "HEAD"]),
        identity("git-version", ["git", "--version"]),
        identity("rg-version", ["rg", "--version"]),
    ]
    original_seal_bytes = (ROOT / (OLD + "seal.json")).read_bytes()
    assert sha(original_seal_bytes) == PINNED[OLD + "seal.json"]
    original_seal = json.loads(original_seal_bytes)
    original_members = {entry["path"]: entry for entry in original_seal["files"]}
    rows = []
    for rel in INPUTS:
        assert not rel.startswith("verification/swift-ordered-retention-analyzer-envelope-correction/")
        data = (ROOT / rel).read_bytes()
        digest = sha(data)
        if rel in PINNED:
            assert digest == PINNED[rel], rel
        old_entry = original_members.get(rel)
        if old_entry is not None:
            assert digest == old_entry["sha256"] and len(data) == old_entry["bytes"], rel
        destination = OWN / "inputs" / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        assert not destination.exists(), str(destination)
        destination.write_bytes(data)
        assert destination.read_bytes() == data
        rows.append({
            "path": rel,
            "bytes": len(data),
            "sha256": digest,
            "snapshot": str(destination.relative_to(ROOT)),
            "original_review_seal_member_verified": old_entry is not None,
            "root_selected_digest_pin_verified": rel in PINNED,
        })

    plan = json.loads((OWN / "baseline.json").read_bytes())
    cases = plan["cases"]
    assert len(cases) == len({case["id"] for case in cases}) == 32
    assert all(case["expected"] and case["input"] and case["seam"] for case in cases)
    assert plan["corrected_source_accessed"] is False
    assert plan["correction_operation_proposal_accessed"] is False
    assert plan["numeric_costs_selected"] is False
    assert plan["later_execution"]["historical_64_timeout_rerun"] is False
    assert plan["promotions"]["implementation_acceptance"] is False
    assert plan["promotions"]["ga_gates"] == 0
    assert len(plan["invariants"]["zero_fields"]) == 11
    assert "E_LEAF*N" in plan["cost_symbols"]["public_debit"]
    document = DOC.read_text()
    assert "mutation,+" not in document
    assert "425" not in document and "47" not in document

    # Re-read exactly the allowlist only. Do not hash/import broad historical
    # harnesses, correction source/ledgers/tests, or a mutable checkout closure.
    assert all(sha((ROOT / row["path"]).read_bytes()) == row["sha256"] for row in rows)
    closure = "".join(
        f"{row['path']}\0{row['sha256']}\0{row['bytes']}\n"
        for row in sorted(rows, key=lambda row: row["path"])
    ).encode()
    receipt = {
        "schema": 1,
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "preaccess-behavior-baseline-frozen-no-analyzer-execution",
        "scope": "allowlisted immutable input acquisition plus JSON/document integrity only",
        "command": [sys.executable, "-B", str(Path(__file__).relative_to(ROOT))],
        "cwd": str(ROOT),
        "python": sys.version,
        "python_executable": sys.executable,
        "script_sha256": sha(Path(__file__).read_bytes()),
        "commands": commands,
        "source_revision_context": (OWN / "commands/revision.stdout").read_text().strip(),
        "input_closure_sha256": sha(closure),
        "input_closure_digest_rule": "UTF8 sorted path NUL sha256 NUL decimal_bytes LF; immutable allowlist only",
        "analyzer_correction_source_digest": None,
        "whole_working_tree_or_original_packet_verified": False,
        "inputs": rows,
        "selected_input_members_unchanged": len(rows),
        "independent_pending_case_count": len(cases),
        "artifact_checks_passed": [
            "pinned original review seal and selected interface/addendum hashes",
            "listed original review members match their frozen seal where present",
            "exact input snapshots equal their sources before and after acquisition",
            "32 unique expected-outcome cases and11 zero fields",
            "costs remain symbolic; no corrected source or numeric execution selected",
            "historical replay not rerun and acceptance promotions remain false",
        ],
        "not_executed": [
            "compiler identity or compilation",
            "analyzer or behavior tests",
            "historical64 replay",
            "native/UI/capture/simulator/emulator/device",
            "process discovery",
            "hosted or catalog/WorkerV2 harness",
        ],
        "mutations": "only lane-owned document and verification packet; no source/root metadata/commit/push",
        "cleanup": "no test runtime, owned scratch, native/capture instance or long-lived child created; identity children returned synchronously",
        "remaining": "root supplies exact correctedsource and selected costcontract including early-finalize funding; all32 controls pending",
        "product_acceptance": False,
        "ga_gate_promotions": 0,
    }
    write_json(OWN / "acquisition.json", receipt)
    summary = {
        "status": receipt["status"],
        "inputs": len(rows),
        "pending_cases": len(cases),
        "input_closure_sha256": receipt["input_closure_sha256"],
        "analyzer_executions": 0,
        "compiler_calls": 0,
        "source_revision_context": receipt["source_revision_context"],
    }
    write_json(OWN / "commands/freeze.stdout.json", summary)
    members = [DOC] + sorted(
        path for path in OWN.rglob("*")
        if path.is_file() and path.name not in ("seal.json", "seal.sha256")
    )
    seal = {
        "schema": 1,
        "scope": "preaccess behavioral baseline and exact allowlisted immutable inputs only",
        "status": "frozen-no-implementation-or-cost-acceptance",
        "files": [
            {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha(path.read_bytes())}
            for path in sorted(members)
        ],
        "excluded": [str((OWN / "seal.json").relative_to(ROOT)), str((OWN / "seal.sha256").relative_to(ROOT))],
    }
    write_json(OWN / "seal.json", seal)
    digest = sha((OWN / "seal.json").read_bytes())
    (OWN / "seal.sha256").write_text(digest + "  " + str((OWN / "seal.json").relative_to(ROOT)) + "\n")
    print(json.dumps({**summary, "seal_sha256": digest}, sort_keys=True))


if __name__ == "__main__":
    main()
