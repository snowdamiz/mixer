"""One exclusive source146 library metadata/MIR rebind, never product runtime."""
import datetime,gzip,hashlib,json,os,shutil,signal,struct,subprocess,time
from pathlib import Path
from prepare import D,R,inputs,put,sha,canonical
WORK=D/'owned-work';VM=WORK/'vm'
COMPILER=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
KEYS=('MIXER_LOADER_MANIFEST_SHA256','MIXER_LOADER_COMMAND_SHA256','MIXER_LOADER_COMPILE_ENV_SHA256','MIXER_LOADER_COMPILER_SHA256','MIXER_LOADER_COMPILER_VERSION_SHA256')
def counted(values):
 values=[x.encode() if isinstance(x,str) else x for x in values]
 assert len(values)<=64 and all(len(x)<4096 and b'\0' not in x for x in values)
 return struct.pack('<Q',len(values))+b''.join(struct.pack('<Q',len(x))+x for x in values)
def command(argv,env,timeout=180):
 at=datetime.datetime.now(datetime.timezone.utc).isoformat();start=time.monotonic()
 p=subprocess.Popen(argv,cwd=R,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
 timed=False;actions=[]
 try:out,err=p.communicate(timeout=timeout)
 except subprocess.TimeoutExpired:
  timed=True;os.killpg(p.pid,signal.SIGKILL);actions.append('SIGKILL-owned-command-group-after-timeout');out,err=p.communicate()
 # Only the one owned group is checked; there is no process listing/inventory.
 try:os.killpg(p.pid,0);present=True
 except ProcessLookupError:present=False
 if present:
  os.killpg(p.pid,signal.SIGKILL);actions.append('SIGKILL-residual-owned-group')
  for _ in range(20):
   try:os.killpg(p.pid,0);time.sleep(.05)
   except ProcessLookupError:present=False;break
 return out,err,dict(at=at,argv=argv,cwd=str(R),environment=env,timeout_seconds=timeout,timed_out=timed,exit_code=p.returncode,elapsed_seconds=time.monotonic()-start,direct_child_pid=p.pid,direct_child_waited=True,owned_group_absent=not present,cleanup_actions=actions,global_process_inventory=False,product_runtime=False)
def main():
 assert not WORK.exists();WORK.mkdir()
 old,new,oldrefs,newrefs,oldm,newm,hosts,custody=inputs()
 for rel,b in new.items():
  p=VM/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
 clean=dict(PATH='/usr/bin:/bin',TMPDIR=str(WORK),CARGO_MANIFEST_DIR=str(VM),RUSTC_BOOTSTRAP='1',SDKROOT='/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk')
 ver,vererr,verreceipt=command([str(COMPILER),'--version','--verbose'],clean,10)
 (D/'compiler-version.stdout').write_bytes(ver);(D/'compiler-version.stderr').write_bytes(vererr);put('compiler-version-receipt.json',verreceipt)
 assert verreceipt['exit_code']==0 and sha(ver)=='352d6857968e80a6357a926ac685b9b07f77c479aaafde33e73a53945e802909'
 compiler_digest=sha(COMPILER.read_bytes());assert compiler_digest=='dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0'
 argv=[str(COMPILER),'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','opt-level=0','-C','overflow-checks=yes','-C','panic=unwind','-Zmir-opt-level=0','-Zmir-include-spans=yes']
 for f in ('experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache'):argv+=['--cfg','feature="'+f+'"']
 argv+=['--cfg','mixer_bootstrap_one_fixture_v1','--crate-type','rlib',str(VM/'src/lib.rs'),'--emit=metadata='+str(WORK/'source146.rmeta')+',mir='+str(WORK/'source146.mir')]
 manifest=dict(schema=1,compiled_input_kind='Exact accepted source146 production library metadata/MIR; no runtime fixture or executable',distribution=newm,host_support=hosts,orchestration=dict(separate_from_host11=True,private_bootstrap_cfg=True,selected_route='one private no-WASI fixture route; uncalled',test_overlay_selected=False,source_tools=[dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in (D/'prepare.py',D/'compile_mir.py')]),compiler=dict(path=str(COMPILER),bytes=COMPILER.stat().st_size,sha256=compiler_digest,version_sha256=sha(ver)),SDKROOT=clean['SDKROOT'])
 manifest_bytes=canonical(manifest);assert len(manifest_bytes)<=65536
 argbytes=counted(argv);envbytes=counted([k+'='+v for k,v in sorted(clean.items())]);assert len(argbytes)<=16384 and len(envbytes)<=16384
 pre=D/'preimages';pre.mkdir();(pre/'manifest.json').write_bytes(manifest_bytes);(pre/'argv.bin').write_bytes(argbytes);(pre/'environment.bin').write_bytes(envbytes)
 identities=dict(zip(KEYS,[sha(manifest_bytes),sha(argbytes),sha(envbytes),compiler_digest,sha(ver)]))
 env={**clean,**identities};out,err,receipt=command(argv,env,180)
 (D/'compiler.stdout').write_bytes(out);(D/'compiler.stderr').write_bytes(err)
 receipt.update(schema=1,compiler_sha256=compiler_digest,compiler_version=ver.decode(),source_members=146,host_support_members=11,source_tree_sha256=newm['tree_sha256'],source_manifest_sha256=sha((D/'source146-manifest.json').read_bytes()),compile_identity_keys=identities,test_overlay=False,no_WASI_route=True,scope='one exact accepted146 production library compile-only; full preopt MIR and typed nonempty metadata; no product execution',output={n:dict(bytes=len(b),sha256=sha(b)) for n,b in [('stdout',out),('stderr',err)]})
 if receipt['exit_code']==0:
  raw=(WORK/'source146.mir').read_bytes();packed=gzip.compress(raw,mtime=0);(D/'whole-source146.mir.gz').write_bytes(packed)
  meta=(WORK/'source146.rmeta').read_bytes();assert len(meta)>0
  receipt['MIR']=dict(raw_bytes=len(raw),raw_sha256=sha(raw),archive_bytes=len(packed),archive_sha256=sha(packed),lossless_gzip=True)
  receipt['metadata']=dict(bytes=len(meta),sha256=sha(meta),nonempty=True,retained=False,executed=False)
 put('compiler-receipt.json',receipt)
 put('preimages/binding.json',dict(schema=1,source_members=146,source_tree_sha256=newm['tree_sha256'],host_support_members=11,host_support_tree_sha256=hosts['tree_sha256'],manifest_sha256=sha(manifest_bytes),argv_sha256=sha(argbytes),environment_sha256=sha(envbytes),compiler_sha256=compiler_digest,compiler_version_sha256=sha(ver),compile_keys=identities,orchestration_separate=True,actual_fixture_or_output_executable=False))
 assert receipt['exit_code']==0 and not receipt['timed_out'] and receipt['owned_group_absent'],receipt
 print(json.dumps(dict(status='exclusive-source146-compile-only-success',metadata=receipt['metadata'],MIR=receipt['MIR'])))
if __name__=='__main__':main()
