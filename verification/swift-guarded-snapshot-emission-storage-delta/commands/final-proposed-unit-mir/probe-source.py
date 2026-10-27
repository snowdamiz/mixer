"""Owned, bounded compiler-only evidence. No product or native execution."""
from pathlib import Path
import difflib, hashlib, json, os, re, shutil, signal, subprocess, sys, time

HERE=Path(__file__).resolve().parent
REPO=HERE.parent.parent
BASE=HERE.parent/'swift-guarded-snapshot-scope-authority-correction'
HELPER=HERE.parent/'swift-guarded-snapshot-emission-bound-implementation'
OWNER=HERE.parent/'swift-guarded-snapshot-owner-storage-closure'
RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
INITIAL='src/experimental_swift_reactor/cache/initial_profile_v1.rs'
CALLEE='src/experimental_swift_reactor/cache/initial_profile_v1/emission_bound_v1.rs'
SEALS={BASE:'351caf4860621989119d16b474dbb53c496a688c4efb0cbb3abb918825b79e6c',
 HELPER:'e92026187ef181ddbcc178e53611ce5e4aa0111c613e9c8ad3a4aca58ff8ffcc',
 HERE.parent/'swift-guarded-snapshot-emission-bound-independent':'135fd7c67ba64191ebe0b63d67c3ed7df787827c444ea15d956f2a9945b8cf95',
 OWNER:'afd33c1df35e4072e582789a38c14372f9a8efc4c6243301df4399e4899f2e4b',
 HERE.parent/'swift-guarded-snapshot-writer-work-audit':'1dba5632efbf285f303eddc4c9dcb727d0bfaae9f24400a32de98a8989d292ea',
 HERE.parent/'swift-guarded-snapshot-writer-work-correction':'b1dd6bf46cd8416637e169ab00fc4e1aa03c094d6c89edb71f0f9721369bd5f7'}

def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def save(name,v):(HERE/name).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def members(p):return [{'path':str(x.relative_to(p)),'bytes':x.stat().st_size,'sha256':sha(x.read_bytes())} for x in sorted(p.rglob('*')) if x.is_file()]

def custody():
 rows=[]
 for p,h in SEALS.items():
  raw=(p/'seal.json').read_bytes();assert sha(raw)==h
  manifest=json.loads(raw)
  for r in manifest['members']:
   b=(p/r['path']).read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256'],(p,r['path'])
  rows.append({'path':str(p.relative_to(REPO))+'/seal.json','sha256':h,'verified_members':len(manifest['members']),
   'status':'frozen candidate under independent review; conditional baseline only' if p==OWNER else 'bound predecessor'})
 p=HERE.parent/'swift-semantic-adapter-root-review/guarded-snapshot-emission-bound-host-acceptance.json'
 assert sha(p.read_bytes())=='97f2d8d24a24f16d614013c5ff3bd8f34c747b87bfa355cb79b46ad51ca88a5b'
 rows.append({'path':str(p.relative_to(REPO)),'sha256':sha(p.read_bytes()),'status':'accepted pure helper only; undispatched'})
 source=members(BASE/'source/vm');assert len(source)==144 and sha(canonical(source))=='575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896'
 return {'schema':1,'inputs':rows,'source144_tree_sha256':sha(canonical(source)),
  'owner_base_accepted':False,'root_git_revision':subprocess.run(['git','rev-parse','HEAD'],cwd=REPO,capture_output=True,check=True,text=True,timeout=10).stdout.strip()}

def prepare():
 save('input-custody.json',custody())
 s=(HELPER/'overlay/vm'/INITIAL).read_text()
 before='''fn proposed_emission_work_v1(_shape:&SnapshotShapeV1)->Result<u64,AError>{
    // Deliberate compile-time preparation stop. The old P/R record rationale
    // does not cover repeated record_word validation/directory search. Root is
    // obtaining a separate source action audit. No rounded placeholder debits
    // can accidentally admit this source if called before that review.
    Err(AError::WorkAuditPending)
}'''
 after='''fn proposed_emission_work_v1(shape:&SnapshotShapeV1)->Result<u64,AError>{
    emission_bound_v1::checked_snapshot_emission_bound_v1(shape)
}'''
 assert s.count(before)==1
 proposed=s.replace(before,after)
 for rel,raw in [(INITIAL,proposed.encode()),(CALLEE,(HELPER/'overlay/vm'/CALLEE).read_bytes())]:
  p=HERE/'overlay/vm'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
 (HERE/'direct-delegation.patch').write_text(''.join(difflib.unified_diff(s.splitlines(True),proposed.splitlines(True),fromfile='accepted-unused-helper/'+INITIAL,tofile='proposed-only/'+INITIAL)))
 save('proposal.json',{'schema':1,'scope':'metadata-only direct tail delegation; never executed or operationally selected',
  'body':after,'helper_unchanged_sha256':sha((HERE/'overlay/vm'/CALLEE).read_bytes()),
  'baseline_wrapper':before,'baseline_initial_sha256':sha((BASE/'source/vm'/INITIAL).read_bytes()),
  'accepted_helper_initial_sha256':sha(s.encode()),'proposed_initial_sha256':sha(proposed.encode()),
  'source_count':145,'unchanged_loader_descriptor':{'source_count':144,'support_count':11},'genuine_loader_binding':False,
  'actual_base_WorkAuditPending_preserved':True,'owner_base_accepted':False})

def run(label,vm,extra,unit=False):
 command=HERE/'commands'/label;command.mkdir(parents=True,exist_ok=False)
 (command/'probe-source.py').write_bytes(Path(__file__).read_bytes())
 save(str(command.relative_to(HERE)/'source-preimage.json'),{'members':members(vm),'probe_sha256':sha(Path(__file__).read_bytes())})
 version=subprocess.run([str(RUSTC),'--version','--verbose'],capture_output=True,check=True,timeout=10).stdout
 argv=[str(RUSTC),'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','opt-level=0','-C','overflow-checks=yes','-C','panic=unwind']
 for f in ['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']:argv+=['--cfg','feature="'+f+'"']
 argv+=(['--test'] if unit else ['--crate-type','rlib'])+[str(vm/'src/lib.rs')]+extra
 env={'PATH':'/usr/bin:/bin','TMPDIR':str(HERE/'owned-work'),'CARGO_MANIFEST_DIR':str(vm),'RUSTC_BOOTSTRAP':'1',
  'MIXER_LOADER_COMPILER_SHA256':sha(RUSTC.read_bytes()),'MIXER_LOADER_COMPILER_VERSION_SHA256':sha(version),
  'MIXER_LOADER_MANIFEST_SHA256':sha(canonical(members(vm))),'MIXER_LOADER_COMMAND_SHA256':sha(canonical(argv))}
 env['MIXER_LOADER_COMPILE_ENV_SHA256']=sha(canonical(env))
 start=time.monotonic();p=subprocess.Popen(argv,cwd=REPO,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
 timed=False;actions=[]
 try:out,err=p.communicate(timeout=55)
 except subprocess.TimeoutExpired:
  timed=True
  try:os.killpg(p.pid,signal.SIGKILL);actions.append('SIGKILL owned process group')
  except ProcessLookupError:pass
  out,err=p.communicate()
 try:os.killpg(p.pid,0);absent=False
 except ProcessLookupError:absent=True
 (command/'stdout').write_bytes(out);(command/'stderr').write_bytes(err)
 artifacts=[]
 if '-o' in argv:
  artifact=Path(argv[argv.index('-o')+1])
  if artifact.exists():artifacts=members(artifact.parent) if artifact.is_dir() else [{'path':str(artifact.relative_to(HERE)),'bytes':artifact.stat().st_size,'sha256':sha(artifact.read_bytes())}]
 receipt={'schema':1,'argv':argv,'environment':env,'rustc_version':version.decode(),'compiler_sha256':sha(RUSTC.read_bytes()),
  'exit_code':p.returncode,'elapsed_seconds':time.monotonic()-start,'timeout_seconds':55,'timed_out':timed,'owned_process_group':p.pid,
  'new_session':True,'child_reaped':True,'owned_group_absent':absent,'cleanup_actions':actions,'artifacts_before_cleanup':artifacts,
  'stdout_sha256':sha(out),'stderr_sha256':sha(err),'scope':'compiler only; zero VM/encoder/writer/runtime/native/UI/capture execution; no process inventory'}
 save(str(command.relative_to(HERE)/'receipt.json'),receipt)
 print(json.dumps({'label':label,'exit_code':p.returncode,'seconds':receipt['elapsed_seconds'],'owned_group_absent':absent}),flush=True)
 assert absent and not timed
 return p.returncode

def extracted_functions(text):
 result=[]
 for m in re.finditer(r'(?m)^fn .*?\n\}',text,re.S):
  h=m.group().splitlines()[0]
  if any(h.startswith('fn '+n+'(') for n in ['proposed_emission_work_v1','emission_bound_v1::checked_snapshot_emission_bound_v1','checked_snapshot_emission_bound_v1','begin_snapshot_access_v1','begin_snapshot_access_v1::{closure#0}']):result.append(m.group())
 return result

def compiler_mir():
 prepare();work=HERE/'owned-work';work.mkdir(exist_ok=False)
 try:
  vm=work/'vm';shutil.copytree(BASE/'source/vm',vm)
  for p in (HERE/'overlay/vm').rglob('*'):
   if p.is_file():target=vm/p.relative_to(HERE/'overlay/vm');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
  for unit in (False,True):
   mode='unit' if unit else 'production';out=work/(mode+'.mir')
   code=run('final-proposed-'+mode+'-mir',vm,['--emit=mir','-Zmir-opt-level=0','-Zmir-include-spans=yes','-o',str(out)],unit)
   assert code==0
   fs=extracted_functions(out.read_text());assert len(fs)==4,[x.splitlines()[0] for x in fs]
   (HERE/(mode+'-functions.mir')).write_text('\n\n'.join(x.replace(str(vm/'src')+'/','source/') for x in fs)+'\n')
 finally:
  artifacts=members(work);shutil.rmtree(work)
  save('mir-cleanup.json',{'removed_members':artifacts,'scratch_absent':not work.exists(),'only_owned_scratch_removed':True})

def decode_tuple(line):
 raw=re.search(r'c"(.*?)"',line)[1];out=bytearray();i=0
 while i<len(raw):
  if raw[i]=='\\':out.append(int(raw[i+1:i+3],16));i+=3
  else:out.append(ord(raw[i]));i+=1
 assert len(out)==16,(line,len(out))
 return {'bytes':int.from_bytes(out[:8],'little'),'alignment':int.from_bytes(out[8:],'little')}

def compiler_layouts():
 requests=json.loads((HERE/'layout-requests.json').read_text());work=HERE/'owned-work';work.mkdir(exist_ok=False)
 results={r['type']:{} for r in requests}
 try:
  vm=work/'vm';shutil.copytree(BASE/'source/vm',vm)
  for p in (HERE/'overlay/vm').rglob('*'):
   if p.is_file():target=vm/p.relative_to(HERE/'overlay/vm');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
  seam='\n// Layout measurement tuples only, never product storage or execution.\n'
  for r in requests:
   t=re.sub(r'(?<![\w:])experimental_swift_reactor::','crate::experimental_swift_reactor::',r['type'])
   if t.startswith('&'):t="&'static "+t[1:]
   seam+='#[no_mangle]\nstatic '+r['symbol']+':(usize,usize)=(std::mem::size_of::<'+t+'>(),std::mem::align_of::<'+t+'>());\n'
  (HERE/'layout-seam.rs').write_text(seam)
  p=vm/CALLEE;p.write_text(p.read_text()+seam)
  p=vm/'src/lib.rs';p.write_text('#![feature(never_type)]\n'+p.read_text())
  for unit in (False,True):
   mode='unit' if unit else 'production';out=work/(mode+'.ll')
   code=run('final-actual-'+mode+'-layouts',vm,['--emit=llvm-ir','-Zmir-opt-level=0','-o',str(out)],unit)
   assert code==0
   ir=out.read_text();lines=[]
   for r in requests:
    matched=[l for l in ir.splitlines() if l.startswith('@'+r['symbol']+' =')];assert len(matched)==1
    lines+=matched;results[r['type']][mode]={**decode_tuple(matched[0]),'evidence':mode+'-layout-tuples.llvm','symbol':r['symbol']}
   (HERE/(mode+'-layout-tuples.llvm')).write_text('\n'.join(lines)+'\n')
  save('type-layouts.json',{'schema':1,'target':'aarch64-apple-darwin','compiler':str(RUSTC),'types':[{'type':t,**r} for t,r in results.items()],
   'scope':'Actual compiler const sizes and alignments in full production and cfg(test) source. LLVM measurement tuples introduce no budget arrays or product owners. Host only; no target-device qualification.'})
 finally:
  artifacts=members(work);shutil.rmtree(work)
  save('layout-cleanup.json',{'removed_members':artifacts,'scratch_absent':not work.exists(),'only_owned_scratch_removed':True})

def compiler_recipe():
 work=HERE/'owned-work';work.mkdir(exist_ok=False)
 try:
  vm=work/'const-only';(vm/'src').mkdir(parents=True)
  recipe=(HERE/'checked-additive-recipe.rs').read_text();(vm/'src/lib.rs').write_text(recipe)
  for unit in (False,True):
   mode='unit' if unit else 'production'
   assert run('checked-recipe-'+mode,vm,['--emit=metadata','-o',str(work/(mode+'.rmeta'))],unit)==0
  negative='\nconst NEGATIVE_OVERFLOW:u64=u64::MAX.checked_add(NET_DELTA).expect("deliberate checked delta overflow");\n'
  (HERE/'overflow-negative-seam.rs').write_text(negative);(vm/'src/lib.rs').write_text(recipe+negative)
  assert run('checked-recipe-overflow-negative',vm,['--emit=metadata','-o',str(work/'overflow.rmeta')])!=0
  assert 'E0080' in (HERE/'commands/checked-recipe-overflow-negative/stderr').read_text()
 finally:
  artifacts=members(work);shutil.rmtree(work)
  save('recipe-cleanup.json',{'removed_members':artifacts,'scratch_absent':not work.exists(),'only_owned_scratch_removed':True})

if __name__=='__main__':
 if sys.argv[1]=='mir':compiler_mir()
 elif sys.argv[1]=='layouts':compiler_layouts()
 elif sys.argv[1]=='recipe':compiler_recipe()
 else:raise ValueError(sys.argv[1])
