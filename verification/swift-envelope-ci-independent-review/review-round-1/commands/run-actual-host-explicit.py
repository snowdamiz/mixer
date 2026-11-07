#!/usr/bin/env python3
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROUND = Path(__file__).resolve().parents[1]
REPO = ROUND.parents[2]
runner = ROUND / 'portable-root/scripts/ci/check-analyzer-envelope.py'
compiler = Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc')
out = ROUND / 'portable-root/runs/actual-host-explicit'
argv = [sys.executable, '-B', str(runner), '--out', str(out), '--rustc', str(compiler)]
row = {'schema': 1, 'argv': argv, 'cwd': str(REPO), 'started_utc': datetime.now(timezone.utc).isoformat(),
       'timeout_seconds': 600, 'runner_sha256': hashlib.sha256(runner.read_bytes()).hexdigest(),
       'compiler_sha256_before': hashlib.sha256(compiler.read_bytes()).hexdigest(),
       'scope': 'Fresh full exact-byte portable host closure; prior PATH-missing attempt remains failed.'}
start = time.monotonic()
with (ROUND / 'actual-host-explicit.stdout').open('xb') as stdout, (ROUND / 'actual-host-explicit.stderr').open('xb') as stderr:
    result = subprocess.run(argv, cwd=REPO, stdout=stdout, stderr=stderr, timeout=600)
row.update({'exit': result.returncode, 'finished_utc': datetime.now(timezone.utc).isoformat(), 'elapsed_seconds': round(time.monotonic()-start,6)})
for name in ('stdout','stderr'):
    path = ROUND / ('actual-host-explicit.' + name)
    row[name] = {'path':path.name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
with (ROUND / 'actual-host-explicit-command.json').open('x') as stream:
    json.dump(row, stream, indent=2, sort_keys=True)
    stream.write('\n')
print(json.dumps({'exit':result.returncode,'elapsed_seconds':row['elapsed_seconds'],'receipt':str(out/'receipt.json')},sort_keys=True))
sys.exit(result.returncode)
