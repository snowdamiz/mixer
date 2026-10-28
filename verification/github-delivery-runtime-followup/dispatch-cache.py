"""One authorized dispatch of the reviewed deadline comparison at the pushed head."""
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
HEAD = 'fb7c7f20f8a308424ef4b7092d19d3d4de2c7627'


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


assert not (OUT / 'cache-dispatch-once.json').exists()
assert json.loads((OUT / 'receipt.json').read_bytes())['commit'] == HEAD
assert command('cache-dispatch-local-head', ['git', 'rev-parse', 'HEAD']).decode().strip() == HEAD
assert command('cache-dispatch-remote-head', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split()[0] == HEAD
save('cache-dispatch-once.json', {'at': datetime.now(timezone.utc).isoformat(), 'head': HEAD,
    'workflow': 'swift-cache-deadline-campaign-v2.yml', 'dispatches_authorized': 1,
    'maximum_full_attempts': 2, 'second_conditional_on_verified_CacheWork': True})
output = command('cache-dispatch', ['gh', 'workflow', 'run', 'swift-cache-deadline-campaign-v2.yml',
    '--ref', 'main', '--repo', 'snowdamiz/mixer'])
print(output.decode().strip())
