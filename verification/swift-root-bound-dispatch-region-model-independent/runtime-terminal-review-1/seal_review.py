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
assert len(members) == 6 and (D / 'review.stderr').read_bytes() == b''
report = json.loads((D / 'review-result.json').read_bytes())
assert report['original_result'] == 'FAILED_IMMUTABLE' and report['new_controller_execution_released'] is False
seal = {'schema': 1, 'status': 'FROZEN_INDEPENDENT_FAILED_RUNTIME_TERMINAL_REVIEW_NO_COMPILE_TEST_PASS',
    'member_count': len(members), 'members': members,
    'tree_sha256': hashlib.sha256(json.dumps(members, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
    'controller_sha256': report['controller_sha256'], 'plan_sha256': report['plan_sha256'],
    'original_failed_result_preserved': True, 'compiler_or_test_pass_accepted': False,
    'new_execution_released': False}
with (D / 'seal.json').open('x') as stream:
    json.dump(seal, stream, indent=2, sort_keys=True)
    stream.write('\n')
print(json.dumps({'seal_sha256': hashlib.sha256((D / 'seal.json').read_bytes()).hexdigest(),
                  'tree_sha256': seal['tree_sha256'], 'member_count': len(members),
                  'review_result_sha256': hashlib.sha256((D / 'review-result.json').read_bytes()).hexdigest()}))
