#!/usr/bin/env python3
"""Check accepted immutable bindings without reclassifying later source edits."""
from pathlib import Path
import hashlib
import json

here = Path(__file__).resolve().parent
root = here.parents[1]
receipt = json.loads((here / 'acceptance.json').read_text())
assert receipt['status'] == 'accepted-private-active-frame-contract-for-implementation'
for name, expected in receipt['bindings'].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
assert not any(receipt[key] for key in ['runtimeImplementationAccepted', 'nativeRuntimeAccepted', 'gaGatePassed'])
print(json.dumps({'status': 'verified-private-contract-acceptance-only',
                  'bindings': len(receipt['bindings']), 'frameRuntimeAcceptance': False}))
