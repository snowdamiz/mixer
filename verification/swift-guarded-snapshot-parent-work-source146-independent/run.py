#!/usr/bin/env python3
"""Retain bounded pure-review commands and failures in this owned packet."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

here=Path(__file__).resolve().parent
name=sys.argv[1]
if '/' in name or name in ('.','..'):
    raise SystemExit('one receipt directory name required')
out=here/name
out.mkdir(exist_ok=False)
script=here/'review.py'
(out/'review.py').write_bytes(script.read_bytes())
command=[sys.executable,str(script)]+sys.argv[2:]
start=time.monotonic()
done=subprocess.run(command,cwd=here.parent.parent,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
for n,data in [('stdout',done.stdout),('stderr',done.stderr)]:
    (out/n).write_bytes(data)
def identity(path):
    raw=Path(path).read_bytes()
    return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
receipt={'schema':1,'at':datetime.datetime.now(datetime.UTC).isoformat(),'argv':command,'cwd':str(here.parent.parent),'python':platform.python_version(),'python_identity':identity(sys.executable),'review_identity':identity(script),'runner_identity':identity(__file__),'exit_code':done.returncode,'elapsed_seconds':time.monotonic()-start,'timeout_seconds':60,'compiler_or_product_execution':False,'stdout':identity(out/'stdout'),'stderr':identity(out/'stderr')}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps({'receipt':str(out/'receipt.json'),'exit_code':done.returncode,'stdout':done.stdout.decode(),'stderr':done.stderr.decode()}))
raise SystemExit(done.returncode)
