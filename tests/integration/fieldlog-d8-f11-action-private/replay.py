"""Run the private action fixture with read-only inputs in an owned process group."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent
TIME_LIMIT = 720
DISK_LIMIT_KIB = 1_572_864


def allocated_kib(scratch):
    blocks = scratch.stat().st_blocks
    directories = [scratch]
    linked_files = set()
    while directories:
        try:
            with os.scandir(directories.pop()) as entries:
                for entry in entries:
                    try:
                        info = entry.stat(follow_symlinks=False)
                    except FileNotFoundError:
                        continue
                    if stat.S_ISDIR(info.st_mode):
                        directories.append(entry.path)
                    elif info.st_nlink > 1:
                        identity = (info.st_dev, info.st_ino)
                        if identity in linked_files:
                            continue
                        linked_files.add(identity)
                    blocks += info.st_blocks
        except FileNotFoundError:
            continue
    return (blocks + 1) // 2


def absent(pgid):
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return True
    return False


def retire(worker):
    for sig in (signal.SIGTERM, signal.SIGKILL):
        if worker.poll() is not None and absent(worker.pid):
            return
        try:
            os.killpg(worker.pid, sig)
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if worker.poll() is not None and absent(worker.pid):
                return
            time.sleep(0.05)
    raise RuntimeError("Worker group absence was not established")


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("stage", "fieldlog", "vertical"):
        parser.add_argument(name, type=lambda s: Path(s).resolve(strict=True))
    args = parser.parse_args()
    stage, fieldlog, vertical = args.stage, args.fieldlog, args.vertical
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_ALLOW_PROTOCOL="file", GIT_NO_LAZY_FETCH="1", GIT_OPTIONAL_LOCKS="0",
               GIT_TERMINAL_PROMPT="0", GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null",
               CARGO_NET_OFFLINE="true", PYTHONDONTWRITEBYTECODE="1")
    protected = {stage, fieldlog, vertical.parents[2], HERE}
    for repository in (stage, fieldlog):
        for flag in ("--absolute-git-dir", "--git-common-dir"):
            path = subprocess.check_output(
                ["git", "-C", repository, "rev-parse", "--path-format=absolute", flag],
                env=env, text=True, timeout=5).strip()
            protected.add(Path(path).resolve())
    paths = " ".join(f"(subpath {json.dumps(str(path))})" for path in sorted(protected))
    profile = f"(version 1) (allow default) (deny network*) (deny file-write* {paths})"
    scratch = Path(tempfile.mkdtemp(prefix="f11-host-actions-", dir="/private/tmp"))
    worker = None
    attempted = False
    peak = 0
    result = {}

    def interrupt(signum, _frame):
        raise RuntimeError(f"Replay interrupted by signal {signum}")

    signal.signal(signal.SIGTERM, interrupt)
    try:
        with (scratch / "output").open("xb") as out, (scratch / "log").open("xb") as log:
            attempted = True
            worker = subprocess.Popen(
                ["/usr/bin/sandbox-exec", "-p", profile, "/bin/bash", HERE / "worker.sh", stage, fieldlog,
                 scratch, vertical],
                cwd=scratch, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=log, start_new_session=True)
            while True:
                peak = max(peak, allocated_kib(scratch))
                if peak > DISK_LIMIT_KIB or time.monotonic() - started >= TIME_LIMIT - 10:
                    raise RuntimeError("Replay resource limit reached")
                try:
                    status = worker.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    continue
                break
        if not absent(worker.pid):
            raise RuntimeError("Worker exited while its group was still present")
        if status:
            with (scratch / "log").open("rb") as log:
                log.seek(max(0, os.fstat(log.fileno()).st_size - 6000))
                result["blocker"] = {
                    "exit": status, "phase": (scratch / "phase").read_text().strip()
                    if (scratch / "phase").exists() else "launch", "logTail": log.read().decode(errors="replace"),
                }
        else:
            result = json.loads((scratch / "output").read_bytes())
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError, KeyboardInterrupt) as exc:
        result["blocker"] = {"error": str(exc)}
    finally:
        try:
            if worker is not None:
                retire(worker)
            elif attempted:
                raise RuntimeError("Launch interrupted before recording a process identity")
        except (OSError, RuntimeError) as exc:
            result["hold"] = {"reason": str(exc), "scratch": str(scratch), "pgid": worker.pid if worker else None}
        else:
            shutil.rmtree(scratch)
    result["run"] = {"seconds": round(time.monotonic() - started, 2), "limitSeconds": TIME_LIMIT,
                     "peakAllocatedKiB": peak, "limitAllocatedKiB": DISK_LIMIT_KIB,
                     "workerGroupAbsent": "hold" not in result, "scratchRemoved": "hold" not in result,
                     "network": "denied"}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return int("blocker" in result or "hold" in result or result["run"]["seconds"] > TIME_LIMIT)


if __name__ == "__main__":
    raise SystemExit(main())
