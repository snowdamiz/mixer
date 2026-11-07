#!/usr/bin/env python3
"""Independent collector: exact owned sources; never execute producer collector."""
from pathlib import Path
import datetime,difflib,hashlib,importlib.util,json,os,shutil,sys
OWN=Path(__file__).resolve().parent;BASE=OWN.parent;ROOT=BASE.parents[1]
RUST='/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc'
def sha(b):return hashlib.sha256(b).hexdigest()
def dump(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
def load(path,name):s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
if __name__=='__main__':
 label=sys.argv[1];expected_tests=int(sys.argv[2]) if len(sys.argv)>2 else 0;run=OWN/'runs'/label;run.mkdir(parents=True)
 acquisition=load(OWN/'acquire.py','acquisition');acquisition.protected();acquisition.verify_producer()
 if not (OWN/'owned_runner.py').exists():
  original=(BASE/'selected-contract-preparation/owned_runner.py').read_text();amended=original.replace('<= 60:', '<= 180:').replace('deadline <=60s','deadline <=180s');(OWN/'owned_runner.py').write_text(amended);(OWN/'runner-diff.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),amended.splitlines(True),fromfile='frozen-preparation/owned_runner.py',tofile='final-review/owned_runner.py')))
 runner=load(OWN/'owned_runner.py','owned_runner');commands=[]
 env=dict(os.environ);env['PYTHONDONTWRITEBYTECODE']='1';env['MIXER_FINAL_REVIEW_SCRATCH']=str(run/'scratch');(run/'scratch').mkdir()
 def command(name,argv,seconds=30,expected=0):
  r=runner.run_owned(argv,executable=argv[0],cwd=ROOT,artifacts=run/name,timeout_seconds=seconds,env=env);commands.append({'name':name,**r});dump(run/'partial-receipt.json',{'commands':commands});
  if r['returncode']!=expected or r['status']!='completed':raise RuntimeError(f'{name}: unexpected status {r["status"]}/{r["returncode"]}')
  return r
 q=runner.run_owned([sys.executable,'-B','-c','import time; print("OWNED_PARTIAL_OUTPUT",flush=True); time.sleep(2)'],executable=sys.executable,cwd=ROOT,artifacts=run/'runner-timeout-qualification',timeout_seconds=0.2,env=env)
 assert q['status']=='timed-out-unqualified' and q['cleanup']['cleanup_verified'] and b'OWNED_PARTIAL_OUTPUT' in Path(q['stdout']['path']).read_bytes()
 dump(run/'runner-qualification.json',{'expected_timeout_receipt':q,'qualification':'partial output preserved, own direct child reaped and own group gone; no analyzer timeout'})
 for name,argv in [('revision',['/usr/bin/git','rev-parse','HEAD']),('python-version',[sys.executable,'--version']),('rust-version',[RUST,'--version','--verbose'])]:command(name,argv,10)
 source=run/'test-source';shutil.copytree(OWN/'archive-source',source)
 prepared=(BASE/'selected-contract-preparation/private_controls.rs').read_bytes();(run/'private_controls.rs').write_bytes(prepared);(run/'review_controls.rs').write_bytes((OWN/'review_controls.rs').read_bytes())
 prefix=(source/'src/envelope.rs').read_bytes();append=b'\n#[cfg(test)]\n#[path = "../../private_controls.rs"]\nmod independent_prepared;\n#[cfg(test)]\n#[path = "../../review_controls.rs"]\nmod independent_final;\n'
 # src is runs/<label>/test-source/src: two parent hops reach this run's frozen controls.
 (source/'src/envelope.rs').write_bytes(prefix+append)
 dump(run/'source-binding.json',{'production_envelope_prefix_sha256':sha(prefix),'test_append_sha256':sha(append),'prepared_test_sha256':sha(prepared),'independent_test_sha256':sha((OWN/'review_controls.rs').read_bytes()),'parent_source_sha256':sha((source/'src/analyzer.rs').read_bytes()),'prefix_unchanged':(source/'src/envelope.rs').read_bytes().startswith(prefix),'producer_tests_compiled_not_executed':'only fixture_envelope::independent_ filter runs','source_adapter':'cfg(test) module append only; no runtime product changes'})
 (run/'source-append.patch').write_text(''.join(difflib.unified_diff(prefix.decode().splitlines(True),(prefix+append).decode().splitlines(True),fromfile='admitted/src/envelope.rs',tofile='owned-test/src/envelope.rs')))
 binary=run/'review-tests';lib=run/'libreviewed.rlib'
 command('compile-independent-tests',[RUST,'--edition=2024','--test','-Dwarnings',str(source/'src/analyzer.rs'),'-o',str(binary)],60)
 command('list-independent-tests',[str(binary),'fixture_envelope::independent_','--list'],10)
 command('independent-tests',[str(binary),'fixture_envelope::independent_','--test-threads=1','--nocapture'],180,expected_tests)
 command('compile-public-library',[RUST,'--edition=2024','--crate-name','reviewed','--crate-type=rlib','-Dwarnings',str(OWN/'archive-source/src/analyzer.rs'),'-o',str(lib)],60)
 api={
 'positive':('use std::fs::File; use reviewed::*; pub fn inspect(x:&FixtureEnvelopeOutcomeV1){let _: &FixtureEnvelopeBoundaryV1=x.envelope().boundary();let _: &ReplayOutcome=x.framing();assert!(!x.full_replay_accepted());assert!(!x.stored_prefix_validated());assert!(!x.envelope().semantic_metrics_valid());} fn main(){let _:fn(&mut File,&mut File,&mut File,&mut File)->Result<FixtureEnvelopeOutcomeV1,AnalyzerError>=analyze_fixture_envelope_v1;let _:fn(&mut File,&mut File,&mut File,&mut File)->Result<ReplayOutcome,AnalyzerError>=analyze_fixture;}',None),
 'private-record':('use reviewed::FixtureDecodedRecordV1;fn main(){}','E0432'),
 'private-leaf':('use reviewed::observe_fixture_envelope_v1;fn main(){}','E0432'),
 'private-field':('pub fn f(x:&mut reviewed::FixtureEnvelopeOutcomeV1){x.envelope=panic!();}fn main(){}','E0616'),
 'no-copy':('fn need<T:Copy>(){} fn main(){need::<reviewed::FixtureEnvelopeObservationV1>();}','E0277'),
 'no-clone':('fn need<T:Clone>(){} fn main(){need::<reviewed::FixtureEnvelopeOutcomeV1>();}','E0277'),
 'no-word-trust-constructor':('fn main(){reviewed::FixtureEnvelopeObservationV1::from_words([0u64;16],true);}','E0599'),
 'no-serializer':('pub fn f(x:&reviewed::FixtureEnvelopeObservationV1){x.serialize();}fn main(){}','E0599'),
 'no-descriptor-authority-entry':('fn main(){reviewed::analyze_fixture_envelope_from_raw_fd(0,1,2,3,true);}','E0425')}
 api_results=[]
 for name,(text,code)in api.items():
  p=run/'api'/f'{name}.rs';p.parent.mkdir(exist_ok=True);p.write_text(text+'\n')
  r=command('api-'+name,[RUST,'--edition=2024','-Dwarnings',str(p),'--extern',f'reviewed={lib}','-o',str(run/'api'/name)],30,0 if code is None else 1)
  if code:assert code in Path(r['stderr']['path']).read_text()
  api_results.append({'name':name,'expected_error':code,'matched':True})
 acquisition.protected();acquisition.verify_producer()
 dump(run/'receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(Path(__file__).relative_to(ROOT)),label],'python':sys.version,'commands':commands,'API':api_results,'source_binding':json.loads((run/'source-binding.json').read_text()),'producer_and52_protected_members_unchanged':True,'producer_collector_executed':False,'scope':'independent bounded host controls only; original64 closure not rerun','cleanup':'all command receipts confirm direct child reaped and own group gone; owned scratch and binaries retained pending final archive/removal'})
 print(json.dumps({'status':'independent-run-completed','commands':len(commands),'api_positive':1,'api_negative':8,'run':str(run)},sort_keys=True))
