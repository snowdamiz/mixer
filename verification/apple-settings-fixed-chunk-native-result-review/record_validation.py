#!/usr/bin/env python3
"""Record the offline validator only. No native/network/Git dispatch capability."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

base = Path(__file__).resolve().parent
root = base.parents[1]
source = base / 'validate.py'
out = base / 'commands/final-validation'
out.mkdir(parents=True, exist_ok=False)
command = [sys.executable, '-B', str(source)]
start = datetime.datetime.now(datetime.UTC).isoformat()
clock = time.monotonic()
result = subprocess.run(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
elapsed = time.monotonic() - clock
(out / 'stdout.json').write_bytes(result.stdout)
(out / 'stderr.log').write_bytes(result.stderr)
sha = lambda raw: hashlib.sha256(raw).hexdigest()
receipt = {'schema': 1, 'argv': command, 'cwd': str(root), 'startedUTC': start,
           'finishedUTC': datetime.datetime.now(datetime.UTC).isoformat(), 'elapsedSeconds': elapsed,
           'exitCode': result.returncode, 'pythonVersion': sys.version, 'pythonExecutable': sys.executable,
           'validatorSHA256': sha(source.read_bytes()),
           'stdoutSHA256': sha(result.stdout), 'stderrSHA256': sha(result.stderr),
           'scope': 'Offline frozen evidence hash/archive checks, exact unchanged pure oracle replay, host negative controls and public SDK source checks only',
           'nativeAttemptsByReview': 0, 'nativeQueriesByReview': 0, 'nativeCompileByReview': False,
           'gaAccepted': False, 'physicalPhones': 'disconnected-deferred'}
(out / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
parsed = json.loads(result.stdout)
print(json.dumps({'exitCode': result.returncode, 'passed': parsed['passed'], 'checks': len(parsed['checks']), 'inputs': len(parsed['inputs']), 'receipt': str(out / 'receipt.json')}))
sys.exit(result.returncode)
