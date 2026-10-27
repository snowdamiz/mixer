"""Bounded child runner; all attempts, including failures, remain owned here."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent
R=D.parents[1]
name=sys.argv[1]
assert name.replace('-','').isalnum()
A=D/'commands'/name
A.mkdir(parents=True,exist_ok=False)
for p in [D/'review.py',Path(__file__)]:shutil.copy2(p,A/p.name)
env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0'}
argv=[sys.executable,'-B',str(D/'review.py')]
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
now=time.monotonic();p=subprocess.Popen(argv,cwd=R,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
timed_out=False
try:out,err=p.communicate(timeout=50)
except subprocess.TimeoutExpired:
 timed_out=True;os.killpg(p.pid,signal.SIGKILL);out,err=p.communicate()
try:os.killpg(p.pid,0);absent=False
except ProcessLookupError:absent=True
(A/'stdout').write_bytes(out);(A/'stderr').write_bytes(err)
record=dict(schema=1,at=started,argv=argv,environment=env,cwd=str(R),python_version=sys.version,python_executable_sha256=hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),review_sha256=hashlib.sha256((D/'review.py').read_bytes()).hexdigest(),source_tree_sha256='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',exit_code=p.returncode,timed_out=timed_out,elapsed_seconds=time.monotonic()-now,direct_child_pid=p.pid,direct_child_waited=True,owned_group_absent=absent,global_process_inventory=False,compiler_or_product_executed=False,outputs={k:dict(bytes=len(v),sha256=hashlib.sha256(v).hexdigest()) for k,v in [('stdout',out),('stderr',err)]})
(A/'receipt.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
print(json.dumps(record,sort_keys=True));print(out.decode());print(err.decode(),file=sys.stderr)
assert absent and not timed_out
sys.exit(p.returncode)
