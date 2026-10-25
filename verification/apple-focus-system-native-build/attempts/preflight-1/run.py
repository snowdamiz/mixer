#!/usr/bin/env python3
"""Once-only driver wrapper retaining EOF, exit and owned group observations."""
import datetime
import os
import signal
import subprocess
import sys
import time
from common import *

def members(group):
    r = subprocess.run(['/bin/ps', '-axo', 'pid=,pgid='], capture_output=True, timeout=10, check=True)
    assert not r.stderr
    return [int(s.split()[0]) for s in r.stdout.decode().splitlines() if int(s.split()[1]) == group]

def main():
    target = BASE / 'driver-command.json'
    assert not target.exists() and not OUT.exists(), 'Preserve earlier execution'
    argv = [sys.executable, '-B', str(BASE / 'build.py')]
    initial = {'argv': argv, 'cwd': str(ROOT), 'script': binding(BASE / 'build.py'), 'common': binding(BASE / 'common.py'),
               'python': sys.version, 'startedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'timeoutSeconds': 900}
    target.write_bytes(canonical(initial))
    stamp = time.monotonic()
    p = subprocess.Popen(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    sent, timedout = [], False
    try: out, err = p.communicate(timeout=900)
    except subprocess.TimeoutExpired:
        timedout = True
        if members(p.pid): os.killpg(p.pid, signal.SIGTERM); sent.append('SIGTERM')
        try: out, err = p.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            if members(p.pid): os.killpg(p.pid, signal.SIGKILL); sent.append('SIGKILL')
            out, err = p.communicate(timeout=5)
    (BASE / 'driver.stdout').write_bytes(out)
    (BASE / 'driver.stderr').write_bytes(err)
    receipt = {**initial, 'exitCode': p.returncode, 'ownedPID': p.pid, 'ownedPGID': p.pid,
               'processGroupAbsent': not members(p.pid), 'stdoutEOF': True, 'stderrEOF': True, 'timedOut': timedout,
               'signalsSent': sent, 'elapsedSeconds': time.monotonic() - stamp,
               'stdout': binding(BASE / 'driver.stdout'), 'stderr': binding(BASE / 'driver.stderr')}
    (BASE / 'driver-receipt.json').write_bytes(canonical(receipt))
    print(out.decode(), end='')
    if err: print(err.decode(), file=sys.stderr, end='')
    print(json.dumps({'driverExitCode': p.returncode, 'driverGroupAbsent': receipt['processGroupAbsent'], 'stdoutEOF': True, 'stderrEOF': True}))
    return p.returncode

if __name__ == '__main__': sys.exit(main())
