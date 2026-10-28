#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

D=Path(__file__).resolve().parent
members=[]
for path in sorted(D.rglob('*')):
    assert not path.is_symlink()
    if path.is_file() and path.name!='seal.json':
        raw=path.read_bytes()
        members.append({'path':path.relative_to(D).as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
assert len(members)==8 and (D/'review.stderr').read_bytes()==b''
result=json.loads((D/'review-result.json').read_bytes())
assert result['findings']==[] and result['compiler_release_recommended'] is True
assert result['checked_input_members']==273 and result['before_after_custody_equal'] is True
subject={'base_capture_plan_sha256':result['base_capture_plan_sha256'],
 'controller_plan_sha256':result['controller_plan_sha256'],'controller_sha256':result['controller_sha256'],
 'capture_packet_seal_sha256':result['producer_seal_sha256']}
seal={'schema':1,'status':'FROZEN_INDEPENDENT_CAPTURE_SOURCE_REVIEW_ONE_COMPILER_RELEASE_RECOMMENDED',
 'member_count':len(members),'member_bytes':sum(row['bytes'] for row in members),'members':members,
 'tree_sha256':hashlib.sha256(json.dumps(members,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
 'independent_source_review_subject':subject,'findings':[],'compiler_release_recommended':True,
 'this_review_controller_import_syntax_compiler_capture_test_actual_parser_version_or_process_probe_actions':0,
 'raw_capture_only':True,'frontier_complete':False,'all_results_local_geometry_only':True,
 'complete_capacity_accepted':False,'physical_capacity_prices_backings_root_funding_product_GA_accepted':False}
with (D/'seal.json').open('x') as stream:
    json.dump(seal,stream,indent=2,sort_keys=True);stream.write('\n')
print(json.dumps({'seal_sha256':hashlib.sha256((D/'seal.json').read_bytes()).hexdigest(),
 'tree_sha256':seal['tree_sha256'],'member_count':len(members),
 'result_sha256':hashlib.sha256((D/'review-result.json').read_bytes()).hexdigest()}))
