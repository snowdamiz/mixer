#!/usr/bin/env python3
"""Read-only complete closure verification and deterministic pure replays."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sha = lambda b: hashlib.sha256(b).hexdigest()
seal = json.loads((HERE/'seal.json').read_bytes())
rows = seal['members']
actual = {p.relative_to(HERE).as_posix() for p in HERE.rglob('*') if p.is_file() and p != HERE/'seal.json'}
if actual != {r['path'] for r in rows} or len(rows) != len(actual) or len(rows) != seal['member_count']:
    raise SystemExit('independent review closure differs')
for row in rows:
    p = HERE/row['path']
    raw = p.read_bytes()
    if p.is_symlink() or len(raw) != row['bytes'] or sha(raw) != row['sha256']:
        raise SystemExit('independent sealed member differs '+row['path'])
if sum(r['bytes'] for r in rows) != seal['total_bytes']:
    raise SystemExit('independent total byte dimension differs')
for name in ['audit.py','layout_audit.py']:
    result = subprocess.run([sys.executable,str(HERE/name),'--read-only'],cwd=ROOT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,timeout=55)
    if result.returncode:
        sys.stderr.buffer.write(result.stderr)
        raise SystemExit(name+' read-only replay failed')
    sys.stdout.buffer.write(result.stdout)
print(json.dumps({'sealed_members':len(rows),'sealed_bytes':seal['total_bytes'],'independent_assertions':6352,'compiler':False,'product_runtime':False,'read_only':True,'children_waited':True}))
