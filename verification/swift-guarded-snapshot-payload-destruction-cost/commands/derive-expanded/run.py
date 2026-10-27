#!/usr/bin/env python3
"""Record only owned pure Python commands, direct child, no process inventory."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
name=sys.argv[1]
if not name.replace('-','').isalnum(): raise SystemExit('unsafe command name')
folder=HERE/'commands'/name
folder.mkdir(parents=True,exist_ok=False)
program='freeze.py' if '--freeze' in sys.argv else 'derive.py'
argv=[sys.executable,str(HERE/program)]+(['--check-only'] if '--check-only' in sys.argv else [])
for p in (HERE/'derive.py',HERE/'model.py',HERE/'run.py'):
    shutil.copyfile(p,folder/p.name)
environment={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0'}
started=time.monotonic()
child=subprocess.Popen(argv,cwd=ROOT,env=environment,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
timed_out=False
try: stdout,stderr=child.communicate(timeout=45)
except subprocess.TimeoutExpired:
    timed_out=True;child.kill();stdout,stderr=child.communicate()
(folder/'stdout').write_bytes(stdout);(folder/'stderr').write_bytes(stderr)
def record(raw): return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'argv':argv,'cwd':str(ROOT),'environment':environment,'timeout_seconds':45,
         'elapsed_seconds':time.monotonic()-started,'exit_code':child.returncode,'timed_out':timed_out,
         'python':platform.python_version(),'python_executable':str(Path(sys.executable).resolve()),
         'python_executable_identity':record(Path(sys.executable).resolve().read_bytes()),
         'source_files':{p.name:record(p.read_bytes()) for p in [HERE/program,HERE/'model.py',HERE/'run.py']},
         'stdout':record(stdout),'stderr':record(stderr),'direct_child_pid':child.pid,'direct_child_waited':True,
         'scope':'pure payload component derivation/controls or packet hashes only',
         'product_runtime':False,'compiler':False,'native_runtime':False,'global_process_inventory':False,
         'descendants_started_by_command':False,'cleanup':'direct Python child completed; no scratch or runtime started'}
(folder/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
sys.stdout.buffer.write(stdout);sys.stderr.buffer.write(stderr)
raise SystemExit(child.returncode)
