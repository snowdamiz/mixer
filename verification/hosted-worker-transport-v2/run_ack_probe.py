#!/usr/bin/env python3
"""Retained pre/post-repair delayed-ack regression, each in an owned fresh BEAM."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
label = sys.argv[1]
assert label in ['attempt-4-pre-ack-fix', 'attempt-5-post-ack-fix']
args = [shutil.which('elixir'), '--erl', '+S 2:2 +SDcpu 1 +SDio 1']
for dependency in ['mint', 'jason', 'hpax']:
    args += ['-pa', str(HERE/'locked/hosted/_build/test/lib'/dependency/'ebin')]
args += [str(HERE/'compile_and_test.exs'), 'fault', 'delayed_retirement_ack']
inputs = [p for p in (HERE/'candidate').rglob('*') if p.is_file()]
rows = [{'path': str(p.relative_to(HERE)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(inputs)]
started = time.monotonic()
environment = {'PATH': os.environ['PATH'], 'LANG': 'C.UTF-8', 'ERL_CRASH_DUMP': '/dev/null', 'ERL_CRASH_DUMP_SECONDS': '0'}
p = subprocess.Popen(args, cwd=ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
try:
    out, err = p.communicate(timeout=40)
except subprocess.TimeoutExpired:
    os.killpg(p.pid, signal.SIGKILL)
    out, err = p.communicate()
finally:
    try: os.killpg(p.pid, signal.SIGKILL)
    except ProcessLookupError: pass
assert len(out) <= 2_097_152 and len(err) <= 2_097_152
(HERE/(label+'.stdout')).write_bytes(out)
(HERE/(label+'.stderr')).write_bytes(err)
result = {'args': args, 'cwd': str(ROOT), 'exit_code': p.returncode, 'duration_ms': round((time.monotonic()-started)*1000),
    'inputs': rows, 'stdout_sha256': hashlib.sha256(out).hexdigest(), 'stderr_sha256': hashlib.sha256(err).hexdigest(),
    'cleanup': 'owned fresh BEAM command group disposed'}
(HERE/(label+'.json')).write_text(json.dumps(result, indent=2)+'\n')
observed = HERE/'delayed-retirement-ack.json'
if observed.exists(): shutil.copyfile(observed, HERE/(label+'-observation.json'))
print(json.dumps({'case': 'delayed_retirement_ack', 'exit_code': p.returncode, 'label': label}))
raise SystemExit(p.returncode)
