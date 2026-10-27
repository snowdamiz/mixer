"""Fresh bounded boundary regressions and unchanged stdio cleanup suite."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import platform
import subprocess
import sys
import time

D = Path(__file__).resolve().parent
ROOT = D.parents[1]
records = []


def identity(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def run(name, arguments, expected=0, cwd=D):
    out, err = D / "logs" / (name + ".stdout"), D / "logs" / (name + ".stderr")
    started = time.monotonic()
    with out.open("xb") as stdout, err.open("xb") as stderr:
        child = subprocess.Popen([sys.executable, "-B", *map(str, arguments)], cwd=cwd,
                                 stdout=stdout, stderr=stderr,
                                 env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        timed_out = False
        try:
            child.wait(timeout=30)
        except subprocess.TimeoutExpired:
            timed_out = True
            child.kill()
            child.wait(timeout=10)
    row = {"name": name, "argv": [sys.executable, "-B", *map(str, arguments)], "cwd": str(cwd),
           "exit": child.returncode, "expected_exit": expected, "timeout": timed_out,
           "terminal_reaped": True, "elapsed_seconds": time.monotonic() - started,
           "stdout": {"path": str(out.relative_to(D)), **identity(out)},
           "stderr": {"path": str(err.relative_to(D)), **identity(err)}}
    records.append(row)
    save(D / "commands.json", records)
    assert not timed_out and child.returncode == expected, row
    return out


def main():
    (D / "logs").mkdir()
    cases = ["zero", "one", "chunks31", "chunks32", "cap512-at32", "unfinished33",
             "eintr31-complete32", "eintr32", "eintr30-data-eof32", "eintr31-eof32",
             "eintr30-complete31", "eintr31-short32", "invalid-negative", "invalid-overcap",
             "invalid-bool", "invalid-float"]
    boundary_results = []
    for variant in ("old", "new"):
        for case in cases:
            expected = 1 if variant == "old" and case in ("chunks32", "cap512-at32", "eintr31-complete32") else 0
            out = run(variant + "-" + case, [D / "boundary_case.py", variant, case], expected)
            result = json.loads(out.read_bytes())
            assert result["required_behavior_pass"] == (expected == 0) and result["healthy_zero"]
            boundary_results.append(result)
    cwd = D / "new/replay/corrected/replay"
    run("new-unchanged-producer26", ["test_preparation.py"], cwd=cwd)
    producer = json.loads((cwd / "test-results.json").read_bytes())
    assert producer["methods"] == 26 and producer["errors"] == producer["failures"] == producer["skips"] == 0
    assert any(row.get("snapshot_leaf_mutations") == 307 for row in producer["observations"])
    stdcases = [("healthy",), ("reuse-uncertain",)]
    stdcases += [("close", pattern, body) for pattern in ("p-", "q-", "-p", "-q", "pp", "pq", "qp", "qq") for body in ("primary", "result")]
    stdcases += [("close", "pq", "both")]
    stdcases += [("acquire", str(index), stage, mode) for index in (0, 1) for stage in ("before", "post-acquire", "pre-prepare", "post-prepare", "unlink-pre", "unlink-post") for mode in ("-", "p", "q") if not (index == 0 and stage == "before" and mode != "-")]
    stdcases += [("child", body, mix) for body in ("primary", "result") for mix in ("stdio", "mixed")]
    assert len(stdcases) == 57
    stdio = []
    for index, args in enumerate(stdcases):
        out = run("stdio-" + str(index).zfill(2) + "-" + "-".join(args), [D / "stdio_case.py", *args])
        result = json.loads(out.read_bytes())
        assert result["ownership_at_process_exit"]["healthy_zero"] == (result["cleanup_kind"] == "healthy-zero")
        stdio.append(result)
    assert sum(row["cleanup_kind"] == "healthy-zero" for row in stdio) == 5
    for path in D.rglob("owned-scratch"):
        assert not list(path.iterdir())
    old = D / "old/replay/corrected/replay/prototype.py"
    new = D / "new/replay/corrected/replay/prototype.py"
    assert identity(old)["sha256"] == "54d8b967b996ff273039824fffa6042e9ca9ef383079ce1427aadf45f23114a1"
    assert identity(new)["sha256"] == "af8d04f4940bca83c341d72970ef088852e27919305cda7aa7d53396ea2d2ccf"
    save(D / "results.json", {"boundary": boundary_results, "producer": producer, "stdio": stdio})
    save(D / "receipt.json", {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "R03-one-line-correction-host-controls-pass-independent-review-pending",
        "command": [sys.executable, "-B", str(Path(__file__))], "runner": identity(Path(__file__)),
        "python": sys.version, "python_executable": str(Path(sys.executable).resolve()),
        "python_executable_identity": identity(Path(sys.executable).resolve()), "platform": platform.platform(),
        "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "old_source": identity(old), "new_source": identity(new), "patch": identity(D / "source.patch"),
        "commands": len(records), "old_boundary_expected_failures_retained": 3, "new_boundary_cases_pass": 16,
        "unchanged_producer_methods_pass": 26, "snapshot_mutations": 307,
        "unchanged_stdio_cases_pass": 57, "stdio_healthy_zero_cases": 5, "stdio_unresolved_cases": 52,
        "all_owned_children_terminal_reaped": all(row["terminal_reaped"] for row in records),
        "owned_scratch_empty": True, "original142_lifecycle_cases_not_replayed": "Unchanged retained-wrapper lifecycle; original659 packet retains their passing evidence. New checks cover changed read boundary, unchanged26 composition suite and unchanged57 stdio ownership/cleanup cases including actual fixed children.",
        "source_limits_unchanged": {"max_read_attempts": 32, "max_bytes_per_parent_log_read": 512},
        "canonical_real_Rust_provenance_context_native_OTA_GA_accepted": False})
    print(json.dumps({"commands": len(records), "new_boundary_pass": 16, "old_required_failures": 3,
                      "producer_methods": 26, "stdio_cases": 57, "cleanup": "terminally-reaped/scratch-empty"}))


if __name__ == "__main__":
    main()
