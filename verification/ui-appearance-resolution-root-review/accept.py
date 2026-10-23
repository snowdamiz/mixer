#!/usr/bin/env python3
"""Bind the frozen producer and independent public-API appearance evidence."""
import datetime
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P = ROOT / 'verification/ui-appearance-resolution/candidate-2'
R = ROOT / 'verification/ui-appearance-resolution-review/candidate-2'
sha = lambda data: hashlib.sha256(data).hexdigest()
p = json.loads((P / 'receipt.json').read_text())
r = json.loads((R / 'receipt.json').read_text())
lock = json.loads((P / 'input-lock.json').read_text())
assert p['status'] == 'passed-pure-data-and-compilation-only'
assert r['status'] == 'passed-pure-data-independent-review-only' and not r['blockers']
digest = sha(json.dumps(lock['files'], sort_keys=True, separators=(',', ':')).encode())
assert digest == lock['source_tree_sha256'] == p['source_tree_sha256'] == r['producer_source_collection_sha256']
assert lock['files'] == r['producer_source_files'] and len(lock['files']) == 61
bindings = {}
checks = 0


def bind(path, expected=None):
    global checks
    data = path.read_bytes()
    actual = sha(data)
    if expected is not None:
        assert actual == expected, str(path)
    bindings[str(path.relative_to(ROOT))] = actual
    checks += 1
    return data


for path, expected in lock['files'].items():
    for base in [ROOT, P / 'inputs', R / 'inputs']:
        bind(base / path, expected)
bind(P / 'receipt.json', r['producer_receipt_sha256'])
bind(R / 'producer-receipt.json', r['producer_receipt_sha256'])
bind(P / 'input-lock.json', r['producer_input_lock_sha256'])
bind(R / 'producer-input-lock.json', r['producer_input_lock_sha256'])
for path, expected in r['review_sources'].items():
    bind(R.parent / path, expected)
assert sha(json.dumps(r['review_sources'], sort_keys=True, separators=(',', ':')).encode()) == r['review_source_collection_sha256']
for receipt in [p, r]:
    for command in receipt['commands']:
        expected_failure = command.get('expected_failure', False)
        assert (command['exit_code'] != 0) == expected_failure
        log = bind(ROOT / command['log'], command['log_sha256']).decode()
        if expected_failure:
            assert 'disabled' in log and 'let' in log
for mode in ['debug', 'release']:
    result = r['results'][mode]
    assert result['status'] == 'passed' and result['assertions'] == 350077 and result['cases'] == 29278
    log = (R / ('independent-' + mode + '.log')).read_text()
    parsed = [json.loads(line.removeprefix('REVIEW_RESULT ')) for line in log.splitlines() if line.startswith('REVIEW_RESULT ')]
    assert parsed == [result]
    tests = re.findall(r'Test run with (\d+) tests in \d+ suites passed', (P / ('sdk-' + mode + '.log')).read_text())
    assert sorted(map(int, tests)) == [2, 10, 74], tests
assert r['results']['debug'] == r['results']['release']
for path, meta in p['artifacts'].items():
    assert len(bind(ROOT / path, meta['sha256'])) == meta['bytes']
for path in [Path(__file__), R / 'receipt.json', R.parent / 'README.md']:
    bind(path)
result = {
    'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'decision': 'accepted-pure-appearance-resolution-data-only',
    'integrator': 'root', 'independent_reviewer': 'appearance_resolution_review',
    'source_tree_sha256': digest, 'binding_checks': checks, 'bindings': bindings,
    'sdk_tests_per_mode': 86, 'new_focused_tests_per_mode': 20,
    'independent_cases_per_mode': 29278, 'independent_assertions_per_mode': 350077,
    'review': 'All ten kinds; distinct translucent palettes and state combinations; exact scale and spacing boundaries; aggregate height floors; full-configuration admission; identity/event preservation. Root inspected the immutable resolver, admission order, disabled inheritance and alpha modulation.',
    'limits': 'Pure data and host/iOS/official Android module compilation only. sharedCandidate1 tokens remain provisional against the unchanged iOS reference. No native adapter consumption, font/resource capture, installed or signed authority, numerical geometry/raster parity, physical devices, immutable FieldLog publication, or GA qualification. Compiled module hashes are local observations; frozen source and command logs are retained.'
}
(HERE / 'acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'decision': result['decision'], 'checks': checks}))
