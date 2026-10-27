#!/usr/bin/env python3
"""Waited, offline-only command receipts, exclusively in the owned directory."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

D=Path(__file__).resolve().parent
R=D.parents[1]
if (D/"seal.json").exists():raise SystemExit("frozen-independent-review")
mode=sys.argv[1]
targets={"review":D/"review.py","review-check":D/"review.py","controls":D/"controls.py","controls-check":D/"controls.py","candidate-reproduction":R/"verification/swift-guarded-snapshot-remaining-work-interfaces/verify.py"}
if mode not in targets:raise SystemExit("unknown-offline-command")
commands=D/"commands"
commands.mkdir(exist_ok=True)
existing=[p for p in commands.iterdir() if p.is_dir() and p.name.startswith("attempt-")]
attempt=commands/f"attempt-{len(existing)+1:03d}"
attempt.mkdir()
argv=[sys.executable,str(targets[mode])]+(["--check"] if mode.endswith("-check") else [])
for p in (D/"run.py",D/"review.py",D/"controls.py"):
    (attempt/("source-"+p.name)).write_bytes(p.read_bytes())
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
result=subprocess.run(argv,cwd=R,env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1"),capture_output=True)
(attempt/"stdout").write_bytes(result.stdout)
(attempt/"stderr").write_bytes(result.stderr)
receipt={"schema":1,"started":started,"ended":datetime.datetime.now(datetime.timezone.utc).isoformat(),"argv":argv,"cwd":str(R),"returncode":result.returncode,"tool":sys.executable,"tool_version":sys.version,"tool_sha256":hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),"source_tree_sha256":"690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185","candidate_seal_sha256":"e644f57466368837445abd57506edeab9ab87135571b354be4ee772e31ddf23a","scope":"Python offline evidence/API checks only; no compiler/product/native/UI/capture/inventory/Git or foreign writes; subprocess waited","stdout_sha256":hashlib.sha256(result.stdout).hexdigest(),"stderr_sha256":hashlib.sha256(result.stderr).hexdigest()}
(attempt/"receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps({"attempt":str(attempt.relative_to(R)),"mode":mode,"returncode":result.returncode}))
print(result.stdout.decode(),end="")
print(result.stderr.decode(),end="",file=sys.stderr)
raise SystemExit(result.returncode)
