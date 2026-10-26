#!/usr/bin/env python3
"""Record both independent Python executions, including failed attempts."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
run=HERE/'commands'/stamp
run.mkdir(parents=True)
checker=(HERE/'check.py').read_bytes()
(run/'checker-source.py.txt').write_bytes(checker)
results=[]
for name,args in [('normal',[]),('optimized',['-O'])]:
    command=[sys.executable,*args,str(HERE/'check.py')]
    started=datetime.datetime.now(datetime.timezone.utc)
    p=subprocess.run(command,cwd=ROOT,text=True,capture_output=True,timeout=90)
    (run/(name+'.stdout')).write_text(p.stdout)
    (run/(name+'.stderr')).write_text(p.stderr)
    results.append(dict(name=name,command=command,exit=p.returncode,started=started.isoformat(),finished=datetime.datetime.now(datetime.timezone.utc).isoformat(),stdout_sha256=hashlib.sha256(p.stdout.encode()).hexdigest(),stderr_sha256=hashlib.sha256(p.stderr.encode()).hexdigest()))
    print(name,p.returncode,p.stdout[-2200:],p.stderr[-2500:],flush=True)
receipt=dict(schema=1,python=sys.version,executable=sys.executable,checker_sha256=hashlib.sha256(checker).hexdigest(),commands=results,all_passed=all(x['exit']==0 for x in results),scope='independent offline Python source/model; no producer code or Rust/native runtime',owned_cleanup='both bounded sequential checker children reaped; no external scratch/native/capture processes started; other projects untouched')
(run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
(HERE/'latest-run.json').write_text(json.dumps(dict(path=str(run.relative_to(HERE))),indent=2)+'\n')
sys.exit(0 if receipt['all_passed'] else 1)
