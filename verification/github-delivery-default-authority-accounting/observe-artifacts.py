"""Read-only bounded artifact capture for the exact Phoenix CI run."""
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
name, endpoint = sys.argv[1:]
assert name in ['phoenix-artifacts-1', 'phoenix-artifact-1']
assert endpoint == 'repos/snowdamiz/mixer/actions/runs/40576103499/artifacts' or (
    endpoint.startswith('repos/snowdamiz/mixer/actions/artifacts/')
    and endpoint.endswith('/zip')
    and endpoint.split('/')[-2].isdigit()
)
assert not (OUT / (name + '.stdout')).exists()
argv = ['gh', 'api', endpoint]
start = time.monotonic()
with (OUT / (name + '.stdout')).open('xb') as stdout, (OUT / (name + '.stderr')).open('xb') as stderr:
    child = subprocess.Popen(argv, stdout=stdout, stderr=stderr, start_new_session=True)
    exceeded = None
    while child.poll() is None:
        if time.monotonic() - start >= 45:
            exceeded = 'time'
        if stdout.tell() + stderr.tell() > 8 * 1024 * 1024:
            exceeded = 'output'
        if exceeded:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=5)
            break
        time.sleep(0.05)
    child.wait()
try:
    os.killpg(child.pid, 0)
    absent = False
except ProcessLookupError:
    absent = True
files = {}
for suffix in ['stdout', 'stderr']:
    path = OUT / (name + '.' + suffix)
    with path.open('rb') as stream:
        files[suffix] = {'bytes': path.stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}
receipt = {'argv': argv, 'exit': child.returncode, 'limit_exceeded': exceeded,
    'elapsed_seconds': time.monotonic() - start, 'at': datetime.now(timezone.utc).isoformat(),
    'source_commit': '837e7084a0c6e69a88848b484fa3556563c75a59', 'owned_pid': child.pid,
    'owned_pgid': child.pid, 'owned_child_reaped': True, 'owned_group_absent': absent,
    'python': sys.version, 'files': files}
with (OUT / (name + '.command.json')).open('x') as stream:
    json.dump(receipt, stream, indent=2)
    stream.write('\n')
assert exceeded is None and absent and child.returncode == 0
assert sum(value['bytes'] for value in files.values()) <= 8 * 1024 * 1024
print(json.dumps(receipt))
