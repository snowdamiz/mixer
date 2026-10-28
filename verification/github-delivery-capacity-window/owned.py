"""Fresh bounded Git/gh custody for this one delivery; no inventory probes."""
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
    def __init__(self, seconds, count, prefix):
        self.deadline = time.monotonic() + seconds
        self.maximum = count
        self.prefix = prefix
        self.records = []

    def run(self, name, argv, seconds=30):
        assert len(self.records) < self.maximum, "finite owned command count"
        assert argv[0] in ("git", "gh"), "only selected delivery tools"
        if argv[0] == "git":
            argv = ["git", "-c", "gc.auto=0", "-c", "maintenance.auto=false", *argv[1:]]
        label = self.prefix + name
        remaining = self.deadline - time.monotonic()
        assert remaining > 10, "aggregate command deadline"
        started = time.monotonic()
        child = subprocess.Popen(argv, cwd=ROOT, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 start_new_session=True)
        save(label + ".started.json", {"at": now(), "argv": argv,
             "ownedPID": child.pid, "ownedPGID": child.pid,
             "timeoutSeconds": min(seconds, remaining - 8)})
        timed_out = False
        try:
            stdout, stderr = child.communicate(timeout=min(seconds, remaining - 8))
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(child.pid, signal.SIGTERM)
            try:
                stdout, stderr = child.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                stdout, stderr = child.communicate(timeout=2)
        try:
            os.killpg(child.pid, 0)
            group_absent = False
        except ProcessLookupError:
            group_absent = True
        assert len(stdout) + len(stderr) <= 2 * 1024 * 1024, "delivery output cap"
        for suffix, data in (("stdout", stdout), ("stderr", stderr)):
            with (OUT / (label + "." + suffix)).open("xb") as stream:
                stream.write(data)
        result = {"at": now(), "argv": argv, "exit": child.returncode,
                  "timedOut": timed_out, "elapsedSeconds": time.monotonic() - started,
                  "ownedPID": child.pid, "ownedPGID": child.pid,
                  "directChildReaped": child.returncode is not None,
                  "ownedGroupAbsent": group_absent,
                  "stdoutEOF": True, "stderrEOF": True,
                  "stdout": row(OUT / (label + ".stdout")),
                  "stderr": row(OUT / (label + ".stderr"))}
        save(label + ".command.json", result)
        self.records.append({"name": label, **{k: result[k] for k in
            ("exit", "timedOut", "directChildReaped", "ownedGroupAbsent", "stdoutEOF", "stderrEOF")}})
        assert not timed_out and group_absent and child.returncode == 0, label
        return stdout
