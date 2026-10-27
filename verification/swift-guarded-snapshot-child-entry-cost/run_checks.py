#!/usr/bin/env python3
"""Rerun only pure tools. The one compiler probe is deliberately not replayed."""
from pathlib import Path
import hashlib,json,subprocess,sys,time
D=Path(__file__).resolve().parent
rows=[]
for name in ('prepare.py','probe_analysis.py','controls.py'):
    command=[sys.executable,str(D/name)];start=time.monotonic()
    p=subprocess.run(command,capture_output=True,text=True,timeout=60,env={**__import__('os').environ,'PYTHONDONTWRITEBYTECODE':'1'})
    (D/(name+'.stdout')).write_text(p.stdout);(D/(name+'.stderr')).write_text(p.stderr)
    rows.append(dict(command=command,python=sys.version,script_sha256=hashlib.sha256((D/name).read_bytes()).hexdigest(),elapsed_seconds=time.monotonic()-start,exit_code=p.returncode,child_waited=True,stdout_sha256=hashlib.sha256(p.stdout.encode()).hexdigest(),stderr_sha256=hashlib.sha256(p.stderr.encode()).hexdigest(),scope='pure parsing/analysis/finite numeric controls only; no compiler/native/product execution'))
    if p.returncode:
        (D/'command-receipts.json').write_text(json.dumps(rows,indent=2)+'\n');raise SystemExit(p.stderr)
(D/'command-receipts.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(dict(pure_tools_completed=len(rows),compiler_probe_replayed=False,candidate_complete=False,independent_review_required=True)))
