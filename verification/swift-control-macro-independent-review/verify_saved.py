#!/usr/bin/env python3
"""Verify retained independent-review evidence without rerunning host code."""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


path = Path(sys.argv[1]).resolve()
receipt = json.loads(path.read_text())
assert receipt['status'] == 'independent-host-review-passed-bounded-extraction'
assert all(receipt[key] is False for key in ['sourceMutation', 'productHooksAdded', 'swiftExecution',
                                            'nativeRuntime', 'physicalRuntime', 'gaAcceptance'])
details = receipt['details']
assert sha(ROOT / details['producerReceipt']) == details['producerReceiptSHA256']
if 'reviewScriptSHA256' in details:
    assert sha(path.parent / 'review.py') == details['reviewScriptSHA256']
for command in receipt['commands']:
    assert command['exitCode'] == 0
    assert command['diagnosticBootstrap'] is False
    for stream in ['stdout', 'stderr']:
        assert sha(path.parent / command[stream]) == command[stream + 'SHA256']
for key in ['freshPublicReplay', 'freshPrivateReplay']:
    if key in details:
        assert sha(Path(details[key]['binary'])) == details[key]['binarySHA256']
seal_path = HERE / 'seal.json'
if seal_path.exists():
    for name, digest in json.loads(seal_path.read_text())['bindings'].items():
        assert sha(ROOT / name) == digest, name
print(json.dumps(dict(status='verified-saved-independent-bounded-host-review',
                      receipt=str(path.relative_to(ROOT)), nativeRuntime=False,
                      swiftExecution=False, gaAcceptance=False), sort_keys=True))
