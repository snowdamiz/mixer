#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

D = Path(__file__).resolve().parent
entries = []
for path in sorted(D.rglob('*')):
    assert not path.is_symlink()
    if path.is_file() and path.name != 'seal.json':
        raw = path.read_bytes()
        entries.append({'path': path.relative_to(D).as_posix(), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
assert len(entries) == 7 and (D/'review.stderr').read_bytes() == b''
result = json.loads((D/'review-result.json').read_bytes())
assert result['findings'] == [] and result['passed'] == 16 and result['before_after_custody_equal'] is True
assert result['runtime_pins_reconstructed'] == 76 and result['checked_input_members'] == 86
seal = {'schema':1,'status':'FROZEN_INDEPENDENT_SYNTHETIC16_HOST_TERMINAL_REVIEW_ACCEPTED_SCOPE_ONLY',
 'member_count':len(entries),'member_bytes':sum(row['bytes'] for row in entries),'members':entries,
 'tree_sha256':hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
 'root_release_sha256':result['root_release']['sha256'],'producer_seal_sha256':result['producer_seal']['sha256'],
 'root_receipt_sha256':result['root_receipt']['sha256'],'root_observation_sha256':result['root_observation']['sha256'],
 'first_refusal_preserved':True,'synthetic_host_only_accepted':True,
 'this_review_candidate_import_test_actual_input_compiler_capture_runtime_or_process_probe_actions':0,
 'all_results_local_geometry_only':True,'complete_capacity_accepted':False,
 'physical_capacity_prices_backings_root_funding_product_GA_accepted':False}
with (D/'seal.json').open('x') as stream:
    json.dump(seal, stream, indent=2, sort_keys=True)
    stream.write('\n')
print(json.dumps({'seal_sha256':hashlib.sha256((D/'seal.json').read_bytes()).hexdigest(),
 'tree_sha256':seal['tree_sha256'],'member_count':len(entries),
 'result_sha256':hashlib.sha256((D/'review-result.json').read_bytes()).hexdigest()}))
