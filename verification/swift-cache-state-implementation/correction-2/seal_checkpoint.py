#!/usr/bin/env python3
"""Immutable correction2 behavior/proof-gap checkpoint, repo-relative members."""
import datetime,hashlib,json,pathlib,re,runpy,shutil,sys
ROOT=pathlib.Path(__file__).resolve().parent;REPO=ROOT.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=ROOT/'candidate-repo-seal.json';assert not out.exists()
runpy.run_path(str(ROOT/'audit_correction.py'),run_name='__main__')
for dirname,expected in [('g3-proposal','e57b30d5ef4ab540f98e8fa60d324c9497b5d0afeeb001c09c5ec549ebd1768b'),('g3-proposal-2','08b6b164cb4cb8d420538f9bcf4cb0b97850912789b29635aaf8e140a74263b7')]:
 p=ROOT/dirname/'seal.json';assert sha(p)==expected
 for m in json.loads(p.read_text())['members']:
  q=REPO/m['path'];assert q.stat().st_size==m['bytes']and sha(q)==m['sha256']
validation=json.loads((ROOT/'evidence/final-validation.json').read_text())
actual={str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'source').rglob('*'))if p.is_file()};assert actual==validation['source_sha256']
for mode in ['debug','optimized']:
 for stem,n in [(f'tests-{mode}',84),(f'regression-producer-{mode}-tests',108),(f'regression-independent-{mode}-tests',98)]:
  assert f'test result: ok. {n} passed; 0 failed;'in(ROOT/'evidence'/f'{stem}.stdout').read_text()
  assert json.loads((ROOT/'evidence'/f'{stem}.json').read_text())['exit']==0
 for name,count in [('api-summary.json',16),('old-api-summary.json',9)]:
  v=json.loads((ROOT/'evidence'/name).read_text());rows=[r for r in v.get('probes',v.get('controls'))if r['mode']==mode];assert len(rows)==count and all(r['compile_success']==r['expected_success']for r in rows)
# Preserve all raw input/report bytes once by SHA; private poison stays separate.
pool=ROOT/'evidence/content';pool.mkdir();cases=[];counts={}
for mode in ['debug','optimized']:
 r=json.loads((ROOT/'evidence'/f'tests-{mode}.json').read_text());start=r['started'];end=start+r['elapsed'];c={'public_actual_four_File':0,'private_injected_poison':0}
 for p in sorted((ROOT/'evidence/public-cases'/mode).iterdir()):
  raw=(p/'result.txt').read_text();private='boundary: InternalPoisoned'in raw;scope='private_injected_poison'if private else'public_actual_four_File';c[scope]+=1
  m=re.search(r'input_stamps_before_and_after=\[Stamp \{ fields: \[([^\]]+)',raw);f=[int(v.strip())for v in m[1].split(',')];stamp=f[4]+f[5]/1e9;assert start<=stamp<=end
  if private:
   target=ROOT/'evidence/private-fault-cases'/mode/p.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.move(p,target);p=target
  files=[]
  for q in sorted(p.glob('*.bin')):
   h=sha(q);dest=pool/(h+'.bin')
   if not dest.exists():shutil.copyfile(q,dest)
   assert sha(dest)==h
   files.append({'original_name':q.name,'bytes':q.stat().st_size,'sha256':h,'content_path':str(dest.relative_to(REPO))});q.unlink()
  row={'case':str(p.relative_to(ROOT)),'scope':scope,'files':files,'result_sha256':sha(p/'result.txt'),'input_mtime':stamp,'test_command_interval':[start,end],'private_public_reachability_credit':0 if private else None};cases.append(row);(p/'files.json').write_text(json.dumps(row,indent=2)+'\n')
 assert c=={'public_actual_four_File':29,'private_injected_poison':2};counts[mode]=c
(ROOT/'evidence/case-catalog.json').write_text(json.dumps({'counts_per_mode':counts,'cases':cases,'all_raw_bytes_preserved':True,'stale_cases':0,'new_seeded_private_transfer_controls_public_reachability_credit':0},indent=2)+'\n')
commands=[]
for p in sorted((ROOT/'evidence').rglob('*.start.json')):
 q=p.with_name(p.name.replace('.start.json','.json'));r=json.loads(q.read_text());assert r['parent_exit_observed']and r['failure']is None
 commands.append({'receipt':str(q.relative_to(ROOT)),'pid':r['pid'],'pgid':r['pgid'],'exit':r['exit'],'parent_exit_observed':True})
removed=[]
for p in sorted(ROOT.rglob('__pycache__')):
 for q in sorted(p.rglob('*')):
  if q.is_file():removed.append({'path':str(q.relative_to(ROOT)),'bytes':q.stat().st_size,'sha256':sha(q)})
 shutil.rmtree(p)
assert not list(ROOT.glob('.scratch-*'))
cleanup=json.loads((ROOT/'evidence/owned-product-cleanup.json').read_text());assert all(r['absent_after_removal']and not(ROOT/r['path']).exists()for r in cleanup)
for p in ROOT.rglob('*'):
 if p.is_file():assert p.suffix not in['.pyc','.rlib','.binary']and p.read_bytes()[:4]not in[b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'\x7fELF'],p
(ROOT/'evidence/final-cleanup.json').write_text(json.dumps({'commands':commands,'all_started_parents_have_observed_terminal_exits':True,'all_final_owned_products_hashed_before_removal':True,'product_hashes':'evidence/owned-product-cleanup.json','removed_bytecode':removed,'no_build_products_or_scratch_retained':True,'native_capture_or_process_inventory':False},indent=2)+'\n')
lib={str(p.relative_to(REPO)):sha(p)for p in sorted((ROOT/'source/library').glob('*.rs'))};digest=hashlib.sha256(json.dumps(actual,sort_keys=True,separators=(',',':')).encode()).hexdigest()
(ROOT/'handoff.json').write_text(json.dumps({'schema':1,'status':'frozen selected24-copy correction2 behavior checkpoint; work/lifetime proofs still open','selection_sha256':'c083b9bc61b2728847392f070cf0ae38de9d0c72b159d083cf384c96ad23b249','baseline_correction1_seal_sha256':'b141dab4e6c1ecc00bd4dc50a84852ae07b31438bc0126cc724e4b47fbb8f7a6','original454_and_correction1814_unchanged':True,'source_tree_digest':digest,'library_sha256':lib,'new_methods':30,'new_literal_methods_included':3,'old_producer_mapping':{'embedded':54,'separate_fixture':17,'private_transport':7,'total':78},'old_independent':14,'unique_methods_per_mode':122,'modes':['debug','optimized'],'binary_counts':[84,108,98],'API_controls_per_mode':{'new':16,'inherited':9},'complete_layout_rows_per_mode':23,'fresh_public_Result':488,'counts_actual_File_per_mode':counts,'literal_endpoint_equivalence_verified':True,'all_G1_G7_and_source_budget_proof_accepted':False,'lifetime_29344_union_proved':False,'three_partial_paid_exclusions_runtime_credit':0,'unselected_G3_proposals':['g3-proposal/seal.json','g3-proposal-2/seal.json'],'G3_implementation_not_changed':True,'further_source_edits_require_new_root_selection_and_closure':True,'proof_gap_inventory':'proofs/source-accounting-disposition.json','no_optimizer_margin_or_cap_increase':True,'independent_accepted':False,'root_implementation_accepted':False,'native_runtime_or_capture_started':False,'GA_qualified':False},indent=2)+'\n')
ms=[{'path':str(p.relative_to(REPO)),'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(ROOT.rglob('*'))if p.is_file()]
s={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,str(pathlib.Path(__file__).resolve())],'python':sys.version,'builder_sha256':sha(pathlib.Path(__file__)),'status':'frozen correction2 selected24-copy behavior and open-proof checkpoint; no source-budget or lifetime acceptance','member_path_base':'repository-root','owned_scope':['verification/swift-cache-state-implementation/correction-2/**'],'excluded':[str(out.relative_to(REPO))],'members':ms,'member_count':len(ms),'member_bytes':sum(m['bytes']for m in ms),'source_tree_digest':digest,'library_sha256':lib,'source_budget_accepted':False,'lifetime_proof_accepted':False,'root_implementation_accepted':False,'independent_accepted':False,'native_runtime_or_capture_started':False,'GA_qualified':False}
out.write_text(json.dumps(s,indent=2)+'\n')
for m in ms:
 p=REPO/m['path'];assert p.stat().st_size==m['bytes']and sha(p)==m['sha256']
assert {str(p.relative_to(REPO))for p in ROOT.rglob('*')if p.is_file()}=={m['path']for m in ms}|{str(out.relative_to(REPO))}
print(json.dumps({'seal':str(out.relative_to(REPO)),'sha256':sha(out),'members':len(ms),'bytes':s['member_bytes'],'source_tree_digest':digest,'library_sha256':lib,'source_budget_accepted':False,'lifetime_proof_accepted':False},indent=2))
