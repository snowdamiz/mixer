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
assert len(members)==12 and sum(row['bytes'] for row in members)<8388608
assert (D/'review.stderr').read_bytes()==b''
result=json.loads((D/'review-result.json').read_bytes())
assert result['findings']==[] and result['merged_incomplete_conclusion_accepted'] is True
assert result['checked_input_members']==50 and result['before_after_custody_equal'] is True
assert result['unresolved_targets']==['Caller','Closure','Dispatch','Body']
seal={'schema':1,'status':'FROZEN_INDEPENDENT_MERGED_FOUR_TARGET_MAPPING_INCOMPLETE',
 'member_count':len(members),'member_bytes':sum(row['bytes'] for row in members),'members':members,
 'tree_sha256':hashlib.sha256(json.dumps(members,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
 'caller_closure_seal_sha256':result['caller_closure_seal']['sha256'],
 'dispatch_body_seal_sha256':result['dispatch_body_seal']['sha256'],
 'root_mapping_selection_sha256':result['selection']['sha256'],
 'merged_incomplete_conclusion_accepted':True,'unresolved_targets':result['unresolved_targets'],
 'whole_function_span_hashes_checked':7516,'cause_of_nonidentification_proved':False,
 'compiler_version_link_test_model_native_geometry_verifier_or_process_probe_actions':0,
 'automatic_recapture_or_source_flag_reachability_change_authorized':False,
 'frontier_complete':False,'root_semantic_approval':False,'physical_peak_or_capacity_accepted':False,'GA_accepted':False}
with (D/'seal.json').open('x') as stream:json.dump(seal,stream,indent=2,sort_keys=True);stream.write('\n')
print(json.dumps({'seal_sha256':hashlib.sha256((D/'seal.json').read_bytes()).hexdigest(),
 'tree_sha256':seal['tree_sha256'],'member_count':len(members),
 'result_sha256':hashlib.sha256((D/'review-result.json').read_bytes()).hexdigest()}))
