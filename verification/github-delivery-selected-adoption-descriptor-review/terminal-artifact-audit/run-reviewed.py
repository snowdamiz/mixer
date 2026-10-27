"""Run one immutable, bounded data-audit phase; own and reap its process group."""
import datetime
import errno
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PHASES = {
    "terminal-collection": ("phases.py", "collect"),
    "core-jvm-audit": ("phases.py", "core-jvm"),
    "capability-collection": ("capability_review.py", "collect"),
    "capability-audit": ("capability_review.py", "audit"),
    "acceptance": ("phases.py", "accept"),
}


def digest(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def group_exists(pgid):
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    return True


assert __debug__ and len(sys.argv) == 2 and sys.argv[1] in PHASES
name = sys.argv[1]
assert not (HERE / "seal.json").exists()
assert not (HERE / (name + ".command.json")).exists(), "Each fresh phase is one-shot"
preparation = json.loads((HERE / "preparation.json").read_bytes())
for item in preparation["execution_scripts"]:
    assert digest((HERE / item["path"]).read_bytes()) == item["digest"]
if name != "terminal-collection":
    previous = list(PHASES)[list(PHASES).index(name) - 1]
    row = json.loads((HERE / (previous + ".command.json")).read_bytes())
    assert row["exit_code"] == 0 and not row["timed_out"]
    assert row["direct_child_reaped"] and row["owned_process_group_absent_after_reaping"]
script, action = PHASES[name]
argv = [sys.executable, "-B", str(HERE / script), action]
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
tick = time.monotonic()
child = subprocess.Popen(argv, cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
timed_out = False
signals_sent = []
try:
    stdout, stderr = child.communicate(timeout=60)
except subprocess.TimeoutExpired:
    timed_out = True
    try:
        os.killpg(child.pid, signal.SIGKILL)
        signals_sent.append("SIGKILL on owned phase process group")
    except ProcessLookupError:
        pass
    stdout, stderr = child.communicate(timeout=5)
direct_child_reaped = child.poll() is not None
group_absent = not group_exists(child.pid)
if not group_absent:
    os.killpg(child.pid, signal.SIGKILL)
    signals_sent.append("SIGKILL on remaining owned phase process group")
    # This is a scoped liveness probe of our own group, never a process inventory.
    until = time.monotonic() + 5
    while group_exists(child.pid) and time.monotonic() < until:
        time.sleep(0.02)
    group_absent = not group_exists(child.pid)
for stream, payload in (("stdout", stdout), ("stderr", stderr)):
    (HERE / (name + "." + stream)).write_bytes(payload)
record = {
    "started_utc": started,
    "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "elapsed_seconds": time.monotonic() - tick,
    "argv": argv, "cwd": str(REPO), "exit_code": child.returncode,
    "stdout": digest(stdout), "stderr": digest(stderr), "python": sys.version,
    "timed_out": timed_out, "child_timeout_seconds": 60,
    "direct_child_pid": child.pid, "owned_process_group": child.pid,
    "direct_child_reaped": direct_child_reaped,
    "owned_process_group_absent_after_reaping": group_absent,
    "cleanup_signals": signals_sent,
    "auditor_sources_verified_before_child": preparation["execution_scripts"],
    "scope": "One fresh read-only data audit phase; no artifact imports, execution or extraction; no CI retry or Git/network mutation",
    "process_inventory_queried": False,
}
(HERE / (name + ".command.json")).write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({k: record[k] for k in ("exit_code", "timed_out", "elapsed_seconds", "direct_child_reaped", "owned_process_group_absent_after_reaping")}))
if child.returncode != 0 or timed_out or not direct_child_reaped or not group_absent:
    raise SystemExit(1)
