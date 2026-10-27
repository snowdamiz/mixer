"""Run one <=55s pure Python custody check in an exactly owned process group."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "commands" / "preparation-001"
OUT.mkdir(parents=True, exist_ok=False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def manifest():
    paths = [HERE / "check_preparation.py", HERE / "review-plan.json", HERE / "run_preparation.py"]
    for name in ("swift-guarded-snapshot-actual-owner-rust-selection", "swift-guarded-snapshot-actual-owner-rust-preaccess"):
        paths.extend(p for p in (ROOT / "verification" / name).rglob("*") if p.is_file())
    for name in ("guarded-snapshot-actual-owner-Rust-implementation-selection.json", "guarded-snapshot-actual-owner-Rust-contract-amendment.json", "guarded-snapshot-actual-owner-Rust-H09-H10-amendment.json"):
        paths.append(ROOT / "verification/swift-semantic-adapter-root-review" / name)
    return [{"path": str(p.relative_to(ROOT)), "bytes": len(p.read_bytes()), "sha256": sha(p.read_bytes())} for p in sorted(paths)]


before = manifest()
environment = {"PATH": "/opt/homebrew/bin:/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "TZ": "UTC", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0"}
argv = [sys.executable, "-B", str(HERE / "check_preparation.py")]
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
t0 = time.monotonic()
with (OUT / "stdout").open("wb") as stdout, (OUT / "stderr").open("wb") as stderr:
    proc = subprocess.Popen(argv, cwd=ROOT, env=environment, stdout=stdout, stderr=stderr, start_new_session=True)
    pid = proc.pid
    pgid = os.getpgid(pid)
    timed_out = False
    try:
        code = proc.wait(timeout=55)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(pgid, signal.SIGKILL)
        code = proc.wait(timeout=5)
try:
    os.killpg(pgid, 0)
    group_absent = False
except ProcessLookupError:
    group_absent = True
after = manifest()
receipt = {"schema": 1, "status": "passed" if code == 0 and not timed_out and group_absent and before == after else "failed", "started_at": started, "seconds": time.monotonic() - t0, "deadline_seconds": 55, "argv": argv, "cwd": str(ROOT), "environment": environment, "tool": {"path": sys.executable, "version": sys.version, "sha256": sha(Path(sys.executable).read_bytes())}, "source_revision_historical_selection": "9398732c23648a82097d5a72b02b1c77af818e41", "input_members": len(before), "input_tree_sha256": sha(json.dumps(before, sort_keys=True, separators=(",", ":")).encode()), "inputs_unchanged": before == after, "pid": pid, "pgid": pgid, "waited": True, "exit_code": code, "timed_out": timed_out, "owned_process_group_absent": group_absent, "compiler_test_binary_native_UI_or_Git_execution": False, "producer_source_accessed": False}
for name, value in (("input-before.json", before), ("input-after.json", after), ("receipt.json", receipt)):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
for name in ("stdout", "stderr"):
    raw = (OUT / name).read_bytes()
    assert len(raw) <= 4194304
    receipt[name] = {"bytes": len(raw), "sha256": sha(raw)}
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(json.dumps(receipt, sort_keys=True))
raise SystemExit(0 if receipt["status"] == "passed" else 1)
