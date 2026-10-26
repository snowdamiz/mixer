#!/usr/bin/env python3
"""Source-bound independent preaccess controls; exact140 test-only variants."""
from pathlib import Path
import datetime,hashlib,importlib.util,json,os,selectors,shutil,signal,subprocess,sys,tempfile,time
OUT=Path(__file__).resolve().parent
PRE=OUT.parent
SOURCE=OUT/'staging/verification/component/source/vm'
RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
FEATURES=['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
def manifest(base):
 m=[{'path':str(p.relative_to(base)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(base.rglob('*')) if p.is_file()]
 return {'schema':1,'member_count':len(m),'members':m,'tree_sha256':hashlib.sha256(json.dumps(m,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
def command(argv,name,env):
 folder=OUT/'independent-commands'/name;folder.mkdir(parents=True,exist_ok=False);start=time.monotonic();killed=None
 with (folder/'stdout').open('wb') as a,(folder/'stderr').open('wb') as b:
  p=subprocess.Popen(list(map(str,argv)),env=env,cwd=OUT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
  sel=selectors.DefaultSelector();sel.register(p.stdout,selectors.EVENT_READ,(a,0));sel.register(p.stderr,selectors.EVENT_READ,(b,0))
  while sel.get_map():
   if time.monotonic()-start>60 and not killed:killed='time';os.killpg(p.pid,signal.SIGKILL)
   for key,_ in sel.select(timeout=.1):
    block=os.read(key.fileobj.fileno(),65536)
    if not block:sel.unregister(key.fileobj);key.fileobj.close();continue
    dest,n=key.data;dest.write(block[:max(0,8388608-n)]);n+=len(block);sel.modify(key.fileobj,selectors.EVENT_READ,(dest,n))
    if n>8388608 and not killed:killed='output';os.killpg(p.pid,signal.SIGKILL)
  sel.close();code=p.wait(timeout=5)
 r={'argv':list(map(str,argv)),'cwd':str(OUT),'exit_code':code,'elapsed_seconds':time.monotonic()-start,'timeout_seconds':60,'output_byte_limit_each':8388608,'supervisor_killed_for':killed,'owned_child_reaped':True,'stdout_sha256':sha(folder/'stdout'),'stderr_sha256':sha(folder/'stderr')};write(folder/'receipt.json',r);return r,(folder/'stderr').read_text()
def args(variant,mode,out,metadata=False):
 a=[RUSTC,'--test','--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C',f'opt-level={0 if mode=="debug" else 3}','-C','overflow-checks=yes']
 if metadata:a+=['--emit=metadata']
 for f in FEATURES:a+=['--cfg',f'feature="{f}"']
 return a+[variant/'src/lib.rs','-o',out]
def main():
 scratch=Path(tempfile.mkdtemp(prefix='independent-candidate-',dir=OUT));env=os.environ.copy();env['TMPDIR']=str(scratch/'tmp');Path(env['TMPDIR']).mkdir();env['MIXER_INDEPENDENT_PREACCESS_FIXTURES']=str(PRE/'fixtures');receipts=[]
 environment={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,'python_executable_sha256':sha(Path(sys.executable)),'rustc':str(RUSTC),'rustc_sha256':sha(RUSTC),'source_manifest':manifest(SOURCE),'independent_source_sha256':sha(OUT/'independent_controls.rs'),'features':FEATURES,'owned_scratch':str(scratch),'compiler_environment':{k:env[k] for k in ['SDKROOT','MACOSX_DEPLOYMENT_TARGET','RUSTFLAGS'] if k in env}}
 try:
  for mode in ['debug','optimized']:
   variant=scratch/'variant';shutil.copytree(SOURCE,variant);path='src/experimental_swift_reactor/cache/initial_profile_v1/tests.rs';delta=(OUT/'independent_controls.rs').read_bytes();q=variant/path;q.write_bytes(q.read_bytes()+b'\n'+delta)
   write(OUT/'independent-variants'/f'{mode}-actual-owner-tests.json',{'source_manifest':manifest(variant),'original_tree_sha256':environment['source_manifest']['tree_sha256'],'append_path':path,'append_bytes_sha256':hashlib.sha256(b'\n'+delta).hexdigest(),'independent_test_input_sha256':sha(OUT/'independent_controls.rs'),'preaccess_seal_sha256':'b9048e6edd9941ca3293badd322d89fbfb16a25c1cb02502896d38c589b4295a'})
   env['CARGO_MANIFEST_DIR']=str(variant);binary=scratch/f'unit-{mode}';r,_=command(args(variant,mode,binary),f'{mode}-compile-independent-controls',env);receipts.append(r);assert r['exit_code']==0
   environment[f'{mode}_executable']={'sha256':sha(binary),'bytes':binary.stat().st_size}
   directory=OUT/'independent-artifacts'/mode;directory.mkdir(parents=True,exist_ok=False);env['MIXER_INITIAL_PROFILE_EVIDENCE_DIR']=str(directory)
   for method in ['independent_preaccess_exact_bytes_and_actual_files','independent_header_retained_for_four_actual_file_errors']:
    r,_=command([binary,'--exact','experimental_swift_reactor::cache::initial_profile_v1::tests::'+method,'--nocapture','--test-threads=1'],f'{mode}-{method}',env);receipts.append(r);assert r['exit_code']==0
   shutil.rmtree(variant)
   # Independently frozen compiler fixture sources at the root-selected sites.
   for fixture in sorted((PRE/'predeclared-compile-cases').glob('*.rs')):
    modes=['internal','external'] if fixture.stem=='positive_contract' else ['external'] if fixture.stem in ['guard_literal_from_sibling','external_selection_literal'] else ['internal']
    for placement in modes:
     shutil.copytree(SOURCE,variant)
     path='src/experimental_swift_reactor/cache.rs' if placement=='external' else 'src/experimental_swift_reactor/cache/initial_profile_v1/compile_contracts.rs'
     delta='\n#[cfg(test)] mod initial_profile_external_contract { include!(env!("MIXER_INITIAL_PROFILE_COMPILE_CASE")); }\n' if placement=='external' else '\ninclude!(env!("MIXER_INITIAL_PROFILE_COMPILE_CASE"));\n';q=variant/path;q.write_text(q.read_text()+delta)
     env['MIXER_INITIAL_PROFILE_COMPILE_CASE']=str(fixture);a=args(variant,mode,scratch/'case.rmeta',True)
     if placement=='internal':a[1:1]=['--cfg','mixer_initial_profile_contract_internal','--check-cfg','cfg(mixer_initial_profile_contract_internal)','--check-cfg','cfg(test)','--check-cfg','cfg(feature, values(any()))','--check-cfg','cfg(mixer_initial_profile_component_host)']
     key=f'{mode}-{placement}-{fixture.stem}';write(OUT/'independent-variants'/f'{key}.json',{'source_manifest':manifest(variant),'append_path':path,'append_bytes':delta,'fixture_path':str(fixture),'fixture_sha256':sha(fixture),'environment':{'MIXER_INITIAL_PROFILE_COMPILE_CASE':str(fixture)},'ordinary_product_changed':False})
     r,stderr=command(a,key,env);positive=fixture.stem=='positive_contract';expected=None if positive else 'E0603' if placement=='external' else 'lifetime may not live long enough' if fixture.stem in ['guard_escape','proof_escape'] else 'E0061' if fixture.stem in ['row_foreign_snapshot','callback_reentry'] else 'E0502'
     r['expected_diagnostic']=expected;r['expectation_met']=r['exit_code']==0 if positive else r['exit_code']!=0 and expected in stderr
     write(OUT/'independent-commands'/key/'receipt.json',r);receipts.append(r);assert r['expectation_met'],key
     shutil.rmtree(variant)
 finally:
  shutil.rmtree(scratch);environment['cleanup']={'owned_scratch_removed':not scratch.exists(),'owned_children_reaped':all(r['owned_child_reaped'] for r in receipts),'compiler_products_retained':False,'native_capture_or_process_inventory':False};write(OUT/'independent-environment.json',environment);write(OUT/'independent-command-receipts.json',receipts)
 print(json.dumps({'independent_commands':len(receipts),'all_expected':all(r.get('expectation_met',r['exit_code']==0) for r in receipts),'cleanup':environment['cleanup']}))
if __name__=='__main__':main()
