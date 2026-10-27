"""Bounded owned-directory command runner; preserves every failed attempt."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent
R=D.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
name=sys.argv[1]
assert name.isidentifier()
where=D/'commands'/name
where.mkdir(exist_ok=False)
source=(D/'independent.py').read_bytes()
(where/'independent.py').write_bytes(source)
argv=[sys.executable,'-B',str(D/'independent.py')]+sys.argv[2:]
env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
started=time.monotonic()
try:
    p=subprocess.run(argv,cwd=R,env=env,capture_output=True,timeout=60)
    code=p.returncode;out=p.stdout;err=p.stderr;timed_out=False
except subprocess.TimeoutExpired as e:
    code=None;out=e.stdout or b'';err=e.stderr or b'';timed_out=True
(where/'stdout').write_bytes(out);(where/'stderr').write_bytes(err)
record=dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),argv=argv,cwd=str(R),environment=env,
    python_version=sys.version,python_executable=sys.executable,python_executable_sha256=sha(Path(sys.executable).read_bytes()),
    review_helper_sha256=sha(source),source_tree_sha256='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',
    inherited_host_revision=json.loads((R/'verification/swift-guarded-snapshot-native-open-binary-closure/freeze-command.json').read_bytes())['git_revision'],
    current_git_metadata_read=False,exit_code=code,elapsed_seconds=time.monotonic()-started,timed_out=timed_out,
    stdout_sha256=sha(out),stderr_sha256=sha(err),compiler=False,disassembler=False,product_runtime=False,native_runtime=False,
    UI_or_capture=False,global_process_inventory=False,writes_scope=str(D))
(where/'command.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
print(json.dumps(record,sort_keys=True));print(out.decode());print(err.decode())
sys.exit(0 if code==0 else 1)
