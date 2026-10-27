#!/opt/homebrew/opt/python@3.14/bin/python3.14
"""Read-only terminal evidence audit; no subprocess, compiler, runtime or network."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    original_bindings = 0
    copied_bindings = 0
    retained_outputs = 0
    outcomes = {}
    for number in range(1, 7):
        candidate = PACKET / f"candidate-{number}"
        plan_path = candidate / "execution-plan.json"
        plan = json.loads(plan_path.read_text())
        for entry in plan["selected_inputs"] + plan["tool_files"] + [entry for dependency in plan["dependencies"] for entry in dependency["files"]]:
            source = Path(entry["path"])
            source = source if source.is_absolute() else ROOT / source
            assert source.stat().st_size == entry["bytes"] and sha(source) == entry["sha256"], entry["path"]
            original_bindings += 1
        for entry in plan["selected_inputs"]:
            copied = candidate / "inputs" / entry["path"]
            assert copied.stat().st_size == entry["bytes"] and sha(copied) == entry["sha256"], str(copied)
            copied_bindings += 1
        receipt_path = candidate / "execution/receipt.json"
        if number in [1, 5]:
            assert not receipt_path.exists()
            outcomes[f"candidate-{number}"] = "superseded-before-execution"
            continue
        release = json.loads((candidate / "root-execution-release.json").read_text())
        assert release["released"] is True and release["execution_plan_sha256"] == sha(plan_path)
        receipt = json.loads(receipt_path.read_text())
        assert receipt["execution_plan_sha256"] == sha(plan_path)
        assert receipt["original_input_changes"] == [] and receipt["original_input_read_errors"] == []
        assert len(receipt["owned_processes"]) == 8
        assert all(item["direct_child_reaped"] and item["process_group_absent"] and not item["cleanup_errors"] for item in receipt["owned_processes"])
        for key in ["all_owned_children_reaped_and_groups_absent", "postgres_port_closed", "postmaster_pid_file_absent", "scratch_removed"]:
            assert receipt["cleanup"][key] is True
        assert not Path(receipt["cleanup"]["scratch_path"]).exists()
        for name, expected in receipt["outputs"].items():
            assert sha(receipt_path.parent / name) == expected, name
            retained_outputs += 1
        outcomes[f"candidate-{number}"] = receipt["status"]
        if number == 6:
            assert receipt["status"] == "passed" and receipt["elapsed_seconds"] <= 55
            assert receipt["exunit_result"] == {"total": 7, "failures": 0, "skipped": 0, "excluded": 0}
            assert all(receipt["postrun_observations"].values())
            for key in ["owner_alive_before_normal_stop", "owner_dependencies_alive_before_normal_stop", "owner_normal_stop", "owned_components_stopped", "default_owner_absent", "default_repo_absent", "admission_absent", "ephemeral_tls_key_directory_removed"]:
                assert receipt["component_cleanup"][key] is True
            assert receipt["component_cleanup"]["jwks_tls_requests"] >= 1
            assert receipt["cleanup"]["fixture_tls_port_closed"] is True
            raw = (receipt_path.parent / "default-authority-tests.stdout.txt").read_text()
            assert "COMPILED 39 frozen ordinary modules; warnings=0" in raw
            assert "COMPILED 3 test modules; warnings=0" in raw
            assert "Result: 7 passed" in raw
        else:
            assert receipt["status"] == "failed"
    result = {"status": "passed-offline-terminal-audit", "original_bindings": original_bindings,
              "copied_bindings": copied_bindings, "retained_output_hashes": retained_outputs,
              "outcomes": outcomes, "actual_runtime_replayed": False,
              "qualification": "Candidate6 seven-method local default-authority slice only; prior failures retained; production/session/HTTP/native/GA remain pending"}
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
