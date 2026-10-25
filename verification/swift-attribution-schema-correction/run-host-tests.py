#!/usr/bin/env python3
"""One bounded host-only command with exact input/output and environment receipt."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time

H = Path(__file__).resolve().parent
R = H.parent.parent
P = H.parent / 'swift-current-attribution-full-preparation'
Q = H.parent / 'swift-current-attribution-preparation-review'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
save = lambda p, v: Path(p).write_text(json.dumps(v, indent=2, sort_keys=True) + '\n')
name = sys.argv[1]
directory = H / 'commands' / name
assert not directory.exists()
assert not (H / 'owned-scratch').exists() and not (H / 'owned-tmp').exists()
assert not (H / 'root-selection.json').exists() and not (H / 'target-attempt-started.json').exists()
directory.mkdir(parents=True)
code = {n: sha(H / n) for n in ('diagnostic.py', 'telemetry.py', 'test_driver.py', 'test_schema.py', 'test_selection.py', 'run-host-tests.py')}
bindings = {str(p.relative_to(R)): sha(p) for p in
            [P / 'prepared-seal.json', Q / 'seal.json', *sorted((Q / 'parser-reproductions').glob('*.stdout'))]}
argv = [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', str(H), '-p', 'test_*.py', '-v']
env = {k: v for k, v in os.environ.items() if k in ('HOME', 'USER', 'LOGNAME', 'PATH', 'TMPDIR')}
env['PYTHONDONTWRITEBYTECODE'] = '1'
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
clock = time.monotonic()
(H / 'owned-scratch/tmp').mkdir(parents=True)
(H / 'owned-tmp').mkdir()
save(directory / 'started.json', {'argv': argv, 'cwd': str(R), 'UTC': started,
    'codeSHA256': code, 'externalInputsSHA256': bindings, 'environment': env,
    'scope': 'finite Python host tests only; native/guest/real-target dispatch mocked'})
with (directory / 'stdout').open('wb') as out, (directory / 'stderr').open('wb') as err:
    child = subprocess.Popen(argv, cwd=R, env=env, stdout=out, stderr=err, start_new_session=True)
    exit_code = child.wait(timeout=45)
ps = subprocess.check_output(['/bin/ps', '-axo', 'pid=,pgid=,comm='], text=True, timeout=10)
group_rows = [r for r in ps.splitlines() if len(r.split()) >= 2 and int(r.split()[1]) == child.pid]
assert not group_rows
scratch_files = [p for n in ('owned-scratch', 'owned-tmp') for p in (H / n).rglob('*') if p.is_file()]
assert not scratch_files, [str(p) for p in scratch_files]
for n in ('owned-scratch', 'owned-tmp'): shutil.rmtree(H / n)
assert code == {n: sha(H / n) for n in code}
assert bindings == {n: sha(R / n) for n in bindings}
receipt = {'schema': 1, 'argv': argv, 'cwd': str(R), 'environment': env, 'UTC': started,
    'python': {'path': sys.executable, 'resolvedPath': str(Path(sys.executable).resolve()),
               'sha256': sha(sys.executable), 'version': sys.version},
    'platform': platform.platform(), 'machine': platform.machine(),
    'sourceRevisionContext': '7b6048642b42e4900cccff4e14aa0fe8949ab35e',
    'sourceRevisionMeaning': 'root delivery context from independent review; immutable file digests authoritative; no Git query',
    'codeSHA256': code, 'externalInputsSHA256': bindings, 'inputsUnchanged': True,
    'exitCode': exit_code, 'passed': exit_code == 0, 'durationSeconds': time.monotonic() - clock,
    'stdoutSHA256': sha(directory / 'stdout'), 'stderrSHA256': sha(directory / 'stderr'),
    'processGroup': child.pid, 'processGroupEmpty': not group_rows, 'signalsSent': [],
    'rawStreamEOFConfirmed': True, 'scratchCleaned': True, 'ownedScratchBytesRemoved': 0,
    'fullTargetAttempts': 0, 'realTargetValidations': 0, 'realTargetInitializeCalls': 0,
    'realTargetCorpusCalls': 0, 'nativeOrDeviceRuns': 0, 'productionSourceChanged': False}
save(directory / 'receipt.json', receipt)
print(json.dumps(receipt, sort_keys=True))
raise SystemExit(exit_code)
