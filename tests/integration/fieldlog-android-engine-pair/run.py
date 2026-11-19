#!/usr/bin/env python3
"""Build and verify one private FieldLog Android engine upgrade pair."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

RECIPE = Path(__file__).resolve().parent
REPO = RECIPE.parents[2]
GIB = 1024 ** 3
# Cancel slightly early to leave room for writes during process shutdown.
STOP_FREE = 7 * GIB + 256 * 1024 ** 2


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


class Custody:
    # This is the cleanup authority. Receipts may fail to reach disk.
    pending = None


def recipe_env(campaign):
    # Shell startup files and imported functions can restore the stripped Git overrides.
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("GIT_", "BASH_FUNC_")) and key not in {"BASH_ENV", "ENV"}}
    return env | {
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
        "TMPDIR": str(campaign / "scratch/tmp"),
        # Git looks up global attributes independently of GIT_CONFIG_GLOBAL.
        "XDG_CONFIG_HOME": str(campaign / "scratch/xdg-config"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def origin_closed(campaign):
    result = campaign / "handoff/origin-result.json"
    if not result.is_file() or any((campaign / "scratch").glob("fieldlog-cohort-origin-*.service-custody.json")):
        return False
    receipt = json.loads(result.read_bytes())
    return isinstance(receipt, dict) and receipt.get("workRemoved") is True


def run(campaign, custody, name, argv, seconds, *, cwd=None):
    if custody.pending is not None:
        raise RuntimeError(f"terminal custody unresolved for {custody.pending}")
    free = shutil.disk_usage(campaign).free
    if free < STOP_FREE:
        raise RuntimeError(f"{name} blocked by disk reserve ({free} free bytes)")
    row = {"command": [str(arg) for arg in argv], "minimumFreeBytes": free}
    log_path = campaign / f"{name}.log"
    result_path = campaign / f"{name}.json"
    hold_path = campaign / "HOLD.json"
    print(f"{name}: {log_path}", flush=True)
    with log_path.open("x") as log:
        custody.pending = name
        try:
            child = subprocess.Popen(argv, cwd=cwd or campaign, env=recipe_env(campaign),
                                     stdout=log, stderr=log, start_new_session=True)
        except BaseException:
            write(hold_path, row | {"stage": name, "reason": "launch identity unobserved"})
            raise
        try:
            row.update(pid=child.pid, pgid=child.pid)
            deadline = time.monotonic() + seconds
            while child.poll() is None:
                free = shutil.disk_usage(campaign).free
                row["minimumFreeBytes"] = min(free, row["minimumFreeBytes"])
                if free < STOP_FREE or time.monotonic() >= deadline:
                    raise RuntimeError(f"{name} stopped at the disk reserve or deadline ({free} free bytes)")
                time.sleep(0.25)
        except BaseException:
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            except OSError as error:
                row["stopError"] = str(error)
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            raise
        finally:
            row["exit"] = child.poll()
            try:
                os.killpg(child.pid, 0)
            except ProcessLookupError:
                row["ownedGroupAbsent"] = row["exit"] is not None
            except OSError as error:
                row["observationError"] = str(error)
            closed = row.get("ownedGroupAbsent") is True
            if closed and name == "origin":
                try:
                    closed = origin_closed(campaign)
                except (OSError, ValueError) as error:
                    closed = False
                    row["nestedObservationError"] = str(error)
            if closed:
                custody.pending = None
            else:
                write(hold_path, row | {"stage": name, "reason": "terminal custody unconfirmed"})
            write(result_path, row)
    if hold_path.exists() or row["exit"]:
        raise RuntimeError(f"{name} failed, see {log_path}")


BUILD_PHASES = (("native", 1100), ("guests", 90), ("tools", 500), ("package", 230))


def seal(campaign, custody):
    handoff = campaign / "handoff"
    for name in ("prepare", *(phase for phase, _ in BUILD_PHASES), "origin"):
        shutil.copyfile(campaign / f"{name}.json", handoff / f"{name}-command.json")
    shutil.copyfile(RECIPE / "replay/ROOT-RUN.md", handoff / "ROOT-RUN.md")
    with (handoff / "SHA256SUMS").open("x") as sums:
        for path in sorted(handoff.rglob("*")):
            if path.is_file() and path != handoff / "SHA256SUMS":
                with path.open("rb") as source:
                    digest = hashlib.file_digest(source, "sha256").hexdigest()
                sums.write(f"{digest}  {path.relative_to(handoff)}\n")
    run(campaign, custody, "seal", ["shasum", "-a", "256", "-c", "SHA256SUMS"], 60, cwd=handoff)
    print(f"Sealed handoff in {handoff}", flush=True)


def main():
    os.umask(0o077)
    parent = REPO / "verification/local"
    if shutil.disk_usage(REPO).free < 12 * GIB:
        raise RuntimeError("FieldLog engine pair requires at least 12 GiB free at admission")
    parent.mkdir(parents=True, exist_ok=True)
    campaign = Path(tempfile.mkdtemp(dir=parent, prefix="fieldlog-android-engine-pair."))
    print(campaign, flush=True)
    (campaign / "scratch/tmp").mkdir(parents=True)
    sealed = False
    custody = Custody()
    try:
        run(campaign, custody, "prepare", ["/bin/bash", RECIPE / "replay/prepare.sh", RECIPE, REPO, campaign], 180)
        for phase, seconds in BUILD_PHASES:
            run(campaign, custody, phase, [sys.executable, "-B", RECIPE / "replay/toolchain.py", campaign,
                                           "/bin/bash", RECIPE / "replay/build.sh", RECIPE, campaign, phase], seconds)
        run(campaign, custody, "origin", [sys.executable, "-B", campaign / "handoff/replay/origin.py", "verify",
                                "--work-parent", campaign / "scratch",
                                "--result", campaign / "handoff/origin-result.json"], 120)
        seal(campaign, custody)
        sealed = True
    finally:
        if custody.pending is not None:
            print(f"Retaining {campaign}: terminal custody unresolved for {custody.pending}", file=sys.stderr)
        else:
            shutil.rmtree(campaign / "scratch")
            if sealed:
                for path in (*campaign.glob("*.log"), *campaign.glob("*.json")):
                    path.unlink()
            elif (campaign / "handoff").exists():
                shutil.rmtree(campaign / "handoff")


if __name__ == "__main__":
    main()
