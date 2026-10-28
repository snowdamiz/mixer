#!/usr/bin/env python3
"""Read-only candidate-3 integrity, narrow delta and retained failure facts."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import sys


HERE = Path(__file__).resolve().parent
PREPARED = HERE if HERE.name == "prepared-3" else HERE / "prepared-3"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()


def main():
    assert sys.dont_write_bytecode
    seal = json.loads((PREPARED / "freeze.json").read_bytes())
    assert seal["sole_excluded_relative_path"] == "freeze.json"
    rows = seal["files"]
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
    assert sha(encoded(rows)) == seal["tree_sha256"]
    plan = json.loads((PREPARED / "execution-plan.json").read_bytes())
    prior_plan = json.loads((PREPARED / "inputs/prior-prepared-2/execution-plan.json").read_bytes())
    prior_seal = json.loads((PREPARED / "inputs/prior-prepared-2/freeze.json").read_bytes())
    assert sha((PREPARED / "execution-plan.json").read_bytes()) == seal["execution_plan_sha256"]
    assert plan["runtime_release_granted"] is False and seal["runtime_release_granted"] is False
    assert plan["warning_policy"] == prior_plan["warning_policy"]
    assert [phase["id"] for phase in plan["phases"]] == ["prod", "test"]
    assert plan["phases"] == prior_plan["phases"] and plan["limits"] == prior_plan["limits"]
    assert len(plan["source_roster"]) == 18
    assert plan["source_tree_sha256"] == seal["source_tree_sha256"]
    assert "hosted/test/mixer_hosted/identity/key_owner_test.exs" not in [row["path"] for row in plan["canonical_inputs"]]
    runner = (PREPARED / "runner.py").read_text()
    prior_runner = (PREPARED / "inputs/prior-prepared-2/runner.py").read_text()
    assert runner.replace("prepared.name != 'prepared-3'", "prepared.name != 'prepared-2'").replace("'executions' / 'candidate-3'", "'executions' / 'candidate-2'") == prior_runner
    correction = json.loads((PREPARED / "charlist-correction.json").read_bytes())
    before = (PREPARED / "charlist-correction-beforeimage.exs").read_bytes()
    after = (PREPARED / "inputs" / correction["path"]).read_bytes()
    assert sha(before) == correction["before_sha256"] and sha(after) == correction["after_sha256"]
    assert before.count(b"'jwks.fixture.invalid'") == 1
    assert before.replace(b"'jwks.fixture.invalid'", b'~c"jwks.fixture.invalid"', 1) == after
    prior_source_pin = next(row for row in prior_seal["files"] if row["path"] == "inputs/" + correction["path"])
    assert prior_source_pin["sha256"] == sha(before)
    schemas_bytes = (PREPARED / "required-artifact-schemas.json").read_bytes()
    schema_pin = next(row for row in prior_seal["files"] if row["path"] == "required-artifact-schemas.json")
    assert sha(schemas_bytes) == schema_pin["sha256"]
    schemas = json.loads(schemas_bytes)
    assert schemas["required_artifacts"] == len(schemas["schemas"]) == 17
    assert set(schemas["schemas"]) == {phase["id"] + "/" + name for phase in plan["phases"] for name in phase["required_artifacts"]}
    assert schemas["schemas"]["test/exunit-result.json"]["fields"]["total"]["value"] == 9
    observed = json.loads((PREPARED / "candidate-2-observed-failure.json").read_bytes())
    assert observed["OpenSSL_invocations"] == 1 and observed["OpenSSL_args"] == [["version"]]
    assert observed["ExUnit_methods_executed"] == 0 and observed["TLS_fixtures_started"] == 0
    assert observed["group_observation"]["groups_equal"] is False and plan["known_execution_blockers"]
    spec = importlib.util.spec_from_file_location("offline_inflight_validator_v3", PREPARED / "artifact-validation.py")
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
    for invalid in [{}, {"total": 9, "extra": False}]:
        try:
            validator.validate(invalid, {"type": "object", "fields": {"total": rule}})
        except ValueError:
            rejected += 1
    assert rejected == 7
    print(json.dumps({"status": "PASS-offline-candidate-3-integrity-only-known-group-finding-pending-review",
        "sealed_files": len(rows), "unchanged_artifact_schemas": 17, "future_methods": 9,
        "negative_schema_controls_rejected": rejected, "known_prior_OpenSSL_group_finding": True,
        "new_compiler_formatter_runtime_test_TLS_OpenSSL_invocations": 0,
        "source_tree_sha256": seal["source_tree_sha256"], "freeze_sha256": sha((PREPARED / "freeze.json").read_bytes()),
        "execution_plan_sha256": seal["execution_plan_sha256"], "runtime_release_granted": False}, indent=2))


if __name__ == "__main__":
    main()
