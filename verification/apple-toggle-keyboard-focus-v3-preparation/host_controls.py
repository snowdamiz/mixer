#!/usr/bin/env python3
import datetime
import hashlib
import json
import pathlib
import re
import subprocess
import sys
BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
assert not (BASE / 'packet-seal.json').exists(), 'Sealed preparation is immutable'
attempt = len(list(BASE.glob('host-test-attempt-*.json'))) + 1
argv = [sys.executable, '-B', str(BASE / 'test_settings_telemetry.py')]
p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=60)
match = re.search(r'Ran (\d+) tests? in ', p.stderr)
sources = {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(BASE.glob('*.py'))}
value = {'schema': 'mixer.apple-toggle.keyboard-v3-host-controls.1', 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'command': argv, 'pythonVersion': sys.version, 'exitCode': p.returncode, 'testsRun': int(match.group(1)) if match else 0, 'expectedTestsRun': 44, 'stdout': p.stdout, 'stderr': p.stderr, 'sourceFiles': sources, 'nativeExecuted': False}
(BASE / f'host-test-attempt-{attempt}.json').write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
if p.returncode or value['testsRun'] != value['expectedTestsRun']:
    print(p.stderr); raise SystemExit(1)
(BASE / 'host-controls.json').write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
print(json.dumps({'status': 'host-controls-passed', 'testsRun': value['testsRun'], 'nativeExecuted': False}))
