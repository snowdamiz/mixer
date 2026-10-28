#!/usr/bin/env python3
"""Seal this new independent review only; no model execution or old-file writes."""
import hashlib
import json
from pathlib import Path
import sys
import time

D = Path(__file__).resolve().parent
started = time.monotonic()
members = []
for path in sorted(D.rglob('*')):
    assert time.monotonic() - started < 55
    assert not path.is_symlink()
    if path.is_file() and path.name != 'seal.json':
        raw = path.read_bytes()
        members.append({'path': path.relative_to(D).as_posix(), 'bytes': len(raw),
                        'sha256': hashlib.sha256(raw).hexdigest()})
assert len(members) == 10
assert {row['path'] for row in members} == {'REVIEW.md', 'checked-inputs.json', 'review-result.json',
    'review_source.py', 'review.stdout', 'review.stderr', 'seal_review.py',
    'review-attempt-1/review_source.py', 'review-attempt-1/review.stdout', 'review-attempt-1/review.stderr'}
report = json.loads((D / 'review-result.json').read_bytes())
assert report['root_host_compile_test_release_recommended'] is True and report['findings'] == []
assert report['before_after_custody_equal'] is True and report['declared_test_methods'] == 24
assert (D / 'review.stderr').read_bytes() == b''
seal = {'schema': 1,
    'status': 'FROZEN_INDEPENDENT_V2_SOURCE_REVIEW_R01_CORRECTED_HOST_PLAN_RECOMMENDED_NOT_EXECUTED',
    'member_count': len(members), 'member_bytes': sum(row['bytes'] for row in members), 'members': members,
    'tree_sha256': hashlib.sha256(json.dumps(members, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
    'producer_seal_sha256': report['producer_seal_sha256'], 'host_plan_sha256': report['host_plan_sha256'],
    'review_source_command': report['command'],
    'seal_command': [sys.executable, '-B', 'verification/swift-root-bound-dispatch-region-model-independent/v2-review/seal_review.py'],
    'declared_tests': 24, 'compiled_or_executed_tests': 0,
    'root_host_compile_test_release_recommended': True, 'actual_physical_prices_grants_funding_ownership_GA_accepted': False}
with (D / 'seal.json').open('x') as stream:
    json.dump(seal, stream, indent=2, sort_keys=True)
    stream.write('\n')
print(json.dumps({'seal_sha256': hashlib.sha256((D / 'seal.json').read_bytes()).hexdigest(),
                  'tree_sha256': seal['tree_sha256'], 'member_count': seal['member_count'],
                  'review_result_sha256': hashlib.sha256((D / 'review-result.json').read_bytes()).hexdigest()}))
