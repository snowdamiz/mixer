#!/usr/bin/env python3
"""Read-only terminal/formatting/new-candidate custody; no producer replay."""
from datetime import datetime, timezone
import ast
import difflib
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import time

START = time.monotonic()
REPO = Path(__file__).resolve().parents[3]
REVIEW = Path(__file__).resolve().parent
LANE = REPO / "verification/console-key-owner-lifecycle-implementation"


def sha(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            assert time.monotonic() - START < 55
            data = stream.read(262144)
            if not data:
                return result.hexdigest()
            result.update(data)


def pairs(values):
    result = {}
    for key, value in values:
        assert key not in result
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))


def verify(items, root):
    seen = set()
    for item in items:
        relative = item["path"]
        assert relative not in seen
        seen.add(relative)
        parsed = PurePosixPath(relative)
        assert not parsed.is_absolute() and ".." not in parsed.parts and str(parsed) == relative
        path = root / relative
        assert path.is_file() and not path.is_symlink() and path.stat().st_size == item["bytes"]
        assert sha(path) == item["sha256"], str(path)
    return seen


def tree(items):
    return hashlib.sha256("".join(v["path"] + "\0" + str(v["bytes"]) + "\0" + v["sha256"] + "\n" for v in items).encode()).hexdigest()


def packet(path, seal_name, expected, count):
    assert sha(path / seal_name) == expected
    seal = read(path / seal_name)
    sealed = verify(seal["files"], path)
    actual = set()
    for file in path.rglob("*"):
        assert not file.is_symlink()
        if file.is_file() and file.relative_to(path).as_posix() != seal_name:
            actual.add(file.relative_to(path).as_posix())
    assert sealed == actual and len(sealed) == count
    assert tree(seal["files"]) == seal["tree_sha256"]
    return seal


def main():
    old = LANE / "prepared-2"
    new = LANE / "prepared-3"
    execution = LANE / "executions/candidate-2"
    formatting = LANE / "formatting-pass-1"
    old_seal = packet(old, "freeze.json", "d59a6d3987a3dd892b24bc2fbefba079926dcbb8ade28ad9c429ddd4a54f19ef", 234)
    new_seal = packet(new, "freeze.json", "fc4f644bccc627470bdb027a65d2e4d80cde51ca32c684b23a85fd6c1e80e307", 253)
    format_seal = packet(formatting, "seal.json", "fef6619cd13eced0d40b5dec0925d44e0b49eb80a41eb5c15ec52b6b38a25003", 12)
    old_plan = read(old / "execution-plan.json")
    plan = read(new / "execution-plan.json")
    assert sha(new / "execution-plan.json") == "80d718131fd6b0ba48d6c7e4b9a6eb7c9d704eee95f4b91555a82dc944acd4fd"
    assert new_seal["execution_plan_sha256"] == sha(new / "execution-plan.json")
    prepared = verify(plan["prepared_files"], new)
    assert len(prepared) == 252 and prepared | {"execution-plan.json"} == {v["path"] for v in new_seal["files"]}
    assert len(verify(plan["canonical_inputs"], REPO)) == 216
    assert tree(plan["canonical_inputs"]) == plan["source_tree_sha256"]
    assert plan["tools"] == old_plan["tools"] and len(plan["tools"]) == 969
    for item in plan["tools"]:
        path = Path(item["path"])
        assert path.stat().st_size == item["bytes"] and sha(path) == item["sha256"]
    for key in ("dependencies", "source_roster", "test_source", "phases", "limits", "environment", "elixir", "boot", "artifact_schemas", "scope", "pending"):
        assert plan[key] == old_plan[key], key
    expected_runner = (old / "runner.py").read_text().replace("prepared.name != 'prepared-2'", "prepared.name != 'prepared-3'", 1).replace("output = lane / 'executions' / 'candidate-2'", "output = lane / 'executions' / 'candidate-3'", 1)
    assert expected_runner == (new / "runner.py").read_text()
    changed = []
    for item in old_seal["files"]:
        relative = item["path"]
        if relative != "execution-plan.json" and (old / relative).read_bytes() != (new / relative).read_bytes():
            changed.append(relative)
    assert sorted(changed) == ["inputs/hosted/lib/mixer_hosted/identity/admission.ex", "inputs/hosted/test/mixer_hosted/identity/key_owner_lifecycle_test.exs", "runner.py"]
    terminal_path = REPO / "verification/console-session-and-checkout-root-review/key-owner-lifecycle-candidate-2-terminal.json"
    terminal = read(terminal_path)["terminal"]
    execution_paths = verify(terminal["execution_members"], REPO)
    assert len(execution_paths) == 19
    assert execution_paths == {p.relative_to(REPO).as_posix() for p in execution.rglob("*") if p.is_file()}
    for field in ("plan", "release", "review", "receipt"):
        verify([terminal[field]], REPO)
    release = read(REPO / terminal["release"]["path"])
    receipt = read(execution / "receipt.json")
    observed = read(execution / "observations.json")
    assert release["status"] == "root-released-exact-plan" and release["single_execution"] is True
    assert release["execution_plan_sha256"] == receipt["execution_plan_sha256"] == observed["execution_plan_sha256"] == sha(old / "execution-plan.json")
    assert receipt["status"] == "failed" and receipt["errors"] == ["RuntimeError: phase failed: corrected"]
    assert not receipt["cleanup_errors"] and not receipt["observed_signals_at_cutoff"]
    assert [(v["id"], v["returncode"]) for v in observed["phases"]] == [("original", 0), ("corrected", 1)]
    assert observed["all_original_pins_rechecked"] is True and not observed["original_changes"]
    assert observed["scratch_removed"] is True and not Path(observed["scratch_path"]).exists()
    assert len(observed["owned_processes"]) == 2 and all(v["direct_child_reaped"] is True and v["group_absent"] is True for v in observed["owned_processes"])
    schema_packet = read(old / "required-artifact-schemas.json")
    schemas = dict(schema_packet["schemas"])
    for name, paths in schema_packet["shared_schema_bindings"].items():
        for path in paths:
            assert path not in schemas
            schemas[path] = schema_packet["shared_schemas"][name]
    assert set(observed["artifacts"]) == set(schemas) and len(schemas) == 13
    types = {"boolean": bool, "integer": int, "string": str}
    for relative, schema in schemas.items():
        value = read(execution / relative)
        assert value == observed["artifacts"][relative] and set(value) == set(schema)
        for key, rule in schema.items():
            assert type(value[key]) is types[rule["type"]]
            assert value[key] in rule["enum"] if "enum" in rule else value[key] == rule["value"]
    original_stdout = (execution / "original/stdout.txt").read_text()
    corrected_stdout = (execution / "corrected/stdout.txt").read_text()
    assert "ORIGINAL DEFECT REPRODUCED" in original_stdout
    assert original_stdout.count("COMPILED 19 ordinary identity modules; warnings=0") == 1
    assert corrected_stdout.count("COMPILED 19 ordinary identity modules; warnings=0") == 1
    assert "COMPILED 1 lifecycle test module; warnings=0" in corrected_stdout and "Result: 7 passed" in corrected_stdout
    assert "read-only formatting equality failed: hosted/lib/mixer_hosted/identity/admission.ex" in corrected_stdout
    assert "FORMAT CHECK 3 authored canonical files; unchanged=3" not in corrected_stdout
    format_plan = read(formatting / "execution-plan.json")
    format_receipt = read(formatting / "receipt.json")
    format_observed = read(formatting / "observations.json")
    assert format_receipt["execution_plan_sha256"] == sha(formatting / "execution-plan.json")
    assert format_receipt["status"] == "passed" and format_receipt["formatter_vm_invocations"] == 1 and format_receipt["product_compiler_test_invocations"] == 0
    assert format_observed == format_receipt["observations"] and format_observed["returncode"] == 0
    assert format_observed["child_pid"] == 30316
    assert all(format_observed[k] is True for k in ("direct_child_reaped", "owned_group_absent", "scratch_removed", "all_input_tool_pins_stable"))
    assert not format_observed["errors"] and not format_observed["cleanup_errors"]
    assert not Path(format_plan["cwd"]).exists()
    assert read(formatting / "tool-pins.json") == plan["tools"]
    paths = [item["path"] for item in format_plan["source_pins"]]
    assert len(paths) == 3
    source_diffs = []
    for relative in paths:
        before = (old / "inputs" / relative).read_bytes()
        after = (formatting / "outputs" / Path(relative).name).read_bytes()
        assert b"".join(before.split()) == b"".join(after.split())
        assert after == (REPO / relative).read_bytes() == (new / "inputs" / relative).read_bytes()
        source_diffs += list(difflib.unified_diff(before.decode().splitlines(True), after.decode().splitlines(True), fromfile="before/" + relative, tofile="formatted/" + relative))
    assert "".join(source_diffs) == (formatting / "formatting-only.diff").read_text() == (new / "canonical-formatting-only.diff").read_text()
    for item in format_seal["files"] + [{"path": "seal.json", "bytes": (formatting / "seal.json").stat().st_size, "sha256": sha(formatting / "seal.json")}]:
        assert (formatting / item["path"]).read_bytes() == (new / "formatting-evidence" / item["path"]).read_bytes()
    for name in ("runner.py", "prepare-v3.py"):
        ast.parse((new / name).read_text(), filename=name)
    result = {
        "schema": 1,
        "status": "candidate2-failure-preserved-formatting-provenance-and-prepared3-source-review-passed",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "command": "python3 -B verification/console-key-owner-lifecycle-independent/review-3/audit_terminal_and_candidate.py",
        "python": sys.version,
        "review_script_sha256": sha(Path(__file__)),
        "root_candidate2_terminal_sha256": sha(terminal_path),
        "candidate2_execution_files": 19,
        "candidate2_status": "failed after seven passed tests because admission formatting equality failed",
        "candidate2_test_counts": observed["artifacts"]["corrected/exunit-result.json"],
        "candidate2_observed_versions": observed["artifacts"]["corrected/runtime.json"],
        "candidate2_exact_children_groups_reaped": observed["owned_processes"],
        "candidate2_scratch_removed": True,
        "candidate2_source_tool_pins_historically_stable": True,
        "formatter_seal_sha256": sha(formatting / "seal.json"),
        "formatter_vm_invocations_historical": 1,
        "formatter_exact_pid_reaped": 30316,
        "formatter_group_scratch_cleanup_recorded": True,
        "manual_diff_review": "Whitespace only outside literals; no functions, guards, contracts or assertions changed; KeyOwner unchanged.",
        "Elixir_AST_comparison_executed_by_independent_review": False,
        "prepared3_freeze_sha256": sha(new / "freeze.json"),
        "prepared3_plan_sha256": sha(new / "execution-plan.json"),
        "prepared3_source_revision": plan["source_revision"],
        "prepared3_selected_source_tree_sha256": plan["source_tree_sha256"],
        "verified": {"preserved_prepared2_members": 234, "formatter_members": 12, "prepared3_members": 253, "prepared3_canonical_pins": 216, "prepared3_prepared_pins": 252, "tool_pins": 969, "same_strict_thirteen_artifacts": True, "same_bootstraps_phases_dependencies_scope": True, "runner_only_candidate_path_changes": True, "canonical_matches_recorded_formatter_outputs": True},
        "recommend_root_exact_single_host_release": True,
        "product_implementation_accepted_by_this_review": False,
        "producer_replay_or_runtime_invocations_by_review": 0,
        "elapsed_seconds": round(time.monotonic() - START, 6),
        "scope": "Read-only terminal evidence and formatting/source/custody review; no compiler/formatter/test replay, process inventory, DB/network/native/UI/capture."
    }
    (REVIEW / "audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
