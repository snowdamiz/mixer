from pathlib import Path
import hashlib,json,os,secrets,shutil,struct,subprocess,sys,tempfile,time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRODUCER=ROOT/'verification/swift-real-profile-loader-binding';SOURCE=PRODUCER/'source/vm'
RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
PREFIX='experimental_swift_reactor::retained_profile_loader_v1::independent_review_controls::'
IDENTITIES=['MIXER_LOADER_MANIFEST_SHA256','MIXER_LOADER_COMMAND_SHA256','MIXER_LOADER_COMPILE_ENV_SHA256','MIXER_LOADER_COMPILER_SHA256','MIXER_LOADER_COMPILER_VERSION_SHA256']
FEATURES=['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']
def digest(b):return hashlib.sha256(b).digest()
def ident(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':digest(b).hex()}
def write(name,v):(HERE/name).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def manifest(folder):
 members=[{'path':str(p.relative_to(folder)),'bytes':len(p.read_bytes()),'sha256':digest(p.read_bytes()).hex()}for p in sorted(folder.rglob('*'))if p.is_file()]
 return {'members':members,'member_count':len(members),'tree_sha256':digest(json.dumps(members,sort_keys=True,separators=(',',':')).encode()).hex()}
def counted(values):return struct.pack('<Q',len(values))+b''.join(struct.pack('<Q',len(v))+v for v in values)
def environment(values):return counted([os.fsencode(k)+b'='+os.fsencode(v)for k,v in sorted(values.items(),key=lambda p:os.fsencode(p[0]))])
def word(b,at,n):struct.pack_into('<Q',b,at,n)
def build_wire(parts,compiler,binary):
 b=bytearray(512);b[:8]=b'MIXLBD01'
 for at,n in[(8,1),(16,512),(24,512+sum(map(len,parts))),(32,144),(40,11),(80,len(binary))]:word(b,at,n)
 b[88:108]=b'aarch64-apple-darwin'
 for i,p in enumerate(parts):word(b,48+i*8,len(p));b[152+i*32:184+i*32]=digest(p)
 b[280:312]=compiler;b[312:344]=digest(binary);return bytes(b)+b''.join(parts)
def file_identity(p):
 s=os.stat(p);return struct.pack('<QQQQqqqq',s.st_dev,s.st_ino,s.st_size,s.st_mode,s.st_mtime_ns//10**9,s.st_mtime_ns%10**9,s.st_ctime_ns//10**9,s.st_ctime_ns%10**9)
def session_wire(source,build,binary,nonce,argv,env):
 parts=[file_identity(source),counted([os.fsencode(a)for a in argv]),environment(env),os.fsencode(ROOT)]
 b=bytearray(512);b[:8]=b'MIXLSE01'
 for at,n in[(8,1),(16,512),(24,512+sum(map(len,parts))),(32,os.stat(source).st_size)]:word(b,at,n)
 for i,p in enumerate(parts):word(b,40+i*8,len(p));b[240+i*32:272+i*32]=digest(p)
 for i,n in enumerate([67108864,16777216,1048576,512000000,120000]):word(b,72+i*8,n)
 b[112:144]=nonce;b[144:176]=digest(source.read_bytes());b[176:208]=digest(build);b[208:240]=digest(binary)
 return bytes(b)+b''.join(parts)
def main():
 scratch=Path(tempfile.mkdtemp(prefix='independent-host-',dir=HERE));variant=scratch/'source';shutil.copytree(SOURCE,variant)
 logdir=HERE/'independent-logs';logdir.mkdir(exist_ok=True);receipts=[];artifacts=[];sessions=[]
 env={'PATH':'/usr/bin:/bin','TMPDIR':str(scratch),'CARGO_MANIFEST_DIR':str(variant)}
 def run(label,args,environment=env,executable=None):
  out=logdir/(label+'.stdout');err=logdir/(label+'.stderr');start=time.monotonic();killed=None
  with out.open('wb')as o,err.open('wb')as e:
   child=subprocess.Popen([os.fsencode(a)for a in args],cwd=ROOT,env=environment,executable=executable,stdout=o,stderr=e)
   while True:
    try:code=child.wait(timeout=.05);break
    except subprocess.TimeoutExpired:
     if time.monotonic()-start>60:killed='time'
     if out.stat().st_size+err.stat().st_size>1048576:killed='output'
     if killed:child.kill();child.wait();code=124;break
  row={'label':label,'argv_raw_hex':[os.fsencode(a).hex()for a in args],'argv':[os.fsdecode(a)for a in args],'executable':None if executable is None else os.fsdecode(executable),'cwd':str(ROOT),'exit_code':code,'elapsed_seconds':time.monotonic()-start,'timeout_seconds':60,'output_byte_limit':1048576,'killed_for':killed,'terminally_waited':True,'stdout':ident(out),'stderr':ident(err)}
  receipts.append(row);write('independent-command-receipts.json',receipts);print(label+': '+str(code),flush=True)
  assert code==0,(label,err.read_text(errors='replace')[-4000:],out.read_text(errors='replace')[-4000:]);return out.read_bytes()
 def flags(opt):
  a=[RUSTC,'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','opt-level='+opt,'-C','overflow-checks=yes','-C','panic=unwind']
  for f in FEATURES:a+=['--cfg','feature="'+f+'"']
  return a
 try:
  runner_before=ident(Path(__file__));version=run('rustc-version',[RUSTC,'-vV']);revision=run('revision',['git','rev-parse','HEAD']).decode().strip();compiler=ident(RUSTC)
  module=variant/'src/experimental_swift_reactor/retained_profile_loader_v1.rs';delta='\n#[cfg(test)] mod independent_review_controls { include!("'+str(HERE/'independent_controls.rs')+'"); }\n';module.write_bytes(module.read_bytes()+delta.encode())
  source_manifest=manifest(variant);assert source_manifest['member_count']==144
  closure={'distribution':source_manifest,'host_support':manifest(PRODUCER/'host'),'independent_inputs':[ident(HERE/n)for n in ['independent_controls.rs','original_fixture.rs','sha256-single-byte.bin','run_independent.py']],'compiler':compiler,'compiler_version_sha256':digest(version).hex(),'baseline_source_tree_sha256':'3d7776d8ca3dc10894522079b49e0e8602b567c2e3926f9438b51c843fd6af13'}
  preimage=json.dumps(closure,sort_keys=True,separators=(',',':')).encode();assert len(preimage)<=65536;write('independent-build-input-manifest.json',closure);write('independent-source-variant.json',{'accepted_source_tree_sha256':closure['baseline_source_tree_sha256'],'variant_tree_sha256':source_manifest['tree_sha256'],'member_count':144,'append_path':'src/experimental_swift_reactor/retained_profile_loader_v1.rs','exact_append':delta,'fixture':ident(HERE/'independent_controls.rs'),'fixture_dependency_rewrite':'frozen original fixture replaces use mixer_vm:: with use crate:: only','original_fixture_source':ident(ROOT/'verification/swift-typed-result-codec-implementation/source/vm/tests/swift_reactor_validation_fixture.rs')})
  data=HERE/'independent-preimages';data.mkdir(exist_ok=True)
  for mode,opt in [('debug','0'),('optimized','3')]:
   binary=scratch/('unit-'+mode);args=flags(opt)+['--test',variant/'src/lib.rs','-o',binary];parts=[preimage,counted([os.fsencode(a)for a in args]),environment(env),version]
   comp_env=env|dict(zip(IDENTITIES,[digest(parts[0]).hex(),digest(parts[1]).hex(),digest(parts[2]).hex(),compiler['sha256'],digest(parts[3]).hex()]))
   run('compile-'+mode,args,comp_env);artifacts.append(ident(binary));binary_bytes=binary.read_bytes();build=build_wire(parts,bytes.fromhex(compiler['sha256']),binary_bytes);(data/('build-'+mode+'.bin')).write_bytes(build)
   fixtures=scratch/('fixtures-'+mode);fixtures.mkdir();emit_env=env|{'MIXER_REVIEW_FIXTURE_ROOT':str(fixtures)};run('emit-late-fixture-'+mode,[binary,'--exact',PREFIX+'independent_emit_late_fixture','--nocapture','--test-threads=1'],emit_env)
   for name in ['valid.wasm','late.wasm']:
    target=data/name
    if target.exists():assert target.read_bytes()==(fixtures/name).read_bytes()
    else:shutil.copyfile(fixtures/name,target)
   assert digest((fixtures/'late.wasm').read_bytes()).hex()=='81b28ffe0b37df1b44837cf1a849c470d2edafff2b6a89c4e0c5189da6287b55'
   helpers=run('independent-helpers-'+mode,[binary,PREFIX,'--skip','independent_emit_late_fixture','--skip','independent_actual_loader_child','--nocapture','--test-threads=1'],env|{'MIXER_REVIEW_EMPTY_ROOT':str(fixtures)})
   assert b'6 passed; 0 failed' in helpers
   cases=['late-failure','raw-argv','alias-source-session','alias-source-executable','alias-build-session','alias-build-executable','alias-session-executable']+['allocation-'+str(n)for n in range(5)]
   for case in cases:
    folder=scratch/(mode+'-'+case);folder.mkdir();source=fixtures/('valid.wasm'if case=='raw-argv'else'late.wasm');buildpath=folder/'build.bin';sessionpath=folder/'session.bin';buildpath.write_bytes(build)
    runtime=env|{'MIXER_REVIEW_CASE':case,'MIXER_REVIEW_SOURCE':str(source),'MIXER_REVIEW_BUILD':str(buildpath),'MIXER_REVIEW_SESSION':str(sessionpath),'MIXER_REVIEW_EXECUTABLE':str(binary)}
    argv=[b'review-\xff'if case=='raw-argv'else os.fsencode(binary),b'--exact',os.fsencode(PREFIX+'independent_actual_loader_child'),b'--nocapture',b'--test-threads=1']
    nonce=secrets.token_bytes(32);session=session_wire(source,build,binary_bytes,nonce,argv,runtime);sessionpath.write_bytes(session);runtime['MIXER_LOADER_EXPECTED_SESSION_SHA256']=digest(session).hex();runtime['MIXER_LOADER_EXPECTED_NONCE_HEX']=nonce.hex();retained=data/(mode+'-'+case+'.bin');retained.write_bytes(session)
    sessions.append({'mode':mode,'case':case,'source':ident(source),'session':ident(retained),'build_sha256':digest(build).hex(),'binary_sha256':digest(binary_bytes).hex(),'nonce':nonce.hex(),'argv_raw_hex':[a.hex()for a in argv],'runtime_without_two_identity_keys':{os.fsencode(k).hex():os.fsencode(v).hex()for k,v in runtime.items()if k not in ['MIXER_LOADER_EXPECTED_SESSION_SHA256','MIXER_LOADER_EXPECTED_NONCE_HEX']}})
    output=run(mode+'-'+case,argv,runtime,executable=os.fsencode(binary));assert b'INDEPENDENT_'in output;shutil.rmtree(folder)
  assert ident(Path(__file__))==runner_before;assert manifest(variant)==source_manifest;assert ident(RUSTC)==compiler
  write('independent-receipt.json',{'schema':1,'status':'independent-selected-loader-controls-pass','git_revision_context':revision,'producer_seal_sha256':'e1701fb93056b763a06164d7ccf0cae3112f2e27baaa3f4a35aedd8e747665a2','source_tree_sha256':closure['baseline_source_tree_sha256'],'variant_tree_sha256':source_manifest['tree_sha256'],'runner_hashed_before_compile':runner_before,'actual_compiler':compiler,'rustc_version':version.decode(),'commands':len(receipts),'helper_methods_each_mode':6,'genuine_loader_cases_each_mode':12,'emitter_methods_each_mode':1,'modes':['debug','optimized'],'artifacts_compiled_and_removed':artifacts,'scope':'Private loader host correlation only; no runtime/native/OTA/FieldLog/GA acceptance'})
 finally:
  write('independent-session-observations.json',sessions);shutil.rmtree(scratch);write('independent-cleanup.json',{'scratch_path':str(scratch),'scratch_removed':not scratch.exists(),'all_owned_children_terminally_waited':all(c['terminally_waited']for c in receipts),'frozen_producer_writes':False,'native_UI_capture_process_inventory_used':False,'File_drop_proven_close':False})
if __name__=='__main__':main()
