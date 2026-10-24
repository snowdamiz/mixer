#!/usr/bin/env python3
"""Seal only the independent review; never changes producer inputs."""
import datetime
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
target = HERE / 'review-seal.json'
assert not target.exists(), 'Independent review already sealed'
receipt = json.loads((HERE / 'receipt.json').read_bytes())
assert receipt['status'] == 'CHANGES_REQUIRED_DIAGNOSTIC_CONTRACT'
assert receipt['boundFilesVerifiedBeforeAndAfter'] == 92
assert receipt['producerTestsPassed'] == 44 and receipt['unchangedV2TestsPassed'] == 29
assert receipt['independentTests']['contractFindingMethods'] == 3
assert receipt['nativeExecuted'] is False and receipt['compiled'] is False
assert not (HERE / '.scratch').exists()
files = [p for p in HERE.iterdir() if p.is_file()] + [ROOT / 'docs/apple-toggle-keyboard-focus-v3-independent-review.md', ROOT / 'verification/apple-toggle-keyboard-focus-v3-preparation/packet-seal.json', ROOT / 'verification/apple-toggle-keyboard-focus-v3-root-review/selection.json']
mapping = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
value = {'schema': 'mixer.apple-toggle.keyboard-v3-independent-review-seal.1', 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': receipt['status'], 'preparationSealSHA256': receipt['preparationSealSHA256'], 'selectionSHA256': receipt['selectionSHA256'], 'sourceRevisionContext': receipt['sourceRevisionContext'], 'files': mapping, 'fileMapSHA256': hashlib.sha256(json.dumps(mapping, sort_keys=True, separators=(',', ':')).encode()).hexdigest(), 'nativeExecuted': False, 'compiled': False, 'nativeAuthorization': False, 'nativeKeyboardQualification': False, 'carrierAccepted': False, 'gaAccepted': False}
target.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
print(json.dumps({'status': value['status'], 'reviewSealSHA256': hashlib.sha256(target.read_bytes()).hexdigest(), 'files': len(mapping), 'nativeAuthorization': False}, sort_keys=True))
