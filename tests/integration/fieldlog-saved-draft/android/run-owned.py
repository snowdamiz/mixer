#!/usr/bin/env python3
"""Run one full Android source rebuild and verify its process custody."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time


MIXER_REVISION = "5dea19db36610e312b51918b384364ba590b6ef8"
VM_BUILDER_SHA256 = "cbae2f5f02b1d8a468a331a71f31e9c4fad1957d16142db0d4e3d0ad2e6fa010"
VM_COMMANDS = {
    "android": ("android-linker-version",),
    "host": ("apple-sdk", "apple-clang-path", "apple-linker-version"),
}
CREATE_COMMANDS = {("swift", "--version"), ("python3", "android-build.py", "inspect")}
MAX_RECEIPT_BYTES = 2 * 1024 * 1024


def present(path):
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    return True


def load_receipt(path):
    if path.resolve(strict=True) != path:
        raise ValueError(f"Receipt path traverses a symlink: {path}")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError(f"Expected a regular receipt: {path}")
        raw = stream.read(MAX_RECEIPT_BYTES + 1)
    if len(raw) > MAX_RECEIPT_BYTES:
        raise ValueError(f"Receipt exceeds size limit: {path}")
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def zero_exit(value):
    return type(value) is int and value == 0


def prepared_project(work):
    path = work / "prepared/.fieldlog-build/commands.json"
    rows, checksum = load_receipt(path)
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise ValueError(f"Expected exactly one create command in {path}")
    row = rows[0]
    if row.get("label") != "create" or not zero_exit(row.get("exitCode")) or row.get("ownedGroupAbsent") is not True:
        raise ValueError(f"Create terminal facts are missing or unresolved in {path}")
    return {"receiptSHA256": checksum}


def mixer_create_tools(work):
    tmp = work / "tmp"
    if tmp.resolve(strict=True) != tmp:
        raise ValueError(f"Receipt directory traverses a symlink: {tmp}")
    contexts = list(tmp.glob("mixer-command-receipts-*"))
    if len(contexts) != 1 or contexts[0].is_symlink():
        raise ValueError(f"Expected one Mixer create receipt directory under {tmp}")
    directories = sorted(contexts[0].glob("command-*"))
    if len(directories) != len(CREATE_COMMANDS):
        raise ValueError(f"Incomplete or unexpected Mixer create commands in {contexts[0]}")
    facts = ("terminalCustody", "directChildReaped", "ownedGroupAbsent", "stdoutEOF", "stderrEOF", "descriptorsClosed")
    observed = {}
    for directory in directories:
        if directory.is_symlink() or present(directory / "HOLD.json"):
            raise ValueError(f"Mixer create command custody is unresolved at {directory}")
        path = directory / "receipt.json"
        row, checksum = load_receipt(path)
        if (not isinstance(row, dict) or row.get("schema") != "mixer.owned-command.2"
                or row.get("state") != "TERMINAL" or not zero_exit(row.get("exitCode"))
                or any(row.get(fact) is not True for fact in facts)):
            raise ValueError(f"Mixer create tool terminal facts are missing or unresolved in {path}")
        command = row.get("command")
        if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
            raise ValueError(f"Invalid Mixer create tool argv in {path}")
        key = tuple(command)
        if len(command) == 3 and command[0] == "python3" and Path(command[1]).is_absolute():
            key = (command[0], Path(command[1]).name, command[2])
        if key not in CREATE_COMMANDS or key in observed:
            raise ValueError(f"Unexpected or duplicate Mixer create tool in {path}")
        observed[key] = checksum
    return {"receiptSHA256ByCommand": {" ".join(key): observed[key] for key in sorted(observed)}}


def vm_build(work, target):
    directory = work / f"{target}-engine"
    if directory.is_symlink() or present(directory / "failure.json"):
        raise ValueError(f"VM build has unresolved custody at {directory}")
    path = directory / "receipt.json"
    receipt, checksum = load_receipt(path)
    if (not isinstance(receipt, dict) or receipt.get("schema_version") != 1
            or receipt.get("target_selector") != target or receipt.get("source_revision") != MIXER_REVISION
            or receipt.get("builder_sha256") != VM_BUILDER_SHA256 or not receipt.get("completed_utc")):
        raise ValueError(f"Missing pinned VM completion evidence in {path}")
    expected = ("rust-sysroot", "rustc-version", "cargo-version", "llvm-nm-version",
                *VM_COMMANDS[target], "cargo-build", "archive-symbols")
    rows = receipt.get("commands")
    if (not isinstance(rows, list) or len(rows) != len(expected)
            or any(not isinstance(row, dict) or row.get("name") != name
                   or not zero_exit(row.get("exit_code")) or "problem" not in row or row["problem"] is not None
                   for row, name in zip(rows, expected))):
        raise ValueError(f"Incomplete or unresolved VM command evidence in {path}")
    library = receipt.get("library")
    archive = library.get("sha256") if isinstance(library, dict) else None
    if not isinstance(archive, str) or re.fullmatch(r"[0-9a-f]{64}", archive) is None:
        raise ValueError(f"Missing VM archive digest in {path}")
    return {"receiptSHA256": checksum, "verifiedCommandGroups": len(expected), "archiveSHA256": archive}


def nested_custody(output):
    work = output / "work"
    checks = {
        "preparedProject": lambda: prepared_project(work),
        "mixerCreateTools": lambda: mixer_create_tools(work),
        "androidVM": lambda: vm_build(work, "android"),
        "hostVM": lambda: vm_build(work, "host"),
    }
    results = {}
    for label, check in checks.items():
        try:
            results[label] = {"state": "TERMINAL", **check()}
        except (OSError, ValueError, RecursionError) as error:
            results[label] = {"state": "UNKNOWN", "reason": str(error)}
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("timeout", type=int)
    parser.add_argument("output", type=Path, help="fresh rebuild directory passed to the recipe")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.timeout <= 0 or not args.command:
        parser.error("Expected a positive timeout and a rebuild command")
    output = args.output.parent.resolve(strict=True) / args.output.name
    if present(output):
        parser.error("Rebuild output must be absent before launch")

    receipt = args.receipt
    record = {"command": args.command, "timeoutSeconds": args.timeout, "rebuildOutput": str(output),
              "outerTerminalCustody": "UNKNOWN", "terminalCustody": "UNKNOWN"}
    with receipt.open("x") as stream:
        def persist():
            stream.seek(0)
            json.dump(record, stream, indent=2)
            stream.write("\n")
            stream.truncate()
            stream.flush()
            os.fsync(stream.fileno())

        persist()
        try:
            child = subprocess.Popen(args.command, start_new_session=True)
            record["pid"] = record["pgid"] = child.pid
            persist()
            started = time.monotonic()
            record["exit"] = child.wait(timeout=args.timeout)
            record["elapsedSeconds"] = round(time.monotonic() - started, 3)
            for _ in range(20):
                try:
                    os.killpg(child.pid, 0)
                except ProcessLookupError:
                    record["outerTerminalCustody"] = "reaped_and_group_absent"
                    break
                time.sleep(0.1)
            if record["outerTerminalCustody"] == "reaped_and_group_absent":
                nested = nested_custody(output)
                record["nestedCustody"] = nested
                if all(result["state"] == "TERMINAL" for result in nested.values()):
                    record["terminalCustody"] = "TERMINAL"
                else:
                    record["hold"] = "Expected nested terminal evidence is missing or unresolved."
            else:
                record["hold"] = "Direct child reaped, but its process group remained present."
        except (OSError, subprocess.TimeoutExpired, KeyboardInterrupt) as error:
            record["hold"] = f"{type(error).__name__}: {error}"
        finally:
            try:
                persist()
            except OSError as error:
                record["terminalCustody"] = "UNKNOWN"
                print(f"Could not persist custody in {receipt}: {error}", file=sys.stderr)
    if record["terminalCustody"] != "TERMINAL":
        print(f"UNKNOWN custody. Preserve the attempt containing {output} and {receipt}", file=sys.stderr)
        return 74
    exit_code = record["exit"]
    return exit_code if exit_code >= 0 else 128 - exit_code


if __name__ == "__main__":
    sys.exit(main())
