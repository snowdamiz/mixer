#!/usr/bin/env python3
"""Read-only independent packet seal and report reproduction."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

D=Path(__file__).resolve().parent
seal_raw=(D/"seal.json").read_bytes()
seal=json.loads(seal_raw)
names=set()
for row in seal["members"]:
    p=Path(row["path"])
    if p.is_absolute() or ".." in p.parts or str(p) in names or (D/p).is_symlink():raise SystemExit("unsafe-member")
    names.add(str(p));data=(D/p).read_bytes()
    if len(data)!=row["bytes"] or hashlib.sha256(data).hexdigest()!=row["sha256"]:raise SystemExit("changed-member:"+str(p))
if names!={str(p.relative_to(D)) for p in D.rglob("*") if p.is_file() and p.name!="seal.json"}:raise SystemExit("unsealed-members")
if len(names)!=seal["member_count"] or sum(x["bytes"] for x in seal["members"])!=seal["bytes"]:raise SystemExit("seal-count")
for name in ("review.py","controls.py"):
    result=subprocess.run([sys.executable,str(D/name),"--check"],cwd=D.parents[1],env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1"),capture_output=True)
    if result.returncode:
        print(result.stdout.decode(),end="");print(result.stderr.decode(),end="",file=sys.stderr);raise SystemExit(result.returncode)
    print(name+": pass")
print(json.dumps({"status":"frozen-independent-read-only-reproduction-pass","seal_sha256":hashlib.sha256(seal_raw).hexdigest(),"members":len(names),"bytes":seal["bytes"],"root_selected_fourteen":False,"accepted_bound":False,"operational_grant":False}))
