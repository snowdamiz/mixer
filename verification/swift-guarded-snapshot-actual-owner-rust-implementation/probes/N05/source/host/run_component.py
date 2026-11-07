#!/usr/bin/env python3
"""Bounded exact-method host runner. No native/capture/process inventory."""
from pathlib import Path
import datetime,hashlib,json,os,platform,shutil,subprocess,sys,tempfile,time
OUT=Path(__file__).resolve().parents[1]
ROOT=OUT.parents[1]
SOURCE=OUT/'source/vm'
RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
METHODS=['selected_layout_and_places','fresh_header_rows_and_cleanup','same_control_wasi_and_unrelated_owners','complete17_drift_precedes_prepare','explicit_narrowed_budgets','header_retained_when_actual_row_file_refuses','all64_slot_pin_pairs_checked','local_structure_refusals']
PREFIX='experimental_swift_reactor::cache::initial_profile_v1::tests::'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,j):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(j,indent=2,sort_keys=True)+'\n')
def manifest(src):
 members=[{'path':str(p.relative_to(src)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(src.rglob('*')) if p.is_file()]
 return {'schema':1,'member_count':len(members),'members':members,'tree_sha256':hashlib.sha256(json.dumps(members,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
def command(argv,folder,env,timeout=60):
 folder.mkdir(parents=True,exist_ok=False);started=time.monotonic();limit=8*1024*1024
 with (folder/'stdout').open('wb') as stdout_file,(folder/'stderr').open('wb') as stderr_file:
  child=subprocess.Popen([str(v) for v in argv],env=env,cwd=ROOT,stdout=stdout_file,stderr=stderr_file)
  killed=None
  while True:
   try:code=child.wait(timeout=.05);break
   except subprocess.TimeoutExpired:
    if time.monotonic()-started>timeout:killed='time'
    if (folder/'stdout').stat().st_size+(folder/'stderr').stat().st_size>limit:killed='output'
    if killed:child.kill();child.wait();code=124;break
 stdout=(folder/'stdout').read_bytes();stderr=(folder/'stderr').read_bytes()
 receipt={'argv':[str(v) for v in argv],'cwd':str(ROOT),'exit_code':code,'timeout_seconds':timeout,'output_byte_limit':limit,'supervisor_killed_for':killed,'elapsed_seconds':time.monotonic()-started,'stdout_sha256':sha(folder/'stdout'),'stderr_sha256':sha(folder/'stderr'),'owned_child_reaped':True}
 write(folder/'receipt.json',receipt);return receipt,stdout,stderr

def main():
 attempt=len(list((OUT/'commands').glob('attempt-*')))+1;logs=OUT/'commands'/f'attempt-{attempt}'
 scratch=Path(tempfile.mkdtemp(prefix='initial-profile-component-',dir=OUT));env=os.environ.copy();env['TMPDIR']=str(scratch/'tmp');Path(env['TMPDIR']).mkdir();env['CARGO_MANIFEST_DIR']=str(SOURCE)
 env['MIXER_INITIAL_PROFILE_EVIDENCE_DIR']=str(OUT/'artifacts'/f'attempt-{attempt}');Path(env['MIXER_INITIAL_PROFILE_EVIDENCE_DIR']).mkdir(parents=True)
 receipts=[];environment={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,'python_sha256':sha(Path(sys.executable)),'platform':platform.platform(),'rustc':str(RUSTC),'rustc_sha256':sha(RUSTC),'runner_sha256':sha(Path(__file__)),'scratch':str(scratch),'compiler_environment':{k:os.environ[k] for k in ['MACOSX_DEPLOYMENT_TARGET','SDKROOT','RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS'] if k in os.environ},'features':['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']}
 roster=json.loads((ROOT/'verification/swift-initial-profile-construction-protocol/test-budget-records.json').read_text())['records']
 tests_source=(SOURCE/'src/experimental_swift_reactor/cache/initial_profile_v1/tests.rs').read_text()
 for record in roster:
  explicit='(\"'+record['id']+'\",SwiftRunBudget {'+','.join(f'{k}:{v}' for k,v in record['budget'].items())+'})'
  assert explicit in tests_source,'missing complete literal budget: '+record['id']
 assert 'SwiftRunBudget::default' not in tests_source
 environment['complete_frozen_budget_literals_verified']=len(roster)
 source=manifest(SOURCE);assert source['member_count']==140;write(OUT/f'source-manifest-attempt-{attempt}.json',source)
 try:
  for name,args in [('rustc-vV',['-vV']),('target-cfg',['--print','cfg','--target','aarch64-apple-darwin']),('target-features',['--print','target-features','--target','aarch64-apple-darwin'])]:
   result,stdout,_=command([RUSTC]+args,logs/name,env);receipts.append(result);environment[name]=stdout.decode(errors='replace')
  if '--contracts-only' not in sys.argv:
   target_ir=scratch/'target-data-layout.ll'
   target_argv=[RUSTC,'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','--crate-type','lib','--emit=llvm-ir']
   for feature in environment['features']:target_argv+=['--cfg',f'feature="{feature}"']
   target_argv+=[SOURCE/'src/lib.rs','-o',target_ir]
   result,_,_=command(target_argv,logs/'target-data-layout',env);receipts.append(result)
   assert result['exit_code']==0
   environment['target_ir_sha256']=sha(target_ir);environment['target_ir_bytes']=target_ir.stat().st_size
   environment['target_data_layout']=[line for line in target_ir.read_text().splitlines() if line.startswith('target datalayout') or line.startswith('target triple')]
   measured={};executables=[]
   for mode,opt in [('debug','0'),('optimized','3')]:
    for config in ['unit','host','ordinary']:
     artifact=scratch/f'{config}-{mode}.dylib' if config!='unit' else scratch/f'unit-{mode}'
     argv=[RUSTC,'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C',f'opt-level={opt}','-C','overflow-checks=yes','-C','panic=unwind']
     argv+=['--test'] if config=='unit' else ['--crate-type','cdylib']
     if config=='host':argv+=['--cfg','mixer_initial_profile_component_host']
     for feature in environment['features']:argv+=['--cfg',f'feature="{feature}"']
     argv+=[SOURCE/'src/lib.rs','-o',artifact]
     result,_,_=command(argv,logs/f'{config}-{mode}-compile',env);receipts.append(result)
     if result['exit_code']:continue
     environment[f'{config}_{mode}_executable']={'sha256':sha(artifact),'bytes':artifact.stat().st_size}
     if config=='ordinary':
      result,stdout,_=command(['/usr/bin/nm','-gU',artifact],logs/f'{config}-{mode}-symbols',env)
      result['expectation_met']=result['exit_code']==0 and b'mixer_initial_profile_component_host_v1' not in stdout
      receipts.append(result);continue
     directory=OUT/'artifacts'/f'attempt-{attempt}'/f'{config}-{mode}';directory.mkdir();env['MIXER_INITIAL_PROFILE_EVIDENCE_DIR']=str(directory)
     env['MIXER_INITIAL_PROFILE_EXPECTED_ARTIFACT_SHA256']=sha(artifact)
     argv=[artifact,'--exact',PREFIX+METHODS[0],'--nocapture','--test-threads=1'] if config=='unit' else [sys.executable,Path(__file__).resolve(),'--invoke-host-method',artifact,'1']
     result,stdout,_=command(argv,logs/f'{config}-{mode}-layout',env,timeout=30);receipts.append(result)
     rows=[]
     for line in stdout.decode(errors='replace').splitlines():
      parts=line.split('\t')
      if len(parts)==5 and parts[0]=='TYPE':rows.append({'id':int(parts[1]),'bytes':int(parts[3]),'alignment':int(parts[4])})
     expected_path=ROOT/'verification/swift-semantic-adapter-root-review/initial-profile-unit-test-local-structure.json' if config=='unit' else ROOT/'verification/swift-initial-profile-construction-protocol/local-structure-proposal.json'
     expected=[{k:e[k] for k in ['id','bytes','alignment']} for e in json.loads(expected_path.read_text())['type_layout']]
     measured[f'{config}-{mode}']={'rows':rows,'expected_path':str(expected_path),'expected_sha256':sha(expected_path),'exact_all165':rows==expected}
     executables.append((config,mode,artifact,directory))
   write(OUT/f'actual-layout-comparison-attempt-{attempt}.json',measured)
   assert len(measured)==4 and all(v['exact_all165'] for v in measured.values()),'STOP: further actual layout drift; no table use or behavior execution'
   if '--measure-only' not in sys.argv:
    for config,mode,artifact,directory in executables:
     env['MIXER_INITIAL_PROFILE_EVIDENCE_DIR']=str(directory)
     env['MIXER_INITIAL_PROFILE_EXPECTED_ARTIFACT_SHA256']=sha(artifact)
     methods=METHODS[1:]+(['original_prepare_construct_completion_outcomes','occupancy_foreign_proof_and_prepare_failures','authentic_owner_and_every_initial_field','post_acquire_chronology_cannot_reenter','canonical_ceilings_and_prepare_capacity','foreign_wasi_prepare_owned_cleanup','control_live_counts_and_peaks','all17_explicit_exhaustions','supported_count_boundary'] if config=='unit' else [])
     for method in methods:
      argv=[artifact,'--exact',PREFIX+method,'--nocapture','--test-threads=1'] if config=='unit' else [sys.executable,Path(__file__).resolve(),'--invoke-host-method',artifact,str(METHODS.index(method)+1)]
      result,_,_=command(argv,logs/f'{config}-{mode}-{method}',env,timeout=30);receipts.append(result)
     if config=='unit':
      env['MIXER_PROFILE_EVIDENCE_DIR']=str(directory)
      row_roster=json.loads((ROOT/'verification/swift-cache-state-profile-adapter/required-tests.json').read_text())['methods']
      for method in row_roster:
       result,_,_=command([artifact,'--exact',method,'--nocapture','--test-threads=1'],logs/f'{config}-{mode}-accepted-row-{method.split("::")[-1]}',env,timeout=30);receipts.append(result)
  if '--contracts-only' in sys.argv:
   amendment=ROOT/'verification/swift-semantic-adapter-root-review/initial-profile-compile-placement-amendment.md'
   assert sha(amendment)=='fc367c1745e1c7b80d758ba1edd4d0df226053654d4dd054d284253033adc481'
   environment['compile_placement_amendment_sha256']=sha(amendment)
   cases=[('positive_contract','descendant',None),('positive_contract','sibling',None),('guard_literal_from_sibling','sibling','E0603'),('external_selection_literal','sibling','E0603'),('guard_escape','descendant','lifetime may not live long enough'),('proof_escape','descendant','lifetime may not live long enough'),('cache_move','descendant','E0505'),('cache_mutation','descendant','E0502'),('control_mutation','descendant','E0502'),('row_foreign_snapshot','descendant','E0061'),('callback_reentry','descendant','E0308')]
   for mode,opt in [('debug','0'),('optimized','3')]:
    for name,placement,expected in cases:
     variant=scratch/'variant';shutil.copytree(SOURCE,variant)
     path='src/experimental_swift_reactor/cache.rs' if placement=='sibling' else 'src/experimental_swift_reactor/cache/initial_profile_v1/compile_contracts.rs'
     delta='\n#[cfg(test)] mod initial_profile_external_contract { include!(env!("MIXER_INITIAL_PROFILE_COMPILE_CASE")); }\n' if placement=='sibling' else '\ninclude!(env!("MIXER_INITIAL_PROFILE_COMPILE_CASE"));\n'
     destination=variant/path;destination.write_bytes(destination.read_bytes()+delta.encode())
     fixture=Path(__file__).parent/'compile_cases'/(name+'.rs');env['MIXER_INITIAL_PROFILE_COMPILE_CASE']=str(fixture)
     key=f'{mode}-{placement}-{name}';actual=manifest(variant);assert actual['member_count']==140
     write(OUT/'compiler-variants'/f'attempt-{attempt}'/(key+'.json'),{'manifest':actual,'source_distribution_tree_sha256':source['tree_sha256'],'test_only_append_path':path,'test_only_append_bytes':delta,'fixture_path':str(fixture),'fixture_sha256':sha(fixture),'fixture_declared_path':'verification/swift-initial-profile-construction-host/compile_cases/'+fixture.name,'environment':{'MIXER_INITIAL_PROFILE_COMPILE_CASE':str(fixture)}})
     env['CARGO_MANIFEST_DIR']=str(variant)
     argv=[RUSTC,'--test','--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','--emit=metadata','-C',f'opt-level={opt}','-C','overflow-checks=yes']
     for feature in environment['features']:argv+=['--cfg',f'feature="{feature}"']
     if placement=='sibling':argv+=['--cfg','mixer_initial_profile_external_contract']
     argv+=[variant/'src/lib.rs','-o',scratch/'case.rmeta']
     result,_,stderr=command(argv,logs/key,env);result['expected_diagnostic']=expected;result['expected_compile_success']=expected is None
     result['expectation_met']=result['exit_code']==0 if expected is None else result['exit_code']!=0 and expected in stderr.decode(errors='replace')
     receipts.append(result);shutil.rmtree(variant)
 finally:
  shutil.rmtree(scratch);environment['cleanup']={'owned_scratch_removed':not scratch.exists(),'owned_children_reaped':all(r['owned_child_reaped'] for r in receipts),'native_or_capture_process_started':False,'compiler_products_retained':False}
  write(OUT/f'environment-attempt-{attempt}.json',environment);write(OUT/f'command-receipts-attempt-{attempt}.json',receipts)
 print(json.dumps({'attempt':attempt,'commands':len(receipts),'unexpected':[r['argv'] for r in receipts if not r.get('expectation_met',r['exit_code']==0)],'cleanup':environment['cleanup']}))
 if any(not r.get('expectation_met',r['exit_code']==0) for r in receipts):sys.exit(1)
if __name__=='__main__':
 if len(sys.argv)==4 and sys.argv[1]=='--invoke-host-method':
  import ctypes
  method=int(sys.argv[3]);assert method in range(1,9)
  library=Path(sys.argv[2]).resolve();assert library.is_file() and library.parent.parent==OUT and library.name in {'host-debug.dylib','host-optimized.dylib'} and library.parent.name.startswith('initial-profile-component-')
  assert sha(library)==os.environ['MIXER_INITIAL_PROFILE_EXPECTED_ARTIFACT_SHA256']
  symbol=ctypes.CDLL(str(library)).mixer_initial_profile_component_host_v1
  symbol.argtypes=[ctypes.c_uint32];symbol.restype=ctypes.c_uint32
  sys.exit(symbol(method))
 main()

