from pathlib import Path
import json,re,hashlib
O=Path(__file__).resolve().parent;B=O/'rebound';OLD=O.parent
m=json.loads((B/'input-manifest.json').read_text());roles=json.loads((B/'source-review.json').read_text());prior=json.loads((OLD/'decision.json').read_text())
mapnames={'FinalOutputBorrows':'FinalOutputBorrows','ClockLeaf':'FinalClockInventory','FaultLeaf':'FinalFaultInventory','CategoryLeaves':'FinalCategoryInventory','RefundParent':'FinalRefundInventory','RecordParent':'FinalRecordInventory','FinishConstFormulaParent':'FinalFinishInventory'}
def parse(name):
 s=(B/'logs'/(name+'.log')).read_text();d={'layouts':{},'fields':{},'shapes':{}}
 for line in s.splitlines():
  x=re.search(r'\blayout (\w+) (\d+) (\d+)$',line)
  if x:d['layouts'][x[1]]={'size':int(x[2]),'align':int(x[3])}
  x=re.fullmatch(r'field (\w+) (\w+) (\d+) (\d+) (\d+)',line)
  if x:d['fields'].setdefault(x[1],{})[x[2]]={'size':int(x[3]),'align':int(x[4]),'offset':int(x[5])}
  x=re.fullmatch(r'shape (.+) (\d+) (\d+)',line)
  if x:d['shapes'][x[1]]={'size':int(x[2]),'align':int(x[3])}
 assert 'foundation 17368 final 864' in s
 assert len(d['layouts'])==7 and sum(map(len,d['fields'].values()))==84
 return d
d=parse('metadata-production-debug')
for name in ['metadata-production-release','metadata-unit-debug','metadata-unit-release']:
 e=parse(name);assert d['layouts']==e['layouts'] and d['fields']==e['fields']
 assert e['shapes']['RuntimeControl']=={'size':1720,'align':8}
for old,new in mapnames.items():
 assert d['layouts'][new]==prior['layouts'][old]
 for f in prior['source_roles'][old]:assert d['fields'][new][f['field']]=={k:f[k] for k in ['size','align','offset']}
for suffix in ['debug','release']:
 roots=(B/'logs'/('root-branches-'+suffix+'.log')).read_text();assert '2 passed; 0 failed' in roots
 assert roots.count('final-boundary cleanup case=')==7
 assert 'admission previous=16504 additional=864 foundation=17368' in roots
 edge=(B/'logs'/('independent-underflow-'+suffix+'.log')).read_text();assert '1 passed; 0 failed' in edge and edge.count('independent finish checked-counter branch')==2
 cache=(B/'logs'/('cache-rebound-'+suffix+'.log')).read_text();assert '1 passed; 0 failed' in cache and 'final_boundary=864 total=17368' in cache
# The final source snapshot itself remains immutable; probe hooks are separate.
for p,h in m['files'].items():
 q=B/'inputs/frozen-vm'/Path(p).relative_to('vm') if p.startswith('vm/') else B/'inputs'/p
 assert hashlib.sha256(q.read_bytes()).hexdigest()==h,p
seal=json.loads((OLD/'seal.json').read_text());assert all(hashlib.sha256((OLD/p).read_bytes()).hexdigest()==h for p,h in seal['files'].items())
commands=json.loads((B/'commands.json').read_text());assert len(commands)==13 and all(x['exit_code']==0 for x in commands)
keyfiles=['vm/src/experimental_swift_reactor/control.rs','vm/src/experimental_swift_reactor/control_tests.rs','vm/src/experimental_swift_reactor/cache_tests.rs','vm/src/experimental_swift_reactor/execution.rs','vm/src/experimental_swift_reactor/execution_tests.rs','docs/swift-final-boundary-accounting.md']
result={'schema':'mixer.swift-final-boundary-root-correction-independent-review.v1','decision':'accepted_scoped_final_boundary_named_object_correction','root_integration_acceptance':False,'source_revision':m['revision'],'source_tree_digest':m['source_tree_digest'],'exact_source_sha256':{p:m['files'][p] for p in keyfiles},'production_layouts':d['layouts'],'field_count':84,'field_offsets_and_types_match_proposal':True,'prod_test_debug_release_groups_identical':True,'runtime_control_layout':d['shapes']['RuntimeControl'],'old_seven_counts_unchanged':True,'runtime_formula_array_iterator_fold_absent':True,'whole_phase_allowance':864,'previous_foundation':16504,'corrected_foundation':17368,'outside_additive_control_inventory_formula_byte_identical':True,'helper_phase_order':'large supplied return storage ends; refund and Result end; record and assignment end; finish consumes original control','old_class_assignments':'3 proof, 3 control, 3 adopted, 4 failure, 4 usage, 6 ticket, 6 optional-WASI remain disjoint; no borrow relabeled as diagnostic; whole wrappers separately reserved','rebound_delta':'Only pub(super) visibility of metadata const and the cache test expected sum/output; no owner/algorithm/cap changes','new_root_tests_per_profile':2,'root_admission_boundaries_per_profile':3,'root_actual_wasi_cleanup_cases_per_profile':7,'independent_extra_tests_per_profile':1,'independent_extra_underflow_branches_per_profile':2,'actual_cache_layout_snapshot_replayed_per_profile':1,'metadata_probes_per_profile':{'production':1,'unit':1},'commands':13,'all_commands_passed':True,'previous_review_seal_files_unchanged':True,'scope':'Independent review of exact corrected final-boundary requested-memory accounting only. Authored named Rust object model, conservative whole-parent groups; excludes compiler stack, opaque standard-library internals, allocator overhead and RSS. Original C3/C2 receipts remain historical. Root full feature/legacy/privacy matrices and final integration acceptance are separate. No executor constructor/interpreter/full target execution, devices, published FieldLog, release, signing, store, operational or GA acceptance.'}
(O/'decision.json').write_text(json.dumps(result,indent=2)+'\n');print('accepted scoped source',result['exact_source_sha256']['vm/src/experimental_swift_reactor/control.rs'],'fields',result['field_count'],'commands',len(commands))
