"""Bounded read-only GitHub evidence capture for the exact failed fixture job."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

D=Path(__file__).resolve().parent
name=sys.argv[1]
argv=sys.argv[2:]
assert name.replace('-','').replace('_','').isalnum() and not (D/(name+'.command.json')).exists()
assert argv[0]=='gh' and argv[1]=='api' and argv[2].startswith('repos/snowdamiz/mixer/actions/')
assert len(argv)==3, 'Read-only GET only'
start=time.monotonic()
p=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
timeout=False
try:
    stdout,stderr=p.communicate(timeout=45)
except subprocess.TimeoutExpired:
    timeout=True;os.killpg(p.pid,signal.SIGKILL);stdout,stderr=p.communicate()
try:os.killpg(p.pid,0);absent=False
except ProcessLookupError:absent=True
for key,data in [('stdout',stdout),('stderr',stderr)]:
    with (D/(name+'.'+key)).open('xb') as f:f.write(data)
r=dict(argv=argv,exit_code=p.returncode,timed_out=timeout,elapsed_seconds=time.monotonic()-start,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),python=sys.version,source_commit='c4d04e56d0175f4c036c878db5ccb7bd9c7b30f0',run_id=40507305688,attempt=1,read_only=True,owned_child_waited=True,owned_group_absent=absent,global_process_inventory=False,outputs={k:dict(bytes=len(v),sha256=hashlib.sha256(v).hexdigest()) for k,v in [('stdout',stdout),('stderr',stderr)]})
(D/(name+'.command.json')).write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r))
assert not timeout and absent and p.returncode==0
