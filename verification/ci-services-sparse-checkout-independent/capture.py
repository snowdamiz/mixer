"""One-shot bounded owner of the independent audit process group."""
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
ROOT = OUT.parents[1]
sha = lambda b: hashlib.sha256(b).hexdigest()
assert not (OUT / 'capture.json').exists()
env = dict(os.environ)
argv = [sys.executable, '-B', str(OUT / 'audit.py'), '--run']
start = time.monotonic()
child = subprocess.Popen(argv, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
pid, pgid = child.pid, os.getpgid(child.pid)
timed = False
signals = []
try:
    stdout, stderr = child.communicate(timeout=45)
except subprocess.TimeoutExpired:
    timed = True
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(pgid, sig)
            signals.append(sig.name)
        except ProcessLookupError:
            pass
        try:
            stdout, stderr = child.communicate(timeout=5)
            break
        except subprocess.TimeoutExpired:
            continue
    else:
        raise RuntimeError('owned audit exceeded 55 seconds')
try:
    os.killpg(pgid, 0)
    absent = False
except ProcessLookupError:
    absent = True
(OUT / 'audit.stdout').write_bytes(stdout)
(OUT / 'audit.stderr').write_bytes(stderr)
receipt = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'argv': argv, 'cwd': str(ROOT),
           'environment': env, 'python': sys.version, 'python_executable': str(Path(sys.executable).resolve()),
           'python_sha256': sha(Path(sys.executable).resolve().read_bytes()),
           'audit_sha256': sha((OUT / 'audit.py').read_bytes()), 'capture_sha256': sha(Path(__file__).read_bytes()),
           'supervisor_pid': os.getpid(), 'supervisor_pgid': os.getpgrp(), 'pid': pid, 'pgid': pgid,
           'exit': child.returncode, 'timed_out': timed, 'elapsed_seconds': time.monotonic() - start,
           'signals_sent': signals, 'owned_child_reaped': True, 'owned_group_absent': absent,
           'stdout_sha256': sha(stdout), 'stderr_sha256': sha(stderr)}
(OUT / 'capture.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(stdout.decode(), end='')
if stderr:
    print(stderr.decode(), end='', file=sys.stderr)
assert child.returncode == 0 and absent and not timed
