#!/usr/bin/env python3
"""Read-only closure delta and retained failure audit; no producer replay."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import sys
import time

START = time.monotonic()
REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
LANE = REPO / "verification/console-key-owner-fixture-cleanup-ci-correction"


def sha(path):
    assert time.monotonic() - START < 55
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pairs(values):
    result = {}
    for key, value in values:
        assert key not in result
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def verify(items, root=None):
    seen = set()
    for item in items:
        assert item["path"] not in seen
        seen.add(item["path"])
        path = root / item["path"] if root else Path(item["path"])
        assert path.is_file() and path.stat().st_size == item["bytes"] and sha(path) == item["sha256"]
    return seen


def packet(path, expected, count):
    assert sha(path / "freeze.json") == expected
    sealed = read(path / "freeze.json")
    listed = verify(sealed["files"], path)
    actual = set()
    for file in path.rglob("*"):
        assert not file.is_symlink()
        if file.is_file() and file.relative_to(path).as_posix() != "freeze.json":
            actual.add(file.relative_to(path).as_posix())
    assert listed == actual and len(actual) == count
    assert hashlib.sha256("".join(v["path"] + "\0" + str(v["bytes"]) + "\0" + v["sha256"] + "\n" for v in sealed["files"]).encode()).hexdigest() == sealed["tree_sha256"]
    return sealed


def main():
    packet(LANE / "prepared-1", "34ab3c96238e0e8100331d42109d834d313b39bec9b86582e7ffd78080f97019", 221)
    old = LANE / "prepared-2"
    new = LANE / "prepared-3"
    old_seal = packet(old, "5ce0557d8cae549b7257a2d0ddfd59f73c4bd59d463fa20377e0038dfd64172e", 225)
    packet(new, "c79e8af319b32376d1d6dc4b074436eb10b20bae8415062f6313b1615989a910", 229)
    assert sha(new / "execution-plan.json") == "8e9df8c3eb6f4653629f1fa4694e0df662ad0473f03a31c95f3bbf718afc1852"
    previous = read(old / "execution-plan.json")
    plan = read(new / "execution-plan.json")
    assert len(verify(plan["prepared_files"], new)) == 228
    assert len(verify(plan["canonical_inputs"], REPO)) == 26
    assert len(verify(plan["tools"])) == 980
    for key in ("source_roster", "test_source", "selection", "tools", "dependencies", "artifact_schemas", "limits", "environment", "scope"):
        assert plan[key] == previous[key], key
    probe = "hosted/test/support/identity_socket_probe.ex"
    assert plan["test_support"] == previous["test_support"] + [probe]
    assert sha(new / "inputs" / probe) == "8135af832ad0f1877e7370ff491c882597c1510d82f15c011a35897e936f9416"
    assert (new / "inputs" / probe).read_bytes() == (REPO / probe).read_bytes()
    assert (new / "runner.py").read_text() == (old / "runner.py").read_text().replace("prepared.name != 'prepared-2'", "prepared.name != 'prepared-3'").replace("'candidate-2'", "'candidate-3'")
    changed = [v["path"] for v in old_seal["files"] if v["path"] != "execution-plan.json" and (old / v["path"]).read_bytes() != (new / v["path"]).read_bytes()]
    assert sorted(changed) == ["bootstrap.exs", "runner.py"]
    diff = []
    for name in ("runner.py", "bootstrap.exs"):
        diff += list(difflib.unified_diff((old / name).read_text().splitlines(True), (new / name).read_text().splitlines(True), fromfile="prepared-2/" + name, tofile="prepared-3/" + name))
    assert "".join(diff) == (new / "candidate3-only.diff").read_text()
    failure = LANE / "executions/candidate-2"
    closure = read(new / "source-closure-review.json")
    assert len(verify(closure["retained_failed_execution_members"], failure)) == 6
    assert {v["path"] for v in closure["retained_failed_execution_members"]} == {v.relative_to(failure).as_posix() for v in failure.rglob("*") if v.is_file()}
    receipt = read(failure / "receipt.json")
    observation = read(failure / "observations.json")
    assert receipt["status"] == "failed" and sha(failure / "receipt.json") == "3550d2902cc411a5ffbd566f8a6efe0eafc683e6a38527995fc7f8bd74df3f2f"
    assert receipt["execution_plan_sha256"] == sha(old / "execution-plan.json")
    assert not receipt["cleanup_errors"] and not observation["cleanup_errors"]
    assert observation["owned_processes"] == [{"pid": 51011, "direct_child_reaped": True, "group_absent": True}]
    assert observation["scratch_removed"] is True and not Path(observation["scratch_path"]).exists()
    assert observation["all_original_pins_rechecked"] is True and not observation["original_changes"]
    stdout = (failure / "corrected/stdout.txt").read_text()
    assert "COMPILED 19 frozen accepted identity modules; warnings=0" in stdout and "COMPILED 3 frozen canonical support modules; warnings=0" in stdout
    assert "SocketProbe.info/1 is undefined" in stdout and "TEST_COMPILE_REJECTED" in stdout and "Running ExUnit" not in stdout
    assert not (failure / "corrected/exunit-result.json").exists()
    ssl = read(failure / "corrected/openssl-01.json")
    assert ssl["argv"] == ["/opt/homebrew/Cellar/openssl@3/3.6.5/bin/openssl", "version"] and ssl["child_reaped"] is True and ssl["exit_code"] == 0
    result = {"schema":1,"status":"retained-compile-failure-preserved-prepared3-minimal-source-closure-review-passed","created_at":datetime.now(timezone.utc).isoformat(),"command":"python3 -B verification/console-key-owner-fixture-cleanup-ci-independent/review-3/audit_delta.py","python":sys.version,"script_sha256":sha(Path(__file__)),"plan_sha256":sha(new/'execution-plan.json'),"freeze_sha256":sha(new/'freeze.json'),"source_revision":plan['source_revision'],"selected_source_tree_sha256":plan['source_tree_sha256'],"verified":{"prior_packet_members_preserved":[221,225],"new_members":229,"prepared_pins":228,"canonical_pins":26,"tool_pins":980,"exact_recorded_diff":True,"only_prior_bootstrap_and_runner_changed":True,"canonical_test_product_schemas_wrapper_tools_dependencies_same":True,"new_probe_source_sha256":sha(new/'inputs'/probe)},"retained_failure":{"files":6,"receipt_sha256":sha(failure/'receipt.json'),"reason":"SocketProbe.info compile warnings in unselected test bodies; no tests started","OpenSSL_version_probe_only":True,"outer_pid_reaped":51011,"group_absent":True,"scratch_removed":True,"historical_posthashes_stable":True,"observation_seconds":observation['elapsed_seconds']},"recommend_root_single_exact_bounded_host_release":True,"runtime_or_producer_replay_invocations":0,"elapsed_seconds":round(time.monotonic()-START,6),"scope":"Focused source dependency completion; targeted runtime and full Phoenix CI remain pending."}
    (OUT / "audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
