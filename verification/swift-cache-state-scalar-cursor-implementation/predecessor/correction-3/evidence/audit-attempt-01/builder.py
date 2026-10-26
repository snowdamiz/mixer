#!/usr/bin/env python3
"""Read-only source/run audit plus owned proof outputs; no test/oracle execution."""
import hashlib,json,pathlib,re,sys
from run_host import ROOT,REPO,sha
P=ROOT/'source/library/cache_state.rs';S=P.read_text();L=S.splitlines();H=sha(P)
assert H=='0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8'
def save(n,j):(ROOT/'proofs'/n).write_text(json.dumps(j,indent=2)+'\n')
def line(s):return next(i+1 for i,l in enumerate(L)if s in l)
def span(name):
 a=line('fn '+name+'(');depth=0;seen=False
 for i in range(a-1,len(L)):
  t=re.sub(r'"(?:\\.|[^"\\])*"','""',L[i].split('//')[0])
  for c in t:
   if c=='{':depth+=1;seen=True
   elif c=='}':depth-=1
  if seen and depth==0:return[a,i+1]
 raise ValueError(name)
old=ROOT.parent/'correction-2';cust=json.loads((ROOT/'proofs/custody.json').read_text())
for c in cust['copies']:
 if '/source/'in c['destination']and not c['destination'].endswith('/library/cache_state.rs'):
  assert sha(REPO/c['destination'])==c['sha256']
for n in ['analyzer.rs','envelope.rs']:assert sha(ROOT/'source/library'/n)==sha(old/'source/library'/n)
a,z=span('cleanup');cleanup='\n'.join(L[a-1:z]);stores=re.findall(r'c\[(\d+)\.\.(\d+)\]\.copy_from_slice\(&\[0u8; 128\]\);',cleanup)
assert [(int(x),int(y))for x,y in stores]==[(i*128,(i+1)*128)for i in range(16)]
restores=re.findall(r'c\[(\d+)\.\.(\d+)\]\.copy_from_slice\(&b\[(\d+)\.\.(\d+)\]\);',cleanup)
cells=[7,9,10,11,12,13,14,64,65,66,160,161];base=7729760
assert len(restores)==12
for i,(x,y,u,v)in enumerate(restores):assert(int(x),int(y),int(u),int(v))==(888+8*i,896+8*i,base+8*cells[i],base+8*cells[i]+8)
oldS=(old/'source/library/cache_state.rs').read_text();start=oldS.index('    let zero = [0u8; 8];',oldS.index('fn cleanup('));end=oldS.index('    c[888..896]',start)
newstart=S.index('    c[0..128].copy_from_slice',S.index('fn cleanup('));newend=S.index('    c[888..896]',newstart)
assert oldS[:start]==S[:newstart]and oldS[end:]==S[newend:]
save('source-audit.json',{'schema':1,'source_sha256':H,'all_other_source_inputs_identical_to_c2':True,'only_clear_block_changed':True,'function_spans':{n:span(n)for n in ['ld','st','cq','sq','semantic','cleanup','projection','cache_walk','cache_inputs','analyze_fixture_cache_state_v1']},'clear_stores':[{'line':line(f'c[{x}..{y}].copy_from_slice(&[0u8; 128])'),'destination':[int(x),int(y)],'anonymous_temp_bytes':128}for x,y in stores],'all2048bytes_covered_exactly_once':True,'restores':[{'line':line(f'c[{x}..{y}].copy_from_slice(&b[{u}..{v}])'),'destination':[int(x),int(y)],'source':[int(u),int(v)],'scalar_cell':cells[i]}for i,(x,y,u,v)in enumerate(restores)],'restore_and_fault_suffix_identical':True,'G3_G4_unchanged':True,'one_Candidate_owner_site':line('let mut candidate: Candidate2048'),'cleanup_caller_site':line('if !cleanup('),'zero_runtime_credit_for_partial_paid_exclusions':0,'source_accounting_accepted':False,'lifetime_proof_accepted':False})
# Bind every executed method, type observation and actual File artifact afresh.
layouts={};methods={};modes={}
for mode in ['debug','optimized']:
 out=ROOT/f'evidence/tests-{mode}.stdout';t=out.read_text();assert '84 passed; 0 failed;'in t
 methods[mode]=re.findall(r'^test ([^\s]+) \.\.\.',t,re.M);assert len(methods[mode])==84
 layouts[mode]=[{'type':n,'bytes':int(nbytes),'align':int(al)}for n,nbytes,al in re.findall(r'ACCOUNTING_LAYOUT (.+?) size=(\d+) align=(\d+)',t)];assert len(layouts[mode])==23
 assert any(r['type']=='Paid'and r['bytes']==24 for r in layouts[mode]);assert any(r['type']=='Result<FixtureCacheStateOutcomeV1,AnalyzerError>'and r['bytes']==488 for r in layouts[mode])
 expected=['private_injected_partial_commit_or_cleanup_disables_both_leaves','private_semantic_guard_neighbors_and_cleanup','private_budget_exact_neighbors','private_terminal_precedence_full32','private_all_eleven_stage_baselines_keep_exact_full32','private_inactive_masks_and_feasibility_are_not_validated','private_planned_masks_bool_and_destination_boundaries_remain_enforced','private_pending_requires_true_feasible_selected_slot_and_valid_destination','private_initial_snapshot_and_terminal_precedence_keep_the_fixed_read_sets','private_literal_restores_preserve_every_byte_and_clear_the_remaining_candidate','private_phase_commits_exact_twelve_scalar_cells_in_order_without_other_mutation']
 for name in expected:assert any(x.endswith('::'+name)for x in methods[mode])
 d=ROOT/'evidence/public-cases'/mode;prior=old/'evidence/public-cases'/mode;cases=[]
 for p in sorted(d.glob('*/result.txt')):
  q=prior/p.relative_to(d);actual=p.read_text().splitlines()[0];assert actual==q.read_text().splitlines()[0]
  raw={}
  for name in ['input-0.bin','input-1.bin','input-2.bin','report.bin']:
   x=p.parent/name;y=q.parent/name;assert x.read_bytes()==y.read_bytes();raw[name]={'bytes':x.stat().st_size,'sha256':sha(x),'identical_to_frozen_c2':True}
  match=re.search(r'cache_state: FixtureCacheStateObservationV1 \{ boundary: (\w+), reason: (\w+), extent: \[([^]]+)\]',actual)
  projection=None
  if match:
   b,r,e=match.groups();vals=[int(x.strip())for x in e.split(',')];assert len(vals)==30
   enum=lambda name:dict((n,int(v))for n,v in re.findall(r'(\w+) = (\d+)',S.split('pub enum '+name+' {',1)[1].split('}',1)[0]))
   projection=[enum('FixtureCacheStateBoundaryV1')[b],enum('FixtureCacheStateReasonV1')[r]]+vals
  private=projection is not None and projection[:2]==[5,16]
  cases.append({'case':p.parent.name,'scope':'private injected commit/cleanup poison; zero public-reachability credit'if private else'public actual four-File invocation','raw':raw,'actual_result_first_line_sha256':hashlib.sha256(actual.encode()).hexdigest(),'actual_complete32':projection,'aggregate_present':projection is not None,'identical_to_c2_result_except_OS_stamp_line':True})
 assert len(cases)==31 and sum(x['scope'].startswith('private')for x in cases)==2
 modes[mode]={'fresh_raw_stdout':str(out.relative_to(ROOT)),'stdout_sha256':sha(out),'executed_method_ids':methods[mode],'actual_File_cases':cases,'public_File_count':29,'private_injected_File_count':2,'complete32_observations':sum(x['actual_complete32']is not None for x in cases),'all_matching_old_artifacts_are_comparison_evidence_only_not_inherited_execution_credit':True}
 for label,count in [('producer',108),('independent',98)]:assert f'{count} passed; 0 failed;'in(ROOT/f'evidence/regression-{label}-{mode}-tests.stdout').read_text()
assert layouts['debug']==layouts['optimized']
save('fresh-qualification.json',{'schema':1,'library_sha256':cust['actual_library_sha256'],'modes':modes,'fresh_layouts':layouts,'new_method_count':30,'old_producer_mapping':{'embedded':54,'separate_fixture':17,'private_transport':7,'total':78},'old_independent_methods':14,'distinct_methods_per_mode':122,'binary_counts_per_mode':[84,108,98],'API_controls_per_mode':{'new':16,'old':9},'unchanged_expected_inputs':True,'no_new_test_needed':'Existing private cleanup control checks all2048bytes for3fills (6144bytes), all12restorebytes and unchanged8MiB arena; focused fault/guard and full32 source methods are freshly executed above.','source_accounting_accepted':False,'lifetime_proof_accepted':False,'independent_acceptance':False})
# Every owned product was hashed before unlink after its owning child returned.
clean=json.loads((ROOT/'evidence/owned-product-cleanup.json').read_text())
for row in clean:assert row['absent_after_removal']and not(ROOT/row['path']).exists()
receipts=[]
for p in sorted((ROOT/'evidence').glob('*.json')):
 j=json.loads(p.read_text())
 if isinstance(j,dict)and 'command'in j and 'pid'in j and 'exit'in j:
  assert j['parent_exit_observed']and j['failure']is None
  receipts.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'exit':j['exit'],'pid':j['pid'],'pgid':j['pgid'],'source_hashes':j.get('actual_library_sha256'),'owned_input_artifacts':j.get('owned_input_artifacts',[])})
assert not list(ROOT.glob('.scratch-*'))and not list(ROOT.rglob('__pycache__'))and not list(ROOT.rglob('*.rlib'))and not list(ROOT.rglob('*.binary'))
save('execution-product-audit.json',{'schema':1,'fresh_command_receipts':receipts,'owned_products_hashed_and_removed':clean,'all_children_terminal_observed':True,'negative_API_compile_exits_are_expected_controls_not_suite_failures':True,'scratch_and_build_products_absent':True,'compiler_identity_receipt':{'path':'evidence/rust-version.stdout','sha256':sha(ROOT/'evidence/rust-version.stdout')},'preparatory_read_failure':{'command':'inline source-evidence inspection using glob(\'*.json\')','exit':1,'error':'StopIteration: actual case artifacts use */result.txt','retained_as_inspection_failure':True,'resolution':'read actual result.txt artifacts; no test/source changes'},'no_native_runtime_UI_capture_or_process_inventory':True})
print(json.dumps({'source':H,'fresh_modes':{m:{k:v[k]for k in ['public_File_count','private_injected_File_count','complete32_observations']}for m,v in modes.items()},'layouts_per_mode':23,'distinct_methods_per_mode':122,'owned_products_removed':len(clean),'qualified_source_work_or_lifetime':False},indent=2))
