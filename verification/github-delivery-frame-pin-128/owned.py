"""Bounded commands owned by this delivery; never inspect unrelated processes."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]


def now():
    return datetime.now(timezone.utc).isoformat()


def save(name, value):
    with (OUT / name).open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def row(path):
    assert path.is_file() and not path.is_symlink(), path
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


class Commands:
    def __init__(self, seconds, prefix=""):
        self.deadline = time.monotonic() + seconds
        self.records = []
        self.prefix = prefix

    def run(self, name, argv, cap=30):
        name = self.prefix + name
        if argv[0] == "git":
            argv = ["git", "-c", "gc.auto=0", "-c", "maintenance.auto=false", *argv[1:]]
        remaining = self.deadline - time.monotonic()
        assert remaining > 8, "aggregate deadline before " + name
        start = time.monotonic()
        timed = False
        with (OUT / (name + ".stdout")).open("xb") as out, (OUT / (name + ".stderr")).open("xb") as err:
            child = subprocess.Popen(argv, cwd=ROOT, stdout=out, stderr=err, start_new_session=True)
            save(name + ".started.json", {"at": now(), "argv": argv, "owned_pid": child.pid,
                 "owned_pgid": child.pid, "timeout_seconds": min(cap, remaining - 7)})
            try:
                child.wait(timeout=min(cap, remaining - 7))
            except subprocess.TimeoutExpired:
                timed = True
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=2)
        try:
            os.killpg(child.pid, 0)
            absent = False
        except ProcessLookupError:
            absent = True
        result = {"argv": argv, "exit": child.returncode, "timed_out": timed,
                  "elapsed_seconds": time.monotonic() - start, "owned_pid": child.pid,
                  "owned_pgid": child.pid, "direct_child_reaped": True, "owned_group_absent": absent,
                  "stdout": row(OUT / (name + ".stdout")), "stderr": row(OUT / (name + ".stderr"))}
        save(name + ".command.json", result)
        self.records.append({"name": name, "exit": child.returncode, "timed_out": timed,
                             "direct_child_reaped": True, "owned_group_absent": absent})
        assert not timed and absent and child.returncode == 0, name
        return (OUT / (name + ".stdout")).read_bytes()
