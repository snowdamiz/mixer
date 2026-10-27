"""Owned bounded compiler/const/private-control runs; no VM/writer dispatch."""
from pathlib import Path
import ast,json,os,re,shutil,signal,subprocess,sys,time
sys.dont_write_bytecode=True
from prepare import HERE,BASE,BASE_TREE,CONTROL,PROFILE,RUSTC,sha,canonical,members,write,custody
FEATURES=['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']
OVERLAYS=[(CONTROL,'control-tests.inc.rs'),(PROFILE,'profile-tests.inc.rs'),('src/experimental_swift_reactor/cache.rs','cache-tests.inc.rs')]
def bounded(argv,env,cwd,timeout=55):
 start=time.monotonic();p=subprocess.Popen(argv,env=env,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);actions=[];timed=False
 try:out,err=p.communicate(timeout=timeout)
 except subprocess.TimeoutExpired:
  timed=True
  try:os.killpg(p.pid,signal.SIGTERM);actions.append('SIGTERM owned group')
  except ProcessLookupError:pass
  try:out,err=p.communicate(timeout=2)
  except subprocess.TimeoutExpired:
   try:os.killpg(p.pid,signal.SIGKILL);actions.append('SIGKILL owned group')
   except ProcessLookupError:pass
   out,err=p.communicate(timeout=2)
 try:os.killpg(p.pid,0);absent=False
 except ProcessLookupError:absent=True
 return out,err,dict(argv=list(map(str,argv)),cwd=str(cwd),exit_code=p.returncode,elapsed_seconds=time.monotonic()-start,timeout_seconds=timeout,timed_out=timed,owned_process_group=p.pid,new_session=True,child_reaped=True,owned_group_absent=absent,cleanup_actions=actions)
def blocks(text):
 return [m.group(0) for m in re.finditer(r'^fn [^\n]+\{\n.*?^\}\n',text,re.M|re.S)]
def selected(text):
 out={}
 for b in blocks(text):
  h=b.splitlines()[0]
  if 'snapshot_commit_storage_v1(' in h:key='commit'
  elif 'end_construction_phase_with_wasi<' in h:key='normalizer'
  elif 'end_construction_phase_with_wasi(' in h:key='normalizer'
  elif 'begin_snapshot_access_v1' in h:key='begin-closure' if '{closure#0}' in h else 'begin'
  elif 'complete(' in h and 'SnapshotAccessV1' in h:key='complete'
  elif 'foundation_construction_bytes(' in h:key='common-floor'
  elif 'snapshot_scope_candidate_foundation_v1(' in h:key='selected-floor'
  else:continue
  assert key not in out,(key,h);out[key]=b
 assert set(out)=={'commit','normalizer','begin','begin-closure','complete','common-floor','selected-floor'},list(out)
 return out
def norm_type(s):
 s=re.sub(r'/Users/[^\s:}]*?/vm/src/','source/',s)
 s=re.sub(r'(?<![A-Za-z])(?:control::|accounted::)','',s)
 return s
def roles(b):
 # Every declaration, including parameters in header and the existing return.
 return [dict(name=m.group(1),type=norm_type(m.group(2))) for m in re.finditer(r'^\s+let (?:mut )?(_\d+): (.*?);(?: //|$)',b,re.M)]
def run(label):
 binding=custody();directory=HERE/'commands'/label;directory.mkdir(parents=True,exist_ok=False)
 scratch=HERE/'owned-work'/label;scratch.mkdir(parents=True,exist_ok=False)
 env={'PATH':'/usr/bin:/bin','TMPDIR':str(scratch),'RUSTC_BOOTSTRAP':'1'}
 version,versionerr,vr=bounded([str(RUSTC),'--version','--verbose'],env,HERE,10)
 (directory/'compiler-version-stdout').write_bytes(version);(directory/'compiler-version-stderr').write_bytes(versionerr)
 assert vr['exit_code']==0 and vr['owned_group_absent']
 pre=dict(schema=1,source_binding=binding,driver_sha256=sha(Path(__file__).read_bytes()),compiler_sha256=sha(RUSTC.read_bytes()))
 unit=label.endswith('unit');standalone=label.startswith('scalar-');targeted=label=='control-tests'
 try:
  if standalone:
   # Reuse only the already independently reviewed pure integer harness function.
   inp=BASE/'verify.py';tree=ast.parse(inp.read_text());fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='standalone_source')
   exact=ast.get_source_segment(inp.read_text(),fn);space={'HERE':HERE};exec(compile(exact,str(inp),'exec'),space)
   source=scratch/'scalar.rs';source.write_text(space['standalone_source'](unit=unit,overflow='overflow' in label,negative=label.endswith('negative')))
   (directory/'standalone-source.rs').write_bytes(source.read_bytes());pre.update(pure_harness_input_sha256=sha(inp.read_bytes()),pure_harness_function_sha256=sha(exact.encode()),standalone_source_sha256=sha(source.read_bytes()))
   artifact=scratch/'scalar';argv=[str(RUSTC),'--crate-name','phase_retention_scalar','--edition=2021','-C','overflow-checks=yes',str(source),'-o',str(artifact)]
   if unit:argv+=['--cfg','test']
  else:
   origin=BASE/'source/vm' if label.startswith('baseline-') else HERE/'source/vm'
   vm=scratch/'vm';shutil.copytree(origin,vm);pre['copied_source_members']=members(vm)
   if targeted:
    pre['test_overlays']=[]
    for target,overlay in OVERLAYS:
     fragment=(HERE/overlay).read_bytes();p=vm/target;p.write_bytes(p.read_bytes()+b'\n'+fragment)
     pre['test_overlays'].append(dict(target=target,path=overlay,bytes=len(fragment),sha256=sha(fragment)))
    pre['instrumented_source_members']=members(vm)
   source=vm/'src/lib.rs';artifact=scratch/('control-tests' if targeted else 'candidate.rmeta');mir=scratch/'candidate.mir'
   argv=[str(RUSTC),'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','opt-level=0','-C','overflow-checks=yes','-C','panic=unwind','-Zmir-opt-level=0','-Zmir-include-spans=yes']
   for feature in FEATURES:argv+=['--cfg','feature="'+feature+'"']
   argv+=['--test'] if unit or targeted else ['--crate-type','rlib']
   argv+=[str(source)]
   argv+=['-o',str(artifact)] if targeted else ['--emit=metadata='+str(artifact)+',mir='+str(mir)]
   pre['encoder_support_members']=members(HERE.parent/'swift-guarded-snapshot-encoder-implementation/host');assert len(pre['encoder_support_members'])==11
  env.update(CARGO_MANIFEST_DIR=str(source.parent.parent if not standalone else scratch),MIXER_LOADER_COMPILER_SHA256=sha(RUSTC.read_bytes()),MIXER_LOADER_COMPILER_VERSION_SHA256=sha(version),MIXER_LOADER_MANIFEST_SHA256=sha(canonical(pre)),MIXER_LOADER_COMMAND_SHA256=sha(canonical(argv)))
  env['MIXER_LOADER_COMPILE_ENV_SHA256']=sha(canonical(env));(directory/'source-preimage.json').write_text(json.dumps(pre,indent=2,sort_keys=True)+'\n')
  out,err,receipt=bounded(argv,env,HERE.parent.parent)
  (directory/'stdout').write_bytes(out);(directory/'stderr').write_bytes(err)
  negative=label.endswith('negative');ok=receipt['exit_code']!=0 and b'E0080' in err if negative else receipt['exit_code']==0
  receipt.update(schema=1,source_binding=binding,compiler_sha256=sha(RUSTC.read_bytes()),compiler_version=version.decode(),compiler_version_command=vr,environment=env,stdout_sha256=sha(out),stderr_sha256=sha(err),expectation_met=ok,expected_result='E0080 checked const overflow' if negative else 'success',scope='Private test overlay compile; only filtered control helpers execute' if targeted else 'Pure scalar constants' if standalone else 'Exact source metadata and focused MIR only',test_overlay=targeted)
  if artifact.exists():receipt['removed_artifact']=dict(bytes=artifact.stat().st_size,sha256=sha(artifact.read_bytes()))
  if not standalone and not targeted and mir.exists():
   receipt['removed_full_mir']=dict(bytes=mir.stat().st_size,sha256=sha(mir.read_bytes()));focus=selected(mir.read_text());(directory/'focused-functions.mir').write_text('\n'.join(focus.values()))
   receipt['focused_roles']={k:roles(v) for k,v in focus.items()};receipt['focused_headers']={k:v.splitlines()[0] for k,v in focus.items()}
  (directory/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
  assert ok and receipt['owned_group_absent'] and not receipt['timed_out'],err.decode()[-5000:]
  if (standalone and not negative) or targeted:
   args=[str(artifact),'phase_retention_controls_v1::','--test-threads=1','--nocapture'] if targeted else [str(artifact)]
   rout,rerr,rr=bounded(args,{'PATH':'/usr/bin:/bin'},scratch,15)
   (directory/'run-stdout').write_bytes(rout);(directory/'run-stderr').write_bytes(rerr)
   rr.update(schema=1,source_binding=binding,executable_sha256=sha(artifact.read_bytes()),source_preimage_sha256=sha((directory/'source-preimage.json').read_bytes()),stdout_sha256=sha(rout),stderr_sha256=sha(rerr),scope='Finite actual RuntimeControl/complete helpers on synthetic checked private ledgers; not admission/VM/writer/profile loader' if targeted else 'Pure integer constants; synthetic F0 is not a measured production floor')
   (directory/'run-receipt.json').write_text(json.dumps(rr,indent=2,sort_keys=True)+'\n')
   assert rr['exit_code']==0 and rr['owned_group_absent'] and not rr['timed_out'],rout.decode()+rerr.decode()
   print(rout.decode().strip())
  print(json.dumps(dict(label=label,exit_code=receipt['exit_code'],expectation_met=ok,elapsed_seconds=receipt['elapsed_seconds'])),flush=True)
 finally:
  shutil.rmtree(scratch);(directory/'cleanup.json').write_text(json.dumps(dict(scratch_removed=not scratch.exists(),owned_scratch=str(scratch)),indent=2)+'\n')
 custody()
if __name__=='__main__':
 assert len(sys.argv)==2
 assert sys.argv[1] in ['baseline-production','baseline-unit','candidate-production','candidate-unit','scalar-production','scalar-unit','scalar-overflow','scalar-overflow-negative','control-tests']
 run(sys.argv[1])
