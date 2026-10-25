#!/usr/bin/env python3
"""Retain exact host commands, inputs and outputs, including every failed attempt."""
import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import sys

H=pathlib.Path(__file__).resolve().parent
output=H/'attempts'/('attempt-'+sys.argv[1])
output.mkdir(exist_ok=False)
sha=lambda value:hashlib.sha256(value).hexdigest()
inputs={}
for name in ['observation.py','test_observation.py','test_join_correction.py','validate.py','record_attempt.py','input-bindings.json']:
 raw=(H/name).read_bytes();path=output/'execution-inputs'/name;path.parent.mkdir(exist_ok=True);path.write_bytes(raw)
 inputs[name]={'bytes':len(raw),'sha256':sha(raw)}
argv=[sys.executable,'-B',str(H/'validate.py'),str(output)]
env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
result=subprocess.run(argv,cwd=H,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
(output/'stdout').write_bytes(result.stdout);(output/'stderr').write_bytes(result.stderr)
record={'schema':1,'argv':argv,'cwd':str(H),'environmentOverrides':{'PYTHONDONTWRITEBYTECODE':'1'},'startedUTC':start,'finishedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tool':{'executable':sys.executable,'version':sys.version},'sourceRevision':'9102ad3ee1247187c01ea5f55c42caaac882961b','executionInputs':inputs,'executionInputTreeSHA256':sha((json.dumps(inputs,sort_keys=True,separators=(',',':'))+'\n').encode()),'exitCode':result.returncode,'stdoutSHA256':sha(result.stdout),'stderrSHA256':sha(result.stderr),'scope':'Isolated host adapter/fixtures only; no compiler/native/UI/network/Git operation'}
(output/'command.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
print(json.dumps({'attempt':output.name,'exitCode':result.returncode,'stdoutBytes':len(result.stdout),'stderrBytes':len(result.stderr)},sort_keys=True))
raise SystemExit(result.returncode)
