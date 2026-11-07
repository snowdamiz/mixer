#!/usr/bin/env python3
"""Record an owned black-box corrected-runner invocation."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROUND=Path(__file__).resolve().parents[1]
REPO=ROUND.parents[2]
p=argparse.ArgumentParser()
p.add_argument('name');p.add_argument('--compiler',type=Path,default=Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc'))
p.add_argument('--optimize',action='store_true');p.add_argument('--expected',choices=['pass','fail'],required=True)
a=p.parse_args()
if not a.name.replace('-','').isalnum():raise RuntimeError('case must be a simple owned name')
runner=ROUND/'portable-root/scripts/ci/check-analyzer-envelope.py'
digest=hashlib.sha256(runner.read_bytes()).hexdigest()
if digest!='4c56beec330b8118f01be3a6e7460f9857e4b1e8b61f29b4a9bce16fb6c1130c':raise RuntimeError('corrected runner differs')
out=ROUND/'portable-root/runs'/a.name
argv=[sys.executable,*(['-O'] if a.optimize else []),'-B',str(runner),'--out',str(out),'--rustc',str(a.compiler)]
row={'schema':1,'argv':argv,'cwd':str(REPO),'expected':a.expected,'started_utc':datetime.now(timezone.utc).isoformat(),'runner_sha256':digest,'compiler_sha256':hashlib.sha256(a.compiler.read_bytes()).hexdigest(),'timeout_seconds':600}
start=time.monotonic()
with (ROUND/(a.name+'.stdout')).open('xb') as stdout,(ROUND/(a.name+'.stderr')).open('xb') as stderr:
    result=subprocess.run(argv,cwd=REPO,stdout=stdout,stderr=stderr,timeout=600)
row.update({'exit':result.returncode,'finished_utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':round(time.monotonic()-start,6)})
receipt=json.loads((out/'receipt.json').read_bytes())
row.update({'status':receipt['status'],'errors':receipt['errors'],'command_names':[r['name'] for r in receipt['commands']],'expectation_met':(result.returncode==0 and receipt['status']=='passed-host-fixture-check') if a.expected=='pass' else (result.returncode!=0 and receipt['status']=='failed')})
for name in ('stdout','stderr'):
    path=ROUND/(a.name+'.'+name);row[name]={'path':path.name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
with (ROUND/(a.name+'-command.json')).open('x') as stream:json.dump(row,stream,indent=2,sort_keys=True);stream.write('\n')
print(json.dumps({'name':a.name,'status':row['status'],'expected':a.expected,'expectation_met':row['expectation_met'],'elapsed_seconds':row['elapsed_seconds'],'commands':len(receipt['commands']),'errors':receipt['errors']},sort_keys=True))
sys.exit(0 if row['expectation_met'] else 1)
