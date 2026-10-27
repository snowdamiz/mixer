#!/usr/bin/env python3
"""Run exactly one byte/time-bounded Python checker; no other child commands."""
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

p = Path(__file__).resolve().parent
mode = 'build' if '--build' in sys.argv[1:] else 'check'
directory = p / 'commands' / mode
for attempt in range(1, 10):
    directory = p / 'commands' / (mode if attempt == 1 else mode + '-' + str(attempt))
    if not directory.exists():
        break
directory.mkdir(parents=True, exist_ok=False)
hashes = {}
for name in ['contract.py','check.py','run_offline.py']:
    b=(p/name).read_bytes()
    hashes[name]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
command = [sys.executable,'-B',str(p/'check.py')] + (['--build'] if mode=='build' else [])
start = time.monotonic()
at = datetime.now(timezone.utc).isoformat()
try:
    result = subprocess.run(command, capture_output=True, timeout=35, cwd=p.parents[1])
    stdout,stderr=result.stdout,result.stderr
    code=result.returncode
    timeout=False
except subprocess.TimeoutExpired as e:
    stdout,stderr=e.stdout or b'',e.stderr or b''
    code=None
    timeout=True
for name,body in [('stdout',stdout),('stderr',stderr)]:
    (directory/name).write_bytes(body)
    hashes[name]={'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}
report = {'schema':1,'at':at,'command':command,'cwd':str(p.parents[1]),'python':sys.version,
          'python_executable':sys.executable,'source_and_output':hashes,
          'elapsed_seconds':round(time.monotonic()-start,6),'exit_code':code,'timed_out':timeout,
          'limits':{'wall_seconds':35,'checker_CPU_seconds':25,'read_bytes':210000000,'each_MIR_decompressed_bytes':90000000},
          'scope':'offline Python custody/delta inventory only; no compiler, product/native runtime, network or process inventory',
          'cleanup':{'owned_Python_child_waited':True,'compiler_or_native_children_started':0,
                     'source_MIR_or_build_scratch_created':False,'python_bytecode_disabled':True,
                     'temporary_files_created':0,'other_projects_processes_touched':False}}
(directory/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'mode':mode,'exit_code':code,'timed_out':timeout,'elapsed_seconds':report['elapsed_seconds'],'receipt':str(directory/'receipt.json')}))
if code != 0 or timeout:
    sys.stdout.buffer.write(stdout)
    sys.stderr.buffer.write(stderr)
    raise SystemExit(1)
