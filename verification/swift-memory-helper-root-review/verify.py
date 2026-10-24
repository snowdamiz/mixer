#!/usr/bin/env python3
"""Verify frozen prerequisite acceptance, never memory behavior or release authority."""
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--live-baseline', action='store_true')
args = parser.parse_args()
here = Path(__file__).resolve().parent
root = here.parents[1]
receipt = json.loads((here / 'acceptance.json').read_text())
for name, digest in receipt['bindings'].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
assert receipt['sourceAccountingPreflightAccepted']
assert receipt['isolatedMemoryBehaviorTestingAuthorized']
for name in ['implementationAccepted', 'behaviorAccepted', 'memoryOpcodesExecutedByRoot',
             'liveIntegrated', 'nativeRuntime', 'physicalRuntime', 'gaAcceptance']:
    assert receipt[name] is False, name
assert receipt['producerBindingsVerified'] == 319
assert receipt['reviewBindingsVerified'] == 129
assert all(command['exitCode'] == 0 for command in receipt['commands'])
if args.live_baseline:
    manifest = json.loads((root / 'verification/swift-memory-helper-contract/baseline-source-manifest.json').read_text())
    assert len(manifest) == 121
    for name, digest in manifest.items():
        assert hashlib.sha256((root / 'vm' / name).read_bytes()).hexdigest() == digest, name
print(json.dumps({'verified': True, 'bindings': len(receipt['bindings']),
                  'scope': 'type-borrow-logical-accounting prerequisite only',
                  'behaviorAccepted': False, 'liveBaselineChecked': args.live_baseline}))
