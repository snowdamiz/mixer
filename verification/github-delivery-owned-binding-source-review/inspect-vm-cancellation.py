"""Read-only, write-once exact-job diagnostics with owned group deadlines."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

OUT = Path(__file__).resolve().parent
KIND = sys.argv[1]
commands = {
    'job': ['gh', 'api', 'repos/snowdamiz/mixer/actions/jobs/122311014684'],
    'annotations': ['gh', 'api', 'repos/snowdamiz/mixer/check-runs/122311014684/annotations'],
    'log': ['gh', 'run', 'view', '40538740144', '--repo', 'snowdamiz/mixer', '--job', '122311014684', '--log'],
}
argv = commands[KIND]
name = 'vm-cancellation-' + KIND
assert not (OUT / (name + '.stdout')).exists()
start = time.monotonic()
child = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
timed = False
try:
    stdout, stderr = child.communicate(timeout=45)
except subprocess.TimeoutExpired:
    timed = True
    os.killpg(child.pid, signal.SIGTERM)
    try:
        stdout, stderr = child.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGKILL)
        stdout, stderr = child.communicate(timeout=5)
try:
    os.killpg(child.pid, 0)
    absent = False
except ProcessLookupError:
    absent = True
for suffix, data in [('stdout', stdout), ('stderr', stderr)]:
    with (OUT / (name + '.' + suffix)).open('xb') as stream:
        stream.write(data)
receipt = {'argv': argv, 'exit': child.returncode, 'timed_out': timed,
    'elapsed_seconds': time.monotonic() - start, 'at': datetime.now(timezone.utc).isoformat(),
    'commit': 'a96712bbd79ff4c0709d2811dd2846b4a0ea0096',
    'owned_child_reaped': True, 'owned_group_absent': absent, 'python': sys.version,
    'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'stdout_bytes': len(stdout), 'stdout_sha256': hashlib.sha256(stdout).hexdigest(),
    'stderr_sha256': hashlib.sha256(stderr).hexdigest()}
with (OUT / (name + '.command.json')).open('x') as stream:
    json.dump(receipt, stream, indent=2)
    stream.write('\n')
print(json.dumps(receipt))
assert child.returncode == 0 and not timed and absent
