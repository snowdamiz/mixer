#!/usr/bin/env python3
"""Record the accepted verification CLI with native/runtime execution blocked."""
import contextlib
import datetime
import hashlib
import io
import json
import pathlib
import runpy
import sys
import time

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PACKET = ROOT / 'verification/apple-toggle-keyboard-full-case-v3-adapter'
EXPECTED = '137b6dc9b681eff1358712c34d9b71a3b356072ee6954b4a99e9a8c32b60f46b'
COMMAND = [sys.executable, '-B', str(pathlib.Path(__file__).resolve())]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


attempts = []
def audit(event, args):
    if event in {'subprocess.Popen', 'os.system', 'os.posix_spawn', 'os.fork', 'os.forkpty',
                 'os.exec', 'socket.connect', 'socket.bind', 'socket.getaddrinfo'}:
        attempts.append(event)
        raise AssertionError('Prohibited process/network/native action: ' + event)


sys.addaudithook(audit)
assert sha(PACKET / 'packet-seal.json') == EXPECTED
stdout, stderr = io.StringIO(), io.StringIO()
start = time.monotonic()
with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
    runpy.run_path(str(PACKET / 'verify_isolated.py'), run_name='__main__')
assert sha(PACKET / 'packet-seal.json') == EXPECTED
assert not attempts
(BASE / 'isolated.stdout').write_text(stdout.getvalue())
(BASE / 'isolated.stderr').write_text(stderr.getvalue())
result = json.loads(stdout.getvalue())
assert result['sealSHA256'] == EXPECTED and result['nativeExecution'] is False
receipt = dict(schema=1, observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               argv=COMMAND, executedVerification=str(PACKET / 'verify_isolated.py'), cwd=str(ROOT),
               pythonVersion=sys.version, pythonExecutable=str(pathlib.Path(sys.executable).resolve()),
               pythonBinarySHA256=sha(pathlib.Path(sys.executable).resolve()),
               reviewSourceSHA256=sha(pathlib.Path(__file__).resolve()),
               selectedVerificationSHA256=sha(PACKET / 'verify_isolated.py'),
               adapterSealSHA256=EXPECTED, elapsedSeconds=time.monotonic()-start, exitCode=0,
               stdoutSHA256=sha(BASE / 'isolated.stdout'), stderrSHA256=sha(BASE / 'isolated.stderr'),
               selectedRuntimeExecutionBlocked=True, processNetworkBoundaryAttempts=attempts,
               nativeInstancesQueried=False, compilerInvoked=False, nativeExecution=False,
               sourceRevision=json.loads((ROOT / 'verification/apple-toggle-keyboard-full-case-root-review/v3-source/acceptance.json').read_bytes())['sourceRevision'],
               revisionObservation='Inherited root acceptance metadata; no Git query',
               physicalPhones='disconnected-deferred', nativeAccepted=False, gaAccepted=False)
(BASE / 'isolated.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
print(json.dumps(dict(status='passed-isolated-verification', adapterSealSHA256=EXPECTED, nativeExecution=False)))
