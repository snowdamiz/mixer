#!/usr/bin/env python3
"""Read-only custody source/plan integrity; does not run protocol controls."""
from pathlib import Path
import ast
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
PACKET = HERE if HERE.name == "prepared-7" else HERE / "prepared-7"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()


def main():
    assert sys.dont_write_bytecode
    seal = json.loads((PACKET / "freeze.json").read_bytes())
    assert seal["sole_excluded_relative_path"] == "freeze.json"
    rows = seal["files"]
    expected = {row["path"] for row in rows}
    assert len(expected) == len(rows)
    actual = set()
    for path in PACKET.rglob("*"):
        assert not path.is_symlink()
        if path.is_file() and path.relative_to(PACKET).as_posix() != "freeze.json":
            actual.add(path.relative_to(PACKET).as_posix())
    assert actual == expected
    for row in rows:
        assert not Path(row["path"]).is_absolute() and ".." not in Path(row["path"]).parts
        data = (PACKET / row["path"]).read_bytes()
        assert len(data) == row["bytes"] and sha(data) == row["sha256"], row["path"]
        if row["path"].endswith(".py"):
            ast.parse(data, filename=row["path"])
    assert sha(encoded(rows)) == seal["tree_sha256"]
    runtime = json.loads((PACKET / "execution-plan.json").read_bytes())
    control = json.loads((PACKET / "control-plan.json").read_bytes())
    prior = json.loads((PACKET / "inputs/prior-prepared-6/execution-plan.json").read_bytes())
    assert sha((PACKET / "execution-plan.json").read_bytes()) == seal["execution_plan_sha256"]
    assert sha((PACKET / "control-plan.json").read_bytes()) == seal["control_plan_sha256"]
    assert seal["runtime_or_control_release_granted"] is False
    assert runtime["runtime_release_granted"] is False and control["runtime_release_granted"] is False
    changes = {row["path"] for row, old in zip(runtime["canonical_inputs"], prior["canonical_inputs"], strict=True) if row != old}
    assert changes == {"hosted/mix.lock", "THIRD_PARTY.yml"}
    assert control["canonical_inputs"] == runtime["canonical_inputs"]
    assert runtime["source_tree_sha256"] == seal["source_tree_sha256"]
    assert runtime["source_tree_sha256"] != prior["source_tree_sha256"]
    assert runtime["source_roster"] == prior["source_roster"] and len(runtime["source_roster"]) == 18
    assert "hosted/test/mixer_hosted/identity/key_owner_test.exs" not in [row["path"] for row in runtime["canonical_inputs"]]
    assert runtime["limits"] == prior["limits"] and runtime["warning_policy"] == prior["warning_policy"]
    assert [row["id"] for row in runtime["custody_amendments"]] == ["OCR-A1", "OCR-A2", "OCR-A3"]
    schemas = json.loads((PACKET / "required-artifact-schemas.json").read_bytes())
    assert schemas["required_artifacts"] == len(schemas["schemas"]) == 18
    assert set(schemas["schemas"]) == {phase["id"] + "/" + name for phase in runtime["phases"] for name in phase["required_artifacts"]}
    assert schemas["schemas"]["test/exunit-result.json"]["fields"]["total"]["value"] == 9
    assert len(control["cases"]) == 18 and len(set(control["cases"])) == 18
    assert control["kind"] == "custody-controls-no-product-tests"
    assert control["actual_OpenSSL_TLS_Elixir_or_product_methods"] == 0 and control["maximum_fake_native_grants"] == 10 and control["maximum_fake_native_launches"] == 10 and control["maximum_custody_fake_native_launches"] == 8
    assert runtime["custody_implementation_corrections"] == ["CIR-01", "CIR-02", "CIR-03"]
    assert runtime["direct_VM_cleanup_corrections"] == ["CIR5-01", "CIR5-02"]
    assert control["limits"]["combined_artifact_bytes"] == 1048576
    assert len(control["shared_VM_helper_subchecks"]) == 2
    assert runtime["permission_corrections"] == ["CCT-01", "CCT-02"]
    assert runtime["real_runtime_dependency_closure_compatible"] is False
    assert len(control["synthetic_permission_subchecks"]) == 5 and control["synthetic_permission_additional_processes"] == 0
    assert runtime["dependencies"] == prior["dependencies"]
    assert runtime["tools"][:len(prior["tools"])] == prior["tools"]
    assert schemas["schemas"]["test/custody-result.json"]["fields"]["journal_reconciled"] == {"type": "boolean"}
    runner = (PACKET / "runner.py").read_text()
    controls = (PACKET / "custody-controls.py").read_text()
    assert "'executions' / 'candidate-7'" in runner and '"custody-controls-4"' in controls
    for name in ["custody.py", "openssl-custody-wrapper.py", "custody-controls.py", "fake-custody-child.py", "vm_cleanup.py", "process_authority.py", "permission_controls.py"]:
        assert name in {row["path"] for row in runtime["prepared_files"]}
    print(json.dumps({"status": "PASS-offline-custody-source-and-separate-plan-integrity-only", "files": len(rows),
        "real_artifact_schemas": 18, "unchanged_product_methods": 9, "prospective_fake_controls": 18, "prospective_shared_VM_helper_subchecks": 2, "prospective_synthetic_permission_subchecks": 5,
        "control_native_compiler_formatter_TLS_or_product_executions": 0,
        "freeze_sha256": sha((PACKET / "freeze.json").read_bytes()), "execution_plan_sha256": seal["execution_plan_sha256"],
        "control_plan_sha256": seal["control_plan_sha256"], "runtime_or_control_release_granted": False}, indent=2))


if __name__ == "__main__":
    main()
