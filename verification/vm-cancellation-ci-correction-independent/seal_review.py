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
assert len(members) == 16 and (D / 'review.stderr').read_bytes() == b''
report = json.loads((D / 'review-result.json').read_bytes())
assert report['findings'] == [] and report['bounded_validation_recommended'] is True
assert report['test_pass_claimed'] is False and report['remote_nested_cause_diagnosed'] is False
seal = {'schema': 1, 'status': 'FROZEN_INDEPENDENT_TEST_ONLY_CANCELLATION_SOURCE_REVIEW_ORDINARY_VALIDATION_RECOMMENDED',
    'member_count': len(members), 'members': members,
    'tree_sha256': hashlib.sha256(json.dumps(members, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
    'source_revision': report['source_revision'], 'test_after_sha256': report['test_after_sha256'],
    'validation_plan_sha256': report['validation_plan_sha256'],
    'root_selected_validation': report['root_selected_validation'],
    'source_validation_recommended': True, 'compiler_test_or_remote_cause_pass_claimed': False,
    'new_external_thread_or_compute_bound_latency_qualification': False}
with (D / 'seal.json').open('x') as stream:
    json.dump(seal, stream, indent=2, sort_keys=True)
    stream.write('\n')
print(json.dumps({'seal_sha256': hashlib.sha256((D / 'seal.json').read_bytes()).hexdigest(),
                  'tree_sha256': seal['tree_sha256'], 'member_count': len(members),
                  'review_result_sha256': hashlib.sha256((D / 'review-result.json').read_bytes()).hexdigest()}))
