#!/usr/bin/env python3
"""Bounded outer host Python recorder; selected controls cannot spawn processes."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]


def sha(raw): return hashlib.sha256(raw).hexdigest()


def absent(group):
    try:
        os.killpg(group, 0)
        return False
    except ProcessLookupError:
        return True


def main():
    name, script, *args = sys.argv[1:]
    if not name.replace('-', '').isalnum() or script not in {'review.py', 'seal.py'}:
        raise ValueError('Bound review command required')
    folder = BASE / 'commands' / name; folder.mkdir(parents=True)
    if any(folder.iterdir()): raise ValueError('Preserve existing command evidence')
    if script == 'review.py':
        attempt = BASE / name; attempt.mkdir()
        args = [str(attempt)]
        (attempt / 'review-source.py').write_bytes((BASE / script).read_bytes())
    argv = [sys.executable, '-B', str(BASE / script), *args]
    started = time.monotonic()
    process = subprocess.Popen(argv, cwd=ROOT, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    timed_out, signals = False, []
    try:
        stdout, stderr = process.communicate(timeout=55)
    except subprocess.TimeoutExpired:
        timed_out = True
        for selected in [signal.SIGTERM, signal.SIGKILL]:
            if not absent(process.pid): os.killpg(process.pid, selected); signals.append(int(selected))
            try:
                stdout, stderr = process.communicate(timeout=2)
                break
            except subprocess.TimeoutExpired:
                pass
        else:
            raise RuntimeError('Owned Python command pipes did not reach EOF')
    if not absent(process.pid):
        os.killpg(process.pid, signal.SIGKILL); signals.append(int(signal.SIGKILL))
    group_absent = absent(process.pid)
    (folder / 'stdout.log').write_bytes(stdout); (folder / 'stderr.log').write_bytes(stderr)
    receipt = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'argv': argv, 'cwd': str(ROOT), 'python': sys.version,
        'pythonExecutable': str(Path(sys.executable).resolve()),
        'pythonExecutableSHA256': sha(Path(sys.executable).resolve().read_bytes()),
        'sourceSHA256': sha((BASE / script).read_bytes()),
        'sourceRevisionContext': 'be472ce6424a691de5673e3438d2768264827d23',
        'compileSourceTreeSHA256': '0677712483e4f078cbd10120efd5c9f9d4a13fe31b9f455caa1a984772d2bfeb',
        'runtimeSourceTreeSHA256': '914a446192ea6207abcec314f919c45c9bacf53dd5220d1b2724cbede5175426',
        'PID': process.pid, 'processGroup': process.pid, 'startNewSession': True,
        'exitCode': process.returncode, 'timedOut': timed_out, 'signals': signals,
        'ownedProcessGroup': {'state': 'absent' if group_absent else 'present', 'targetProcessGroup': process.pid},
        'elapsedSeconds': time.monotonic() - started,
        'streams': {key: {'bytes': len(raw), 'sha256': sha(raw), 'eof': True, 'readerFailed': False}
                    for key, raw in [('stdout', stdout), ('stderr', stderr)]},
        'scope': 'One host-only review Python command; outer recorder owns only this child group',
        'nativeExecuted': False, 'nativeExecutionSelected': False}
    (folder / 'receipt.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'command': name, 'exitCode': process.returncode, 'timedOut': timed_out,
                      'ownedGroupAbsent': group_absent, 'stdoutBytes': len(stdout), 'stderrBytes': len(stderr)}))
    if process.returncode != 0 or timed_out or not group_absent: raise SystemExit(1)


if __name__ == '__main__': main()
