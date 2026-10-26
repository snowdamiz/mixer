#!/usr/bin/env python3
"""Independent byte/provenance/declaration arithmetic audit only.

No candidate module is imported, compiled or executed, and no semantic replay
or runtime test is implemented here.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OWNED = ROOT / "verification/swift-semantic-adapter-contract-review"
CANDIDATE = OWNED / "candidate-1"
PACKET = CANDIDATE / "members/verification/swift-semantic-adapter-prerequisite"
RESULTS = OWNED / "review-1"
EXPECTED = "d145cda8cdde0915493f5c75102ae0dc11adb577891b1b773322b5c4d0f32cba"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pairs(values):
    result = {}
    for key, value in values:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_bytes(), object_pairs_hook=pairs)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    RESULTS.mkdir(exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    seal_data = (CANDIDATE / "seal.json").read_bytes()
    require(sha(seal_data) == EXPECTED, "owned candidate seal changed")
    seal = read_json(CANDIDATE / "seal.json")
    for row in seal["members"]:
        original = (ROOT / row["path"]).read_bytes()
        snapshot = (CANDIDATE / "members" / row["path"]).read_bytes()
        require(original == snapshot, f"candidate changed: {row['path']}")
        require(len(snapshot) == row["bytes"] and sha(snapshot) == row["sha256"], "snapshot member mismatch")
    require(sha((ROOT / "verification/swift-semantic-adapter-prerequisite/seal.json").read_bytes()) == EXPECTED,
            "original candidate seal changed")
    preaccess = read_json(OWNED / "preaccess/seal.json")
    for row in preaccess["members"]:
        data = (OWNED / "preaccess" / row["path"]).read_bytes()
        require(len(data) == row["bytes"] and sha(data) == row["sha256"], "preaccess freeze changed")

    seams = read_json(PACKET / "source-seams.json")
    # The sole non-context collection is the explicit source-seam list.
    seam_rows = seams["seams"]
    excerpts = []
    for seam in seam_rows:
        data = (PACKET / seam["snapshot"]).read_bytes()
        excerpt = b"".join(data.splitlines(keepends=True)[seam["first_line"] - 1:seam["last_line"]])
        require(sha(data) == seam["source_sha256"], f"source mismatch: {seam['name']}")
        require(excerpt.decode() == seam["excerpt_utf8"], f"source span mismatch: {seam['name']}")
        require(sha(excerpt) == seam["excerpt_sha256"], f"excerpt digest mismatch: {seam['name']}")
        excerpts.append({"name": seam["name"], "first_line": seam["first_line"],
                         "last_line": seam["last_line"], "excerpt_sha256": sha(excerpt),
                         "source_sha256": sha(data)})

    accepted_matches = []
    for source, accepted in (
        ("13-analyzer.rs", "verification/swift-envelope-ci-pack/source/library/analyzer.rs"),
        ("14-envelope.rs", "verification/swift-envelope-ci-pack/source/library/envelope.rs"),
    ):
        candidate_bytes = (PACKET / "inputs" / source).read_bytes()
        accepted_bytes = (OWNED / "preaccess/accepted-inputs" / accepted).read_bytes()
        require(candidate_bytes == accepted_bytes, f"accepted source differs: {source}")
        accepted_matches.append({"candidate_input": source, "accepted_source": accepted,
                                 "sha256": sha(candidate_bytes)})
    design_seal = read_json(PACKET / "inputs/19-seal.json")
    design_by_path = {row["path"]: row for row in design_seal["members"]}
    provenance_matches = []
    for seam in seam_rows:
        if seam["path"] in design_by_path:
            old = design_by_path[seam["path"]]
            data = (PACKET / seam["snapshot"]).read_bytes()
            require(old["sha256"] == sha(data) and old["bytes"] == len(data), "design seal source mismatch")
            if not any(row["path"] == seam["path"] for row in provenance_matches):
                provenance_matches.append({"path": seam["path"], "sha256": sha(data), "bytes": len(data)})

    contract = read_json(PACKET / "contract.json")
    work = contract["work"]
    memory = contract["memory"]
    recomputed = {
        "semantic_record": sum(row[1] for row in work["semantic_groups"]),
        "new_combined_record": 471 + sum(row[1] for row in work["semantic_groups"]),
        "record_preflight_margin": 8192 - 471 - sum(row[1] for row in work["semantic_groups"]),
        "predicted_aggregate_bytes": 104 + 128 + 256,
        "report_work": 6446 + 256 + 128,
        "complete_role_union": 24656 + sum(memory["extra_groups"].values()),
        "extra_report_roles": sum(memory["complete_new_report_roles"].values()),
        "arithmetic_record_upper": (268435456 - 5017696) // 8151,
        "historical_record_charge": 2889656 * 8151,
        "sort_worst_comparisons_for_64": 64 * 6 - 64 + 1,
        "sort_output_transfers_for_64": 64 * 6,
    }
    require(recomputed["semantic_record"] == 7680, "semantic sum mismatch")
    require(recomputed["new_combined_record"] == work["new_combined_record"], "combined sum mismatch")
    require(recomputed["record_preflight_margin"] == work["preflight_remaining"], "margin mismatch")
    require(recomputed["complete_role_union"] == memory["proposed_union"], "role union mismatch")
    margins = {name: reserved - prior - memory["extra_groups"][name]
               for name, (prior, reserved) in memory["existing_groups"].items()}
    require(all(value >= 0 for value in margins.values()), "named group over reservation")
    old = set(contract["private_contract"]["envelope_owned_scalar_indices"])
    new = {int(key) for key in contract["private_contract"]["semantic_owned_scalar_indices"]}
    require(not old & new, "scalar ownership overlap")
    require(len(contract["observation"]["words"]) == 32, "observation width differs")
    candidate_regions = contract["candidate_regions"]
    cursor = 0
    for region in candidate_regions:
        require(region["offset"] == cursor, "Candidate region gap or overlap")
        cursor += region["bytes"]
    require(cursor == 2048, "Candidate extent differs")
    designs = read_json(PACKET / "test-design.json")
    commands = []
    for name, argv in (("python-version", [sys.executable, "--version"]),
                       ("git-version", ["git", "--version"]),
                       ("revision", ["git", "rev-parse", "HEAD"])):
        completed = subprocess.run(argv, cwd=ROOT, capture_output=True, check=False)
        (RESULTS / f"{name}.stdout").write_bytes(completed.stdout)
        (RESULTS / f"{name}.stderr").write_bytes(completed.stderr)
        require(completed.returncode == 0, f"command failed: {name}")
        commands.append({"argv": argv, "exit_code": completed.returncode,
                         "stdout": f"{name}.stdout", "stderr": f"{name}.stderr"})
    result = {
        "schema": 1, "at_utc": started,
        "command": "python3 verification/swift-semantic-adapter-contract-review/audit_source_contract.py",
        "scope": "independent source-byte/provenance/declaration arithmetic only; no semantic behavior tests",
        "candidate_seal_sha256": EXPECTED, "candidate_members_reverified": len(seal["members"]),
        "candidate_bytes_reverified": seal["member_bytes"],
        "preaccess_members_reverified": len(preaccess["members"]),
        "source_excerpt_checks": excerpts, "accepted_source_byte_matches": accepted_matches,
        "copied_design_seal_source_matches": provenance_matches,
        "current_live_vm_relation": "unavailable; not read or claimed",
        "independent_arithmetic": recomputed, "named_group_remaining_bytes": margins,
        "envelope_scalar_cells": sorted(old), "semantic_scalar_cells": sorted(new),
        "candidate_extent": cursor,
        "future_test_designs_declared": len(designs["cases"]),
        "not_a_test_pass_count": True, "semantic_tests_executed": 0,
        "candidate_helpers_imported_or_executed": False, "compiler_executed": False,
        "commands": commands, "native_capture_processes_started_or_queried": False,
        "source_review_findings": "findings.json",
        "cleanup": "No build scratch or disposable instance created; all synchronous read-only children reaped.",
    }
    (RESULTS / "audit.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: result[key] for key in ("scope", "candidate_members_reverified", "candidate_bytes_reverified",
                                                 "independent_arithmetic", "named_group_remaining_bytes",
                                                 "semantic_tests_executed")}, sort_keys=True))


if __name__ == "__main__":
    main()
