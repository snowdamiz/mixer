#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
old = json.loads((ROOT / 'verification/capability-durable-io-review/2026-10-23-final/receipt.json').read_text())
base = next(x['argv'] for x in old['commands'] if x['name'] == 'private-io-opacity')[:-1]
base = [x.replace('/durable-io-qualified/', '/execution-policy/') for x in base]
record = {'scope': 'Public opacity typecheck with positive control; no execution authority', 'commands': []}
for name, expected in [('public-control', 0), ('private-policy', 1)]:
    args = base + [str(HERE / (name + '.swift'))]
    result = subprocess.run(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log = HERE / (name + '.log'); log.write_bytes(result.stdout)
    record['commands'].append({'argv': args, 'cwd': str(ROOT), 'exit_code': result.returncode, 'expected_exit': expected,
                              'log': str(log.relative_to(ROOT)), 'log_sha256': hashlib.sha256(result.stdout).hexdigest()})
    if result.returncode != expected: raise RuntimeError(name)
    if expected and b"cannot find type 'CapabilityExecutionPolicy' in scope" not in result.stdout: raise RuntimeError('wrong diagnostic')
record['status'] = 'passed'
(HERE / 'opacity-receipt.json').write_text(json.dumps(record, indent=2) + '\n')
print(record['status'])
