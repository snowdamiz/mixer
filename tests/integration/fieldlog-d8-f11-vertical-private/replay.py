"""Run the F11 fixture with read-only inputs, offline, in a bounded process group."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent
TIME_LIMIT = 720
LIMIT_KIB = int(1.4 * 1024 * 1024)


def exists(pgid):
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    return True


def close_group(process):
    for kind in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(process.pid, kind)
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if process.poll() is not None and not exists(process.pid):
                return
            time.sleep(0.05)
    raise RuntimeError("Worker process group did not retire")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("stage", "fieldlog", "f04", "f11"):
        parser.add_argument(name, type=lambda path: Path(path).resolve(strict=True))
    args = parser.parse_args()
    started = time.monotonic()
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_ALLOW_PROTOCOL="file", GIT_NO_LAZY_FETCH="1", GIT_OPTIONAL_LOCKS="0",
               GIT_TERMINAL_PROMPT="0", GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null",
               CARGO_NET_OFFLINE="true", PYTHONDONTWRITEBYTECODE="1")
    protected = {args.stage, args.fieldlog, args.f04, args.f11, HERE}
    for repository in (args.stage, args.fieldlog):
        for flag in ("--absolute-git-dir", "--git-common-dir"):
            protected.add(Path(subprocess.check_output(
                ["git", "-C", repository, "rev-parse", "--path-format=absolute", flag],
                env=env, text=True, timeout=10).strip()).resolve())
    paths = " ".join(f"(subpath {json.dumps(str(path), ensure_ascii=False)})" for path in sorted(protected))
    profile = f"(version 1) (allow default) (deny network*) (deny file-write* {paths})"
    work = Path(tempfile.mkdtemp(prefix="f11-vertical-private-", dir="/private/tmp"))
    process = None
    peak = 0
    result = {}
    try:
        with (work / "result").open("xb") as out, (work / "log").open("xb") as log:
            process = subprocess.Popen(
                ["/usr/bin/sandbox-exec", "-p", profile, "/bin/bash", HERE / "worker.sh",
                 args.stage, args.fieldlog, args.f04, args.f11, work],
                cwd=work, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=log, start_new_session=True)
            while True:
                usage = subprocess.check_output(["/usr/bin/du", "-sk", work], text=True, timeout=4)
                peak = max(peak, int(usage.split()[0]))
                if peak > LIMIT_KIB or time.monotonic() - started >= TIME_LIMIT - 10:
                    raise RuntimeError(f"Resource bound reached at {peak} KiB")
                try:
                    status = process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    continue
                break
        if exists(process.pid):
            raise RuntimeError("Worker exited while its group was still present")
        if status:
            result["blocker"] = {
                "exit": status,
                "stage": (work / "phase").read_text().strip() if (work / "phase").exists() else "launch",
                "logTail": (work / "log").read_text(errors="replace")[-10000:],
            }
        else:
            result = json.loads((work / "result").read_bytes())
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        result["blocker"] = {"error": str(error)}
    finally:
        try:
            if process is not None and (process.poll() is None or exists(process.pid)):
                close_group(process)
        except (OSError, RuntimeError) as error:
            raise RuntimeError(f"Preserved {work} after unknown custody for PGID {process.pid}") from error
        shutil.rmtree(work)
    result["run"] = {
        "elapsedSeconds": round(time.monotonic() - started, 2),
        "maxSeconds": TIME_LIMIT,
        "sampledPeakKiB": peak,
        "maxKiB": LIMIT_KIB,
        "host": f"macOS {platform.mac_ver()[0]} {platform.machine()}",
        "scratchRemoved": not work.exists(),
        "workerGroupAbsent": process is None or not exists(process.pid),
        "network": "denied",
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return int("blocker" in result or result["run"]["elapsedSeconds"] > TIME_LIMIT)


if __name__ == "__main__":
    raise SystemExit(main())
