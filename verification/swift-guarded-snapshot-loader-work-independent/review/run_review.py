#!/usr/bin/env python3
"""Run only the two owned pure review tools and capture bounded receipts."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys,time
D=Path(__file__).resolve().parent
records=[]
for name in ('audit.py','native_controls.py'):
    command=[sys.executable,str(D/name)]
    started=time.monotonic()
    result=subprocess.run(command,capture_output=True,text=True,timeout=60)
    (D/(name+'.stdout')).write_text(result.stdout)
    (D/(name+'.stderr')).write_text(result.stderr)
    records.append(dict(command=command,source_sha256=hashlib.sha256((D/name).read_bytes()).hexdigest(),python=sys.version,elapsed_seconds=time.monotonic()-started,exit_code=result.returncode,child_waited=True,stdout_sha256=hashlib.sha256(result.stdout.encode()).hexdigest(),stderr_sha256=hashlib.sha256(result.stderr.encode()).hexdigest(),scope='pure independent data analysis/models; no product/native/compiler execution'))
    if result.returncode:
        (D/'command-receipts.json').write_text(json.dumps(records,indent=2)+'\n')
        raise SystemExit(result.stderr)
(D/'command-receipts.json').write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps(dict(commands=len(records),all_completed=True,all_pure_checks_pass=True,candidate_accepted=False,reason='two Type-slice callback edges require direct pricing-tool correction')))
