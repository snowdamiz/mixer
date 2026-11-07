"""One authorized dispatch of the reviewed architecture comparison at the pushed head."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

OUT = Path(__file__).parent
ROOT = OUT.parents[1]
HEAD = 'dfd0e3196543cc1749c9cc924cc7accf28c9dc25'


def save(name, value):
    with (OUT / name).open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def command(name, argv):
    start = time.monotonic()
    with (OUT / (name + '.stdout')).open('xb') as out, (OUT / (name + '.stderr')).open('xb') as err:
        child = subprocess.Popen(argv, cwd=ROOT, stdout=out, stderr=err, start_new_session=True)
        save(name + '.started.json', {'argv': argv, 'pid': child.pid, 'pgid': child.pid, 'at': datetime.now(timezone.utc).isoformat()})
        timed = False
        try:
            child.wait(timeout=45)
        except subprocess.TimeoutExpired:
            timed = True
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=3)
    try:
        os.killpg(child.pid, 0)
        absent = False
    except ProcessLookupError:
        absent = True
    data = (OUT / (name + '.stdout')).read_bytes()
    save(name + '.command.json', {'argv': argv, 'exit': child.returncode, 'timed_out': timed,
        'elapsed_seconds': time.monotonic() - start, 'owned_pid': child.pid, 'owned_pgid': child.pid,
        'child_reaped': True, 'group_absent': absent, 'stdout_sha256': hashlib.sha256(data).hexdigest()})
    assert not timed and absent and child.returncode == 0
    return data


assert not (OUT / 'architecture-dispatch-once.json').exists()
assert json.loads((OUT / 'receipt.json').read_bytes())['commit'] == HEAD
assert command('architecture-dispatch-local-head', ['git', 'rev-parse', 'HEAD']).decode().strip() == HEAD
assert command('architecture-dispatch-remote-head', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split()[0] == HEAD
assert hashlib.sha256((ROOT / '.github/workflows/swift-execution-architecture-comparison.yml').read_bytes()).hexdigest() == 'c940e07b0f7a604d97c6b7e7148baa2717057853ffab32b7bb8deb633f7e62a6'
workflow = json.loads(command('architecture-workflow-state', ['gh','api','repos/snowdamiz/mixer/actions/workflows/swift-execution-architecture-comparison.yml']))
assert workflow['state'] == 'active' and workflow['path'] == '.github/workflows/swift-execution-architecture-comparison.yml'
save('architecture-dispatch-once.json', {'at': datetime.now(timezone.utc).isoformat(), 'head': HEAD,
    'workflow': 'swift-execution-architecture-comparison.yml', 'dispatches_authorized': 1,
    'maximum_full_attempts': 2, 'both_preparation_arms_required': True, 'clean_ordinary_resource_failure_may_advance': True})
output = command('architecture-dispatch', ['gh', 'workflow', 'run', 'swift-execution-architecture-comparison.yml',
    '--ref', 'main', '--repo', 'snowdamiz/mixer'])
print(output.decode().strip())
