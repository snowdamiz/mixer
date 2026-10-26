#!/usr/bin/env python3
"""Run only this packet's own JSON/hash/arithmetic programs; preserve failures."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
run=HERE/'commands'/stamp
run.mkdir(parents=True,exist_ok=False)
commands=[([sys.executable,'-B',str(HERE/'build.py')],'build'),([sys.executable,'-B',str(HERE/'verify.py')],'verify'),([sys.executable,'-O','-B',str(HERE/'verify.py')],'verify-optimized')]
receipts=[]
for argv,label in commands:
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    before=time.monotonic()
    try:
        completed=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=30,check=False)
        out,err,code=completed.stdout,completed.stderr,completed.returncode
    except subprocess.TimeoutExpired as failure:
        out,err,code=failure.stdout or b'',failure.stderr or b'',124
    (run/(label+'.stdout')).write_bytes(out)
    (run/(label+'.stderr')).write_bytes(err)
    row={'argv':argv,'started':started,'seconds':time.monotonic()-before,'returncode':code,'stdout_path':str((run/(label+'.stdout')).relative_to(ROOT)),'stderr_path':str((run/(label+'.stderr')).relative_to(ROOT)),'stdout_sha256':hashlib.sha256(out).hexdigest(),'stderr_sha256':hashlib.sha256(err).hexdigest(),'scope':'own offline standard-library Python only; no Rust/compiler/product/native/UI/capture/process inventory/Git/hosted execution'}
    receipts.append(row)
    (run/'receipt.json').write_text(json.dumps({'schema':1,'python':sys.version,'python_executable':sys.executable,'python_binary_sha256':hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),'commands':receipts,'status':'failed-preserved' if code else 'in-progress'},indent=2,sort_keys=True)+'\n')
    if code:
        print(json.dumps({'status':'failed-preserved','returncode':code,'receipt':str((run/'receipt.json').relative_to(ROOT))}))
        raise SystemExit(code)
document=json.loads((run/'receipt.json').read_text())
document['status']='all-own-offline-checks-passed'
(run/'receipt.json').write_text(json.dumps(document,indent=2,sort_keys=True)+'\n')
(HERE/'latest-run.json').write_text(json.dumps({'receipt':str((run/'receipt.json').relative_to(ROOT)),'status':document['status']},indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':document['status'],'receipt':str((run/'receipt.json').relative_to(ROOT)),'candidate_compiled_or_run':False}))
