#!/usr/bin/env python3
"""Freeze correction-only repo-relative custody after source-bound host evidence."""
import datetime,hashlib,json,pathlib,re,runpy,shutil,sys,time
ROOT=pathlib.Path(__file__).resolve().parent;REPO=ROOT.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
canonical=lambda v:json.dumps(v,sort_keys=True,separators=(',',':')).encode()
seal_path=ROOT/'candidate-repo-seal.json';assert not seal_path.exists(),'immutable seal must not be overwritten'
# Re-run custody only; this does not start a compiler/test/native process.
runpy.run_path(str(ROOT/'correction_audit.py'),run_name='__main__')
validation=json.loads((ROOT/'evidence/final-validation.json').read_text())
actual={str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'source').rglob('*'))if p.is_file()}
assert actual==validation['source_sha256']
for mode in ['debug','optimized']:
 for stem,count in [(f'tests-{mode}',81),(f'regression-producer-{mode}-tests',105),(f'regression-independent-{mode}-tests',95)]:
  assert f'test result: ok. {count} passed; 0 failed;'in(ROOT/'evidence'/f'{stem}.stdout').read_text()
  assert json.loads((ROOT/'evidence'/f'{stem}.json').read_text())['exit']==0
 for name,n in [('api-summary.json',16),('old-api-summary.json',9)]:
  s=json.loads((ROOT/'evidence'/name).read_text());rows=s.get('probes',s.get('controls'));r=[r for r in rows if r['mode']==mode]
  assert len(r)==n and all(x['compile_success']==x['expected_success']for x in r)
# Deduplicate exact raw bytes; preliminary attempts get zero final-command credit.
pool=ROOT/'evidence/content';pool.mkdir(exist_ok=True);cases=[];counts={}
for mode in ['debug','optimized']:
 run=json.loads((ROOT/'evidence'/f'tests-{mode}.json').read_text());start=run['started'];end=start+run['elapsed'];summary={'final_public_four_File':0,'final_private_injected_fault':0}
 for case in sorted((ROOT/'evidence/public-cases'/mode).iterdir()):
  raw=(case/'result.txt').read_text();private='boundary: InternalPoisoned'in raw
  m=re.search(r'input_stamps_before_and_after=\[Stamp \{ fields: \[([^\]]+)',raw);fields=[int(v.strip())for v in m[1].split(',')];stamp=fields[4]+fields[5]/1e9;assert start<=stamp<=end
  scope='final_private_injected_fault'if private else'final_public_four_File';summary[scope]+=1
  if private:
   target=ROOT/'evidence/private-fault-cases'/mode/case.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.move(case,target);case=target
  cases.append({'case':str(case.relative_to(ROOT)),'scope':scope,'result_sha256':sha(case/'result.txt'),'input_mtime_epoch':stamp,'final_command_started':start,'final_command_ended':end,'final_source_credit':True,'public_reachability_credit':not private})
 assert summary=={'final_public_four_File':29,'final_private_injected_fault':2};counts[mode]=summary
for case in sorted((ROOT/'evidence/attempts').rglob('case-*')):
 if case.is_dir()and(case/'result.txt').exists():
  cases.append({'case':str(case.relative_to(ROOT)),'scope':'prior_attempt_zero_final_command_credit','result_sha256':sha(case/'result.txt'),'final_source_credit':False,'public_reachability_credit':False})
for row in cases:
 case=ROOT/row['case'];files=[]
 for p in sorted(case.glob('*.bin')):
  digest=sha(p);target=pool/(digest+'.bin')
  if not target.exists():shutil.copyfile(p,target)
  assert sha(target)==digest
  files.append({'original_name':p.name,'bytes':p.stat().st_size,'sha256':digest,'content_path':str(target.relative_to(REPO))});p.unlink()
 row['files']=files;(case/'files.json').write_text(json.dumps(row,indent=2)+'\n')
(ROOT/'evidence/case-catalog.json').write_text(json.dumps({'schema':1,'counts_per_mode':counts,'cases':cases,'all_raw_bytes_preserved_by_sha256':True,'initial_host_attempt_and_prior_default_API_commands_final_credit':0,'private_guard_matrix_public_reachability_credit':0},indent=2)+'\n')
# Every recorded child must have an observed terminal receipt before cleanup.
commands=[]
for p in sorted((ROOT/'evidence').rglob('*.start.json')):
 receipt=p.with_name(p.name.replace('.start.json','.json'));r=json.loads(receipt.read_text());assert r['parent_exit_observed']
 commands.append({'receipt':str(receipt.relative_to(ROOT)),'pid':r['pid'],'pgid':r['pgid'],'exit':r['exit'],'failure':r['failure'],'group_termination_requested':r['group_termination_requested']})
removed=[]
for p in sorted(ROOT.rglob('__pycache__')):
 for q in sorted(p.rglob('*')):
  if q.is_file():removed.append({'path':str(q.relative_to(ROOT)),'bytes':q.stat().st_size,'sha256':sha(q),'kind':'owned Python bytecode'})
 shutil.rmtree(p)
assert not list(ROOT.glob('.scratch-*'))
for p in ROOT.rglob('*'):
 if p.is_file():
  assert p.suffix not in ['.pyc','.rlib','.binary'],p
  assert p.read_bytes()[:4]not in[b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'\x7fELF'],p
cleanup=json.loads((ROOT/'evidence/owned-product-cleanup.json').read_text());assert all(r['absent_after_removal']and not(ROOT/r['path']).exists()for r in cleanup)
(ROOT/'evidence/final-cleanup.json').write_text(json.dumps({'commands':commands,'all_started_parents_observed_terminal':True,'removed_bytecode':removed,'final_owned_product_hashes':'evidence/owned-product-cleanup.json','no_build_products_or_scratch_retained':True,'preliminary_binary_hash_limitation':'Initial host attempt binaries had already been removed before binary-hash cleanup instrumentation; their hashes are not recovered or claimed. They receive zero final-command credit.','no_process_inventory_performed':True,'native_runtime_or_capture_started':False,'other_projects_untouched':True},indent=2)+'\n')
source_digest=hashlib.sha256(canonical(actual)).hexdigest();lib={str(p.relative_to(REPO)):sha(p)for p in sorted((ROOT/'source/library').glob('*.rs'))}
(ROOT/'handoff.json').write_text(json.dumps({'status':'frozen producer Q9/Q10 correction; root admission and independent review pending','selection_path':'verification/swift-semantic-adapter-root-review/guard-correction-selection.json','selection_sha256':'0f70d7f9ce793d710da4d1d3dc97debaf8474d8bfb9031f77fdd1af5ddbc22fe','original_seal_sha256':'caceb9db9263de46ed876ff109f34eacb8fe13a9bd3ac47758f2bdac5c693ad3','original454_unchanged':True,'product_change_only':'shape_q planned-stage read sets and pending feasibility predicate','source_tree_digest':source_digest,'library_sha256':lib,'new_methods':27,'new_guard_methods_included':5,'private_guard_scenarios_per_mode':4337,'private_guard_public_reachability_credit':0,'inherited_producer_mapping':{'embedded':54,'separate_public':17,'private_transport':7,'total':78},'inherited_independent':14,'unique_methods_per_mode':119,'modes':['debug','optimized'],'API_controls_per_mode':{'new':16,'inherited':9},'actual_File_counts_per_mode':counts,'fresh_layouts':{'replay':104,'envelope':128,'old_aggregate':232,'observation':256,'new_aggregate':488,'complete_Result':488},'unchanged_caps':{'groups':[256,2560,2568,768,640,640,248],'semantic':7680,'inherited':471,'combined':8151,'preflight':8192,'setup':512,'finish':256,'terminal_guard':128,'role_union':29344,'reserved':41984,'global':65536,'Candidate':2048},'inherited637_scalar_block_and_P01_P35_review':'pending; producer ledgers supplied, not endorsed','three_partial_paid_exclusions_runtime_pass_credit':0,'public_from_empty_reachability_of_guard_defects':'not established','independent_accepted':False,'root_implementation_accepted':False,'fullReplayAccepted':False,'storedPrefixValidated':False,'semanticMetricsValid':False,'realBindingVerified':False,'native_runtime_or_capture_started':False,'GA_qualified':False},indent=2)+'\n')
# Current tool source is retained; supplementary API execution explicitly supersedes old default-only API credit.
(ROOT/'evidence/tooling-provenance.json').write_text(json.dumps({'python':sys.version,'seal_command':[sys.executable,str(pathlib.Path(__file__).resolve())],'tool_sources':{str(p.relative_to(ROOT)):sha(p)for p in sorted(ROOT.glob('*.py'))},'final_host_coordinator':'final_validate.py','API_supplement':'supplement_api_modes.py','initial_host_run':'retained raw attempt, zero final-command credit','prior_default_only_API_commands':'retained raw commands, zero final API credit','tool_source_changes_between_stages':'API scripts added optimized mode after the first full suite; supplement receipt binds unchanged product bytes and all final API modes.','no_optimizer_work_credit':True},indent=2)+'\n')
members=[{'path':str(p.relative_to(REPO)),'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(ROOT.rglob('*'))if p.is_file()]
assert len({m['path']for m in members})==len(members)
seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'frozen-producer-guard-correction-awaiting-root-admission-and-independent-review','member_path_base':'repository-root','owned_scope':[str(ROOT.relative_to(REPO))+'/**'],'excluded':[str(seal_path.relative_to(REPO))],'members':members,'member_count':len(members),'member_bytes':sum(m['bytes']for m in members),'source_tree_digest':source_digest,'library_sha256':lib,'baseline_seal_sha256':'caceb9db9263de46ed876ff109f34eacb8fe13a9bd3ac47758f2bdac5c693ad3','selection_sha256':'0f70d7f9ce793d710da4d1d3dc97debaf8474d8bfb9031f77fdd1af5ddbc22fe','root_implementation_accepted':False,'independent_accepted':False,'native_runtime_or_capture_started':False,'GA_qualified':False}
seal_path.write_text(json.dumps(seal,indent=2)+'\n')
for m in members:
 p=REPO/m['path'];assert p.stat().st_size==m['bytes']and sha(p)==m['sha256']
assert {str(p.relative_to(REPO))for p in ROOT.rglob('*')if p.is_file()}=={m['path']for m in members}|{str(seal_path.relative_to(REPO))}
print(json.dumps({'seal':str(seal_path.relative_to(REPO)),'sha256':sha(seal_path),'members':len(members),'bytes':seal['member_bytes'],'source_tree_digest':source_digest,'library_sha256':lib,'case_counts_per_mode':counts,'original454_unchanged':True,'immutable':True},indent=2))
