#!/usr/bin/env python3
"""Independent read-only candidate-3 terminal audit; never imports producer code."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

START = time.monotonic()
REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
LANE = REPO / "verification/console-key-owner-lifecycle-implementation"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            assert time.monotonic() - START < 55
            chunk = stream.read(262144)
            if not chunk:
                return digest.hexdigest()
            digest.update(chunk)


def pairs(values):
    output = {}
    for key, value in values:
        assert key not in output
        output[key] = value
    return output


def read(path):
    return json.loads(path.read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def check(items, root):
    seen = set()
    for item in items:
        assert item["path"] not in seen
        seen.add(item["path"])
        file = root / item["path"]
        assert file.is_file() and not file.is_symlink()
        assert file.stat().st_size == item["bytes"] and sha(file) == item["sha256"], str(file)
    return seen


def main():
    prepared = LANE / "prepared-3"
    execution = LANE / "executions/candidate-3"
    release_path = REPO / "verification/console-session-and-checkout-root-review/key-owner-lifecycle-candidate-3-release.json"
    assert sha(release_path) == "7d79e3f884f65aaea7830ecef02af6e017f67feb7b49f9d8b95da1b6f89b458e"
    assert sha(prepared / "freeze.json") == "fc4f644bccc627470bdb027a65d2e4d80cde51ca32c684b23a85fd6c1e80e307"
    assert sha(prepared / "execution-plan.json") == "80d718131fd6b0ba48d6c7e4b9a6eb7c9d704eee95f4b91555a82dc944acd4fd"
    freeze = read(prepared / "freeze.json")
    plan = read(prepared / "execution-plan.json")
    sealed = check(freeze["files"], prepared)
    assert len(sealed) == 253
    assert sealed == {file.relative_to(prepared).as_posix() for file in prepared.rglob("*") if file.is_file() and file.relative_to(prepared).as_posix() != "freeze.json"}
    assert len(check(plan["prepared_files"], prepared)) == 252
    assert len(check(plan["canonical_inputs"], REPO)) == 216
    for item in plan["tools"]:
        path = Path(item["path"])
        assert path.stat().st_size == item["bytes"] and sha(path) == item["sha256"]
    assert len(plan["tools"]) == 969
    release = read(release_path)
    receipt = read(execution / "receipt.json")
    observed = read(execution / "observations.json")
    assert release["status"] == "root-released-exact-plan" and release["single_execution"] is True
    for key in ("plan", "preparation_seal", "independent_review"):
        check([release[key]], REPO)
    assert release["execution_plan_sha256"] == receipt["execution_plan_sha256"] == observed["execution_plan_sha256"] == sha(prepared / "execution-plan.json")
    assert receipt["status"] == "passed" and not receipt["errors"] and not receipt["cleanup_errors"]
    assert not receipt["observed_signals_at_cutoff"] and receipt["finite_signal_cutoff_elapsed_seconds"] < 52
    assert receipt["source_revision"] == plan["source_revision"] and receipt["source_tree_sha256"] == plan["source_tree_sha256"]
    assert not observed["errors"] and not observed["cleanup_errors"] and not observed["observed_signals_before_observation_write"]
    assert observed["all_original_pins_rechecked"] is True and not observed["original_changes"]
    assert observed["scratch_removed"] is True and not Path(observed["scratch_path"]).exists()
    assert [(p["id"], p["returncode"]) for p in observed["phases"]] == [("original", 0), ("corrected", 0)]
    assert len(observed["owned_processes"]) == 2
    assert all(p["direct_child_reaped"] is True and p["group_absent"] is True for p in observed["owned_processes"])
    schemas_packet = read(prepared / "required-artifact-schemas.json")
    schemas = dict(schemas_packet["schemas"])
    for kind, paths in schemas_packet["shared_schema_bindings"].items():
        for relative in paths:
            assert relative not in schemas
            schemas[relative] = schemas_packet["shared_schemas"][kind]
    assert len(schemas) == 13 and set(schemas) == set(observed["artifacts"])
    for relative, schema in schemas.items():
        value = read(execution / relative)
        assert set(value) == set(schema) and value == observed["artifacts"][relative]
        for name, rule in schema.items():
            assert type(value[name]) is {"boolean": bool, "integer": int, "string": str}[rule["type"]]
            assert value[name] in rule["enum"] if "enum" in rule else value[name] == rule["value"]
    scratch = Path(observed["scratch_path"])
    for phase in plan["phases"]:
        identity = phase["id"]
        command = read(execution / identity / "command.json")
        expected = [plan["elixir"], "--no-color", "--boot", plan["boot"], "--erl", "+S 2:2 +A 2 -home " + str(scratch / "home")]
        for dependency in plan["dependencies"]:
            expected += ["-pa", str(scratch / "dependencies" / dependency["name"] / "ebin")]
        expected += [str(scratch / phase["bootstrap"]), str(scratch / (identity + "-sources.json")), str(scratch / "inputs" / plan["test_source"]), str(scratch / (identity + "-ebin")), str(scratch / "dependency-metadata.json")]
        assert command["argv"] == expected and command["cwd"] == str(scratch)
        environment = dict(plan["environment"])
        environment.update(HOME=str(scratch / "home"), TMPDIR=str(scratch / "tmp"), MIXER_KEY_OWNER_LIFECYCLE_ROOT_PEM=str(scratch / "root.pem"), MIXER_KEY_OWNER_LIFECYCLE_EVIDENCE=str(execution / identity))
        assert command["environment"] == environment
        stdout = (execution / identity / "stdout.txt").read_bytes()
        assert len(stdout) == next(p["output_bytes"] for p in observed["phases"] if p["id"] == identity)
    original = (execution / "original/stdout.txt").read_text()
    corrected = (execution / "corrected/stdout.txt").read_text()
    assert original.splitlines() == ["COMPILED 19 ordinary identity modules; warnings=0", "ORIGINAL DEFECT REPRODUCED: graceful parent stop leaves a dead, fail-closed pointer"]
    assert corrected.startswith("COMPILED 19 ordinary identity modules; warnings=0\nCOMPILED 1 lifecycle test module; warnings=0\n")
    assert "Result: 7 passed\n" in corrected and 'RESULT {"total":7,"failures":0,"skipped":0,"excluded":0}\n' in corrected
    assert corrected.endswith("FORMAT CHECK 3 authored canonical files; unchanged=3\n")
    assert receipt["output_bytes"] == sum(p["output_bytes"] for p in observed["phases"]) == 459
    old_terminal_path = REPO / "verification/console-session-and-checkout-root-review/key-owner-lifecycle-candidate-2-terminal.json"
    old_terminal = read(old_terminal_path)["terminal"]
    assert len(check(old_terminal["execution_members"], REPO)) == 19
    assert read(LANE / "executions/candidate-2/receipt.json")["status"] == "failed"
    files = []
    for path in sorted(execution.rglob("*")):
        assert not path.is_symlink()
        if path.is_file():
            files.append({"path": path.relative_to(REPO).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)})
    assert len(files) == 19
    output = {
        "schema": 1,
        "status": "passed-independent-terminal-review-bounded-ordinary-socket-free-KOL01-KOL07-only",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "command": "python3 -B verification/console-key-owner-lifecycle-independent/terminal-review-3/audit_terminal.py",
        "python": sys.version,
        "review_script_sha256": sha(Path(__file__)),
        "root_release_sha256": sha(release_path),
        "producer_plan_sha256": sha(prepared / "execution-plan.json"),
        "producer_freeze_sha256": sha(prepared / "freeze.json"),
        "terminal_receipt_sha256": sha(execution / "receipt.json"),
        "source_revision": plan["source_revision"],
        "selected_source_tree_sha256": plan["source_tree_sha256"],
        "execution_files": files,
        "actual_counts": observed["artifacts"]["corrected/exunit-result.json"],
        "observed_runtime": observed["artifacts"]["corrected/runtime.json"],
        "original_defect_reproduced": True,
        "compiled_identity_modules_per_phase": 19,
        "compiler_warnings": 0,
        "three_authored_files_formatting_unchanged": True,
        "owned_process_cleanup": observed["owned_processes"],
        "scratch_removed": True,
        "historical_posthashes_and_current_all_source_tool_pins_stable": True,
        "prepared_packet_members": 253,
        "prepared_plan_pins": 252,
        "canonical_pins": 216,
        "tool_pins": 969,
        "execution_observation_elapsed_seconds": observed["elapsed_seconds"],
        "finite_signal_cutoff_elapsed_seconds": receipt["finite_signal_cutoff_elapsed_seconds"],
        "candidate2_failed_terminal_and_nineteen_files_preserved": True,
        "recommend_bounded_ordinary_socket_free_slice_acceptance": True,
        "product_GA_verified": 0,
        "review_runtime_or_producer_replay_invocations": 0,
        "review_elapsed_seconds": round(time.monotonic() - START, 6),
        "pending": ["KOL08 real refresh/TLS drain", "KOL09 worker-supervisor death with actual active flights", "actual application/provider/HTTP/browser/session integration", "production custody/operation/GA", "native/UI/capture and physical devices"],
        "scope": "Actual source-bound host evidence for ordinary registered-owner socket-free KOL01-KOL07 only; no independent runtime replay, process inventory, DB/network/native/UI/capture."
    }
    (OUT / "audit.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({k:v for k,v in output.items() if k != "execution_files"}, indent=2))


if __name__ == "__main__":
    main()
