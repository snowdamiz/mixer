"""Bounded source/MIR/layout compiler probes; no engine or native execution."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,sys,time
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent.parent
INPUT=ROOT.parent/'swift-guarded-snapshot-scope-authority-correction'
ENC=ROOT.parent/'swift-guarded-snapshot-encoder-storage-closure'
RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def save(path,v):path.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def members(root):return [{'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(root.rglob('*')) if p.is_file()]
def verify():
 for base,name,expected in [(INPUT,'seal.json','351caf4860621989119d16b474dbb53c496a688c4efb0cbb3abb918825b79e6c'),(ENC,'seal.json','a1d597f634b805344ecc3edc1e6bfe0095323130d201d68b5da819c50ac1b322')]:
  b=(base/name).read_bytes();assert sha(b)==expected
  for row in json.loads(b)['members']:
   data=(base/row['path']).read_bytes();assert len(data)==row['bytes'] and sha(data)==row['sha256'],row['path']
 source=members(INPUT/'source/vm');assert len(source)==144 and sha(canonical(source))=='575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896'
 return {'source_tree_sha256':sha(canonical(source)),'source_members':144,'authority_seal_sha256':sha((INPUT/'seal.json').read_bytes()),'encoder_partition_sha256':sha((ENC/'partition.json').read_bytes()),'encoder_formula_status':'provisional frozen producer40531/2658; independent acceptance not inferred'}
def run(label,extra,vm=None,unit=False):
 custody=verify();vm=vm or INPUT/'source/vm';command=ROOT/'commands'/label;command.mkdir(parents=True,exist_ok=False)
 work=ROOT/'owned-work';work.mkdir(exist_ok=True)
 preimage={'members':members(vm),'driver_sha256':sha(Path(__file__).read_bytes())};assert len(preimage['members'])==144
 save(command/'source-preimage.json',preimage)
 version=subprocess.run([str(RUSTC),'--version','--verbose'],capture_output=True,check=True,timeout=10).stdout
 argv=[str(RUSTC),'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','opt-level=0','-C','overflow-checks=yes','-C','panic=unwind']
 for f in ['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']:argv+=['--cfg','feature="'+f+'"']
 argv+=(['--test'] if unit else ['--crate-type','rlib'])+[str(vm/'src/lib.rs')]+extra
 env={'PATH':'/usr/bin:/bin','TMPDIR':str(work),'CARGO_MANIFEST_DIR':str(vm),'RUSTC_BOOTSTRAP':'1',
 'MIXER_LOADER_COMPILER_SHA256':sha(RUSTC.read_bytes()),'MIXER_LOADER_COMPILER_VERSION_SHA256':sha(version),
 'MIXER_LOADER_MANIFEST_SHA256':sha(canonical(preimage)),'MIXER_LOADER_COMMAND_SHA256':sha(canonical(argv))}
 env['MIXER_LOADER_COMPILE_ENV_SHA256']=sha(canonical(env))
 started=time.monotonic();p=subprocess.Popen(argv,cwd=REPO,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
 timed=False;actions=[]
 try:out,err=p.communicate(timeout=55)
 except subprocess.TimeoutExpired:
  timed=True
  try:os.killpg(p.pid,signal.SIGKILL);actions.append('SIGKILL owned group')
  except ProcessLookupError:pass
  out,err=p.communicate()
 try:os.killpg(p.pid,0);absent=False
 except ProcessLookupError:absent=True
 (command/'stdout').write_bytes(out);(command/'stderr').write_bytes(err)
 receipt={'schema':1,'argv':argv,'environment':env,'rustc_version':version.decode(),'compiler_sha256':sha(RUSTC.read_bytes()),'source_binding':custody,
 'exit_code':p.returncode,'elapsed_seconds':time.monotonic()-started,'timeout_seconds':55,'timed_out':timed,'owned_process_group':p.pid,'new_session':True,
 'child_reaped':True,'owned_group_absent':absent,'cleanup_actions':actions,'stdout_sha256':sha(out),'stderr_sha256':sha(err),
 'scope':'source/MIR/layout compiler only; no engine/VM/writer/native/UI/capture/process inventory or Git'}
 save(command/'receipt.json',receipt);print(json.dumps({'label':label,'exit_code':p.returncode,'timed_out':timed,'elapsed_seconds':receipt['elapsed_seconds']}),flush=True)
 return p.returncode
if __name__=='__main__':
 ROOT.mkdir(exist_ok=True)
 if sys.argv[1]=='mir':code=run('unoptimized-source-slots',['--emit=mir','-Zmir-opt-level=0','-Zmir-include-spans=yes','-o',str(ROOT/'owned-work/source-slots.mir')])
 elif sys.argv[1]=='baseline':code=run('inherited-original-source-slots',['--emit=mir','-Zmir-opt-level=0','-Zmir-include-spans=yes','-o',str(ROOT/'owned-work/inherited-slots.mir')],vm=ROOT.parent/'swift-guarded-snapshot-encoder-implementation/source/vm')
 elif sys.argv[1]=='unit':code=run('concrete-next-host-caller',['--emit=mir','-Zmir-opt-level=0','-Zmir-include-spans=yes','-o',str(ROOT/'owned-work/unit-slots.mir')],unit=True)
 elif sys.argv[1]=='layouts':code=run('actual-monomorphic-layouts',['--emit=llvm-ir','-Zmir-opt-level=0','-Zprint-type-sizes','-Clink-dead-code=yes','-o',str(ROOT/'owned-work/actual-types.ll')])
 else:raise ValueError(sys.argv[1])
 raise SystemExit(code)
