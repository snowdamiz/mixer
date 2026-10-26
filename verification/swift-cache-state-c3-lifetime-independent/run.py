#!/usr/bin/env python3
"""Run only this review's own offline checker; retain exact raw command evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
out=HERE/'commands'/stamp
out.mkdir(parents=True,exist_ok=False)
(out/'checker-source.py').write_bytes((HERE/'review.py').read_bytes())
records=[]
for label, flags in [('normal',['-B']),('optimized',['-O','-B'])]:
    command=[sys.executable,*flags,str(HERE/'review.py')]
    run=subprocess.run(command,cwd=HERE.parents[1],capture_output=True)
    (out/(label+'.stdout')).write_bytes(run.stdout)
    (out/(label+'.stderr')).write_bytes(run.stderr)
    records.append({'label':label,'argv':command,'cwd':str(HERE.parents[1]),'returncode':run.returncode,
                    'stdout_sha256':hashlib.sha256(run.stdout).hexdigest(),
                    'stderr_sha256':hashlib.sha256(run.stderr).hexdigest()})
receipt={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'python':sys.version,
         'executable':sys.executable,'runner_argv':sys.argv,
         'checker_sha256':hashlib.sha256((HERE/'review.py').read_bytes()).hexdigest(),
         'source_sha256':hashlib.sha256((HERE.parents[1]/'verification/swift-cache-state-implementation/correction-3/source/library/cache_state.rs').read_bytes()).hexdigest(),
         'commands':records,'scope':'own standard-library offline review only; source is data',
         'native_UI_capture_process_inventory_Git_hosted_actions':False}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
(HERE/'latest-run.json').write_text(json.dumps({'directory':str(out.relative_to(HERE)),
    'receipt_sha256':hashlib.sha256((out/'receipt.json').read_bytes()).hexdigest()},indent=2)+'\n')
print(json.dumps({'commands':records,'receipt':str(out/'receipt.json')},indent=2))
if any(r['returncode'] for r in records):
    raise SystemExit(1)
