#!/usr/bin/env python3
"""Artifact-only cleanup/content preservation and immutable candidate seal."""
import datetime,hashlib,json,pathlib,re,shutil,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parent;REPO=ROOT.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
assert not (ROOT/'seal.json').exists(),'Do not silently overwrite an immutable seal'
validation=json.loads((ROOT/'evidence/final-validation.json').read_text())
actual={str(p.relative_to(ROOT)):sha(p)for p in (ROOT/'source').rglob('*')if p.is_file()}
assert actual==validation['source_sha256']
for mode in ['debug','optimized']:
 for name,count in [('tests',76),('regression-producer',100),('regression-independent',90)]:
  stem=f'{name}-{mode}' if name=='tests'else f'{name}-{mode}-tests'
  text=(ROOT/'evidence'/f'{stem}.stdout').read_text()
  assert f'test result: ok. {count} passed; 0 failed;' in text,(stem,count)
  assert json.loads((ROOT/'evidence'/f'{stem}.json').read_text())['exit']==0
assert json.loads((ROOT/'evidence/old-api-summary.json').read_text())['passed']
# Keep all raw File evidence once by content; separate private injected runs.
pool=ROOT/'evidence/content';pool.mkdir(exist_ok=True);cases=[]
for case in sorted((ROOT/'evidence/public-cases').glob('*/*')):
 if not case.is_dir():continue
 result=(case/'result.txt').read_text();private='boundary: InternalPoisoned' in result
 scope='private-injected-fault' if private else 'public-four-File'
 if private:
  dest=ROOT/'evidence/private-fault-cases'/case.parent.name/case.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(case),str(dest));case=dest
 files=[]
 for p in sorted(case.glob('*.bin')):
  digest=sha(p);target=pool/(digest+'.bin')
  if not target.exists():shutil.copyfile(p,target)
  assert sha(target)==digest
  files.append({'original_name':p.name,'bytes':p.stat().st_size,'sha256':digest,'content_path':str(target.relative_to(ROOT))});p.unlink()
 record={'case':str(case.relative_to(ROOT)),'scope':scope,'files':files,'result_sha256':sha(case/'result.txt'),'synthetic_identity_has_no_real_authority':True}
 (case/'files.json').write_text(json.dumps(record,indent=2)+'\n');cases.append(record)
for mode in ['debug','optimized']:
 assert sum(c['scope']=='private-injected-fault' and '/'+mode+'/' in c['case']for c in cases)==2
(ROOT/'evidence/case-catalog.json').write_text(json.dumps({'cases':cases,'deduplication_preserves_all_raw_bytes_by_sha256':True,'private_scope_rule':'Only the two deliberately injected fault File cases expect InternalPoisoned; their method/counter assertions are in cache_state_tests.rs. They are physically separated and not public passes.','native_or_real_source_authority':False},indent=2)+'\n')
removed=[]
for p in sorted(ROOT.rglob('__pycache__')):
 removed.append({'path':str(p.relative_to(ROOT)),'kind':'owned generated Python bytecode'});shutil.rmtree(p)
for p in sorted(ROOT.glob('.scratch-*')):
 removed.append({'path':str(p.relative_to(ROOT)),'kind':'owned disposable host scratch'});shutil.rmtree(p)
for p in sorted((ROOT/'evidence').iterdir()):
 if p.is_file() and (p.suffix=='.rlib' or re.fullmatch(r'(host-tests|regression-(producer|independent))(-debug|-optimized)?',p.name)):
  removed.append({'path':str(p.relative_to(ROOT)),'kind':'owned executable/archive','bytes':p.stat().st_size,'sha256':sha(p)});p.unlink()
for p in ROOT.rglob('*'):
 if p.is_file():
  assert p.suffix not in ['.pyc','.rlib'],p
  assert p.read_bytes()[:4] not in [b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'\x7fELF'],p
assert not list(ROOT.glob('.scratch-*'))
for p in (ROOT/'evidence').glob('*.start.json'):
 receipt=json.loads(p.with_name(p.name.replace('.start.json','.json')).read_text());assert receipt['parent_exit_observed']
(ROOT/'evidence/final-cleanup.json').write_text(json.dumps({'removed':removed,'all_corrected_runner_started_parents_have_observed_terminal_exits':True,'no_build_products_or_bytecode_in_closure':True,'no_owned_scratch_retained':True,'prior_unobserved_orphan_exit_remains_disappearance_only':True,'prior_interrupted_coordinator_incomplete':True,'native_runtime_or_capture_started':False,'other_projects_untouched':True},indent=2)+'\n')
doc=REPO/'docs/swift-cache-state-implementation.md';(ROOT/'documentation').mkdir(exist_ok=True);shutil.copyfile(doc,ROOT/'documentation'/doc.name)
context=subprocess.run(['git','rev-parse','HEAD'],cwd=REPO,capture_output=True,text=True,check=True,timeout=5).stdout.strip()
lib={str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'source/library').glob('*.rs'))}
source_digest=hashlib.sha256(canonical(actual)).hexdigest()
(ROOT/'handoff.json').write_text(json.dumps({'status':'producer immutable candidate; root admission and independent acceptance pending','context_revision_only':context,'source_tree_digest':source_digest,'library_sha256':lib,'selected_contract_receipt_sha256':'aac275052af88c802b0594c2d47318898d383b90f20d99a3914a4080c1a76dcc','implementation_selection_sha256':'012ef007459aa8561da2f3542902b6f4193c8ac06c5c325944502042103acad3','public_getter_selection_sha256':'80b8b39365e137f5f4db13f8a8348ca79aa17eb5abadf58ac929e3d25aec92e1','new_methods':22,'old_producer_methods':78,'old_independent_methods':14,'unique_methods_per_mode':114,'compiler_modes':['debug','optimized'],'new_API_controls':16,'unchanged_old_API_controls':9,'fresh_layouts':{'replay':104,'envelope':128,'old_aggregate':232,'observation':256,'new_aggregate':488,'complete_Result':488},'producer_source_bounds':{'delta_commit_reset':637,'semantic':7680,'inherited':471,'combined':8151,'preflight':8192,'role_union':29344,'candidate':2048},'three_partial_paid_exclusions_runtime_pass_credit':0,'independent_accepted':False,'fullReplayAccepted':False,'storedPrefixValidated':False,'semanticMetricsValid':False,'realBindingVerified':False,'native_runtime_or_capture_started':False,'GA_qualified':False,'external_owned_document':{'path':str(doc.relative_to(REPO)),'sha256':sha(doc)},'cleanup':'evidence/final-cleanup.json'},indent=2)+'\n')
members=[]
for p in sorted(ROOT.rglob('*')):
 if p.is_file():members.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)})
seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'frozen-producer-candidate-awaiting-root-admission-and-independent-review','excluded':['seal.json'],'members':members,'member_count':len(members),'member_bytes':sum(m['bytes']for m in members),'source_tree_digest':source_digest,'library_sha256':lib,'root_implementation_accepted':False,'independent_accepted':False,'native_runtime_or_capture_started':False,'GA_qualified':False}
(ROOT/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
# No mutation follows this exact-byte verification.
for m in members:
 p=ROOT/m['path'];assert p.stat().st_size==m['bytes'] and sha(p)==m['sha256']
assert sha(doc)==json.loads((ROOT/'handoff.json').read_text())['external_owned_document']['sha256']
print(json.dumps({'seal_sha256':sha(ROOT/'seal.json'),'members':len(members),'bytes':seal['member_bytes'],'source_tree_digest':source_digest,'library_sha256':lib,'case_scopes':{s:sum(c['scope']==s for c in cases)for s in ['public-four-File','private-injected-fault']}},indent=2))
