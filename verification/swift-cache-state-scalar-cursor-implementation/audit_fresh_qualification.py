#!/usr/bin/env python3
"""Read actual artifacts; source custody and finite execution audit only."""
import datetime,hashlib,json,pathlib,re,sys,time
from run_host import ROOT,REPO,sha
started=time.time()
def need(value,message):
 if not value:raise ValueError(message)
def save(name,data):(ROOT/'proofs'/name).write_text(json.dumps(data,indent=2)+'\n')
def h(data):return hashlib.sha256(data).hexdigest()
source=ROOT/'source/library/cache_state.rs';text=source.read_text();oldroot=ROOT/'predecessor/correction-3';old=(oldroot/'source/library/cache_state.rs').read_text()
need(sha(source)=='f98f7801925bc280e0e2a9c08ec2b4841b7ffc2942d2fedf6c4d3b4c1796bf1b','selected exact source')
# Every C3 member is mapped to an unchanged local reference copy; no predecessor
# executable or audit script is imported/executed by this audit.
oldseal=json.loads((oldroot/'candidate-repo-seal.json').read_text());base=pathlib.Path('verification/swift-cache-state-implementation/correction-3')
for member in oldseal['members']:
 relative=pathlib.Path(member['path']).relative_to(base);p=oldroot/relative
 need(p.stat().st_size==member['bytes']and sha(p)==member['sha256'],'frozen predecessor copy '+str(relative))
actual_rows=[]
for p in sorted((ROOT/'source').rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(ROOT/'source');q=oldroot/'source'/rel
 if rel not in [pathlib.Path('library/cache_state.rs'),pathlib.Path('tests/cache_state_tests.rs')]:need(p.read_bytes()==q.read_bytes(),'unchanged source '+str(rel))
 actual_rows.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)})
need({str(p.relative_to(ROOT)):sha(p)for p in(ROOT/'source').rglob('*')if p.is_file()}==json.loads((ROOT/'evidence/source-before.json').read_text()),'latest host source tree exact')
# Two authorized test methods are the only test differences. Compare the entire
# files with just those complete balanced function bodies removed.
def function_range(s,name):
 a=s.index('fn '+name+'() {');level=0
 for i in range(s.index('{',a),len(s)):
  if s[i]=='{':level+=1
  elif s[i]=='}':
   level-=1
   if level==0:return a,i+1
 raise ValueError('unclosed function '+name)
def without_methods(s):
 for name in ['private_actual_merge_exact_worst_case_counts','private_merge_maximum_timestamp_and_all64_slots']:
  a,b=function_range(s,name);s=s[:a]+name+s[b:]
 return s
need(without_methods((ROOT/'source/tests/cache_state_tests.rs').read_text())==without_methods((oldroot/'source/tests/cache_state_tests.rs').read_text()),'only authorized method bodies changed')
for p in (ROOT/'api').rglob('*.rs'):need(p.read_bytes()==(oldroot/'api'/p.relative_to(ROOT/'api')).read_bytes(),'API source unchanged '+str(p))
# Independent exact-byte custody outside the three selected regions. This
# carries selected source arguments into the compiled artifact; it does not
# re-prove universal source-work/lifetime accounting or grant release authority.
def split(s,selected):
 starts=[s.index('// UNSELECTED SOURCE-ONLY SEEDED WIDTH1 PROPOSAL.')if selected else s.index('fn merge('),s.index('// G2. Unselected typed-row proposal;')if selected else s.index('// Shared one-pass bounded probes;'),s.index('// G5. Exact prior successful base+request guard proves subtraction.')if selected else s.index('// The preceding checked base+request guard proves both subtractions.')]
 ends=[s.index('#[cfg(test)]\nstatic COMMIT_FAULT',starts[0]),s.index('    let body = w[6] as usize;',starts[1]),s.index('            sq(c, 10, mask);',starts[2])]
 retained=[s[:starts[0]],s[ends[0]:starts[1]],s[ends[1]:starts[2]],s[ends[2]:]]
 return retained,[{'owner':owner,'byte_range':[a,b],'sha256':h(s[a:b].encode()),'line_range':[s.count('\n',0,a)+1,s.count('\n',0,b)+1]}for owner,a,b in zip(['merge G3/G4','G2','G5'],starts,ends)]
kept,spans=split(text,True);before,before_spans=split(old,False);need(kept==before,'all other cache source bytes exact C3')
selection_path=REPO/'verification/swift-semantic-adapter-root-review/scalar-cursor-selection.json';selection=json.loads(selection_path.read_text());need(sha(selection_path)=='2011535ad73055d52b8a11e8e2625f67c4c3d6b8e063cf2da69d2e497bfce024','root exact selection')
external=[]
for path,digest in selection['inherited_selections'].items():p=REPO/path;need(sha(p)==digest,'inherited decision '+path);external.append({'path':path,'sha256':digest})
review=REPO/'verification/swift-cache-state-scalar-cursor-independent';need(sha(review/'seal.json')=='008dfbb9099d8a59bed142b6e578d96adf99e9b011120370de034bf728ed1aee','selected independent seal')
need(sha(review/'review.md')==next(m['sha256']for m in json.loads((review/'seal.json').read_text())['members']if m['path']=='review.md'),'independent review exact')
# The whole outer span, six final G6 stores, all call arguments/returns, complete
# setup/finish/projection and cleanup helpers occur in exact retained bytes.
save('source-inheritance.json',{'schema':1,'selected_source_sha256':sha(source),'old_source_sha256':h(old.encode()),'new_changed_regions':spans,'old_changed_regions':before_spans,'retained_chunks':[{'bytes':len(s.encode()),'sha256':h(s.encode())}for s in kept],'all_other_cache_state_bytes_identical':True,'other_two_library_files_all_other_tests_vectors_and_API_sources_identical':True,'two_authorized_private_test_methods_only':True,'root_selection_sha256':sha(selection_path),'inherited_decisions':external,'selected_work_groups':selection['all_production_groups'],'combined_selected_work_upper':selection['combined_groups'],'selected_whole_role_union':selection['whole_role_union'],'selected_added_role_peaks':selection['whole_added_peaks'],'selected_allowances':selection['whole_allowances'],'source_model_argument_inherited_only_for_exact_selected_source':True,'host_does_not_measure_logical_roles_machine_stack_ABI_RSS_or_event_work':True,'G2_arena_stability_component_preconditions_remain_conditional':True,'public_File_reachability_beyond_finite_cases_unproved':True})
# Actual fresh host and regression method IDs, complete layouts and full public
# observations are parsed from this run's unmodified output, never relabelled.
methods={};layouts={};cases_by_mode={};baseline=json.loads((oldroot/'proofs/fresh-qualification.json').read_text())
for mode in ['debug','optimized']:
 output=ROOT/f'evidence/tests-{mode}.stdout';s=output.read_text();need('test result: ok. 84 passed; 0 failed;'in s,'host84 '+mode)
 methods[mode]=re.findall(r'^test ([^\s]+) \.\.\.',s,re.M);need(len(methods[mode])==84,'actual method inventory84')
 layouts[mode]=[{'type':n,'bytes':int(size),'align':int(align)}for n,size,align in re.findall(r'ACCOUNTING_LAYOUT (.+?) size=(\d+) align=(\d+)',s)];need(len(layouts[mode])==23,'layout23')
 need('SELECTED_MERGE_ORACLE_CASES=1300'in s,'meaningful merge finite cases')
 old_cases={c['case']:c for c in baseline['modes'][mode]['actual_File_cases']};cases=[]
 paths=sorted(list((ROOT/f'evidence/public-cases/{mode}').glob('*/result.txt'))+list((ROOT/f'evidence/private-fault-cases/{mode}').glob('*/result.txt')))
 for result in paths:
  case=result.parent;manifest=json.loads((case/'files.json').read_text());actual=result.read_text().splitlines()[0]
  prior_case=oldroot/f'evidence/public-cases/{mode}'/case.name
  if not prior_case.exists():prior_case=oldroot/f'evidence/private-fault-cases/{mode}'/case.name
  need(actual==(prior_case/'result.txt').read_text().splitlines()[0],'actual complete result exact C3 '+case.name)
  need(h(actual.encode())==old_cases[case.name]['actual_result_first_line_sha256'],'result hash C3')
  raw={}
  for f in manifest['files']:
   p=REPO/f['content_path'];need(p.stat().st_size==f['bytes']and sha(p)==f['sha256'],'fresh actual content')
   need(f['sha256']==old_cases[case.name]['raw'][f['original_name']]['sha256'],'actual File/report bytes C3')
   raw[f['original_name']]={'bytes':f['bytes'],'sha256':f['sha256']}
  match=re.search(r'cache_state: FixtureCacheStateObservationV1 \{ boundary: (\w+), reason: (\w+), extent: \[([^]]+)\]',actual);projection=None
  if match:
   boundary,reason,extent=match.groups()
   def enum(name):return dict((n,int(v))for n,v in re.findall(r'(\w+) = (\d+)',text.split('pub enum '+name+' {',1)[1].split('}',1)[0]))
   projection=[enum('FixtureCacheStateBoundaryV1')[boundary],enum('FixtureCacheStateReasonV1')[reason]]+[int(v.strip())for v in extent.split(',')];need(len(projection)==32,'complete32')
  private=manifest['scope']=='private_injected_poison';need(private==(projection is not None and projection[:2]==[5,16]),'private File classification')
  cases.append({'case':case.name,'scope':'private injected poison; public reachability credit0'if private else'public actual four-File call','raw':raw,'actual_complete32':projection,'aggregate_present':projection is not None,'manifest':str((case/'files.json').relative_to(ROOT)),'manifest_sha256':sha(case/'files.json'),'identical_to_frozen_C3_result_and_bytes':True})
 public=[c for c in cases if c['scope'].startswith('public')];private=[c for c in cases if c['scope'].startswith('private')]
 need(len(public)==29 and sum(c['aggregate_present']for c in public)==27 and len(private)==2 and all(c['aggregate_present']for c in private),'observed File counts')
 cases_by_mode[mode]={'public_count':len(public),'public_complete32':sum(c['aggregate_present']for c in public),'public_outer_error_no_aggregate':sum(not c['aggregate_present']for c in public),'private_count':len(private),'private_complete32':sum(c['aggregate_present']for c in private),'cases':cases}
need(layouts['debug']==layouts['optimized'],'same fresh complete layouts')
reg=json.loads((ROOT/'evidence/selected-regression-summary.json').read_text());need(reg['all_expected_dispositions_passed']and reg['union_count']==122,'122 distinct method union')
for run in reg['runs']:need(run['complete_disjoint_coverage']and run['method_count']==(108 if run['label']=='producer'else 98),'regression coverage')
api=json.loads((ROOT/'evidence/api-summary.json').read_text());oldapi=json.loads((ROOT/'evidence/old-api-summary.json').read_text())
need(len(api['probes'])==32 and len(oldapi['controls'])==18 and all(p['compile_success']==p['expected_success']for p in api['probes']+oldapi['controls']),'all API dispositions')
for mode in ['debug','optimized']:
 s=(ROOT/f'evidence/changed-controls-{mode}-tests.stdout').read_text();need('test result: ok. 3 passed; 0 failed;'in s and 'PRIVATE_ACTUAL_G5_CAPACITY_CASES=83'in s and 'PRIVATE_ACTUAL_G2_ADMITTED_MALFORMED_CASES=6'in s and 'PRIVATE_ACTUAL_PRE_G5_REFUSALS=5'in s,'actual additional controls')
source_tree_digest=h(json.dumps(actual_rows,sort_keys=True,separators=(',',':')).encode())
save('fresh-qualification.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(ROOT/'audit_fresh_qualification.py')],'python':sys.version,'auditor_sha256':sha(ROOT/'audit_fresh_qualification.py'),'source_rows':actual_rows,'source_tree_digest':source_tree_digest,'source_tree_digest_method':'sha256 canonical sorted-key compact JSON source_rows','library_sha256':{p.name:sha(p)for p in(ROOT/'source/library').glob('*.rs')},'modes':cases_by_mode,'actual_host_method_ids':methods,'fresh_layouts':layouts,'host_method_count':84,'producer_method_count':108,'independent_method_count':98,'distinct_methods_per_mode':122,'new_cache_state_methods':30,'inherited_producer_methods':78,'inherited_independent_methods':14,'API_dispositions_per_mode':{'new':16,'inherited':9},'additional_private_actual_methods':3,'additional_private_actual_cases_per_mode':{'capacity':83,'admitted_malformed':6,'preG5_refusal':5,'merge_in_authorized_method':1300},'producer_Debug_coverage_partition':'17 individually bounded root methods plus91-method embedded group; exact inventory disjoint complete','producer_Debug_prior_full_command_60s_failed':True,'regression_total_wall_seconds':reg['wall_seconds'],'performance_equivalence_claimed':False,'all_fresh_expected_host_dispositions_passed':True,'independent_implementation_review_pending':True,'canonical_integration_selected':False,'full_target_or_native_runtime_or_GA_qualified':False})
# Every compiler/test child is owned, timed, output-capped and reaped. Expected
# negative API exits, original incompatible tests and the timeout remain explicit.
receipts=[]
for p in sorted((ROOT/'evidence').rglob('*.json')):
 j=json.loads(p.read_text())
 if not isinstance(j,dict)or not('command'in j and 'pid'in j and 'exit'in j):continue
 need(j['parent_exit_observed'],'child reaped '+str(p));need(j['per_command_deadline_seconds']==60,'bounded child')
 need(sha(p.with_suffix('.stdout'))==j['stdout_sha256']and sha(p.with_suffix('.stderr'))==j['stderr_sha256'],'raw output hashes '+str(p))
 receipts.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'exit':j['exit'],'failure':j['failure'],'pid':j['pid'],'pgid':j['pgid'],'command':j['command'],'elapsed':j['elapsed'],'owned_input_artifacts':j['owned_input_artifacts']})
products=json.loads((ROOT/'evidence/owned-product-cleanup.json').read_text())
for row in products:need(row['absent_after_removal']and not(ROOT/row['path']).exists(),'owned product removed')
need(not list(ROOT.glob('.scratch-*'))and not list(ROOT.rglob('__pycache__'))and not list(ROOT.rglob('*.rlib'))and not list(ROOT.rglob('*.binary')),'no owned scratch/bytecode/build products')
failed=[r for r in receipts if r['exit']not in [0,1]]
need(any(r['failure']=='timeout'and r['exit']==-9 for r in failed),'timeout explicitly retained')
save('execution-product-audit.json',{'schema':1,'fresh_and_failed_command_receipts':receipts,'owned_products_hashed_before_removal':products,'all_children_reaped':True,'scratch_bytecode_and_build_products_absent':True,'expected_negative_API_exits_are_required_dispositions':True,'original_frozen_private_failures_preserved':'evidence/frozen-attempt1','authoring_assertion_failure_preserved':'evidence/amended-attempt2','authoring_reject_status_failure_preserved':'evidence/changed-controls-attempt1','native_runtime_UI_capture_process_inventory_or_other_project_changes':False,'physical_phones_simulators_emulators_not_used':True,'tool_identity_receipt':'evidence/rust-version.stdout','source_tree_digest':source_tree_digest,'audit_wall_seconds':time.time()-started})
print(json.dumps({'source_tree_digest':source_tree_digest,'fresh_host':[84,84],'fresh_regressions':[108,98],'distinct_methods_per_mode':122,'extra_methods_per_mode':3,'actual_File_per_mode':{m:{k:v for k,v in d.items()if k!='cases'}for m,d in cases_by_mode.items()},'layouts_per_mode':23,'products_hashed_removed':len(products),'commands_audited':len(receipts),'independent_implementation_review_pending':True},indent=2))
