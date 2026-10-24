#!/usr/bin/env python3
"""Offline evidence check for the test-only concurrency/capture repair."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
receipt = json.loads((HERE / 'root-acceptance.json').read_text())
for name, expected in receipt['bindings'].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
candidate = json.loads((HERE / 'candidate-1/receipt.json').read_text())
assert candidate['status'] == 'passed-test-only-observer-concurrency-repair'
assert candidate['runs'] == 8 and candidate['testsPerRun'] == 6
assert candidate['unchangedControlRowsPerRun'] == 795
for name in ['old-captured-concurrent.json', 'old-captured-single.json']:
    assert json.loads((HERE / name).read_text())['exitCode'] == 101
assert not receipt['engineSourceChanged'] and not receipt['nativeRuntime'] and not receipt['gaAcceptance']
print(json.dumps({'status': 'verified-saved-test-only-repair', 'bindings': len(receipt['bindings']),
                  'hostedRecheck': receipt['hostedRecheck']}))
