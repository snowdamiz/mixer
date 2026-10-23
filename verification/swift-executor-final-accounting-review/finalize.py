from pathlib import Path
import json,re,hashlib
O=Path(__file__).resolve().parent;R=O.parents[1]
roles=json.loads((O/'source-roles.json').read_text())['groups']
def parse(name):
 text=(O/'logs'/f'{name}.log').read_text();d={'layouts':{},'fields':{},'plain_shapes':{}}
 for line in text.splitlines():
  m=re.search(r'\blayout (\w+) (\d+) (\d+)$',line)
  if m:d['layouts'][m[1]]={'size':int(m[2]),'align':int(m[3])}
  m=re.fullmatch(r'field (\w+) (\w+) (\d+) (\d+) (\d+)',line)
  if m:d['fields'].setdefault(m[1],{})[m[2]]={'size':int(m[3]),'align':int(m[4]),'offset':int(m[5])}
  m=re.fullmatch(r'shape (.+) (\d+) (\d+)',line)
  if m:d['plain_shapes'][m[1]]={'size':int(m[2]),'align':int(m[3])}
 assert '1 passed; 0 failed' in text
 assert len(d['layouts'])==len(roles)
 assert sum(map(len,d['fields'].values()))==sum(map(len,roles.values()))
 return d
d=parse('debug');assert d==parse('release')
for n,fs in roles.items():
 for f in fs:f.update(d['fields'][n][f['field']])
old=16504
safety=max(d['layouts'][n]['size'] for n in ['RefundParent','RecordParent','FinishConstFormulaParent'])
manifest=json.loads((O/'input-manifest.json').read_text())
critical=['vm/src/experimental_swift_reactor/control.rs','vm/src/experimental_swift_reactor/execution.rs','docs/swift-executor-stage-contract.md','docs/swift-cache-foundation-phase-addendum.md','docs/swift-cache-candidate3-acceptance.md']
frozen_paths={p:(O/'inputs'/p if (O/'inputs'/p).exists() else O/'tree'/p) for p in critical}
current={p:hashlib.sha256(frozen_paths[p].read_bytes()).hexdigest() for p in critical}
assert all(current[p]==manifest['files'][p] for p in critical)
output={'schema':'mixer.swift-executor-final-accounting-independent-review.v1','decision':'blocking_missing_explicit_disjoint_final_boundary_inventory','root_acceptance':False,'base_revision':manifest['revision'],'source_tree_digest':manifest['source_tree_digest'],'source_sha256':current,'measurement_toolchain':'rustc 1.99.0 (b940084d7 2026-09-28), aarch64-apple-darwin','profile_test_counts':{'debug':1,'release':1},'candidate_const_formula_test_counts':{'debug':1,'release':1},'proposal_sha256':hashlib.sha256((O/'foundation-proposal.rs').read_bytes()).hexdigest(),'debug_release_metadata_identical':True,'layouts':d['layouts'],'source_roles':roles,'plain_shapes':d['plain_shapes'],'existing_foundation_bytes':old,'candidate_only':{'constant_evaluated_formula_required':True,'new_disjoint_whole_phase_allowance':safety,'candidate_foundation_bytes':old+safety,'minimum_or_root_accepted_claimed':False,'formula':'existing foundation classes plus max(size_of<RefundParent>, size_of<RecordParent>, size_of<FinishConstFormulaParent>)','switch_rule':'The refund call and its Result end before record_cleanup; record_cleanup call/result and outcome assignment end before finish_owned_cleanup. Outer output refs persist and are included in every complete group. No group changes within a surviving helper parent.','new_whole_wrappers':'Finish classes include complete array, IntoIter, Flatten, loop next output; their fields are never also attributed to plain-ticket classes.'},'observations':{'success_refund':3,'fault_refund':6,'record_cleanup':3,'finish_initial_usage':3,'post_drop_micros':1},'scope':'Authored named Rust objects and explicit source operation/return shapes; conservative complete parent unions, not exact physical simultaneous stack occupancy. No compiler stack, opaque std-library internals, allocator overhead, RSS, executor algorithm, target run, device, GA or implementation acceptance. Metadata probes instantiate no runtime owner.'}
(O/'decision.json').write_text(json.dumps(output,indent=2)+'\n')
print('layouts',d['layouts']);print('candidate only',old,'+',safety,'=',old+safety)
