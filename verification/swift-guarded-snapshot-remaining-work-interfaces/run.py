#!/usr/bin/env python3
"""Record an owned offline check, preserving every attempt and exact tool sources."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

D = Path(__file__).resolve().parent
R = D.parents[1]
if (D / "seal.json").exists():
    raise SystemExit("frozen-packet: use verify.py for read-only checks")
allowed = {"derive.py", "test_interfaces.py", "review.py", "composer.py"}
if len(sys.argv) < 2 or sys.argv[1] not in allowed:
    raise SystemExit("owned-offline-command-required")
commands = D / "commands"
commands.mkdir(exist_ok=True)
index = len(list(commands.glob("attempt-*"))) + 1
out = commands / f"attempt-{index:03d}"
out.mkdir()
sources = {}
for p in sorted(D.glob("*.py")):
    raw = p.read_bytes()
    (out / ("source-" + p.name)).write_bytes(raw)
    sources[p.name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
argv = [sys.executable, str(D / sys.argv[1]), *sys.argv[2:]]
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
p = subprocess.run(argv, cwd=R, env=env, capture_output=True)
for name, raw in (("stdout", p.stdout), ("stderr", p.stderr)):
    (out / name).write_bytes(raw)
receipt = {"schema": 1, "at": started, "argv": argv,
    "cwd": str(R), "tool_version": platform.python_version(), "tool": sys.executable,
    "tool_sha256": hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest(),
    "returncode": p.returncode, "own_sources": sources,
    "source_tree_sha256": "690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185",
    "host_tree_sha256": "027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2",
    "scope": "owned Python/offline source model only; no compiler/runtime/native/UI/capture/global inventory/Git/frozen writes",
    "outputs": {name: {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
                for name, raw in (("stdout", p.stdout), ("stderr", p.stderr))}}
(out / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(p.stdout.decode(), end="")
print(p.stderr.decode(), end="", file=sys.stderr)
print(json.dumps({"receipt": str(out.relative_to(R)), "returncode": p.returncode}))
raise SystemExit(p.returncode)
