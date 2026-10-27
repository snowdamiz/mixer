"""Exact-source metadata/MIR only. No product artifact is linked or executed."""
import datetime,gzip,hashlib,json,os,shutil,signal,subprocess,time
from pathlib import Path
D=Path(__file__).resolve().parent;R=D.parents[1]
BASE=R/'verification/swift-guarded-snapshot-funding-implementation/source/vm'
OVER=R/'verification/swift-guarded-snapshot-descriptor-rebinding/overlay/vm'
MAN=R/'verification/swift-guarded-snapshot-descriptor-rebinding/source-manifest.json'
WORK=D/'owned-work';VM=WORK/'vm'
COMP='/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc'
def sha(b):return hashlib.sha256(b).hexdigest()
def put(n,v):(D/n).write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def prepare():
 m=json.loads(MAN.read_text());assert m['member_count']==145 and m['tree_sha256']=='450b6d9b3a05d160e19fa888b68173286b8f6af20ecc7216fdf86283f09b308a'
 assert not WORK.exists();VM.mkdir(parents=True)
 for member in m['members']:
  rel=Path(member['path']);p=OVER/rel if (OVER/rel).exists() else BASE/rel;b=p.read_bytes()
  assert len(b)==member['bytes'] and sha(b)==member['sha256'],str(rel)
  target=VM/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
 put('compiler-source-manifest.json',m)
 print(json.dumps(dict(status='exact145-prepared',members=145,tree=m['tree_sha256'])))
def run():
 assert VM.exists()
 ver=subprocess.run([COMP,'--version','--verbose'],capture_output=True,timeout=10,check=True)
 (D/'compiler-version.stdout').write_bytes(ver.stdout);(D/'compiler-version.stderr').write_bytes(ver.stderr)
 argv=[COMP,'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','opt-level=0','-C','overflow-checks=yes','-C','panic=unwind','-Zmir-opt-level=0','-Zmir-include-spans=yes']
 for f in ('experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache'):argv+=['--cfg','feature="'+f+'"']
 argv+=['--crate-type','rlib',str(VM/'src/lib.rs'),'--emit=metadata='+str(WORK/'loader.rmeta')+',mir='+str(WORK/'loader.mir')]
 old=json.loads((R/'verification/swift-guarded-snapshot-descriptor-rebinding/preimages/metadata-debug-production/binding.json').read_text())
 env=dict(PATH='/usr/bin:/bin',TMPDIR=str(WORK),CARGO_MANIFEST_DIR=str(VM),RUSTC_BOOTSTRAP='1',**old['compile_keys'])
 started=time.monotonic();at=datetime.datetime.now(datetime.timezone.utc).isoformat()
 child=subprocess.Popen(argv,cwd=R,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
 timed=False
 try:out,err=child.communicate(timeout=180)
 except subprocess.TimeoutExpired:
  timed=True;os.killpg(child.pid,signal.SIGKILL);out,err=child.communicate()
 (D/'compiler.stdout').write_bytes(out);(D/'compiler.stderr').write_bytes(err)
 receipt=dict(schema=1,at=at,argv=argv,environment=env,cwd=str(R),compiler_sha256=sha(Path(COMP).read_bytes()),compiler_version=ver.stdout.decode(),source_manifest_sha256=sha(MAN.read_bytes()),source_tree_sha256=json.loads(MAN.read_text())['tree_sha256'],exit_code=child.returncode,timed_out=timed,timeout_seconds=180,elapsed_seconds=time.monotonic()-started,direct_child_pid=child.pid,direct_child_waited=True,global_process_inventory=False,source_scope='exact accepted descriptor145 foundation; not final combined source',identity_scope='historical production metadata compile keys preserve valid Some/hex branches; this new compiler invocation/binary is not runtime session qualification',output={n:dict(bytes=len(v),sha256=sha(v)) for n,v in [('stdout',out),('stderr',err)]},product_executed=False)
 if child.returncode==0:
  data=(WORK/'loader.mir').read_bytes();packed=gzip.compress(data,mtime=0);(D/'whole-source.mir.gz').write_bytes(packed)
  receipt['mir']=dict(bytes=len(data),sha256=sha(data),gzip_bytes=len(packed),gzip_sha256=sha(packed))
  meta=(WORK/'loader.rmeta').read_bytes();receipt['metadata']=dict(bytes=len(meta),sha256=sha(meta),retained=False)
 put('compiler-receipt.json',receipt)
 if child.returncode!=0:raise SystemExit(child.returncode)
 print(json.dumps(dict(status='compile-only-success',mir=receipt['mir'])))
if __name__=='__main__':
 import sys
 {'prepare':prepare,'run':run}[sys.argv[1]]()
