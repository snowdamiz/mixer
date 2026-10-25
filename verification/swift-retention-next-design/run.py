#!/usr/bin/env python3
"""Bounded host evidence runner; never launches a VM/compiler/native process."""
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
INPUTS = [
    "AGENTS.md", "PLAN.md", "docs/swift-adaptive-retention-design.md",
    "docs/swift-cost-retention-candidate-review.md", "docs/swift-cost-retention-candidate.md",
    "docs/swift-retention-runtime.md", "docs/swift-decode-plan-integration.md",
    "docs/swift-current-attribution-runtime.md", "docs/swift-cache-work-attribution.md",
    "docs/swift-exact-reactor-after-plan-reuse-result.md",
    "vm/src/experimental/cache/mod.rs", "vm/src/experimental/cache/borrowed.rs",
    "vm/src/experimental_swift_reactor/cache.rs",
    "verification/swift-cost-retention-candidate/common-tests.rs",
    "verification/swift-cost-retention-candidate/seal.json",
    "verification/swift-cost-retention-candidate/seal.sha256",
    "verification/swift-cost-retention-candidate/live-baseline-source-manifest.json",
    "verification/swift-cost-retention-candidate/result-summary.json",
    "verification/swift-cost-retention-candidate/commands/baseline-final-swift/stdout",
    "verification/swift-cost-retention-candidate/commands/candidate-expanded-2/stdout",
    "verification/swift-cost-retention-candidate-review/stdout.json",
    "verification/swift-cost-retention-candidate-review/result.json",
    "verification/swift-cost-retention-candidate-review/seal.json",
    "verification/swift-adaptive-retention-design/model.py",
    "verification/swift-adaptive-retention-design/stdout.json",
    "verification/swift-adaptive-retention-design/receipt.json",
    "verification/swift-adaptive-retention-design/seal.json",
    "verification/swift-retention-runtime/result-summary.json",
    "verification/swift-retention-runtime/seal.json",
    "verification/swift-retention-runtime/target-once-events.json",
    "verification/swift-retention-runtime/target-once-result.json",
    "verification/swift-current-attribution-runtime/result-summary.json",
    "verification/swift-current-attribution-runtime/result-seal.json",
    "verification/swift-current-attribution-runtime/target-once-events.json",
    "verification/swift-current-attribution-runtime/target-once-telemetry.json",
    "verification/swift-decode-plan-root-integration/receipt.json",
    "verification/swift-decode-plan-root-integration/acceptance.json",
    "verification/swift-decode-plan-root-integration/live-source-manifest.json",
    "verification/swift-decode-plan-root-integration/live-swift-library.stdout",
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(data):
    return (json.dumps(data, indent=2, sort_keys=True) + "\n").encode()


def manifest(paths):
    return [{"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size,
             "sha256": sha(p.read_bytes())} for p in sorted(paths)]


def write(path, data):
    path.write_bytes(canonical(data))


def source_closure():
    # Hash only the ordinary baseline's already specified member names. Never
    # enumerate/import excluded frozen hosted or rejected WorkerV2 directories.
    expected = json.loads((ROOT / "verification/swift-cost-retention-candidate/live-baseline-source-manifest.json").read_bytes())
    actual = {name: sha((ROOT / "vm" / name).read_bytes()) for name in expected}
    assert len(actual) == 132 and actual == expected
    digest = sha(canonical(actual))
    assert digest == "16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd"
    return {"files": len(actual), "digest": digest}


def main():
    assert len(sys.argv) == 3 and sys.argv[1] in ("model", "tests")
    kind, name = sys.argv[1:]
    assert name.replace("-", "").isalnum()
    attempt = HERE / name
    attempt.mkdir()  # an existing attempt is immutable; no accidental overwrite
    owned_paths = [HERE / "contract.json", HERE / "model.py", HERE / "run.py"]
    if kind == "tests":
        owned_paths.append(HERE / "test_model.py")
    before = manifest([ROOT / p for p in INPUTS] + owned_paths)
    write(attempt / "inputs.json", before)
    closure_before = source_closure()
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    temporary = Path(tempfile.mkdtemp(prefix="mixer-swift-retention-next-design-"))
    identity = temporary.stat()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", TMPDIR=str(temporary))
    argv = [sys.executable, "-B", str(HERE / ("model.py" if kind == "model" else "test_model.py"))]
    write(attempt / "command.json", {"argv": argv, "cwd": str(ROOT), "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "temporary": str(temporary), "temporary_device": identity.st_dev, "temporary_inode": identity.st_ino,
          "environment_overrides": {"PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(temporary)},
          "source_revision": revision, "source_closure": closure_before,
          "python_version": sys.version, "python_executable": sys.executable,
          "python_executable_sha256": sha(Path(sys.executable).resolve().read_bytes()),
          "platform": platform.platform(), "machine": platform.machine(),
          "contract_sha256_before_execution": sha((HERE / "contract.json").read_bytes())})
    completed = None
    try:
        completed = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, timeout=45)
        (attempt / "stdout").write_bytes(completed.stdout)
        (attempt / "stderr").write_bytes(completed.stderr)
    finally:
        current = temporary.stat()
        assert (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino)
        files = list(temporary.rglob("*"))
        assert all(not p.is_symlink() for p in files)
        removed = {"regular_files": sum(p.is_file() for p in files), "logical_bytes": sum(p.stat().st_size for p in files if p.is_file()),
                   "directories_including_root": 1 + sum(p.is_dir() for p in files)}
        shutil.rmtree(temporary)
        write(attempt / "cleanup.json", {"owned_temporary_path": str(temporary), "identity_unchanged": True,
              "removed": removed, "absent_after_cleanup": not temporary.exists(), "signals_sent": [],
              "scope": "Synchronous finite Python child completed; no owned native/compiler/VM/capture runtime or background process was started. No process discovery."})
    after = manifest([ROOT / p for p in INPUTS] + owned_paths)
    closure_after = source_closure()
    write(attempt / "result.json", {"exit_code": completed.returncode, "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "stdout_sha256": sha(completed.stdout), "stderr_sha256": sha(completed.stderr),
          "all_consulted_inputs_unchanged": before == after, "source_closure_unchanged": closure_before == closure_after,
          "scope": "Finite Python host model only. No product code or producer model imported/executed; no VM, guest, native, full target, external service or release qualification."})
    assert completed.returncode == 0 and before == after and closure_before == closure_after
    print(json.dumps({"attempt": name, "exit_code": completed.returncode, "stdout_sha256": sha(completed.stdout),
                      "consulted_inputs_unchanged": before == after, "temporary_removed": not temporary.exists()}, sort_keys=True))


if __name__ == "__main__":
    main()
