"""Fresh exact independent witnesses plus bounded request/EOF controls."""
import datetime
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import tempfile
import time
from verify_inputs import ROOT, REPO, verify, sha, dump


def run(argv, cwd, stem, expected, classification, prototype):
    stdout = ROOT / "logs" / (stem + ".stdout")
    stderr = ROOT / "logs" / (stem + ".stderr")
    script = Path(argv[2])
    if not script.is_absolute():
        script = cwd / script
    start = time.monotonic()
    with stdout.open("xb") as out, stderr.open("xb") as err:
        child = subprocess.Popen(argv, cwd=cwd, stdout=out, stderr=err, start_new_session=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        timeout = False
        try:
            code = child.wait(timeout=20)
        except subprocess.TimeoutExpired:
            timeout = True
            os.killpg(child.pid, signal.SIGKILL)  # This invocation's owned group.
            code = child.wait(timeout=5)
    row = {"argv": argv, "cwd": str(cwd), "exit_code": code, "expected_exit": expected, "classification": classification, "elapsed_seconds": time.monotonic() - start, "timeout_seconds": 20, "timed_out": timeout, "terminal_reaped": child.returncode is not None, "executed_case_source": {"path": str(script.relative_to(ROOT)), "bytes": script.stat().st_size, "sha256": sha(script.read_bytes())}, "prototype_source": {"path": str(prototype.relative_to(ROOT)), "bytes": prototype.stat().st_size, "sha256": sha(prototype.read_bytes())}}
    for stream, path in (("stdout", stdout), ("stderr", stderr)):
        row[stream] = {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha(path.read_bytes())}
    row["observations"] = [json.loads(line) for line in stdout.read_text().splitlines() if line.startswith("{")]
    row["command_disposition_matches"] = not timeout and code == expected
    return row


def main():
    inputs = verify()
    copies = json.loads((ROOT / "source-custody.json").read_text())["copies"]
    for entry in copies:
        assert sha((ROOT / entry["copy"]).read_bytes()) == entry["sha256"]
    (ROOT / "logs").mkdir()
    python = os.path.realpath(sys.executable)
    commands = []
    old = ROOT / "old/replay/corrected/replay/prototype.py"
    new = ROOT / "new/replay/corrected/replay/prototype.py"
    cases = ("zero", "one", "chunks31", "chunks32", "cap512-at32", "unfinished33", "eintr31-complete32", "eintr32", "eintr30-data-eof32", "eintr31-eof32", "eintr30-complete31", "eintr31-short32", "invalid-negative", "invalid-overcap", "invalid-bool", "invalid-float")
    for variant, prototype in (("old", old), ("new", new)):
        for case in cases:
            expected = int(variant == "old" and case in ("chunks32", "cap512-at32", "eintr31-complete32"))
            commands.append(run([python, "-B", str(ROOT / "producer_boundary_case.py"), variant, case], ROOT, variant + "-root-boundary-" + case, expected, "fresh unchanged root boundary control; required old failures retained" if variant == "old" else "fresh unchanged root boundary control", prototype))
    for mode in ("chunks32", "interrupt31"):
        commands.append(run([python, "-B", str(ROOT / "old-independent/boundary_case.py"), "read", mode], ROOT, "old-exact-independent-read-" + mode, 1, "required original independent R03 failure remains on unchanged old source", ROOT / "old-independent/new/replay/corrected/replay/prototype.py"))
    independent = []
    for pattern in ("p-", "q-", "-p", "-q", "pp", "pq", "qp", "qq"):
        for body in ("primary", "result", "both"):
            independent.append(("close", pattern, body))
    independent.append(("close", "pq", "both", "baseexception"))
    for index in (0, 1):
        for stage in ("primitive-before", "captured-birth", "prepare-before", "prepare-after", "unlink-before", "unlink-after"):
            independent.append(("acquire", str(index), stage, "-"))
    for stage in ("primitive-before", "captured-birth", "prepare-before", "prepare-after", "unlink-before", "unlink-after"):
        for mode in ("p", "q"):
            independent.append(("acquire", "1", stage, mode))
    independent += [("path-reuse", mode) for mode in ("before", "after")]
    independent += [("descriptor-reuse",), ("healthy",)]
    independent += [("read", mode) for mode in ("chunks31", "chunks32", "interrupt31", "interrupt32")]
    independent += [("child", mode) for mode in ("healthy", "cleanup-result", "cleanup-primary-result", "read-last", "read-eof-last")]
    assert len(independent) == 62
    for index, case in enumerate(independent):
        commands.append(run([python, "-B", str(ROOT / "boundary_case.py"), *case], ROOT, "independent-" + str(index).zfill(3) + "-" + "-".join(case), 0, "fresh byte-identical independent required behavior/oracle", new))
    commands.append(run([python, "-B", str(ROOT / "mixed_child_case.py")], ROOT, "independent-062-mixed-child-join", 0, "fresh byte-identical independent nested real-child cleanup join", new))
    producer = ROOT / "new/replay/corrected/replay"
    commands.append(run([python, "-B", "test_preparation.py"], producer, "new-unchanged-producer26", 0, "fresh exact26-method307-mutation suite", new))
    dump(ROOT / "command-receipts.json", {"schema": 1, "commands": commands})
    assert len(commands) == 98 and all(x["command_disposition_matches"] for x in commands)
    report = json.loads((producer / "test-results.json").read_text())
    assert report["methods"] == 26 and report["failures"] == report["errors"] == report["skips"] == 0
    assert any(x.get("snapshot_leaf_mutations") == 307 for x in report["observations"])
    for row in commands:
        if row["classification"].startswith("fresh byte-identical"):
            assert row["exit_code"] == 0
    scratch = []
    for path in ROOT.rglob("owned-scratch"):
        assert not list(path.iterdir())
        scratch.append(str(path.relative_to(ROOT)))
    dump(ROOT / "results.json", {"schema": 1, "fresh_commands": 98, "new_exact_independent_cases": 63, "new_exact_independent_behavior_passes": 63, "old_exact_independent_R03_failures_retained": 2, "root_boundary_new_cases": 16, "root_boundary_old_cases": 16, "root_boundary_old_required_failures_retained": 3, "producer": report, "scratch_empty": scratch, "C01_raw_ownership_and_R03_read_correction_scoped_recommendation": "accept finite host correction only", "complete_composition_product_acceptance": False})
    dump(ROOT / "receipt.json", {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "command": [python, "-B", str(Path(__file__))], "cwd": str(ROOT), "python_executable": python, "python_executable_sha256": sha(Path(python).read_bytes()), "python_version": sys.version, "stdlib_tempfile_source": tempfile.__file__, "stdlib_tempfile_sha256": sha(Path(tempfile.__file__).read_bytes()), "platform": platform.platform(), "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(), "git_committed_tree": subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=REPO, text=True).strip(), "input_packets": inputs, "new_prototype_sha256": sha(new.read_bytes()), "old_prototype_sha256": sha(old.read_bytes()), "single_line_delta_verified": True, "fresh_commands": len(commands), "new_exact_independent_cases_pass": 63, "new_root_boundary_cases_pass": 16, "old_required_behavior_failures_retained": 5, "no_case_timeout": True, "all_owned_case_children_terminal_reaped": True, "actual_fixed_children_terminal_reaped_by_owned_references": True, "uncertain_saved_numbers_retried_or_ledgers_erased": False, "native_UI_capture_process_inventory_or_stopped_Android_review": False, "prohibited_hosted_read_import_execution": False, "canonical_index_edit_commit_push_or_publication": False, "source_limits": {"read_attempts": 32, "read_byte_cap": 512, "retained_owners": 9, "retained_descriptors_per_owner": 65, "stdio_owners": 2}, "original142_lifecycle_positions_freshly_replayed": False, "real_Rust_provenance_context_accounting_native_OTA_GA_accepted": False, "complete_composition_accepted": False})
    print(json.dumps({"commands": 98, "new_exact_independent_cases_pass": 63, "new_root_boundary_cases_pass": 16, "old_required_R03_failures_retained": 5, "producer_methods": 26, "mutations": 307, "owned_scratch_empty": scratch}, sort_keys=True))


if __name__ == "__main__":
    main()
