"""Owned, bounded pure-Python offline command recorder. Never launches Rust."""
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
name, script = sys.argv[1:]
assert name.replace("-", "").isalnum() and Path(script).name == script and script.endswith(".py")
OUT = HERE / "commands" / name
OUT.mkdir(parents=True, exist_ok=False)
environment = {"PATH": "/opt/homebrew/bin:/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "TZ": "UTC", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0"}
argv = [sys.executable, "-B", str(HERE / script)]
tool_hash = hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()
script_raw = (HERE / script).read_bytes()
(OUT / script).write_bytes(script_raw)
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
t0 = time.monotonic()
with (OUT / "stdout").open("wb") as stdout, (OUT / "stderr").open("wb") as stderr:
    proc = subprocess.Popen(argv, cwd=ROOT, env=environment, stdout=stdout, stderr=stderr, start_new_session=True)
    pgid = os.getpgid(proc.pid)
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
receipt = {"schema": 1, "status": "passed" if code == 0 and not timed_out and group_absent else "failed", "started_at": started, "seconds": time.monotonic()-t0, "deadline_seconds": 55, "argv": argv, "cwd": str(ROOT), "environment": environment, "tool": {"path": sys.executable, "version": sys.version, "sha256": tool_hash}, "script_sha256": hashlib.sha256(script_raw).hexdigest(), "pid": proc.pid, "pgid": pgid, "waited": True, "exit_code": code, "timed_out": timed_out, "owned_process_group_absent": group_absent, "compiler_test_binary_native_UI_or_Git_execution": False}
for output in ("stdout", "stderr"):
    data = (OUT / output).read_bytes()
    receipt[output] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    assert len(data) <= 4194304
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True)+"\n")
print(json.dumps(receipt, sort_keys=True))
raise SystemExit(0 if receipt["status"] == "passed" else 1)
