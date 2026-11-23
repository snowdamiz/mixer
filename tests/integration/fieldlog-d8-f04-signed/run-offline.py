"""Run the F04 replay with local inputs and bounded, owned scratch."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import time

TIME_LIMIT = 480
SCRATCH_LIMIT_KIB = 1_258_291
RECIPE = Path(__file__).resolve().parent


def git_path(repository, option, env):
    return Path(subprocess.check_output(
        ["git", "-C", repository, "rev-parse", "--path-format=absolute", option],
        env=env, text=True, timeout=10,
    ).strip()).resolve()


def group_exists(pgid):
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    return True


def stop_group(process):
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if process.poll() is not None and not group_exists(process.pid):
                return
            time.sleep(0.05)
    raise RuntimeError(f"Process group {process.pid} custody is unknown")


def scratch_kib(work):
    usage = subprocess.run(
        ["/usr/bin/du", "-sk", work], capture_output=True, text=True, timeout=4,
    )
    if not usage.stdout:
        raise RuntimeError(f"Cannot measure scratch use: {usage.stderr.strip()}")
    return int(usage.stdout.split()[0])


def replay(stage, fieldlog):
    start = time.monotonic()
    if sys.platform != "darwin" or platform.machine() != "arm64":
        raise RuntimeError("The pinned F04 replay requires arm64 macOS")

    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_ALLOW_PROTOCOL="file", GIT_NO_LAZY_FETCH="1", GIT_OPTIONAL_LOCKS="0",
               GIT_TERMINAL_PROMPT="0", GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null")
    read_only = {stage, fieldlog}
    for repository in (stage, fieldlog):
        read_only.add(git_path(repository, "--absolute-git-dir", env))
        read_only.add(git_path(repository, "--git-common-dir", env))
    paths = " ".join(f"(subpath {json.dumps(str(path), ensure_ascii=False)})"
                     for path in sorted(read_only))
    profile = f"(version 1) (allow default) (deny network*) (deny file-write* {paths})"

    work = Path(tempfile.mkdtemp(prefix="f04-task-retry-", dir="/private/tmp"))
    process = None
    peak_kib = 0
    try:
        with (work / "result.json").open("xb") as output:
            process = subprocess.Popen(
                ["/usr/bin/sandbox-exec", "-p", profile, RECIPE / "replay-private.sh",
                 "--worker", stage, fieldlog, work],
                cwd=work, env=env, stdin=subprocess.DEVNULL, stdout=output, start_new_session=True,
            )
            while True:
                peak_kib = max(peak_kib, scratch_kib(work))
                if peak_kib > SCRATCH_LIMIT_KIB:
                    raise RuntimeError(f"Replay scratch limit exceeded at {peak_kib} KiB")
                if time.monotonic() - start >= TIME_LIMIT - 10:
                    raise TimeoutError("Replay reached its deadline before cleanup")
                try:
                    status = process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    continue
                break
        if group_exists(process.pid):
            raise RuntimeError("Replay exited with a live process group")
        if status:
            raise RuntimeError(f"Replay worker exited with status {status}")
        peak_kib = max(peak_kib, scratch_kib(work))
        if peak_kib > SCRATCH_LIMIT_KIB:
            raise RuntimeError(f"Replay scratch limit exceeded at {peak_kib} KiB")
        raw = (work / "result.json").read_bytes()
        result = json.loads(raw)
    finally:
        try:
            if process is not None and (process.poll() is None or group_exists(process.pid)):
                stop_group(process)
        except (OSError, RuntimeError) as exc:
            raise RuntimeError(f"Preserved scratch {work} after unconfirmed process cleanup") from exc
        shutil.rmtree(work)

    elapsed = time.monotonic() - start
    if elapsed > TIME_LIMIT:
        raise TimeoutError("Replay and cleanup exceeded 480 seconds")
    result["run"] = {
        "wallSeconds": round(elapsed, 2),
        "timeLimitSeconds": TIME_LIMIT,
        "peakSampledScratchKiB": peak_kib,
        "scratchLimitKiB": SCRATCH_LIMIT_KIB,
        "networkPolicy": "sandbox-exec deny network*",
        "scratchRemoved": not work.exists(),
        "workerGroupReaped": True,
        "workerStdoutSHA256": hashlib.sha256(raw).hexdigest(),
        "host": f"macOS {platform.mac_ver()[0]} {platform.machine()}",
        "python": platform.python_version(),
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", type=Path, help="Local Mixer repository containing the pinned Stage revision")
    parser.add_argument("fieldlog", type=Path, help="Local FieldLog repository containing the pinned Pair25 base")
    args = parser.parse_args()
    print(json.dumps(replay(args.stage.resolve(strict=True), args.fieldlog.resolve(strict=True)), indent=2))


if __name__ == "__main__":
    main()
