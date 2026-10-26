#!/usr/bin/env python3
"""Append a sealed validation report without modifying the frozen proposal."""
import ast
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent


def identity(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main():
    if (PACKET / "validation.json").exists() or (PACKET / "validation-manifest.json").exists():
        raise SystemExit("Validation report already exists; preserve it")
    commands = []
    for argv in ([sys.executable, "-B", "verification/android-public-owner-contract/verify.py"],
                 ["git", "diff", "--no-index", "--check", "/dev/null", "docs/android-public-owner-contract.md"]):
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
        commands.append({"argv": argv, "exit_code": result.returncode,
                         "stdout": result.stdout, "stderr": result.stderr})
    assert commands[0]["exit_code"] == 0, "Frozen identity verification failed"
    assert commands[1]["exit_code"] == 1 and not commands[1]["stdout"] and not commands[1]["stderr"], "Whitespace findings or unexpected diff result"
    scripts = sorted(PACKET.glob("*.py"))
    data = sorted(PACKET.glob("*.json"))
    for path in scripts:
        ast.parse(path.read_text(), filename=str(path))
    for path in data:
        json.loads(path.read_text())
    report = {
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "Read-only packet/source identity, JSON/Python syntax and documentation whitespace only",
        "argv": [sys.executable, "-B", str(Path(__file__).resolve())],
        "python_version": sys.version, "status": "pass", "commands": commands,
        "format_checks": {"python_scripts": len(scripts), "json_files": len(data), "status": "pass"},
        "whitespace_result": "No findings; no-index exit1 denotes the new-file diff",
        "platform_access_precision": "Official source review records access date only; exact per-request timestamps were not retained. The proposal's exact-access-time wording should be read with this limitation.",
        "behavior_or_native_qualification": False
    }
    (PACKET / "validation.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    members = {}
    for path in (PACKET / "manifest.json", Path(__file__).resolve(), PACKET / "validation.json"):
        members[path.relative_to(ROOT).as_posix()] = identity(path)
    (PACKET / "validation-manifest.json").write_text(json.dumps({"schema": 1, "scope": "Append-only validation supplement sealing the unchanged proposal manifest", "members": members}, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "pass", "frozen_members": 8, "source_inputs": 55,
                      "accepted_profile_inputs": 42, "validation_supplement_members": 3,
                      "scope": report["scope"]}, sort_keys=True))


if __name__ == "__main__":
    main()
