"""Record attempt1, then request one exact-job retry after checkout timeout."""
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
sha = lambda data: hashlib.sha256(data).hexdigest()
terminal = OUT / 'terminal-ci-attempt1.json'
assert not terminal.exists() and not (OUT / 'vm-retry-request.json').exists()
raw = (OUT / 'ci-jobs-5.stdout').read_bytes()
run = json.loads(raw)
assert run['headSha'] == 'a96712bbd79ff4c0709d2811dd2846b4a0ea0096'
assert run['attempt'] == 1 and run['conclusion'] == 'cancelled' and run['status'] == 'completed'
assert len(run['jobs']) == 6
assert sum(j['conclusion'] == 'success' for j in run['jobs']) == 5
vm, = [j for j in run['jobs'] if j['name'] == 'vm']
assert vm['databaseId'] == 122311014684 and vm['conclusion'] == 'cancelled'
assert vm['steps'][1]['conclusion'] == 'cancelled'
assert all(s['conclusion'] == 'skipped' for s in vm['steps'][2:10])
annotations = json.loads((OUT / 'vm-cancellation-annotations.stdout').read_text())
assert any(a['message'] == 'The job has exceeded the maximum execution time of 20m0s' for a in annotations)
assert 'Fetching the repository' in (OUT / 'vm-cancellation-log.stdout').read_text()
terminal_data = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'commit': run['headSha'], 'run': run['databaseId'], 'attempt': 1,
    'status': 'completed', 'conclusion': 'cancelled', 'jobs_passed': 5,
    'jobs_cancelled': 1, 'steps_passed': sum(s['conclusion'] == 'success' for j in run['jobs'] for s in j['steps']),
    'steps_cancelled': 1, 'steps_skipped': 8,
    'VM_tests_ran': False, 'cause': 'GitHub job20m timeout during checkout git fetch; all eight VM tool/test steps skipped',
    'observation': 'ci-jobs-5.stdout', 'observation_sha256': sha(raw),
    'diagnostics': [{ 'path': p.name, 'sha256': sha(p.read_bytes())} for p in [OUT / 'vm-cancellation-job.stdout', OUT / 'vm-cancellation-annotations.stdout', OUT / 'vm-cancellation-log.stdout']],
    'url': run['url'], 'CI_passed': False, 'scope': 'exactcommit remotehost CI only; no native/device/OTA/GA qualification'}
with terminal.open('x') as stream:
    json.dump(terminal_data, stream, indent=2); stream.write('\n')

argv = ['gh', 'run', 'rerun', str(run['databaseId']), '--repo', 'snowdamiz/mixer', '--job', str(vm['databaseId'])]
plan = {'argv': argv, 'scope': 'single exact cancelled VM job only; no dependencies declared',
    'reason': terminal_data['cause'], 'source_commit': run['headSha'],
    'terminal_sha256': sha(terminal.read_bytes()), 'python': sys.version,
    'gh_version': subprocess.check_output(['gh', '--version'], timeout=10, text=True),
    'script_sha256': sha(Path(__file__).read_bytes())}
with (OUT / 'vm-retry-plan.json').open('x') as stream:
    json.dump(plan, stream, indent=2); stream.write('\n')
start = time.monotonic()
child = subprocess.Popen(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
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
    os.killpg(child.pid, 0); absent = False
except ProcessLookupError:
    absent = True
for suffix, data in [('stdout', stdout), ('stderr', stderr)]:
    with (OUT / ('vm-retry.' + suffix)).open('xb') as stream:
        stream.write(data)
receipt = {'argv': argv, 'exit': child.returncode, 'timed_out': timed,
    'elapsed_seconds': time.monotonic() - start, 'at': datetime.now(timezone.utc).isoformat(),
    'source_commit': run['headSha'], 'terminal_sha256': sha(terminal.read_bytes()),
    'owned_child_reaped': True, 'owned_group_absent': absent,
    'stdout_sha256': sha(stdout), 'stderr_sha256': sha(stderr), 'CI_success_claimed': False}
with (OUT / 'vm-retry-request.json').open('x') as stream:
    json.dump(receipt, stream, indent=2); stream.write('\n')
print(json.dumps(receipt))
assert child.returncode == 0 and not timed and absent
