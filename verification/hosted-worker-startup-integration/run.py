#!/usr/bin/env python3
"""Record immutable isolated startup attempts, using only explicit safe inputs."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def main():
    attempt = BASE / "attempts" / datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    attempt.mkdir(parents=True)
    files = sorted(p for folder in ["candidate", "context", "transport", "locked"] for p in (BASE / folder).rglob("*") if p.is_file())
    files += [BASE / name for name in ["compile_and_test.exs", "startup_test.exs", "run.py", "bind_inputs.py", "upstream-binding.json"]]
    rows = [{"path": str(p.relative_to(ROOT)), "sha256": sha(p), "size": p.stat().st_size} for p in sorted(files)]
    save(attempt / "source-map.json", rows)
    elixir = shutil.which("elixir")
    args = [elixir, "--erl", "+S 2:2 +SDcpu 1 +SDio 1"]
    for dep in ["mint", "jason", "hpax"]:
        args += ["-pa", str(BASE / "locked/hosted/_build/test/lib" / dep / "ebin")]
    args += [str(BASE / "compile_and_test.exs")]
    env = {"PATH": os.environ["PATH"], "LANG": "C.UTF-8", "ERL_CRASH_DUMP": "/dev/null", "ERL_CRASH_DUMP_SECONDS": "0"}
    start = time.monotonic()
    process = subprocess.Popen(args, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    timed_out = False
    try:
        out, err = process.communicate(timeout=45)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGKILL)
        out, err = process.communicate()
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    (attempt / "stdout.log").write_bytes(out)
    (attempt / "stderr.log").write_bytes(err)
    unchanged = all(sha(ROOT / row["path"]) == row["sha256"] for row in rows)
    version = subprocess.run([elixir, "--version"], capture_output=True, env=env, timeout=10, check=True)
    (attempt / "tool-version.log").write_bytes(version.stdout + version.stderr)
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, timeout=10, check=True).stdout.decode().strip()
    result = None
    if process.returncode == 0:
        result = json.loads(out.splitlines()[-1])
    passed = process.returncode == 0 and unchanged and result is not None and result["tests"] == 16 and all(result[k] == 0 for k in ["failures", "skipped", "excluded"])
    shutil.rmtree(BASE / "build", ignore_errors=True)
    receipt = {"schema": 1, "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "sourceRevision": revision, "command": args, "cwd": str(ROOT), "toolVersion": version.stdout.decode().strip(),
        "durationMS": round((time.monotonic()-start)*1000), "exitCode": process.returncode, "timedOut": timed_out,
        "sourceInputs": len(rows), "sourceMapSHA256": sha(attempt / "source-map.json"), "inputsUnchanged": unchanged,
        "stdoutSHA256": sha(attempt / "stdout.log"), "stderrSHA256": sha(attempt / "stderr.log"),
        "result": result, "cleanup": {"ownedCommandGroupDisposed": True, "buildDirectoryRemoved": not (BASE / "build").exists()},
        "liveHostedFilesChanged": False, "fullApplicationAccepted": False,
        "status": "isolated-startup-candidate-passed-review-and-complete-app-integration-pending" if passed else "attempt-failed"}
    save(attempt / "receipt.json", receipt)
    print(json.dumps({"attempt": str(attempt.relative_to(ROOT)), "status": receipt["status"], "result": result}))
    sys.exit(0 if passed else 1)

if __name__ == "__main__":
    main()
