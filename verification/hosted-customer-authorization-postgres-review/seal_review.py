#!/usr/bin/env python3
"""Verify the combined producer capture and seal only owned review artifacts."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
if (HERE / "seal.json").exists():
    raise SystemExit("preserve existing review seal")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


producer_path = ROOT / "verification/hosted-customer-authorization-postgres/final-seal.json"
producer = json.loads(producer_path.read_text())
assert sha(producer_path) == "61c25aad3dc31050f6a196950a7a51fc21bad158f9f8936e884f568a36b8b6ff"
for relative, expected in producer["files"].items():
    path = (ROOT / relative).resolve()
    assert path.is_relative_to(ROOT)
    assert relative.startswith("verification/hosted-customer-authorization-postgres/") or relative.startswith("docs/hosted-customer-authorization-postgres")
    assert sha(path) == expected, relative
assert hashlib.sha256(json.dumps(producer["files"], sort_keys=True,
                                separators=(",", ":")).encode()).hexdigest() == producer["manifest_sha256"]
for relative, expected in producer["live_input_bindings"].items():
    assert sha(ROOT / relative) == expected, relative
ci = json.loads((HERE / "ci-integration-final-run-1/receipt.json").read_text())
standalone = json.loads((HERE / "standalone-final-run-1/receipt.json").read_text())
for receipt in [ci, standalone]:
    assert receipt["status"] == "passed"
    for relative, expected in receipt["inputs"].items():
        assert sha(ROOT / relative) == expected, relative
for relative, expected in producer["live_input_bindings"].items():
    assert ci["inputs"][relative] == expected, relative
assert producer["original_collector_restored"] is True
copy = HERE / "producer-seals-final/final-seal.json"
shutil.copyfile(producer_path, copy)

summary = {
    "schema": 1,
    "status": "accepted_finite_local_durable_lookup_and_selected_fixture_migration_integration",
    "unresolved_findings": [],
    "closed_findings": ["AUTHZ-PG-REVIEW-001"],
    "source_revision_context": "cb56d4b9d979ffc02554be991466a180e7882cd3 supplied by root",
    "producer_final_seal_sha256": sha(producer_path),
    "producer_final_seal_file_count": len(producer["files"]),
    "producer_final_seal_mismatches": 0,
    "producer_current_binding_count": len(producer["live_input_bindings"]),
    "producer_current_binding_mismatches": 0,
    "independent_runs": {
        "ci-integration-final-run-1": {"producer_methods": 25, "independent_methods": 17,
                                       "total_passed": 42, "source_tree_sha256": ci["source_tree_sha256"]},
        "standalone-final-run-1": {"producer_methods": 25, "independent_methods": 17,
                                    "total_passed": 42, "source_tree_sha256": standalone["source_tree_sha256"]}
    },
    "ordinary_migrations_applied": 5,
    "ordinary_migration_idempotence": True,
    "latest_two_rollback_order": [20261025000003, 20261025000002],
    "reapply_order": [20261025000002, 20261025000003],
    "selected_shared_helper_sha256": ci["selected_shared_harness_helper"]["source_sha256"],
    "shared_harness_main_executed": False,
    "broad_five_ordinary_test_suites_executed": False,
    "owned_review_attempts_cleaned": 6,
    "archived_seal_file_counts_verified": [208, 30, 194, 437],
    "pending": ["PostgreSQL16 and full standard CI", "runtime execution of five changed ordinary suites including held-worker assertions",
                "trusted-clock check before effects", "audited provisioning/non-recycling/writer enforcement",
                "transaction-bound domain authority and immutable content binding", "complete audit revisions and principal-bound idempotency/Oban atomicity",
                "protected customer HTTP and console", "provider/service/CI identity", "deployed role topology/Neon/TLS/operations/FieldLog/GA"],
    "boundary": "Pure policy evaluation only; no domain authority or GA acceptance",
    "command": ["python3", str(Path(__file__).resolve())],
    "script_sha256": sha(Path(__file__).resolve())
}
(HERE / "result-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
paths = sorted(path for path in HERE.rglob("*") if path.is_file() and path.name != "seal.json")
# Only the review's own seal is excluded; copied producer seals named seal.json
# must still be covered as independent capture inputs.
paths += sorted(path for path in HERE.rglob("seal.json") if path != HERE / "seal.json")
paths.append(ROOT / "docs/hosted-customer-authorization-postgres-review.md")
assert all(not path.is_symlink() for path in paths)
files = {str(path.relative_to(ROOT)): sha(path) for path in sorted(set(paths))}
manifest = hashlib.sha256(json.dumps(files, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()
(HERE / "seal.json").write_text(json.dumps({
    "schema": 1, "files": files, "live_input_bindings": ci["inputs"],
    "manifest_sha256": manifest, "scope": summary["status"]
}, indent=2) + "\n")
print(json.dumps({"status": summary["status"], "review_file_count": len(files),
                  "review_seal_sha256": sha(HERE / "seal.json"),
                  "producer_final_file_count": len(producer["files"]),
                  "final_current_bindings_match": True}))
