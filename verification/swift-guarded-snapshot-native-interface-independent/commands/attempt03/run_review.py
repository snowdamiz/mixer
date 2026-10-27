"""Run a bounded pure offline checker and preserve every attempt."""
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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
attempts = HERE/'commands'
attempts.mkdir(exist_ok=True)
index = len(list(attempts.glob('attempt*'))) + 1
folder = attempts/f'attempt{index:02d}'
folder.mkdir()
for f in ['review.py','run_review.py']:
    shutil.copyfile(HERE/f,folder/f)
argv = [sys.executable,'-B',str(HERE/'review.py')]
started = time.monotonic()
p = subprocess.Popen(argv,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
timed_out = False
try:
    stdout,stderr = p.communicate(timeout=45)
except subprocess.TimeoutExpired:
    timed_out = True
    os.killpg(p.pid,signal.SIGKILL)
    stdout,stderr = p.communicate()
try:
    os.killpg(p.pid,0)
except ProcessLookupError:
    absent = True
else:
    absent = False
(folder/'stdout').write_bytes(stdout)
(folder/'stderr').write_bytes(stderr)
receipt = {'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':argv,
    'cwd':str(ROOT),'python_version':sys.version,'source_tree_sha256':'690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',
    'candidate_seal_sha256':'d02b6602bc7c4419d908db90a8e67d24b1dd3a46f9c9d2c2bb9158c70229b60f',
    'elapsed_seconds':time.monotonic()-started,'exit_code':p.returncode,'timed_out':timed_out,'waited':True,
    'owned_process_group':p.pid,'owned_process_group_absent':absent,
    'stdout_sha256':hashlib.sha256(stdout).hexdigest(),'stderr_sha256':hashlib.sha256(stderr).hexdigest(),
    'scope':'pure offline Python hash/JSON/source-window/type-graph/arithmetic controls; no compiler/product/native/runtime/UI/capture/Git/network/global process inventory',
    'native_runtime':'paused','other_active_lane_read':False}
(folder/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps({'attempt':folder.name,'exit_code':p.returncode,'owned_group_absent':absent,'timed_out':timed_out},sort_keys=True))
print(stdout.decode(),end='')
print(stderr.decode(),end='',file=sys.stderr)
raise SystemExit(p.returncode)
