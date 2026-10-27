#!/usr/bin/env python3
"""Collect bounded pure review commands; children are waited, output preserved."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sha = lambda b: hashlib.sha256(b).hexdigest()
if (HERE / 'seal.json').exists():
    raise SystemExit('frozen review is immutable')
script = sys.argv[1] if len(sys.argv) > 1 else 'audit.py'
if Path(script).name != script or not script.endswith('.py'):
    raise SystemExit('only owned pure script name permitted')
source = HERE / script
count = len(list((HERE / 'commands').glob(script[:-3]+'-*'))) if (HERE / 'commands').exists() else 0
folder = HERE / 'commands' / (script[:-3]+'-'+str(count+1).zfill(2))
folder.mkdir(parents=True)
(folder / 'executed-source.py').write_bytes(source.read_bytes())
snapshots = []
for own in sorted(HERE.glob('*.py')):
    raw = own.read_bytes()
    dest = folder / 'source-inputs' / own.name
    dest.parent.mkdir(exist_ok=True)
    dest.write_bytes(raw)
    snapshots.append({'path':str(own.relative_to(ROOT)), 'bytes':len(raw), 'sha256':sha(raw), 'retained_copy':str(dest.relative_to(HERE))})
revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, check=True).stdout.decode().strip()
argv = [sys.executable, str(source)]
start = time.monotonic()
timed_out = False
try:
    result = subprocess.run(argv, cwd=ROOT, env={**os.environ, 'PYTHONDONTWRITEBYTECODE':'1'}, capture_output=True, timeout=55)
    stdout, stderr, exit_code = result.stdout, result.stderr, result.returncode
except subprocess.TimeoutExpired as exc:
    timed_out = True
    stdout, stderr, exit_code = exc.stdout or b'', exc.stderr or b'', None
(folder / 'stdout').write_bytes(stdout)
(folder / 'stderr').write_bytes(stderr)
receipt = {'schema':1, 'at':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'argv':argv, 'cwd':str(ROOT), 'timeout_seconds':55, 'elapsed_seconds':time.monotonic()-start, 'exit_code':exit_code, 'timed_out':timed_out, 'direct_child_waited':True, 'python_version':sys.version, 'python_executable':str(Path(sys.executable).resolve()), 'python_executable_sha256':sha(Path(sys.executable).resolve().read_bytes()), 'executed_source':{'path':str(source.relative_to(ROOT)), 'bytes':len(source.read_bytes()), 'sha256':sha(source.read_bytes())}, 'source_revision':revision, 'actual_source_tree_sha256':'690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185', 'stdout':{'bytes':len(stdout),'sha256':sha(stdout)}, 'stderr':{'bytes':len(stderr),'sha256':sha(stderr)}, 'compiler':False, 'product_runtime':False, 'native_UI_capture':False, 'global_process_inventory':False, 'subprocess_scope':'one Python child plus read-only git rev-parse child; neither launches children'}
receipt['own_source_inputs'] = snapshots
(folder / 'receipt.json').write_text(json.dumps(receipt, sort_keys=True, indent=2)+'\n')
print(json.dumps({'command':str(folder.relative_to(ROOT)), 'exit_code':exit_code, 'elapsed_seconds':receipt['elapsed_seconds'], 'timed_out':timed_out, 'stdout_tail':stdout[-3000:].decode(errors='replace'), 'stderr_tail':stderr[-4000:].decode(errors='replace')}))
if exit_code != 0:
    raise SystemExit(1)
