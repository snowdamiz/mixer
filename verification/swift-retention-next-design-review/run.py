#!/usr/bin/env python3
"""Record fresh bounded review runs, preserving all attempts and exact streams."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACKET = ROOT / "verification/swift-retention-next-design"


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def load(path):
    return json.loads(path.read_bytes())


def closure():
    expected = load(ROOT / "verification/swift-cost-retention-candidate/live-baseline-source-manifest.json")
    actual = {name: sha((ROOT / "vm" / name).read_bytes()) for name in expected}
    assert len(actual) == 132 and actual == expected
    digest = sha((json.dumps(actual, indent=2, sort_keys=True) + "\n").encode())
    assert digest == "16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd"
    return {"files": 132, "digest": digest, "members": actual}


def sources():
    # A fixed narrow dependency list. No repository-wide discovery or hosted
    # harness sources. Historical other-lane scripts are bound/read, not run.
    paths = {ROOT / member["path"] for member in load(PACKET / "seal.json")["members"]}
    paths |= {PACKET / "seal.json", PACKET / "seal.sha256", HERE / "checks.py", HERE / "run.py"}
    paths |= {ROOT / name for name in (
        "AGENTS.md", "PLAN.md", "mixer-product-plan.md",
        "vm/src/experimental/cache/borrowed.rs", "vm/src/experimental/cache/mod.rs",
        "vm/src/experimental_swift_reactor/cache.rs",
        "verification/swift-cost-retention-candidate/live-baseline-source-manifest.json",
        "verification/swift-cost-retention-candidate/common-tests.rs",
        "verification/swift-cost-retention-candidate/seal.json",
        "verification/swift-cost-retention-candidate/seal.sha256",
        "verification/swift-cost-retention-candidate/result-summary.json",
        "verification/swift-cost-retention-candidate/commands/baseline-final-swift/stdout",
        "verification/swift-cost-retention-candidate/commands/candidate-expanded-2/stdout",
        "verification/swift-adaptive-retention-design/seal.json",
        "verification/swift-adaptive-retention-design/stdout.json",
        "verification/swift-current-attribution-runtime/result-summary.json",
        "verification/swift-current-attribution-runtime/result-seal.json",
        "verification/swift-current-attribution-runtime/target-once-events.json",
        "verification/swift-current-attribution-runtime/target-once-telemetry.json",
        "verification/swift-retention-runtime/seal.json",
        "verification/swift-retention-runtime/result-summary.json",
        "verification/swift-retention-runtime/target-once-events.json",
        "verification/swift-retention-runtime/target-once-result.json",
    )}
    # The rerun of the sealed producer's 24 finite host tests hashes the whole
    # adaptive packet as data; bind those exact inputs before it starts.
    paths |= {ROOT / member["path"] for member in load(ROOT / "verification/swift-adaptive-retention-design/seal.json")["members"]}
    return [{"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha(path.read_bytes())}
            for path in sorted(paths)]


def run(kind, attempt_name):
    assert kind in ("independent", "producer-regression")
    assert attempt_name.replace("-", "").isalnum()
    attempt = HERE / attempt_name
    attempt.mkdir()
    before = sources()
    before_closure = closure()
    write(attempt / "inputs.json", before)
    write(attempt / "live-source-closure.json", before_closure)
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()
    temporary = Path(tempfile.mkdtemp(prefix="mixer-swift-retention-next-review-"))
    identity = temporary.stat()
    target = HERE / "checks.py" if kind == "independent" else PACKET / "test_model.py"
    argv = [sys.executable, "-B", str(target)]
    write(attempt / "command.json", {
        "argv": argv, "cwd": str(ROOT), "kind": kind, "source_revision": revision,
        "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "python_executable": sys.executable, "python_executable_sha256": sha(Path(sys.executable).resolve().read_bytes()),
        "python_version": sys.version, "machine": platform.machine(), "platform": platform.platform(),
        "environment_overrides": {"PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(temporary)},
        "owned_temporary_path": str(temporary), "owned_temporary_identity": {"device": identity.st_dev, "inode": identity.st_ino},
        "producer_seal_sha256": sha((PACKET / "seal.json").read_bytes()),
        "scope": "Synchronous finite Python host review only; no compiler, VM, target, UI/capture, process discovery, native or service runtime",
    })
    completed = None
    exception = None
    try:
        completed = subprocess.run(argv, cwd=ROOT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", TMPDIR=str(temporary)),
                                   capture_output=True, timeout=45)
        (attempt / "stdout").write_bytes(completed.stdout)
        (attempt / "stderr").write_bytes(completed.stderr)
    except BaseException as error:
        exception = {"type": type(error).__name__, "message": str(error)}
        (attempt / "stdout").write_bytes(getattr(error, "stdout", None) or b"")
        (attempt / "stderr").write_bytes(getattr(error, "stderr", None) or b"")
    finally:
        current = temporary.stat()
        assert (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino)
        descendants = list(temporary.rglob("*"))
        assert all(not path.is_symlink() for path in descendants)
        removed = {"regular_files": sum(path.is_file() for path in descendants),
                   "logical_bytes": sum(path.stat().st_size for path in descendants if path.is_file()),
                   "directories_including_root": 1 + sum(path.is_dir() for path in descendants)}
        shutil.rmtree(temporary)
        write(attempt / "cleanup.json", {"owned_temporary_path": str(temporary), "identity_unchanged": True,
              "removed": removed, "absent_after_cleanup": not temporary.exists(), "signals_sent": [],
              "process_discovery": False, "scope": "Only synchronous Python child; -B prevents bytecode products; all owned scratch removed on success/failure"})
    after = sources()
    after_closure = closure()
    changed = [{"path": old["path"], "before": old, "after": new} for old, new in zip(before, after) if old != new]
    write(attempt / "result.json", {
        "exit_code": None if completed is None else completed.returncode, "exception": exception,
        "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "stdout_sha256": sha((attempt / "stdout").read_bytes()), "stderr_sha256": sha((attempt / "stderr").read_bytes()),
        "all_inputs_unchanged": before == after, "input_changes": changed,
        "ordinary_live_source_closure_unchanged": before_closure == after_closure,
        "historical_plan_bound_separately": True,
        "source_revision_before": revision,
        "source_revision_after": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip(),
        "selection": "withheld-no-implementation-no-integration-no-full-target",
    })
    assert completed is not None and completed.returncode == 0 and exception is None
    assert all(change["path"] == "PLAN.md" for change in changed), changed
    assert before_closure == after_closure
    print(json.dumps({"attempt": attempt_name, "exit_code": completed.returncode, "inputs_unchanged": before == after,
                      "live_source_closure_unchanged": True, "owned_temporary_absent": not temporary.exists()}, sort_keys=True))


if __name__ == "__main__":
    for path in (HERE / "checks.py", HERE / "run.py"):
        ast.parse(path.read_text(), filename=str(path))
    assert len(sys.argv) == 3
    run(*sys.argv[1:])
