#!/usr/bin/env python3
"""Read-only finite source/plan audit. No compiler/runtime/fixture child."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import sys


HERE = Path(__file__).resolve().parent
PREPARED = HERE if HERE.name == "prepared-1" else HERE / "prepared-1"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()


def main():
    assert sys.dont_write_bytecode
    freeze = json.loads((PREPARED / "freeze.json").read_bytes())
    assert freeze["sole_excluded_relative_path"] == "freeze.json"
    rows = freeze["files"]
    expected = {row["path"] for row in rows}
    assert len(expected) == len(rows)
    actual = set()
    for path in PREPARED.rglob("*"):
        assert not path.is_symlink()
        if path.is_file() and path.relative_to(PREPARED).as_posix() != "freeze.json":
            actual.add(path.relative_to(PREPARED).as_posix())
    assert actual == expected
    for row in rows:
        assert not Path(row["path"]).is_absolute() and ".." not in Path(row["path"]).parts
        data = (PREPARED / row["path"]).read_bytes()
        assert len(data) == row["bytes"] and sha(data) == row["sha256"], row["path"]
        if row["path"].endswith(".py"):
            ast.parse(data, filename=row["path"])
    assert sha(encoded(rows)) == freeze["tree_sha256"]
    plan = json.loads((PREPARED / "execution-plan.json").read_bytes())
    formatting = json.loads((PREPARED / "formatting-plan.json").read_bytes())
    assert sha((PREPARED / "execution-plan.json").read_bytes()) == freeze["execution_plan_sha256"]
    assert sha((PREPARED / "formatting-plan.json").read_bytes()) == freeze["formatting_plan_sha256"]
    assert [phase["id"] for phase in plan["phases"]] == ["prod", "test"]
    assert [phase["id"] for phase in formatting["phases"]] == ["format"]
    assert plan["limits"]["wall_seconds"] == 55 and plan["limits"]["work_seconds"] == 40
    assert plan["limits"]["cleanup_seconds"] == 46 and plan["limits"]["post_seconds"] == 52
    assert len(plan["source_roster"]) == 18
    assert plan["source_tree_sha256"] == freeze["source_tree_sha256"]
    assert "hosted/test/mixer_hosted/identity/key_owner_test.exs" not in [row["path"] for row in plan["canonical_inputs"]]
    schemas = json.loads((PREPARED / "required-artifact-schemas.json").read_bytes())
    assert set(schemas["schemas"]) == {phase["id"] + "/" + name for phase in plan["phases"] for name in phase["required_artifacts"]}
    assert schemas["required_artifacts"] == len(schemas["schemas"])
    assert schemas["schemas"]["test/exunit-result.json"]["fields"]["total"]["value"] == 9
    assert len([p for p in schemas["schemas"] if p.endswith("-cleanup.json")]) == 7
    spec = importlib.util.spec_from_file_location("offline_inflight_validator", PREPARED / "artifact-validation.py")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    total_rule = schemas["schemas"]["test/exunit-result.json"]["fields"]["total"]
    validator.validate(9, total_rule)
    rejected = 0
    for invalid in [True, 9.0, 8, "9", None]:
        try:
            validator.validate(invalid, total_rule)
        except ValueError:
            rejected += 1
    assert rejected == 5
    object_rule = {"type": "object", "fields": {"total": total_rule}}
    for invalid in [{}, {"total": 9, "extra": False}]:
        try:
            validator.validate(invalid, object_rule)
        except ValueError:
            rejected += 1
    assert rejected == 7
    print(json.dumps({"status": "PASS-offline-source-plan-integrity-only", "sealed_files": len(rows),
        "artifact_schemas": len(schemas["schemas"]), "finite_schema_negative_controls_rejected": rejected,
        "future_methods": 9, "new_methods": 2, "runtime_compiler_formatter_fixture_OpenSSL_invocations": 0,
        "source_tree_sha256": freeze["source_tree_sha256"], "freeze_sha256": sha((PREPARED / "freeze.json").read_bytes()),
        "execution_plan_sha256": freeze["execution_plan_sha256"], "formatting_plan_sha256": freeze["formatting_plan_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
