#!/usr/bin/env python3
"""Audit selected immutable execution inputs, logs, delta and producer seals."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PRODUCER = ROOT / "verification/hosted-customer-authorization-postgres"
OUT = HERE / "final-audit.json"
if OUT.exists():
    raise SystemExit("preserve existing final audit")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


seals = []
for relative in ["seal.json", "correction-seal.json", "ci-integration/seal.json"]:
    path = PRODUCER / relative
    value = json.loads(path.read_text())
    bad = []
    for name, expected in value["files"].items():
        source = (ROOT / name).resolve()
        assert source.is_relative_to(ROOT), name
        assert name.startswith("verification/hosted-customer-authorization-postgres/") or name.startswith("docs/hosted-customer-authorization-postgres"), name
        if not source.is_file() or sha(source) != expected:
            bad.append(name)
    digest = hashlib.sha256(json.dumps(value["files"], sort_keys=True,
                                      separators=(",", ":")).encode()).hexdigest()
    assert not bad, bad
    assert digest == value["manifest_sha256"]
    target = HERE / "producer-seals-final" / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, target)
    seals.append({"path": str(path.relative_to(ROOT)), "sha256": sha(path),
                  "file_count": len(value["files"]), "mismatches": bad})

runs = []
for name in ["run-1", "run-2", "run-3", "correction-run-1",
             "ci-integration-final-run-1", "standalone-final-run-1"]:
    directory = HERE / name
    receipt = json.loads((directory / "receipt.json").read_text())
    for relative, expected in receipt["inputs"].items():
        assert sha(directory / "inputs" / relative) == expected, (name, relative)
    for command in receipt["commands"]:
        assert sha(directory / command["output"]) == command["sha256"], (name, command["label"])
    assert receipt["cleanup"] == {"postgres_stopped": True, "owned_scratch_removed": True}
    assert not Path(receipt["commands"][0]["cwd"]).exists(), name
    current = name in ["ci-integration-final-run-1", "standalone-final-run-1"]
    if current:
        assert receipt["status"] == "passed"
        assert all(command["exit_code"] == 0 for command in receipt["commands"])
        assert "Result: 42 passed" in (directory / "tests.log").read_text()
        for relative, expected in receipt["inputs"].items():
            assert sha(ROOT / relative) == expected, (name, "live input changed", relative)
    runs.append({"run": name, "status": receipt["status"],
                 "source_tree_sha256": receipt["source_tree_sha256"],
                 "input_count": len(receipt["inputs"]),
                 "archived_inputs_match": True, "command_logs_match": True,
                 "current_live_inputs_match": current, "cleanup": receipt["cleanup"]})

ci = json.loads((HERE / "ci-integration-final-run-1/receipt.json").read_text())
assert ci["ci_integration"] is True
assert ci["selected_shared_harness_helper"]["shared_main_executed"] is False
compile_command = next(c for c in ci["commands"] if c["label"] == "compile")
assert not any("/migrations/" in arg for arg in compile_command["argv"])
harness = ROOT / "hosted/scripts/test-local.py"
text = harness.read_text()
helpers = [node for node in ast.parse(text).body
           if isinstance(node, ast.FunctionDef)
           and node.name == "provision_customer_authorization_fixture"]
assert len(helpers) == 1
helper_digest = hashlib.sha256(ast.get_source_segment(text, helpers[0]).encode()).hexdigest()
assert helper_digest == ci["selected_shared_harness_helper"]["source_sha256"]
smoke = (HERE / "ci-integration-final-run-1/migration-smoke.log").read_text()
assert "status: :passed" in smoke
assert "reverted: [20261025000003, 20261025000002]" in smoke
assert "reapplied: [20261025000002, 20261025000003]" in smoke

before = json.loads((PRODUCER / "ci-integration/before-manifest.json").read_text())
delta = json.loads((PRODUCER / "ci-integration/delta-manifest.json").read_text())
patch = []
for relative, old_hash in before.items():
    old = PRODUCER / "ci-integration/inputs-before" / relative
    new = ROOT / relative
    assert sha(old) == old_hash == delta[relative]["before_sha256"], relative
    assert sha(new) == delta[relative]["after_sha256"], relative
    patch.extend(difflib.unified_diff(old.read_text().splitlines(True),
                                      new.read_text().splitlines(True),
                                      fromfile=relative + " BEFORE", tofile=relative + " AFTER"))
patch_text = "".join(patch)
assert patch_text == (PRODUCER / "ci-integration/selected-delta.patch").read_text()
(HERE / "independently-reconstructed-integration-delta.patch").write_text(patch_text)

OUT.write_text(json.dumps({
    "status": "passed",
    "command": ["python3", str(Path(__file__).resolve())],
    "script_sha256": sha(Path(__file__).resolve()),
    "source_revision_context": "cb56d4b9d979ffc02554be991466a180e7882cd3 supplied by root",
    "producer_seals": seals, "review_runs": runs,
    "exact_shared_helper_sha256": helper_digest,
    "shared_harness_main_executed": False,
    "test_side_migration_load_executed": True,
    "independent_delta_matches_producer_patch": True,
    "final_methods_per_mode": {"producer": 25, "independent": 17, "total": 42},
    "all_ordinary_migrations": 5,
    "rollback_reapply_latest_two": True,
    "scope": "Finite selected ordinary PostgreSQL17 evidence adapter and bounded fixture/migration integration only",
    "pending": ["PostgreSQL16 and full standard CI", "five ordinary changed suites runtime execution including held-worker assertions",
                "trusted-clock before-effect check", "complete immutable audit revisions and domain/idempotency/Oban atomicity",
                "protected customer routes/console", "audited provisioning/non-recycling/writers", "provider/Neon/TLS/deployment/operations/FieldLog/GA"]
}, indent=2) + "\n")
print(json.dumps({"status": "passed", "producer_seal_file_counts": [s["file_count"] for s in seals],
                  "current_modes": 2, "methods_each": 42, "cleanup_runs": len(runs),
                  "shared_helper_sha256": helper_digest}))
