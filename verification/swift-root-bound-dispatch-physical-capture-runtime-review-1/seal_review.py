#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

D=Path(__file__).resolve().parent
members=[]
for path in sorted(D.rglob('*')):
    assert not path.is_symlink()
    if path.is_file() and path.name!='seal.json':
        raw=path.read_bytes();members.append({'path':path.relative_to(D).as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
assert len(members)==8 and (D/'review.stderr').read_bytes()==b''
result=json.loads((D/'review-result.json').read_bytes())
assert result['findings']==[] and result['raw_capture_custody_accepted'] is True
assert result['runtime_pins_reconstructed']==283 and result['checked_input_members']==295 and result['before_after_custody_equal'] is True
seal={'schema':1,'status':'FROZEN_INDEPENDENT_RAW_CAPTURE_TERMINAL_CUSTODY_ACCEPTED_ONLY',
 'member_count':len(members),'member_bytes':sum(row['bytes'] for row in members),'members':members,
 'tree_sha256':hashlib.sha256(json.dumps(members,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
 'root_release_sha256':result['root_release']['sha256'],'producer_seal_sha256':result['producer_seal']['sha256'],
 'receipt_sha256':result['receipt']['sha256'],'observation_sha256':result['observation']['sha256'],
 'capture_observation_sha256':result['capture_observation']['sha256'],
 'findings':[],'raw_capture_custody_accepted':True,'first_preflight_refusal_preserved':True,
 'this_review_controller_import_compiler_tests_semantic_map_actual_verifier_runtime_or_process_probe_actions':0,
 'raw_capture_only':True,'frontier_complete':False,'all_results_local_geometry_only':True,
 'complete_capacity_accepted':False,'physical_capacity_prices_backings_root_funding_product_GA_accepted':False}
with (D/'seal.json').open('x') as stream:json.dump(seal,stream,indent=2,sort_keys=True);stream.write('\n')
print(json.dumps({'seal_sha256':hashlib.sha256((D/'seal.json').read_bytes()).hexdigest(),
 'tree_sha256':seal['tree_sha256'],'member_count':len(members),
 'result_sha256':hashlib.sha256((D/'review-result.json').read_bytes()).hexdigest()}))
