#!/usr/bin/env python3
"""Finite preparation whitelist. This entry point cannot select or dispatch a target."""
from pathlib import Path
import datetime
import json
import os
import signal
import subprocess
import sys
import time
from packetlib import HERE as H, ROOT, read, sha

stage = sys.argv[1]
actions = {'assemble':('assemble.py',None,90), 'build':('diagnostic.py','build',220),
           'control-001':('diagnostic.py','control',90), 'control-002':('diagnostic.py','control',90),
           'host-controls':('diagnostic.py','host-controls',60),
           'propose':('diagnostic.py','propose',60), 'cleanup':('diagnostic.py','cleanup',60)}
assert stage in actions
script, action, timeout = actions[stage]
directory = H/'preparation-commands'/stage
assert not directory.exists()
directory.mkdir(parents=True)
argv = [sys.executable,'-B',str(H/script)] + ([action] if action else [])
env={k:os.environ[k] for k in ('HOME','TMPDIR','USER','LOGNAME') if k in os.environ}
env.update(PATH='/opt/homebrew/opt/rustup/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',
           PYTHONDONTWRITEBYTECODE='1')
record={'schema':1,'stage':stage,'argv':argv,'cwd':str(ROOT),'environment':env,
        'tool':{'path':sys.executable,'sha256':sha(sys.executable),'version':sys.version},
        'scriptSHA256':sha(H/script),'wrapperSHA256':sha(__file__),
        'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'timeoutSeconds':timeout,'targetExecutionAllowed':False,'timedOut':False,'signals':[]}
start=time.monotonic()
with (directory/'stdout').open('wb') as out,(directory/'stderr').open('wb') as err:
    child=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=out,stderr=err,start_new_session=True)
    record['processGroup']=record['pid']=child.pid
    (directory/'started.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    try: child.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        record['timedOut']=True
        for sig in (signal.SIGTERM,signal.SIGKILL):
            try: os.killpg(child.pid,sig);record['signals'].append(sig.name)
            except ProcessLookupError: break
            try: child.wait(timeout=5);break
            except subprocess.TimeoutExpired: pass
try: os.killpg(child.pid,0);group='present'
except ProcessLookupError: group='absent'
except OSError: group='unknown'
record.update(exitCode=child.returncode,durationSeconds=time.monotonic()-start,
              finalGroupState=group,scriptUnchanged=sha(H/script)==record['scriptSHA256'],
              stdoutSHA256=sha(directory/'stdout'),stderrSHA256=sha(directory/'stderr'))
record['passed']=child.returncode==0 and not record['timedOut'] and group=='absent' and record['scriptUnchanged']
(directory/'receipt.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
print(json.dumps(record))
sys.exit(0 if record['passed'] else 1)
