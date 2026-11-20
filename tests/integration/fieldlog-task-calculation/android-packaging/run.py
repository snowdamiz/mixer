"""Run one bounded build stage and retain its terminal custody result."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

SCRATCH_LIMIT_KIB = 6 * 1024 * 1024
# Stop before the limit to leave room for files still being written.
SCRATCH_STOP_KIB = 5 * 1024 * 1024


def now():
    return datetime.now(timezone.utc).isoformat()


def size_kib(*roots):
    for attempt in range(3):
        sample = subprocess.run(["/usr/bin/du", "-sk", *roots], text=True, capture_output=True,
                                timeout=10, env=os.environ | {"LC_ALL": "C"})
        if sample.returncode == 0:
            return sum(int(line.split(maxsplit=1)[0]) for line in sample.stdout.splitlines())
        errors = sample.stderr.splitlines()
        # The compiler can rename an intermediate between du's enumeration and stat.
        if (attempt == 2 or not errors or not all(Path(root).is_dir() for root in roots)
                or not all(line.endswith(": No such file or directory") for line in errors)):
            sample.check_returncode()


def group_absent(pid):
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


def main():
    work, output, label, seconds, *command = sys.argv[1:]
    receipt = Path(work) / "logs" / f"{label}.json"
    log = receipt.with_suffix(".log")
    result = {
        "argv": command, "startedUTC": now(), "timeoutSeconds": int(seconds),
        "custody": "UNKNOWN", "peakSampledScratchKiB": size_kib(work, output),
    }

    def save():
        pending = receipt.with_suffix(".new")
        pending.write_text(json.dumps(result, indent=2) + "\n")
        pending.replace(receipt)

    with log.open("xb") as stream:
        save()
        deadline = time.monotonic() + int(seconds)
        child = None
        try:
            child = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            result["pid"] = child.pid
            save()
            while child.poll() is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise RuntimeError("Stage timed out")
                try:
                    child.wait(timeout=min(2, remaining))
                except subprocess.TimeoutExpired:
                    result["peakSampledScratchKiB"] = max(result["peakSampledScratchKiB"], size_kib(work, output))
                    if result["peakSampledScratchKiB"] >= SCRATCH_STOP_KIB:
                        raise RuntimeError("Scratch exceeded the stop threshold")
        except BaseException as error:
            result["interrupted"] = f"{type(error).__name__}: {error}"
        finally:
            result["exit"] = None
            if child is not None:
                collect(child, result)
        # Persist terminal observations even when the final size sample fails.
        if result["custody"] == "closed":
            try:
                result["peakSampledScratchKiB"] = max(result["peakSampledScratchKiB"], size_kib(work, output))
            except Exception as error:
                result["scratchSampleError"] = f"{type(error).__name__}: {error}"
        if result["peakSampledScratchKiB"] >= SCRATCH_LIMIT_KIB:
            result["scratchLimitExceeded"] = True
        result["endedUTC"] = now()
        try:
            save()
        except OSError as error:
            print(f"{label}: terminal receipt write failed: {error}; observed "
                  f"pid={result.get('pid')} exit={result['exit']} custody={result['custody']}", file=sys.stderr)
            return 1
    print(label, result["exit"], result["custody"], flush=True)
    return int(result["exit"] != 0 or result["custody"] != "closed"
               or any(key in result for key in ("interrupted", "collectionErrors", "scratchSampleError",
                                                 "scratchLimitExceeded")))


def collect(child, result):
    errors = []
    if "interrupted" in result:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError as error:
            errors.append(f"signal: {error}")
        try:
            child.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired) as error:
            errors.append(f"wait: {error}")
    result["exit"] = child.returncode
    if child.returncode is not None:
        try:
            for _ in range(21):
                if group_absent(child.pid):
                    result["custody"] = "closed"
                    break
                time.sleep(.05)
        except OSError as error:
            errors.append(f"observe group: {error}")
    if errors:
        result["collectionErrors"] = errors


if __name__ == "__main__":
    sys.exit(main())
