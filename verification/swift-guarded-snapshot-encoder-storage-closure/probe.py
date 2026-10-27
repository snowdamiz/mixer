"""Metadata-only source-slot probe. Never imports or executes an engine harness."""
from pathlib import Path
import json,hashlib,subprocess,os,signal,time,sys
ROOT=Path(__file__).resolve().parent
INPUT=ROOT.parent/'swift-guarded-snapshot-composition-source-preparation'
ENC=ROOT.parent/'swift-guarded-snapshot-encoder-implementation'
RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
def sha(b):return hashlib.sha256(b).hexdigest()
def verify():
 b=(INPUT/'seal.json').read_bytes(); assert sha(b)=='bf17889754e7ef436fababcf8b96f5109285f982bcc48258a0b9e204a95b1751'
 seal=json.loads(b);assert len(seal['members'])==495
 for m in seal['members']:
  b=(INPUT/m['path']).read_bytes();assert len(b)==m['bytes'] and sha(b)==m['sha256'],m['path']
 b=(ENC/'seal.json').read_bytes();assert sha(b)=='eadbe533d23459573ead21c7a9bac54ae929b98cdbc76dd47aebe34b5ceb2b1f'
 source=json.loads((INPUT/'source-manifest.json').read_text())
 members=source['members'];assert len(members)==144
 digest=sha(json.dumps(members,sort_keys=True,separators=(',',':')).encode());assert digest=='140761754a158c72209120de9ac5f78f7a1d5c20c3cddd6deeb9fff7a2d1b395',digest
 return {'composition_seal_sha256':sha((INPUT/'seal.json').read_bytes()),'composition_member_count':495,'source_member_count':144,'source_tree_sha256':digest,'encoder_seal_sha256':sha((ENC/'seal.json').read_bytes())}
def run(label,extra,source_vm=None):
 custody=verify();vm=source_vm or (INPUT/'source/vm');d=ROOT/'commands'/label;d.mkdir(parents=True,exist_ok=False)
 work=ROOT/'owned-work';work.mkdir(exist_ok=True)
 members=[{'path':p.relative_to(vm).as_posix(),'bytes':len(p.read_bytes()),'sha256':sha(p.read_bytes())} for p in sorted(vm.rglob('*')) if p.is_file()]
 assert len(members)==144
 (d/'source-preimage.json').write_text(json.dumps({'members':members,'tree_sha256':sha(json.dumps(members,sort_keys=True,separators=(',',':')).encode())},indent=2)+'\n')
 version=subprocess.run([str(RUSTC),'--version','--verbose'],capture_output=True,check=True).stdout
 argv=[str(RUSTC),'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','opt-level=0','-C','overflow-checks=yes','-C','panic=unwind']
 for f in ['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']:argv+=['--cfg','feature="'+f+'"']
 argv+=['--crate-type','rlib',str(vm/'src/lib.rs')]+extra
 env={'PATH':'/usr/bin:/bin','TMPDIR':str(work),'CARGO_MANIFEST_DIR':str(vm),'RUSTC_BOOTSTRAP':'1'}
 started=time.monotonic();p=subprocess.Popen(argv,cwd=ROOT.parent.parent,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
 cleanup=[];timed=False
 try:out,err=p.communicate(timeout=55)
 except subprocess.TimeoutExpired:
  timed=True
  try:os.killpg(p.pid,signal.SIGTERM);cleanup.append('SIGTERM owned compiler group')
  except ProcessLookupError:pass
  try:out,err=p.communicate(timeout=3)
  except subprocess.TimeoutExpired:
   try:os.killpg(p.pid,signal.SIGKILL);cleanup.append('SIGKILL owned compiler group')
   except ProcessLookupError:pass
   out,err=p.communicate()
 (d/'stdout').write_bytes(out);(d/'stderr').write_bytes(err)
 receipt={'schema':1,'argv':argv,'environment':env,'cwd':str(ROOT.parent.parent),'rustc_version':version.decode(),'compiler_sha256':sha(RUSTC.read_bytes()),'source_binding':custody,'exit_code':p.returncode,'elapsed_seconds':time.monotonic()-started,'timeout_seconds':55,'timed_out':timed,'owned_process_group':p.pid,'new_session':True,'child_reaped':True,'cleanup_actions':cleanup,'stdout_bytes':len(out),'stderr_bytes':len(err),'stdout_sha256':sha(out),'stderr_sha256':sha(err),'scope':'compiler metadata only; no encoder/VM/writer execution, process inventory, native runtime, UI, capture, Git or canonical mutation'}
 (d/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));return p.returncode
if __name__=='__main__':
 if sys.argv[1]=='mir':raise SystemExit(run('metadata-source-slots-unoptimized',['--emit=mir','-Zmir-opt-level=0','-Zmir-include-spans=yes','-o',str(ROOT/'owned-work/source-slots.mir')]))
