#!/usr/bin/env python3
"""Read-only candidate 2 byte/plan/schema integrity; no host runtime child."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import sys


HERE = Path(__file__).resolve().parent
PREPARED = HERE if HERE.name == "prepared-2" else HERE / "prepared-2"


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
    assert sha((PREPARED / "execution-plan.json").read_bytes()) == freeze["execution_plan_sha256"]
    assert freeze["runtime_release_granted"] is False and plan["runtime_release_granted"] is False
    assert [phase["id"] for phase in plan["phases"]] == ["prod", "test"]
    assert plan["limits"]["wall_seconds"] == 55 and plan["limits"]["work_seconds"] == 40
    assert plan["limits"]["cleanup_seconds"] == 46 and plan["limits"]["post_seconds"] == 52
    assert len(plan["source_roster"]) == 18
    assert plan["source_tree_sha256"] == freeze["source_tree_sha256"]
    assert "hosted/test/mixer_hosted/identity/key_owner_test.exs" not in [row["path"] for row in plan["canonical_inputs"]]
    runner = (PREPARED / "runner.py").read_text()
    assert "args.format_only" not in runner and "prepared.name != 'prepared-2'" in runner
    assert "'executions' / 'candidate-2'" in runner
    schemas = json.loads((PREPARED / "required-artifact-schemas.json").read_bytes())
    assert set(schemas["schemas"]) == {phase["id"] + "/" + name for phase in plan["phases"] for name in phase["required_artifacts"]}
    assert schemas["required_artifacts"] == len(schemas["schemas"]) == 17
    assert schemas["schemas"]["test/exunit-result.json"]["fields"]["total"]["value"] == 9
    assert len([p for p in schemas["schemas"] if p.endswith("-cleanup.json")]) == 7
    application = json.loads((PREPARED / "formatting-application.json").read_bytes())
    for change in application["changes"]:
        assert sha((PREPARED / "inputs" / change["path"]).read_bytes()) == change["after_sha256"]
        assert change["exact_formatter_output_applied"] is True and change["non_whitespace_bytes_unchanged"] is True
    assert application["formatting_receipt_sha256"] == sha((PREPARED / "inputs/formatting-1/receipt.json").read_bytes())
    assert application["release_sha256"] == sha((PREPARED / "inputs/root-review/inflight-lifecycle-formatting-1-release.json").read_bytes())
    spec = importlib.util.spec_from_file_location("offline_inflight_validator_v2", PREPARED / "artifact-validation.py")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    rule = schemas["schemas"]["test/exunit-result.json"]["fields"]["total"]
    validator.validate(9, rule)
    rejected = 0
    for invalid in [True, 9.0, 8, "9", None]:
        try:
            validator.validate(invalid, rule)
        except ValueError:
            rejected += 1
    object_rule = {"type": "object", "fields": {"total": rule}}
    for invalid in [{}, {"total": 9, "extra": False}]:
        try:
            validator.validate(invalid, object_rule)
        except ValueError:
            rejected += 1
    assert rejected == 7
    print(json.dumps({"status": "PASS-offline-candidate-2-integrity-only", "sealed_files": len(rows),
        "artifact_schemas": 17, "negative_schema_controls_rejected": rejected, "future_methods": 9,
        "new_candidate_compile_formatter_test_TLS_OpenSSL_invocations": 0,
        "source_tree_sha256": freeze["source_tree_sha256"], "freeze_sha256": sha((PREPARED / "freeze.json").read_bytes()),
        "execution_plan_sha256": freeze["execution_plan_sha256"], "runtime_release_granted": False}, indent=2))


if __name__ == "__main__":
    main()
