from pathlib import Path
import hashlib,json,os,shutil,subprocess,tempfile,time,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SOURCE=ROOT/'verification/swift-typed-result-codec-implementation/source/vm'
RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
def sha(b):return hashlib.sha256(b).hexdigest()
def ident(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
commands=[]
logs=HERE/'baseline-logs';logs.mkdir(exist_ok=True)
scratch=Path(tempfile.mkdtemp(prefix='baseline-host-',dir=HERE))
env=os.environ.copy();env['TMPDIR']=str(scratch);env['CARGO_MANIFEST_DIR']=str(SOURCE)
def save(name,obj):(HERE/name).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
def run(label,args):
 out=logs/(label+'.stdout');err=logs/(label+'.stderr');start=time.monotonic();killed=None
 with out.open('wb') as o,err.open('wb') as e:
  child=subprocess.Popen([str(a) for a in args],cwd=ROOT,env=env,stdout=o,stderr=e)
  while True:
   try:code=child.wait(timeout=.05);break
   except subprocess.TimeoutExpired:
    if time.monotonic()-start>60:killed='time'
    if out.stat().st_size+err.stat().st_size>1048576:killed='output'
    if killed:child.kill();child.wait();code=124;break
 row={'label':label,'argv':[str(a) for a in args],'cwd':str(ROOT),'exit_code':code,'elapsed_seconds':time.monotonic()-start,'timeout_seconds':60,'output_byte_limit':1048576,'killed_for':killed,'terminally_waited':True,'stdout':ident(out),'stderr':ident(err)}
 commands.append(row);save('baseline-command-receipts.json',commands);print(label+': '+str(code),flush=True)
 assert code==0,(label,err.read_text(errors='replace')[-4000:])
 return out.read_text()
def flags(opt):
 a=[RUSTC,'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','opt-level='+opt,'-C','overflow-checks=yes','-C','panic=unwind']
 for feature in ['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']:a+=['--cfg','feature="'+feature+'"']
 return a
try:
 version=run('rustc-version',[RUSTC,'-vV']);revision=run('revision',['git','rev-parse','HEAD']).strip();run('sdk-abi',['xcrun','clang','-std=c11','-fsyntax-only','-Wall','-Werror','-Wno-deprecated-declarations',HERE/'abi_contract.c'])
 results={};artifacts=[]
 for mode,opt in [('debug','0'),('optimized','3')]:
  lib=scratch/('libmixer_vm_'+mode+'.rlib');binary=scratch/('baseline-'+mode);wasm=scratch/('late-'+mode+'.wasm')
  run('compile-library-'+mode,flags(opt)+['--crate-type','rlib',SOURCE/'src/lib.rs','-o',lib]);artifacts.append(ident(lib))
  run('compile-probe-'+mode,[RUSTC,'--edition=2021','--target','aarch64-apple-darwin','-C','opt-level='+opt,'--extern','mixer_vm='+str(lib),HERE/'baseline_late_failure.rs','-o',binary]);artifacts.append(ident(binary))
  env['MIXER_BASELINE_LATE_FAILURE_OUT']=str(wasm)
  result=json.loads(run('late-failure-'+mode,[binary]));result['input_artifact']=ident(wasm);results[mode]=result
 assert results['debug']['input_artifact']['sha256']==results['optimized']['input_artifact']['sha256']
 for field in ['source_bytes','metadata_peak_reserved','scratch_peak_reserved','total_peak_reserved','work_used']:
  assert results['debug']['failure_usage'][field]==results['optimized']['failure_usage'][field]
 save('baseline-late-failure.json',{'schema':1,'source_tree_sha256':'58a90a1cec00fd3ffbe4d8bee90476f6e136114dbe3d506da8ab4bbd035b8ecd','source_members':142,'source_seal_sha256':'4f5e0ffd63c343511948d1bacc933698cd36369f94b3b96f3047ff325cd94b86','source_fixture':ident(HERE/'baseline_late_failure.rs'),'fixture_dependency':ident(SOURCE/'tests/swift_reactor_validation_fixture.rs'),'rustc':ident(RUSTC),'rustc_version':version,'git_revision_context':revision,'results':results,'artifacts_compiled_and_removed':artifacts,'scope':'Host validator failure-usage semantics only; independent late function62 error after full source copy, metadata and prior28 valid bodies; no loader or runtime acceptance'})
finally:
 shutil.rmtree(scratch)
 save('baseline-cleanup.json',{'owned_scratch_path':str(scratch),'scratch_removed':not scratch.exists(),'all_owned_children_terminally_waited':all(c['terminally_waited'] for c in commands),'native_UI_capture_process_inventory_used':False,'frozen_producer_files_written':False})
