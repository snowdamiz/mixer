#!/usr/bin/env python3
"""Bounded recorder for this independent host lane only."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent
def sha(raw): return hashlib.sha256(raw).hexdigest()
def absent(group):
    try: os.killpg(group,0); return False
    except ProcessLookupError: return True

name, script, *args = sys.argv[1:]
if name not in {'controls','seal','verify'} or script not in {'review.py','seal.py'}:
    raise ValueError('Bound review command required')
folder = BASE / 'commands' / name; folder.mkdir(parents=True,exist_ok=False)
argv = [sys.executable,'-B',str(BASE/script),*args]
started = time.monotonic()
process = subprocess.Popen(argv,cwd=BASE.parents[1],env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},
                           stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
signals=[]; timed_out=False
try: stdout,stderr = process.communicate(timeout=55)
except subprocess.TimeoutExpired:
    timed_out=True
    for selected in [signal.SIGTERM,signal.SIGKILL]:
        if not absent(process.pid): os.killpg(process.pid,selected); signals.append(int(selected))
        try: stdout,stderr=process.communicate(timeout=2); break
        except subprocess.TimeoutExpired: continue
    else: raise RuntimeError('Owned child failed to reach EOF')
if not absent(process.pid): os.killpg(process.pid,signal.SIGKILL); signals.append(int(signal.SIGKILL))
group_absent=absent(process.pid)
for n,raw in [('stdout',stdout),('stderr',stderr)]: (folder/(n+'.log')).write_bytes(raw)
value={'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'argv':argv,'cwd':str(BASE.parents[1]),'sourceSHA256':sha((BASE/script).read_bytes()),
       'executedSourceFiles':{p.name:{'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in BASE.glob('*.py')},
       'python':sys.version,'pythonExecutable':str(Path(sys.executable).resolve()),
       'pythonExecutableSHA256':sha(Path(sys.executable).resolve().read_bytes()),
       'PID':process.pid,'processGroup':process.pid,'startNewSession':True,'exitCode':process.returncode,
       'timedOut':timed_out,'signals':signals,'ownedProcessGroup':{'state':'absent' if group_absent else 'present','targetProcessGroup':process.pid},
       'elapsedSeconds':time.monotonic()-started,
       'streams':{n:{'bytes':len(raw),'sha256':sha(raw),'eof':True,'readerFailed':False} for n,raw in [('stdout',stdout),('stderr',stderr)]},
       'nativeExecuted':False,'scope':'One independent bounded host review command'}
(folder/'receipt.json').write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
print(json.dumps({'command':name,'exitCode':process.returncode,'timedOut':timed_out,'ownedGroupAbsent':group_absent}))
if process.returncode or timed_out or not group_absent: raise SystemExit(1)
