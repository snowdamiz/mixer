#!/usr/bin/env python3
"""Bounded offline command recorder for this independent host-only review."""
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
SOURCE = HERE / "source"
TARGET = HERE / "owned-target"
ENV = {key: os.environ[key] for key in ("HOME", "TMPDIR", "USER", "LOGNAME") if key in os.environ}
ENV.update(PATH="/opt/homebrew/opt/rustup/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin", RUSTUP_TOOLCHAIN="stable-aarch64-apple-darwin", CARGO_TARGET_DIR=str(TARGET), CARGO_INCREMENTAL="0", CARGO_NET_OFFLINE="true")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def manifest():
    return {str(path.relative_to(SOURCE)): sha(path) for path in sorted(SOURCE.rglob("*")) if path.is_file()}


def tools():
    info = {}
    for name, arguments in (("rustc", ["-vV"]), ("cargo", ["-V"])):
        actual = Path(subprocess.check_output(["rustup", "which", name], env=ENV, text=True).strip())
        info[name] = {"path": str(actual), "sha256": sha(actual), "version": subprocess.check_output([str(actual), *arguments], env=ENV, text=True).strip()}
    return info


if __name__ == "__main__":
    label, *argv = sys.argv[1:]
    assert argv
    commands = HERE / "commands"
    commands.mkdir(exist_ok=True)
    assert not (commands / (label + ".json")).exists()
    spent = sum(json.loads(path.read_text())["durationSeconds"] for path in commands.glob("*.json"))
    assert spent < 600
    ceiling = min(180, 600 - spent)
    before = manifest()
    row = {"argv": argv, "cwd": str(SOURCE), "environment": ENV, "tools": tools(), "sourceManifest": before, "sourceClosureSHA256": hashlib.sha256((json.dumps(before, indent=2, sort_keys=True) + "\n").encode()).hexdigest(), "sourceRevisionContext": json.loads((HERE / "source-review.json").read_text())["sourceRevisionContext"], "startedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(), "timeoutSeconds": ceiling, "priorCommandSeconds": spent}
    started = time.monotonic()
    child = subprocess.Popen(argv, cwd=SOURCE, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    row.update(pid=child.pid, processGroup=child.pid)
    try:
        stdout, stderr = child.communicate(timeout=ceiling)
        row["timedOut"] = False
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGTERM)
        try:
            stdout, stderr = child.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            stdout, stderr = child.communicate()
        row["timedOut"] = True
    row.update(exitCode=child.returncode, durationSeconds=time.monotonic() - started, finishedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(), sourceUnchanged=before == manifest(), postTools=tools())
    for suffix, data in (("stdout", stdout), ("stderr", stderr)):
        (commands / (label + "." + suffix)).write_bytes(data)
        row[suffix + "SHA256"] = hashlib.sha256(data).hexdigest()
    ps = subprocess.check_output(["/bin/ps", "-axo", "pid=,pgid=,command="], text=True)
    row["remainingProcessGroup"] = [line for line in ps.splitlines() if len(line.split(None, 2)) >= 2 and line.split(None, 2)[1] == str(child.pid)]
    save(commands / (label + ".json"), row)
    print(json.dumps({key: row[key] for key in ("exitCode", "durationSeconds", "timedOut", "sourceUnchanged", "remainingProcessGroup")}))
    print(stdout.decode(errors="replace")[-5000:])
    print(stderr.decode(errors="replace")[-5000:])
    sys.exit(0 if row["exitCode"] == 0 and not row["timedOut"] and row["sourceUnchanged"] and not row["remainingProcessGroup"] else 1)
