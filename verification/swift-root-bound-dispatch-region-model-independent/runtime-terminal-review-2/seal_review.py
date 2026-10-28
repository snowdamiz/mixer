#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

D = Path(__file__).resolve().parent
members = []
for path in sorted(D.rglob('*')):
    assert not path.is_symlink()
    if path.is_file() and path.name != 'seal.json':
        raw = path.read_bytes()
        members.append({'path': path.relative_to(D).as_posix(), 'bytes': len(raw),
                        'sha256': hashlib.sha256(raw).hexdigest()})
assert len(members) == 8 and (D / 'review.stderr').read_bytes() == b''
report = json.loads((D / 'review-result.json').read_bytes())
assert report['acceptance_recommended'] == 'ISOLATED_SYNTHETIC_HOST_MODEL_ONLY'
assert report['compile_exit'] == 0 and report['tests_passed'] == 24
assert report['historical_receipt_preserved_failed'] is True
seal = {'schema': 1, 'status': 'FROZEN_INDEPENDENT_SUCCESSOR_TERMINAL_REVIEW_24_HOST_TESTS_ACCEPTABLE_MODEL_ONLY',
    'member_count': len(members), 'members': members,
    'tree_sha256': hashlib.sha256(json.dumps(members, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
    'root_release_sha256': report['root_release_sha256'], 'controller_sha256': report['controller_sha256'],
    'plan_sha256': report['plan_sha256'], 'compile_exit': 0, 'tests_passed': 24,
    'old_failed_attempt_preserved': True, 'accepted_scope': 'ISOLATED_SYNTHETIC_HOST_MODEL_ONLY',
    'new_controller_model_compiler_runtime_executed_by_reviewer': False,
    'physical_prices_grants_funding_ownership_product_GA_accepted': False}
with (D / 'seal.json').open('x') as stream:
    json.dump(seal, stream, indent=2, sort_keys=True)
    stream.write('\n')
print(json.dumps({'seal_sha256': hashlib.sha256((D / 'seal.json').read_bytes()).hexdigest(),
                  'tree_sha256': seal['tree_sha256'], 'member_count': len(members),
                  'review_result_sha256': hashlib.sha256((D / 'review-result.json').read_bytes()).hexdigest()}))
