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
assert len(members) == 9 and (D / 'review.stderr').read_bytes() == b''
report = json.loads((D / 'review-result.json').read_bytes())
assert report['root_execution_release_recommended'] is True and report['findings'] == []
seal = {'schema': 1, 'status': 'FROZEN_INDEPENDENT_V4_CONTROLLER_SUCCESSOR_PLAN_SOURCE_REVIEW_SINGLE_ATTEMPT_RECOMMENDED_NOT_EXECUTED',
    'member_count': len(members), 'members': members,
    'tree_sha256': hashlib.sha256(json.dumps(members, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
    'controller_sha256': report['controller_sha256'], 'plan_sha256': report['plan_sha256'],
    'root_execution_release_recommended': True, 'old_failed_attempt_preserved': True,
    'compiler_or_test_pass_accepted': False, 'controller_or_model_imported_or_executed': False}
with (D / 'seal.json').open('x') as stream:
    json.dump(seal, stream, indent=2, sort_keys=True)
    stream.write('\n')
print(json.dumps({'seal_sha256': hashlib.sha256((D / 'seal.json').read_bytes()).hexdigest(),
                  'tree_sha256': seal['tree_sha256'], 'member_count': len(members),
                  'review_result_sha256': hashlib.sha256((D / 'review-result.json').read_bytes()).hexdigest()}))
