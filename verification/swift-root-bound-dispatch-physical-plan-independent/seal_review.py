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
assert len(members) == 11 and (D / 'review.stderr').read_bytes() == b''
report = json.loads((D / 'review-result.json').read_bytes())
assert report['findings'] == [] and report['capture_or_actual_saved_verifier_release_recommended_now'] is False
assert len(report['next_executable_source_slice_recommended']) == 2
seal = {'schema': 1, 'status': 'FROZEN_INDEPENDENT_SOURCE_ONLY_PHYSICAL_PLAN_REVIEW_TWO_OFFLINE_FILES_RECOMMENDED',
    'member_count': len(members), 'members': members,
    'tree_sha256': hashlib.sha256(json.dumps(members, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
    'producer_seal_sha256': report['producer_seal_sha256'], 'capture_plan_sha256': report['capture_plan_sha256'],
    'next_slice': report['next_executable_source_slice_recommended'], 'prospective_control_families': 16,
    'compiler_capture_or_actual_verifier_run_released': False,
    'physical_capacity_prices_backing_bounds_root_funding_product_GA_accepted': False}
with (D / 'seal.json').open('x') as stream:
    json.dump(seal, stream, indent=2, sort_keys=True)
    stream.write('\n')
print(json.dumps({'seal_sha256': hashlib.sha256((D / 'seal.json').read_bytes()).hexdigest(),
                  'tree_sha256': seal['tree_sha256'], 'member_count': len(members),
                  'review_result_sha256': hashlib.sha256((D / 'review-result.json').read_bytes()).hexdigest()}))
