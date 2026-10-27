#!/usr/bin/env python3
"""One predeclared, production metadata/MIR compiler invocation; no retry/runtime."""
from pathlib import Path
import datetime,gzip,hashlib,json,os,shutil,signal,subprocess,sys,time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PROVIDER=ROOT/'verification/swift-guarded-snapshot-owned-binding-provider'
BASE=ROOT/'verification/swift-guarded-snapshot-scoped-binding-source'
PROFILE='src/experimental_swift_reactor/cache/initial_profile_v1.rs'
SCRATCH=HERE/'owned-work/compiler-metadata-mir';CMD=HERE/'commands/compiler-metadata-mir'
COMPILER=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
TYPES=[('input_backing','InputBackingDescriptionV1'),('pending_requirement','PendingUpstreamRequirementV1'),('pending_requirements','PendingUpstreamRequirementsV1'),('unqualified_candidate',"UnqualifiedExistingOwnerCandidateV1<'static>"),('shape_refusal','CandidateShapeRefusalV1'),('candidate_result',"Result<UnqualifiedExistingOwnerCandidateV1<'static>, CandidateShapeRefusalV1>"),('identity_references',"[&'static super::ImmutableIdentityPreimageV1<'static>;12]"),('identity_counts','[usize;12]'),('path_counts','[usize;5]'),('retained_path_references',"[&'static [u8];5]")]
def sha(d):return hashlib.sha256(d).hexdigest()
def canonical(o):return json.dumps(o,sort_keys=True,separators=(',',':')).encode()
def write(p,o):p.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n')
def absent(pgid):
 try:os.killpg(pgid,0)
 except ProcessLookupError:return True
 return False
def main():
 assert not (HERE/'compiler-plan.json').exists(),'compile already declared; no retries'
 assert not SCRATCH.exists() and not CMD.exists()
 custody=json.loads((PROVIDER/'proposed-source-custody.json').read_bytes())
 rows=[{k:r[k] for k in ('path','bytes','sha256')} for r in custody]
 assert len(rows)==146 and sha(canonical(rows))=='acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d'
 assert sha(COMPILER.read_bytes())=='dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0'
 suffix='\n// Independent inert metadata/MIR layout query, excluded from candidate distribution.\nfn independent_provider_layout_query_v1(\n'+''.join(f'    _{name}_{op}: [u8; std::mem::{op}_of::<{typ}>()],\n' for name,typ in TYPES for op in ('size','align'))+') {}\n'
 (HERE/'query-layout.inc.rs').write_text(suffix)
 SCRATCH.mkdir(parents=True);CMD.mkdir(parents=True)
 manifest=[]
 for r in custody:
  d=(ROOT/r['origin']).read_bytes();assert (len(d),sha(d))==(r['bytes'],r['sha256'])
  if r['path']==PROFILE:
   fragment=(PROVIDER/'existing-owner-candidate.inc.rs').read_bytes()
   assert fragment.endswith(b'}\n')
   needle=fragment+b'\n}\n}\n';assert d.endswith(needle)
   qfragment=fragment[:-2]+suffix.encode()+fragment[-2:]
   d=d[:-len(needle)]+qfragment+b'\n}\n}\n'
   (HERE/'query-profile.rs').write_bytes(d)
  p=SCRATCH/'vm'/r['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(d)
  manifest.append({'path':r['path'],'bytes':len(d),'sha256':sha(d)})
 write(HERE/'query-source-manifest.json',{'schema':1,'members':manifest,'member_count':146,'tree_sha256':sha(canonical(manifest))})
 env={'CARGO_MANIFEST_DIR':str(SCRATCH/'vm'),'PATH':'/usr/bin:/bin','RUSTC_BOOTSTRAP':'1','SDKROOT':'/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk','TMPDIR':str(SCRATCH)}
 argv=[str(COMPILER),'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','opt-level=0','-C','overflow-checks=yes','-C','panic=unwind','-Zmir-opt-level=0','--cfg','feature="experimental-swift-reactor"','--cfg','feature="experimental-swift-wasi"','--cfg','feature="experimental-stream-validation"','--cfg','feature="experimental-function-cache"','--cfg','mixer_bootstrap_one_fixture_v1','--crate-type','rlib',str(SCRATCH/'vm/src/lib.rs'),'-Zmir-include-spans=yes',f'--emit=metadata={SCRATCH}/query.rmeta,mir={SCRATCH}/query.mir']
 baseline=json.loads((BASE/'commands/compiler-positive/receipt.json').read_bytes())
 plan={'schema':1,'mode':'production-positive-metadata-mir-with-inert-layout-signature','argv':argv,'environment':env,'cwd':str(ROOT),'compiler_path':str(COMPILER),'compiler_sha256':sha(COMPILER.read_bytes()),'compiler_version_preimage':baseline['compiler_version_preimage'],'compiler_version_sha256':baseline['compiler_version_sha256'],'compiler_version_scope':'Retained exact-byte-bound version; no new version process','source_revision':subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'candidate_tree_sha256':'acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d','query_tree_sha256':sha(canonical(manifest)),'source_members':146,'compiler_invocations_authorized':1,'child_timeout_seconds':55,'output_limit_bytes':4194304,'retries':0,'cfg_test':False,'codegen':False,'native_or_product_execution':False,'no_compile_identity_injection':True,'exact_owned_process_group_cleanup':True,'layout_observations':[{'type':t,'name':n,'observations':['size','align']} for n,t in TYPES],'anonymous_and_then_capture_layout':'pending; no production body modified'}
 write(HERE/'compiler-plan.json',plan)
 started=datetime.datetime.now(datetime.timezone.utc).isoformat();begin=time.monotonic();child=None;timed_out=False;output_exceeded=False;error=None;artifacts=[];cleanup_signals=[]
 try:
  with (CMD/'stdout').open('wb') as out,(CMD/'stderr').open('wb') as err:
   child=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=out,stderr=err,start_new_session=True)
   while child.poll() is None:
    timed_out=time.monotonic()-begin>=55
    output_exceeded=sum((CMD/n).stat().st_size for n in ('stdout','stderr'))>4194304
    if timed_out or output_exceeded:
     os.killpg(child.pid,signal.SIGTERM);cleanup_signals.append('SIGTERM')
     try:child.wait(timeout=2)
     except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);cleanup_signals.append('SIGKILL');child.wait(timeout=2)
     break
    time.sleep(0.02)
   child.wait(timeout=2)
  if not absent(child.pid):
   os.killpg(child.pid,signal.SIGTERM);cleanup_signals.append('post-terminal SIGTERM')
   until=time.monotonic()+1
   while not absent(child.pid) and time.monotonic()<until:time.sleep(.02)
   if not absent(child.pid):os.killpg(child.pid,signal.SIGKILL);cleanup_signals.append('post-terminal SIGKILL')
  for name in ('query.rmeta','query.mir'):
   path=SCRATCH/name
   if path.exists():
    data=path.read_bytes();artifacts.append({'path':name,'bytes':len(data),'sha256':sha(data),'retained_uncompressed':False})
    if name=='query.mir':
     compressed=gzip.compress(data,mtime=0);(CMD/'query.mir.gz').write_bytes(compressed)
     artifacts[-1].update(retained_gzip_sha256=sha(compressed),retained_gzip_bytes=len(compressed))
 except BaseException as e:
  error=repr(e)
 finally:
  if child is not None and child.poll() is None:
   os.killpg(child.pid,signal.SIGKILL);cleanup_signals.append('finally SIGKILL');child.wait(timeout=2)
  group_absent=child is not None and absent(child.pid)
  if SCRATCH.exists():shutil.rmtree(SCRATCH)
  receipt=plan|{'state':'complete' if error is None else 'failure','started_at':started,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-begin,'compiler_invocations':int(child is not None),'owned_pid':None if child is None else child.pid,'owned_pgid':None if child is None else child.pid,'exit_code':None if child is None else child.returncode,'timed_out':timed_out,'output_exceeded':output_exceeded,'exception':error,'child_reaped':child is not None and child.returncode is not None,'owned_group_absent':group_absent,'owned_scratch_removed':not SCRATCH.exists(),'cleanup_signals':cleanup_signals,'artifacts':artifacts,'runner_sha256':sha(Path(__file__).read_bytes()),'python_version':sys.version}
  for n in ('stdout','stderr'):
   d=(CMD/n).read_bytes();receipt[n+'_bytes']=len(d);receipt[n+'_sha256']=sha(d)
  receipt['success']=error is None and child is not None and child.returncode==0 and not timed_out and not output_exceeded and group_absent and not SCRATCH.exists() and len(artifacts)==2
  write(CMD/'receipt.json',receipt)
  print(json.dumps({k:receipt[k] for k in ('state','success','elapsed_seconds','exit_code','timed_out','owned_group_absent','owned_scratch_removed','exception')}))
 return 0 if receipt['success'] else 1
if __name__=='__main__':raise SystemExit(main())
