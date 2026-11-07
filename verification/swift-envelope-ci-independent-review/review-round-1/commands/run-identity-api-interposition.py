#!/usr/bin/env python3
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROUND = Path(__file__).resolve().parents[1]
REPO = ROUND.parents[2]
source = ROUND / 'commands/identity-api-interposition.py'
toolchain = ROUND / 'faults/identity-api-toolchain'
(toolchain / 'bin').mkdir(parents=True)
(ROUND / 'faults/identity-api-records').mkdir()
compiler = toolchain / 'bin/rustc'
# The copied wrapper locates round through parents[2], same as this original
# under round/commands only after replacing its BASE with its own round path.
data = source.read_text().replace("BASE = Path(__file__).resolve().parents[2]", "BASE = Path(" + repr(str(ROUND)) + ")")
compiler.write_text('#!' + sys.executable + '\n' + '\n'.join(data.splitlines()[1:]) + '\n')
compiler.chmod(0o755)
runner = ROUND / 'portable-root/scripts/ci/check-analyzer-envelope.py'
out = ROUND / 'portable-root/runs/identity-api-interposition'
argv = [sys.executable,'-B',str(runner),'--out',str(out),'--rustc',str(compiler)]
row = {'schema':1,'argv':argv,'cwd':str(REPO),'started_utc':datetime.now(timezone.utc).isoformat(),
       'timeout_seconds':600,'runner_sha256':hashlib.sha256(runner.read_bytes()).hexdigest(),
       'interposer_sha256':hashlib.sha256(compiler.read_bytes()).hexdigest(),
       'expected':'Fail malformed contradictory compiler identity before product compilation; independently wrong API spans must never pass.',
       'scope':'Independent runner failure control using actual compiler beneath the interposer; not product/compiler qualification.'}
start=time.monotonic()
with (ROUND/'identity-api-interposition.stdout').open('xb') as stdout,(ROUND/'identity-api-interposition.stderr').open('xb') as stderr:
    result=subprocess.run(argv,cwd=REPO,stdout=stdout,stderr=stderr,timeout=600)
row.update({'exit':result.returncode,'finished_utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':round(time.monotonic()-start,6)})
with (ROUND/'identity-api-interposition-command.json').open('x') as stream:
    json.dump(row,stream,indent=2,sort_keys=True);stream.write('\n')
receipt=json.loads((out/'receipt.json').read_bytes())
print(json.dumps({'exit':result.returncode,'status':receipt['status'],'commands':len(receipt['commands']),'errors':receipt['errors'],'receipt':str(out/'receipt.json')},sort_keys=True))
