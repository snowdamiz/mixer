#!/usr/bin/env python3
"""Build, sign, exercise and retire the checkout-local FieldLog host replay."""

import argparse
from datetime import datetime, timezone
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import tempfile
import time


def allocated_kib(path):
    blocks = path.stat().st_blocks
    directories = [path]
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


def main():
    here = Path(__file__).resolve().parent
    repo = here.parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--assembly", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True, help="New compact JSON output path")
    args = parser.parse_args()
    if args.receipt.exists():
        parser.error("choose a new receipt path")
    stage = args.stage.resolve(strict=True)
    assembly = args.assembly.resolve(strict=True)
    assembly_sha = hashlib.sha256(assembly.read_bytes()).hexdigest()
    if assembly_sha != "d438dc618a5284e4fb945bbb7adda63f3246ec10e1580cb8f026864706d2df10":
        parser.error("the assembly script differs from the verified D2 composite input")
    local = repo / "verification/local"
    local.mkdir(exist_ok=True)
    owned = Path(tempfile.mkdtemp(prefix="fieldlog-d2-signed-host-replay.", dir=local))
    log = owned / "command.log"
    argv = ["/bin/bash", str(here / "run.sh"), str(owned), str(stage), str(assembly)]
    start = time.monotonic()
    reason = None
    peak = 0
    limit = 1_572_864
    result = {"schema": 1, "command": argv, "source": {
        "assemblySHA256": assembly_sha,
        "input": "d4c99c2f5327ecff22711c66ef99de770dc1651b",
        "fieldLogTree": "74cdeca2ed0d4b0eb6b1bc1a6c5fa278b8ee498a",
        "mixerSDKAndVM": "6bc461f4fc7c29771718c7c5ce5a2a39b78f4d2d"},
        "scratch": str(owned), "diskLimitKiB": limit, "deadlineSeconds": 660,
        "scope": "macOS arm64 Mach-O with the signed-checklist Swift entry, production VM and host renderer witnesses. Android identity contract bound to the local host binary and archive digests. Android ELF, JNI, emulator and devices were out of scope."}
    with args.receipt.open("x") as output, log.open("wb") as raw:
        proc = subprocess.Popen(argv, cwd=repo, stdout=raw, stderr=subprocess.STDOUT, start_new_session=True)
        result.update(pid=proc.pid, pgid=proc.pid)
        print(f"FieldLog replay PID/PGID {proc.pid}, scratch {owned}", flush=True)
        try:
            while proc.poll() is None:
                allocated = allocated_kib(owned)
                peak = max(peak, allocated)
                if peak > limit or time.monotonic() - start > result["deadlineSeconds"]:
                    reason = "disk limit" if peak > limit else "deadline"
                    break
                time.sleep(1)
        except (KeyboardInterrupt, OSError, subprocess.SubprocessError) as error:
            reason = type(error).__name__
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=3)
        raw.close()
        group = "present"
        for _ in range(30):
            try:
                os.killpg(proc.pid, 0)
            except OSError as error:
                group = errno.errorcode.get(error.errno, str(error.errno))
                break
            time.sleep(0.1)
        result.update(exitCode=proc.returncode, directChildReaped=True, logClosed=True, groupObservation=group,
                      stop=reason, seconds=round(time.monotonic() - start, 3), observedAtUTC=datetime.now(timezone.utc).isoformat())
        if group == "ESRCH":
            peak = max(peak, allocated_kib(owned))
            lines = log.read_text(errors="replace").splitlines()
            result["logSHA256"] = hashlib.sha256(log.read_bytes()).hexdigest()
            result["source"]["replaySHA256"] = {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(here.iterdir()) if path.suffix in (".swift", ".c", ".h", ".sh", ".py")
            }
            result["observations"] = [line for line in lines if line.startswith((
                "COMMAND ", "ABI ", "REFUSED ", "MOUNT ", "MUTATION ", "CLOSED ", "RETIRED ",
                "Owned delivery ", "Cold process ", "Build of product ", "SOURCE ", "OWNER ", "route-then-task ",
                "task-then-route ", "reversed-to-baseline ", "ProductVersion:", "BuildVersion:",
                "Apple Swift", "swift-driver", "Xcode ", "rustc ", "Python ", "git version ")) or "Mach-O" in line]
            material = next((line[9:] for line in lines if line.startswith("MATERIAL ")), None)
            if material:
                result["ephemeralMaterial"] = json.loads(material)
            if proc.returncode or reason:
                result["failureTail"] = lines[-40:]
            shutil.rmtree(owned)
            result["scratchRemoved"] = not owned.exists()
        else:
            result["scratchRemoved"] = False
            result["hold"] = "Preserve the owned scratch and command group because terminal custody was not established."
        result["peakAllocatedKiB"] = peak
        result["status"] = "pass" if (proc.returncode == 0 and not reason and group == "ESRCH"
                                     and result["scratchRemoved"] and peak <= limit) else "incomplete"
        json.dump(result, output, indent=2)
        output.write("\n")
    print(f"{result['status']}: {args.receipt}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
