#!/usr/bin/env python3
"""Complete an evidence receipt from retained actual XCTest stderr, no rerun."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

here = Path(__file__).resolve().parent
root = here.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
original = here / 'initial-receipt.json'
r = json.loads(original.read_text())
assert sha(here / 'initial-run.py') == r['driver_sha256']
for c in r['commands']:
    assert c['exit_code'] == 0
    assert sha(here / c['log']) == c['log_sha256']
counts = re.findall(r'Executed (\d+) tests?, with 0 failures', (here / 'xctest-run.log').read_text())
assert counts and counts[-1] == '6'
binary = here / '.build/ConcreteTests.xctest/Contents/MacOS/ConcreteTests'
command = ['nm', '-gU', str(binary)]
result = subprocess.run(command, capture_output=True)
assert result.returncode == 0
log = here / 'defined-symbols.log'
log.write_bytes(result.stdout + result.stderr)
assert re.search(rb'\b_mixer_vm_\w+$', result.stdout, re.M) is None
r['commands'].append({'name': 'defined-symbols', 'command': command, 'exit_code': 0, 'log': log.name, 'log_sha256': sha(log)})
assert sha(root / r['source']) == r['new_sha256']
owner_path = root / 'verification/capability-cold-start-runtime/2026-10-23-candidate-1/receipt.json'
assert sha(owner_path) == r['owner_receipt_sha256']
owner = json.loads(owner_path.read_text())
for entry in owner['artifacts']['debug'].values():
    assert sha(Path(entry['path'])) == entry['sha256']
r.update(status='both Wasm fixture variants byte-identical and six XCTest functions passed', tests=6,
         artifact={'path': str(binary), 'sha256': sha(binary)}, production_artifacts=owner['artifacts']['debug'],
         initial_receipt_sha256=sha(original), corrected_driver_sha256=sha(here / 'run.py'),
         reconciliation_driver_sha256=sha(Path(__file__)),
         evidence_note='Initial driver read stdout only when counting XCTest results; actual six-test pass was in retained stderr. Both fixture parity and tests succeeded. Receipt completed from combined original log without repeating tests; initial driver and receipt preserved.')
(here / 'receipt.json').write_text(json.dumps(r, indent=2) + '\n')
print(json.dumps({'status': r['status'], 'receipt_sha256': sha(here / 'receipt.json')}))
