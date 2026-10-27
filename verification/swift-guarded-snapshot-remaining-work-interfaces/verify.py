#!/usr/bin/env python3
"""Read-only seal/reproduction checks; writes neither this nor foreign packets."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

D = Path(__file__).resolve().parent
raw = (D / "seal.json").read_bytes()
seal = json.loads(raw)
paths = set()
for member in seal["members"]:
    p = Path(member["path"])
    if p.is_absolute() or ".." in p.parts or str(p) in paths: raise SystemExit("unsafe-seal-member")
    paths.add(str(p))
    target = D / p
    if target.is_symlink(): raise SystemExit("symlink-not-allowed")
    data = target.read_bytes()
    if len(data) != member["bytes"] or hashlib.sha256(data).hexdigest() != member["sha256"]: raise SystemExit("changed-member:" + str(p))
actual = {str(p.relative_to(D)) for p in D.rglob("*") if p.is_file() and p.name != "seal.json"}
if paths != actual: raise SystemExit("unsealed-members")
if len(paths) != seal["member_count"] or sum(x["bytes"] for x in seal["members"]) != seal["bytes"]: raise SystemExit("seal-count")
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
for name in ("derive.py", "composer.py", "test_interfaces.py", "review.py"):
    p = subprocess.run([sys.executable, str(D / name), "--check"], cwd=D.parents[1], env=env, capture_output=True)
    if p.returncode:
        print(p.stdout.decode(), end="")
        print(p.stderr.decode(), end="", file=sys.stderr)
        raise SystemExit(p.returncode)
    print(name + ": pass")
print(json.dumps({"status": "frozen-read-only-reproduction-pass", "seal_sha256": hashlib.sha256(raw).hexdigest(),
    "members": len(paths), "bytes": seal["bytes"], "root_selected_fourteen": False,
    "accepted_bound": False, "operational_grant": False}))
