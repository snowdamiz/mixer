"""Run one bounded Python-only review control and retain its command/output."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
name, target, optimize = sys.argv[1:]
argv = [sys.executable, '-B'] + (['-O'] if optimize == 'optimized' else [])
if target == 'supplied':
    argv += ['-m', 'unittest', 'discover', '-s', 'scripts/ci/tests',
             '-p', 'test_android_generated_java_runner.py', '-v']
else:
    argv += [str(HERE / 'independent_controls.py')]
temporary = HERE / 'tmp' / name
temporary.mkdir()
env = os.environ.copy()
env.update(TMPDIR=str(temporary), PYTHONDONTWRITEBYTECODE='1')
start = time.monotonic()
result = subprocess.run(argv, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT, timeout=55)
log = HERE / (name + '.log')
log.write_bytes(result.stdout)
remaining = sorted(str(p.relative_to(temporary)) for p in temporary.rglob('*'))
if not remaining:
    temporary.rmdir()
record = {'argv': argv, 'cwd': str(ROOT), 'observed_utc': datetime.now(timezone.utc).isoformat(),
          'timeout_seconds': 55, 'elapsed_seconds': round(time.monotonic() - start, 3),
          'exit_code': result.returncode, 'log': log.name, 'bytes': len(result.stdout),
          'sha256': hashlib.sha256(result.stdout).hexdigest(),
          'temporary_entries_remaining': remaining, 'temporary_directory_removed': not temporary.exists()}
(HERE / (name + '-command.json')).write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
print(json.dumps(record))
sys.exit(result.returncode)
