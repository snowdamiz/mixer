"""Bounded independent cases and exact existing witnesses; no producer sealing."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import tempfile
import time
from verify_inputs import ROOT, REPO, verify, sha


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def run(argv, cwd, stem, expected, classification):
    start = time.monotonic()
    outpath = ROOT / "logs" / (stem + ".stdout")
    errpath = ROOT / "logs" / (stem + ".stderr")
    timed_out = False
    with outpath.open("wb") as out, errpath.open("wb") as err:
        child = subprocess.Popen(argv, cwd=cwd, stdout=out, stderr=err, start_new_session=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        try:
            code = child.wait(timeout=20)
        except subprocess.TimeoutExpired:
            timed_out = True
            # Only this case's freshly created process group is ours.
            os.killpg(child.pid, signal.SIGKILL)
            code = child.wait(timeout=5)
    record = {"argv": argv, "cwd": str(cwd), "exit_code": code, "expected_exit": expected, "classification": classification, "elapsed_seconds": time.monotonic() - start, "terminal_reaped": child.returncode is not None, "timeout_seconds": 20, "timed_out": timed_out}
    for stream, path in (("stdout", outpath), ("stderr", errpath)):
        record[stream] = str(path.relative_to(ROOT))
        record[stream + "_sha256"] = sha(path.read_bytes())
        record[stream + "_bytes"] = path.stat().st_size
    rows = []
    for line in outpath.read_text().splitlines():
        if line.startswith("{"):
            rows.append(json.loads(line))
    record["observations"] = rows
    record["command_disposition_matches"] = code == expected and not timed_out
    return record


def main():
    inputs = verify()
    for entry in json.loads((ROOT / "source-custody.json").read_text())["exact_copies"]:
        file = ROOT / entry["copy"]
        assert sha(file.read_bytes()) == entry["sha256"]
    (ROOT / "logs").mkdir(exist_ok=True)
    commands = []
    python = os.path.realpath(sys.executable)
    for variant in ("old", "new"):
        producer = ROOT / variant / "replay/corrected/replay"
        commands.append(run([python, "-B", "test_preparation.py"], producer, variant + "-producer", 0, "fresh exact26-method producer suite in independent copy"))
        for case in ("lifecycle", "multi-close", "nested-primary", "nested-result", "number-reuse", "stdio-close"):
            commands.append(run([python, "-B", str(ROOT / variant / "independent_case.py"), case], ROOT, variant + "-previous-" + case, int(case == "stdio-close"), "raw old required C01 failure" if variant == "old" and case == "stdio-close" else "new raw C01 unused TemporaryFile injection mismatch; not behavior pass" if case == "stdio-close" else "fresh unchanged independent positive"))
    cases = []
    for pattern in ("p-", "q-", "-p", "-q", "pp", "pq", "qp", "qq"):
        for body in ("primary", "result", "both"):
            cases.append(("close", pattern, body))
    cases.append(("close", "pq", "both", "baseexception"))
    for index in (0, 1):
        for stage in ("primitive-before", "captured-birth", "prepare-before", "prepare-after", "unlink-before", "unlink-after"):
            cases.append(("acquire", str(index), stage, "-"))
    for stage in ("primitive-before", "captured-birth", "prepare-before", "prepare-after", "unlink-before", "unlink-after"):
        for mode in ("p", "q"):
            cases.append(("acquire", "1", stage, mode))
    cases += [("path-reuse", mode) for mode in ("before", "after")]
    cases += [("descriptor-reuse",), ("healthy",)]
    cases += [("read", mode) for mode in ("chunks31", "chunks32", "interrupt31", "interrupt32")]
    cases += [("child", mode) for mode in ("healthy", "cleanup-result", "cleanup-primary-result", "read-last", "read-eof-last")]
    expected_failures = {("read", "chunks32"), ("read", "interrupt31")}
    for index, case in enumerate(cases):
        commands.append(run([python, "-B", str(ROOT / "boundary_case.py"), *case], ROOT, str(index).zfill(3) + "-" + "-".join(case), int(case in expected_failures), "required R03 read-boundary failure retained" if case in expected_failures else "independent behavioral requirement"))
    dump(ROOT / "command-receipts.json", {"schema": 1, "commands": commands})
    assert all(x["command_disposition_matches"] for x in commands), "unexpected command result; inspect retained receipts"
    producers = []
    for variant in ("old", "new"):
        report = json.loads((ROOT / variant / "replay/corrected/replay/test-results.json").read_text())
        assert report["methods"] == 26 and report["failures"] == report["errors"] == report["skips"] == 0
        producers.append({"variant": variant, "result": report})
    for command in commands:
        assert command["terminal_reaped"] and not command["timed_out"]
    scratch = [{"path": str(x.relative_to(ROOT)), "entries": len(list(x.iterdir()))} for x in ROOT.rglob("owned-scratch")]
    assert all(x["entries"] == 0 for x in scratch)
    dump(ROOT / "results.json", {"schema": 1, "producers": producers, "new_independent_cases": len(cases), "new_independent_behavior_passes": len(cases) - len(expected_failures), "new_independent_required_failures": len(expected_failures), "previous_independent_positives_each_variant": 5, "raw_C01_classifications": {"old": "required original behavior failure remains", "new": "unused TemporaryFile injection mismatch; not behavior pass"}, "scratch": scratch})
    dump(ROOT / "receipt.json", {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "command": [python, "-B", "run_review.py"], "cwd": str(ROOT), "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(), "git_committed_tree": subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=REPO, text=True).strip(), "input_source_tree_sha256": inputs["candidate_source_tree_sha256"], "python_executable": python, "python_executable_sha256": sha(Path(python).read_bytes()), "python_version": sys.version, "stdlib_tempfile_source": tempfile.__file__, "stdlib_tempfile_sha256": sha(Path(tempfile.__file__).read_bytes()), "platform": platform.platform(), "fresh_commands": len(commands), "independent_cases": len(cases), "independent_passes": len(cases) - len(expected_failures), "required_R03_failures": len(expected_failures), "all_owned_case_children_terminal_reaped": True, "actual_fixed_children_terminal_reaped_by_owned_references": True, "owned_scratch_empty": True, "uncertain_saved_numbers_retried": False, "native_UI_capture_or_process_inventory": False, "hosted_harness_read_import_or_execution": False, "canonical_edits_commits_pushes_or_publication": False, "real_Rust_context_accounting_native_OTA_GA_acceptance": False, "complete_composition_acceptance": False})
    print(json.dumps({"commands": len(commands), "independent_cases": len(cases), "behavior_passes": len(cases) - len(expected_failures), "required_R03_failures": len(expected_failures), "scratch": scratch}, sort_keys=True))


if __name__ == "__main__":
    main()
