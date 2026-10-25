#!/usr/bin/env python3
"""Record one packet-owned Python command with complete streams and owned group absence."""
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


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def absent(group):
    try:
        os.killpg(group, 0)
        return False
    except ProcessLookupError:
        return True


def main():
    name, script, *args = sys.argv[1:]
    if not name.replace('-', '').isalnum() or script not in {'bootstrap.py', 'prepare.py', 'run_controls.py', 'seal.py'}:
        raise ValueError('Bound packet command required')
    folder = BASE / 'commands' / name
    folder.mkdir(parents=True, exist_ok=False)
    argv = [sys.executable, '-B', str(BASE / script), *args]
    started = time.monotonic()
    process = subprocess.Popen(argv, cwd=BASE.parents[1], env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    timed_out = False
    signals = []
    try:
        stdout, stderr = process.communicate(timeout=55)
    except subprocess.TimeoutExpired:
        timed_out = True
        for selected_signal in [signal.SIGTERM, signal.SIGKILL]:
            if not absent(process.pid):
                os.killpg(process.pid, selected_signal); signals.append(int(selected_signal))
            try:
                stdout, stderr = process.communicate(timeout=2)
                break
            except subprocess.TimeoutExpired:
                continue
        else:
            raise RuntimeError('Owned command pipes did not reach EOF')
    if not absent(process.pid):
        os.killpg(process.pid, signal.SIGKILL); signals.append(int(signal.SIGKILL))
    group_absent = absent(process.pid)
    (folder / 'stdout.log').write_bytes(stdout)
    (folder / 'stderr.log').write_bytes(stderr)
    receipt = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'argv': argv, 'cwd': str(BASE.parents[1]), 'sourceSHA256': sha((BASE / script).read_bytes()),
               'sourceRevisionContext': '9102ad3ee1247187c01ea5f55c42caaac882961b',
               'compileSourceTreeSHA256': 'ddd4036d785c1c5f0161f8146ee7295b8df8dcd2bd615b45eebefc4112fcfb0d',
               'commandSourceFiles': {item.name: {'bytes': item.stat().st_size, 'sha256': sha(item.read_bytes())}
                                      for item in sorted(BASE.glob('*.py'))},
               'python': sys.version, 'pythonExecutable': str(Path(sys.executable).resolve()),
               'pythonExecutableSHA256': sha(Path(sys.executable).resolve().read_bytes()),
               'PID': process.pid, 'processGroup': process.pid, 'startNewSession': True,
               'exitCode': process.returncode, 'timedOut': timed_out, 'signals': signals,
               'ownedProcessGroup': {'state': 'absent' if group_absent else 'present', 'targetProcessGroup': process.pid},
               'elapsedSeconds': time.monotonic() - started,
               'streams': {name: {'bytes': len(raw), 'sha256': sha(raw), 'eof': True, 'readerFailed': False}
                           for name, raw in [('stdout', stdout), ('stderr', stderr)]},
               'nativeExecuted': False, 'scope': 'One bounded packet-owned Python preparation/control command'}
    (folder / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'command': name, 'exitCode': process.returncode, 'timedOut': timed_out,
                      'ownedGroupAbsent': group_absent, 'stdoutBytes': len(stdout), 'stderrBytes': len(stderr)}))
    if process.returncode != 0 or timed_out or not group_absent:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
