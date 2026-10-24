#!/usr/bin/env python3
"""Repair recorder metadata from retained raw passing tests, without rerunning them."""

import datetime
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
import run_review as review


def counts(stdout):
    match = re.search(r"Result:\s*(\d+) passed(?:,\s*(\d+) failed)?", stdout)
    assert match, "unknown ExUnit output; do not claim a pass"
    passed, failed = int(match[1]), int(match[2] or 0)
    return {"tests": passed + failed, "failures": failed}


def main():
    here = Path(__file__).resolve().parent
    results_path = here / "results.json"
    results = json.loads(results_path.read_text())
    initial = here / "attempts/initial-harness-version-and-summary-error"
    acceptance = json.loads((here / "source-acceptance.json").read_text())
    assert review.sha(review.SEAL) == review.EXPECTED_SEAL
    for name, expected in acceptance["producer_files_verified"].items():
        assert review.sha(review.ROOT / name) == expected["sha256"]
    for name, expected in acceptance["snapshot_sha256"].items():
        assert review.sha(here / "accepted-source" / name) == expected
    original_recorder = initial / "run_review.py"
    original_hash = results["input_sha256"][str((here / "run_review.py").relative_to(review.ROOT))]
    assert review.sha(original_recorder) == original_hash
    assert review.sha(here / "controls_test.exs") == results["input_sha256"][str((here / "controls_test.exs").relative_to(review.ROOT))]
    for key, label in [("producer_suite", "producer-suite"), ("independent_controls", "independent-controls")]:
        assert results[key]["exit_code"] == 0
        assert results[key]["stdout"] == (here / f"commands/{label}.stdout").read_bytes().decode(errors="replace")
        assert not (here / f"commands/{label}.stderr").read_bytes()
        results[key]["counts"] = counts(results[key]["stdout"])
        assert results[key]["counts"]["failures"] == 0

    corrected = review.run("precise-versions-corrected", [
        review.ELIXIR, "-e",
        'IO.puts("elixir=" <> System.version()); IO.puts("otp=" <> File.read!(Path.join([to_string(:code.root_dir()), "releases", to_string(:erlang.system_info(:otp_release)), "OTP_VERSION"])))',
    ], 10)
    assert corrected["exit_code"] == 0
    assert corrected["stdout"].strip() == "elixir=1.20.4\notp=29.1.1"
    results["initial_precise_versions_error"] = results["precise_versions"]
    results["precise_versions"] = corrected
    results["result"] = "pure_review_passed_root_acceptance_pending"
    results["metadata_correction"] = {
        "corrected_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "reason": "Recorder expected obsolete ExUnit summary format and OTP_VERSION at releases root instead of releases/29; both test processes had already exited zero.",
        "original_attempt": str(initial.relative_to(review.ROOT)),
        "original_recorder_copy": str(original_recorder.relative_to(review.ROOT)),
        "original_recorder_sha256": original_hash,
        "corrected_recorder_sha256": review.sha(here / "run_review.py"),
        "tests_rerun": False,
        "source_or_tests_changed": False,
        "scope": "Read retained passing stdout/exit codes and perform one read-only exact-version query; preserve all original raw evidence and elapsed times.",
    }
    review.save(results_path, results)
    print(json.dumps({
        "result": results["result"],
        "producer_suite": results["producer_suite"]["counts"],
        "independent_controls": results["independent_controls"]["counts"],
        "exact_versions": corrected["stdout"].strip(),
        "tests_rerun": False,
    }, indent=2))


if __name__ == "__main__":
    main()
