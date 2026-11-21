#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import time

CAP = 4 * 1024**3
STOP = CAP - 256 * 1024**2

def allocated(root):
    seen = set()
    size = 0
    for directory, dirs, files in os.walk(root):
        for path in [Path(directory), *(Path(directory) / name for name in [*dirs, *files])]:
            try:
                info = path.lstat()
            except FileNotFoundError:
                continue
            identity = (info.st_dev, info.st_ino)
            if identity not in seen:
                seen.add(identity)
                size += info.st_blocks * 512
    return size

def absent(pgid):
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return True
    return False

def receipt_bytes(row):
    return (json.dumps(row, indent=2) + "\n").encode("utf-8")


def write_receipt(path, row):
    with path.open("xb") as output:
        output.write(receipt_bytes(row))
        output.flush()
        os.fsync(output.fileno())


def publish_receipt(path, row):
    temporary = path.with_suffix(".tmp")
    write_receipt(temporary, row)
    os.replace(temporary, path)


class UnresolvedCustody(RuntimeError):
    pass


def log_sha256(path):
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    with os.fdopen(os.open(path, flags), "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise UnresolvedCustody(f"{path.name} is not a regular file")
        return hashlib.file_digest(stream, "sha256").hexdigest()


class OwnedCommands:
    def __init__(self, root):
        self.root = root
        self.directory = root / "commands"
        self.directory.mkdir()
        self._attempts = {}

    def run(self, name, cwd, seconds, argv, env=None):
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name) or name in self._attempts:
            raise ValueError(f"Invalid or repeated command ID: {name}")
        self._attempts[name] = None
        receipt = self.directory / f"{name}.json"
        log = self.directory / f"{name}.log"
        write_receipt(receipt, {"argv": argv, "custody": "launch pending"})

        started = time.monotonic()
        peak = allocated(self.root)
        free = shutil.disk_usage(self.root).free
        if peak >= STOP or free < 5 * 1024**3:
            raise RuntimeError("Insufficient allocated scratch or free disk before launch")
        reason = None
        with log.open("xb") as stream:
            child = subprocess.Popen(argv, cwd=cwd, env=env, stdout=stream,
                                     stderr=subprocess.STDOUT, start_new_session=True)
            publish_receipt(receipt, {"argv": argv, "pid": child.pid, "pgid": child.pid,
                                      "custody": "running"})
            while True:
                code = child.poll()
                now = time.monotonic()
                peak = max(peak, allocated(self.root))
                free = min(free, shutil.disk_usage(self.root).free)
                if code is not None and absent(child.pid):
                    break
                danger = peak >= STOP or free < 5 * 1024**3
                if (now - started > seconds or danger) and reason is None:
                    reason = "scratch limit" if danger else "deadline"
                    stopping = now
                    try:
                        os.killpg(child.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                if reason and now - stopping > 2:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                if reason and now - stopping > 8:
                    break
                time.sleep(.45)
        terminal = child.poll() is not None and absent(child.pid)
        result = {"argv": argv, "cwd": str(cwd), "deadlineSeconds": seconds,
                  "pid": child.pid, "pgid": child.pid, "groupAbsent": terminal,
                  "childReaped": child.returncode is not None, "logClosed": True,
                  "exit": child.returncode, "stop": reason, "peakAllocatedBytes": peak,
                  "minimumFreeBytes": free, "seconds": round(time.monotonic() - started, 2),
                  "logSHA256": log_sha256(log)}
        publish_receipt(receipt, result)
        if terminal:
            self._attempts[name] = result
        print(name, child.returncode, "closed" if terminal else "UNKNOWN", "peak", peak, flush=True)
        if reason or child.returncode or not terminal:
            print(log.read_text(errors="replace")[-12000:], flush=True)
            raise SystemExit(74 if not terminal else 1)

    def checked_receipts(self):
        for name, observed in self._attempts.items():
            if observed is None:
                raise UnresolvedCustody(f"{name} has no confirmed terminal receipt")
        expected = {f"{name}{suffix}" for name in self._attempts for suffix in (".json", ".log")}
        with os.scandir(self.directory) as entries:
            found = set()
            for entry in entries:
                if not entry.is_file(follow_symlinks=False):
                    raise UnresolvedCustody(f"Unexpected command directory entry: {entry.name}")
                found.add(entry.name)
        if found != expected:
            raise UnresolvedCustody("Command files differ from the attempted command set")
        checked = {}
        for name, observed in self._attempts.items():
            path = self.directory / f"{name}.json"
            if path.read_bytes() != receipt_bytes(observed):
                raise UnresolvedCustody(f"{name} has no matching positive terminal receipt")
            log = self.directory / f"{name}.log"
            if log_sha256(log) != observed["logSHA256"]:
                raise UnresolvedCustody(f"{log.name} digest mismatch")
            checked[name] = observed
        return checked

    def cleanup(self):
        try:
            self.checked_receipts()
        except (UnresolvedCustody, OSError) as error:
            print(f"Preserving scratch with unresolved command custody: {self.root} ({error})",
                  file=sys.stderr)
            return False
        shutil.rmtree(self.root)
        return True


if __name__ == "__main__":
    work, name, cwd, seconds, *argv = sys.argv[1:]
    commands = OwnedCommands(Path(work).resolve())
    commands.run(name, Path(cwd).resolve(), int(seconds), argv)
