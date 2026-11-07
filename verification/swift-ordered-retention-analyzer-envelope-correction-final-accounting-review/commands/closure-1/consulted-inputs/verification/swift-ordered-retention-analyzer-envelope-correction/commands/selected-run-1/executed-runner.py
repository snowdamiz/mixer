#!/usr/bin/env python3
"""Bounded selected-source host collector. Does not import old collectors.
Each owned child has a new process group, deadline, persistent streams, kill/reap
on timeout. Only selected425 source executes; no native/hosted/runtime discovery.
"""
from pathlib import Path
import datetime,hashlib,json,os,re,shutil,signal,subprocess,sys,tarfile,time
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
RUST=Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc')
SEL=P/'inputs/root-correction-numeric-contract-selection.json'
UPSTREAM=[
('swift-ordered-retention-analyzer-design','c52828b9bbd2aea835871f1f6b68c6dd29281499ee080e5e52fefe525d1e92a8'),('swift-ordered-retention-analyzer-review','da87dd37e0983e212bbaf9658bc3177cb47c146bb13d82ddd2fea948c1966ebc'),('swift-ordered-retention-diagnostic-rust','c19bd3fb06e2db11a5e6ecb5aad8de2ca6ee19a35e50a5ba691ecb598bde40bf'),('swift-ordered-retention-diagnostic-completion','2e427447a34357ab4ff70eb220f56754f685a930edf4a89ebc29096fff3b73ba'),('swift-ordered-retention-diagnostic-completion-review','87a6fe21fd5c8f6590992aae8cc826e2502454686cf0d7a8c550acb7965827cc'),('swift-ordered-retention-analyzer-library','777e0a1b7a10d483bacb81475ad6c7af9a4d40fff64dd5ff2f3d893e1cd0fe63'),('swift-ordered-retention-analyzer-library-review','a5e21463c820277e1857a7eebcecdc7e45f40857b9c1b06a1bd4e'),('swift-ordered-retention-analyzer-fsm-contract','bde96e5f4f1b0ad5bc6366fee79a47f7a375247959191b206d8e7799ed4da193'),('swift-ordered-retention-analyzer-fsm-contract-review','101e6c9a67e41cce0e3c82c67ba92ef8025da19376b0578f8ddcdd694fb67212'),('swift-ordered-retention-analyzer-envelope','ea5214e8571277e0a289bb44add5716d8c30e5d0bf3332939f18575ecf3d4eae'),('swift-ordered-retention-analyzer-envelope-accounting-review','225d35ccd2c76c6306f7be21d3931c57a47ba6263897ba1847bfe7995226bf7f'),('swift-ordered-retention-analyzer-envelope-review','03c1986c3a19ae6464ac96cabe7743f6a562118bcb4a05689026df0de2165476'),('swift-ordered-retention-analyzer-envelope-correction-accounting-review','f4b5136a8b513ca208e2f914acfea559d40edfe53a2cfb52a92129c82ec841d0'),('swift-ordered-retention-analyzer-envelope-correction-accounting-review-2','c500c43ee55db92bd7a4bcaf62a90224761ee08dfbba80457069eebd7c8fd9ce')]
# Correct exact accepted hash; tuple above deliberately has no external lookup.
UPSTREAM[6]=(UPSTREAM[6][0],'a5e21463c820277e1857a7eebcecdc7e45f40857b9c1dd39e8741f9b06a1bd4e')
def sha(q):return hashlib.sha256(q.read_bytes()).hexdigest()
def desc(q,base=ROOT):return {'path':str(q.relative_to(base)),'bytes':q.stat().st_size,'sha256':sha(q)}
def verified(path,base):
 value=json.loads(path.read_text());total=0
 for m in value['members']:
  q=base/m['path'];assert q.stat().st_size==m['bytes']and sha(q)==m['sha256'],str(q);total+=m['bytes']
 return {'path':str(path.relative_to(ROOT)),'sha256':sha(path),'members':len(value['members']),'bytes':total}
def upstream():
 out=[]
 for name,h in UPSTREAM:
  path=ROOT/'verification'/name/'seal.json';assert sha(path)==h,(name,'seal');out.append(verified(path,ROOT))
 for name in ('operation-ledger-proposal-1','operation-ledger-proposal-2'):out.append(verified(P/'commands'/name/'manifest.json',P/'commands'/name))
 return out

def main():
 tag=sys.argv[1];assert re.fullmatch(r'selected-run-[1-9][0-9]*',tag)
 run=P/'commands'/tag;run.mkdir(exist_ok=False)
 scratch=P/'scratch'/tag;scratch.mkdir(parents=True,exist_ok=False)
 receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'fresh selected425 fixture envelope host Rust; baseline44 regression+adapted20+6 new, not original timeout closure','commands':[],'source_inputs':[],'status':'running','source_sha256':sha(P/'src/envelope.rs'),'root_selection_sha256':sha(SEL),'native_UI_capture_hosted_process_or_device_discovery':False,'scratch':str(scratch.relative_to(ROOT))}
 active=None
 def save(): (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 def command(name,argv,deadline=60,env=None,success=True):
  nonlocal active
  assert active is None
  strings=[str(x)for x in argv];out=run/(name+'.stdout');err=run/(name+'.stderr')
  record={'name':name,'argv':strings,'deadline_seconds':deadline,'stdout':out.name,'stderr':err.name,'start':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'running','dedicated_process_group':True}
  receipt['commands'].append(record);save();start=time.monotonic()
  with out.open('wb')as fo,err.open('wb')as fe:
   active=subprocess.Popen(strings,cwd=ROOT,stdout=fo,stderr=fe,start_new_session=True,env=env)
   timed=False
   try:code=active.wait(timeout=deadline)
   except subprocess.TimeoutExpired:
    timed=True;os.killpg(active.pid,signal.SIGTERM)
    try:code=active.wait(timeout=2)
    except subprocess.TimeoutExpired:os.killpg(active.pid,signal.SIGKILL);code=active.wait(timeout=5)
   assert active.poll()is not None;active=None
  record.update(status=code,timed_out=timed,child_reaped=True,elapsed_seconds=time.monotonic()-start,stdout_sha256=sha(out),stderr_sha256=sha(err));save()
  print(json.dumps({'command':name,'status':code,'timed_out':timed,'seconds':round(record['elapsed_seconds'],3)}),flush=True)
  if timed or(success and code!=0):raise RuntimeError(name+' failed; streams retained')
  return out.read_text(),err.read_text(),code
 try:
  assert sha(SEL)=='199dfa75b024d04eeef28f2f40165115797a0bbb3d09a2405426172d8339867c'
  assert receipt['source_sha256']=='7b8237abbaec492e595508eb7456dab38fbb0d92d8d3cd5a88184f7c1082b9d1'
  receipt['upstream_before']=upstream();save()
  # Runtime code outside first19 compile-time constant lines is byte-identical
  # after excluding the selected explanatory comment-only update.
  prior=(P/'commands/operation-ledger-proposal-2/source-envelope.rs').read_text().splitlines()
  current=(P/'src/envelope.rs').read_text().splitlines()
  code=lambda ss:'\n'.join(l for l in ss[19:]if not l.lstrip().startswith('//'))
  assert code(prior)==code(current),'nonconstant production mutation'
  for name in ('fixture_tests.rs','independent_tests.rs','private_io_tests.rs'):
   assert sha(P/'tests'/name)==sha(P/'baseline/tests'/name)
  assert sha(P/'baseline/tests/envelope_tests.rs')==sha(ROOT/'verification/swift-ordered-retention-analyzer-envelope/tests/envelope_tests.rs')
  receipt['baseline44_test_files_unchanged']=True;receipt['baseline20_unchanged']=True
  shutil.copy2(__file__,run/'executed-runner.py')
  command('context-revision',['git','rev-parse','HEAD'],10)
  command('python-version',[sys.executable,'--version'],10)
  command('rust-version',[RUST,'--version','--verbose'],10)
  # Fresh evaluation, not copied old binary expected values. The selected model
  # is only the128->425 debit parameter derivation; old model is never executed.
  command('derive-selected-oracle',[sys.executable,'-B',P/'derive_selected_oracle.py'],30,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
  for name in ('src','tests','inputs'):shutil.copytree(P/name,run/'sources'/name)
  for name in ('derive_selected_oracle.py','selected-contract-delta.json','apply_selected_contract.py'):shutil.copy2(P/name,run/'sources'/name)
  proposal=P/'commands/operation-ledger-proposal-2'
  for name in ('operation-ledger.json','memory-and-phase-inventory.json','complete-transfer-edge-inventory.json','finalization-funding-table.json','framing22-crosswalk.json','actual-complete-types.json'):
   v=json.loads((proposal/name).read_text());v['proposal2_source_sha256']=v.get('source_sha256',receipt['source_sha256']);v['source_sha256']=receipt['source_sha256'];v['selected_contract_sha256']=sha(SEL);v['runtime_source_delta']='selected constants/compile-time partition/comments only; body unchanged';(run/('selected-'+name)).write_text(json.dumps(v,indent=2)+'\n')
  receipt['source_inputs']=[desc(q,run/'sources')for q in sorted((run/'sources').rglob('*'))if q.is_file()]
  receipt['source_tree_sha256']=hashlib.sha256(json.dumps(receipt['source_inputs'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
  receipt['tools']=[{'requested_path':str(q),'resolved_path':str(q.resolve()),'bytes':q.stat().st_size,'sha256':sha(q)}for q in (Path(sys.executable),RUST)]
  save()
  lib=run/'libcorrected_envelope.rlib'
  command('compile-selected-library',[RUST,'--edition=2024','--crate-name','corrected_envelope','--crate-type=rlib','-Dwarnings',run/'sources/src/analyzer.rs','-o',lib],60)
  build=run/'build';(build/'inputs').mkdir(parents=True)
  shutil.copytree(run/'sources/tests',build/'tests')
  (build/'inputs/framing.rs').write_bytes((run/'sources/src/analyzer.rs').read_bytes()+(run/'sources/tests/private_io_tests.rs').read_bytes())
  shutil.copy2(run/'sources/src/envelope.rs',build/'inputs/envelope.rs')
  shutil.copy2(run/'sources/tests/independent_tests.rs',build/'independent_tests.rs')
  for n in ('oracle-425.bin','oracle-budget-425.bin'):shutil.copy2(run/'sources/inputs'/n,build/'inputs'/n)
  binary=run/'selected-fixture-tests'
  command('compile-selected-tests',[RUST,'--edition=2024','--test','-Dwarnings',build/'independent_tests.rs','-o',binary],60)
  env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',MIXER_REVIEW_SCRATCH=str(scratch/'review'),MIXER_ANALYZER_LIBRARY_TEST_SCRATCH=str(scratch/'framing'),MIXER_ENVELOPE_SCRATCH=str(scratch/'envelope'),MIXER_ANALYZER_LIBRARY_HISTORICAL=str(run/'sources/inputs/historical'))
  for name in ('review','framing','envelope'):(scratch/name).mkdir()
  receipt['test_environment']={k:v for k,v in env.items()if k.startswith('MIXER_')or k=='PYTHONDONTWRITEBYTECODE'}
  listing,_,_=command('list-selected-tests',[binary,'--list'],10,env)
  receipt['listed_test_methods']=sum(l.endswith(': test')for l in listing.splitlines());assert receipt['listed_test_methods']==70
  baseline,_,_=command('fresh-selected-framing44',[binary,'--test-threads=1','--nocapture','--skip','product::fixture_envelope::'],180,env)
  assert '44 passed; 0 failed' in baseline
  receipt['framing44_passed']=44;save()
  selected,_,_=command('fresh-selected-envelope26',[binary,'product::fixture_envelope::','--test-threads=1','--nocapture'],180,env)
  assert '26 passed; 0 failed' in selected
  assert 'ENVELOPE_ORACLE_CASES=16170'in selected and 'CORRECTED_FINITE_BUDGET_CASES=5544'in selected
  receipt['selected_envelope_passed']=26;receipt['fresh_finite_model_comparisons']=21714
  # Actual public import/signature compile and five fail-closed negative controls.
  api=run/'api';api.mkdir()
  positive='''use corrected_envelope::*;\nfn inspect(x:&FixtureEnvelopeOutcomeV1)->bool {let _=x.framing();let e=x.envelope();let _=(e.boundary(),e.reason(),e.observed_records(),e.state(),e.phase(),e.mask(),e.envelope_debit());x.full_replay_accepted()||e.semantic_metrics_valid()||x.stored_prefix_validated()}\nfn main(){let _f:fn(&mut std::fs::File,&mut std::fs::File,&mut std::fs::File,&mut std::fs::File)->Result<FixtureEnvelopeOutcomeV1,AnalyzerError>=analyze_fixture_envelope_v1;let _i:fn(&FixtureEnvelopeOutcomeV1)->bool=inspect;}\n'''
  (api/'positive.rs').write_text(positive)
  command('api-positive',[RUST,'--edition=2024','-Dwarnings',api/'positive.rs','--extern',str('corrected_envelope='+str(lib)),'-o',api/'positive'],30)
  negatives={
   'private-field':('use corrected_envelope::*; pub fn f(x:&mut FixtureEnvelopeObservationV1){x.envelope_debit=0;} fn main(){}','E0616'),
   'no-clone':('use corrected_envelope::*; fn need<T:Clone>(){} fn main(){need::<FixtureEnvelopeObservationV1>();}','E0277'),
   'no-copy':('use corrected_envelope::*; fn need<T:Copy>(){} fn main(){need::<FixtureEnvelopeOutcomeV1>();}','E0277'),
   'no-record-constructor':('use corrected_envelope::FixtureDecodedRecordV1; fn main(){}','E0432'),
   'no-word-or-boolean-entry':('use corrected_envelope::*; fn main(){let mut words=[0u64;16];let _=analyze_fixture_envelope_v1(&mut words,true);}','E0061')}
  for name,(src,expected)in negatives.items():
   q=api/(name+'.rs');q.write_text(src)
   _,err,code=command('api-negative-'+name,[RUST,'--edition=2024',q,'--extern','corrected_envelope='+str(lib),'-o',api/name],30,success=False)
   assert code!=0 and expected in err,name
  receipt['api_positive_compiles']=1;receipt['api_expected_negative_compiles']=5
  receipt['status']='passed';receipt['methods_passed']=70
 except BaseException as e:
  receipt['status']='failed';receipt['error']=repr(e)
  print(json.dumps({'status':'failed','error':repr(e)}),flush=True)
 finally:
  if active is not None:
   os.killpg(active.pid,signal.SIGTERM)
   try:active.wait(timeout=2)
   except subprocess.TimeoutExpired:os.killpg(active.pid,signal.SIGKILL);active.wait(timeout=5)
   active=None
  try:receipt['upstream_after']=upstream();assert receipt.get('upstream_before')==receipt['upstream_after']
  except BaseException as e:receipt['preservation_error']=repr(e);receipt['status']='failed'
  receipt['scratch_files']=[desc(q,scratch)for q in sorted(scratch.rglob('*'))if q.is_file()]
  with tarfile.open(run/'owned-scratch.tar.gz','w:gz')as tf:tf.add(scratch,arcname='owned-scratch')
  receipt['scratch_archive']=desc(run/'owned-scratch.tar.gz',run)
  shutil.rmtree(scratch);receipt['owned_scratch_removed_after_children_reaped']=not scratch.exists()
  receipt['binaries_removed']=[]
  for q in [run/'libcorrected_envelope.rlib',run/'selected-fixture-tests',run/'api/positive']:
   if q.exists():receipt['binaries_removed'].append(desc(q,run));q.unlink()
  receipt['children_reaped']=True;receipt['finished']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
  print(json.dumps({'status':receipt['status'],'methods':receipt.get('methods_passed'),'finite_comparisons':receipt.get('fresh_finite_model_comparisons'),'source':receipt['source_sha256'],'source_tree':receipt.get('source_tree_sha256'),'cleanup':receipt['owned_scratch_removed_after_children_reaped']}),flush=True)
 if receipt['status']!='passed':raise SystemExit(1)
if __name__=='__main__':main()
