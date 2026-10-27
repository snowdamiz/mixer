"""Verify, record the read-only command, then seal this compact owned packet."""
from pathlib import Path
import json
import os
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
from prepare import HERE, ROOT, sha, canonical, write, identity

assert not (HERE / 'seal.json').exists()
assert not (HERE / 'owned-work').exists()
dest = HERE / 'verification-command'
dest.mkdir(exist_ok=False)
argv = [str(Path(sys.executable).resolve()), str(HERE / 'verify.py')]
environment = {'PATH': '/usr/bin:/bin'}
start = time.monotonic()
with (dest / 'stdout').open('wb') as out, (dest / 'stderr').open('wb') as err:
    child = subprocess.Popen(argv, cwd=ROOT, env=environment, stdout=out, stderr=err, start_new_session=True)
    try:
        code = child.wait(timeout=15)
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGKILL)
        child.wait(timeout=3)
        raise
try:
    os.killpg(child.pid, 0)
except ProcessLookupError:
    absent = True
else:
    absent = False
receipt = {'schema': 1, 'argv': argv, 'cwd': str(ROOT), 'environment': environment,
    'exit_code': code, 'timeout_seconds': 15, 'elapsed_seconds': time.monotonic() - start,
    'child_reaped': True, 'owned_process_group': child.pid, 'owned_group_absent': absent,
    'verifier': identity(HERE / 'verify.py'), 'python': identity(Path(sys.executable).resolve()),
    'python_version': sys.version, 'stdout': identity(dest / 'stdout'), 'stderr': identity(dest / 'stderr'),
    'scope': 'Read-only exact source/support/descriptor and command evidence verification'}
write(dest / 'receipt.json', receipt)
assert code == 0 and absent
members = [{'path': str(p.relative_to(HERE)), 'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
           for p in sorted(HERE.rglob('*')) if p.is_file()]
assert not any(item['path'].endswith('.pyc') or '/__pycache__/' in item['path'] for item in members)
seal = {'schema': 1, 'member_count': len(members), 'member_bytes': sum(item['bytes'] for item in members),
        'members': members, 'tree_sha256': sha(canonical(members)),
        'scope': 'Exact private source145/host11 loader count and build-support rebinding; real candidate metadata plus bounded pure descriptor checks; no genuine loader/engine/VM/writer admission, canonical integration or GA acceptance'}
write(HERE / 'seal.json', seal)
print(json.dumps({'frozen': True, 'member_count': seal['member_count'], 'member_bytes': seal['member_bytes'],
                  'tree_sha256': seal['tree_sha256'], 'seal_sha256': sha((HERE / 'seal.json').read_bytes())}, sort_keys=True))
