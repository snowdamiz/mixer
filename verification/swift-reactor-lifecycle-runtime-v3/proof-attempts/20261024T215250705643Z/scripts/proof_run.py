#!/usr/bin/env python3
"""Retain every proof attempt, command, tool version and exact proof script set."""
from pathlib import Path
import datetime, gzip, subprocess, sys
import collect as c

name = sys.argv[1]
assert name in ['reconcile.py', 'verify_pre_runtime.py']
attempt = c.HERE / 'proof-attempts' / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
attempt.mkdir(parents=True)
for script in c.HERE.glob('*.py'):
    c.save(attempt / 'scripts' / script.name, script.read_bytes())
argv = [sys.executable, '-B', str(c.HERE / name)]
before = c.manifest(c.HERE / 'candidate')
result = subprocess.run(argv, cwd=c.ROOT, capture_output=True)
c.save(attempt / 'stdout.log.gz', gzip.compress(result.stdout, mtime=0))
c.save(attempt / 'stderr.log.gz', gzip.compress(result.stderr, mtime=0))
c.save(attempt / 'command.json', {'argv': argv, 'cwd': str(c.ROOT), 'pythonVersion': sys.version, 'pythonExecutableSHA256': c.sha(Path(sys.executable).read_bytes()), 'exitCode': result.returncode, 'sourceClosure': c.sha(c.enc(before)), 'sourceUnchanged': before == c.manifest(c.HERE / 'candidate'), 'compilerOrRuntimeExecutedByProof': False})
print(str(attempt))
print(result.stdout.decode(errors='replace')[-10000:])
print(result.stderr.decode(errors='replace')[-10000:])
sys.exit(result.returncode)
