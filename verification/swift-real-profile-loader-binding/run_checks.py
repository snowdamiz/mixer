"""Selected-host actual loader tests; bounded subprocesses, no native/mobile/UI runtime."""
from pathlib import Path
import datetime,hashlib,json,os,platform,secrets,shutil,struct,subprocess,sys,tempfile,time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];SOURCE=HERE/'source/vm'
RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
PREFIX='experimental_swift_reactor::retained_profile_loader_v1::tests::'
FEATURES=['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']
IDENTITY_NAMES=['MIXER_LOADER_MANIFEST_SHA256','MIXER_LOADER_COMMAND_SHA256','MIXER_LOADER_COMPILE_ENV_SHA256','MIXER_LOADER_COMPILER_SHA256','MIXER_LOADER_COMPILER_VERSION_SHA256']
DEFAULT=[67108864,16777216,1048576,512000000,120000]
def sha(b):return hashlib.sha256(b).digest()
def ident(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b).hex()}
def write(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def manifest(folder):
 members=[{'path':str(p.relative_to(folder)),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes()).hex()} for p in sorted(folder.rglob('*')) if p.is_file()]
 return {'schema':1,'member_count':len(members),'members':members,'tree_sha256':sha(json.dumps(members,sort_keys=True,separators=(',',':')).encode()).hex()}
def packed(values):
 values=[os.fsencode(x) for x in values];return struct.pack('<Q',len(values))+b''.join(struct.pack('<Q',len(x))+x for x in values)
def env_packed(values):return packed([os.fsencode(k)+b'='+os.fsencode(v) for k,v in sorted(values.items(),key=lambda p:os.fsencode(p[0]))])
def put(b,at,n):struct.pack_into('<Q',b,at,n)
def identity_bytes(p):
 s=os.stat(p);return struct.pack('<QQQQqqqq',s.st_dev,s.st_ino,s.st_size,s.st_mode,s.st_mtime_ns//10**9,s.st_mtime_ns%10**9,s.st_ctime_ns//10**9,s.st_ctime_ns%10**9)
def build_record(parts,compiler_digest,output):
 head=bytearray(512);head[:8]=b'MIXLBD01'
 for at,n in [(8,1),(16,512),(24,512+sum(map(len,parts))),(32,144),(40,11),(80,len(output))]:put(head,at,n)
 for i,p in enumerate(parts):put(head,48+8*i,len(p))
 head[88:88+len(b'aarch64-apple-darwin')]=b'aarch64-apple-darwin'
 for i,p in enumerate(parts):head[152+32*i:184+32*i]=sha(p)
 head[280:312]=compiler_digest;head[312:344]=sha(output)
 return bytes(head)+b''.join(parts)
def session_record(source,source_digest,build,binary,nonce,budget,argv,env,cwd,scenario):
 parts=[identity_bytes(source),packed(argv),env_packed(env),os.fsencode(cwd)]
 if scenario=='argv':parts[1]=packed([b'foreign-command'])
 if scenario=='environment':parts[2]=env_packed({'FOREIGN':'x'})
 if scenario=='cwd':parts[3]=b'/foreign-cwd'
 head=bytearray(512);head[:8]=b'MIXLSE01'
 for at,n in [(8,1),(16,512),(24,512+sum(map(len,parts))),(32,os.stat(source).st_size+(scenario=='source-extent'))]:put(head,at,n)
 for i,p in enumerate(parts):put(head,40+8*i,len(p))
 for i,n in enumerate(budget):put(head,72+i*8,n)
 head[112:144]=nonce if scenario!='nonce' else bytes([nonce[0]^1])+nonce[1:]
 head[144:176]=source_digest;head[176:208]=sha(build);head[208:240]=sha(binary)
 for i,p in enumerate(parts):head[240+32*i:272+32*i]=sha(p)
 return bytes(head)+b''.join(parts)
def main():
 source_manifest=manifest(SOURCE);assert source_manifest['member_count']==144
 old=json.loads((HERE/'baseline-source-manifest.json').read_text());a={m['path']:m for m in source_manifest['members']};b={m['path']:m for m in old['members']}
 assert set(a)-set(b)=={'src/experimental_swift_reactor/retained_profile_loader_v1.rs','src/experimental_swift_reactor/retained_profile_loader_v1_tests.rs'}
 assert [k for k in b if a[k]!=b[k]]==['src/experimental_swift_reactor/mod.rs']
 support=json.loads((HERE/'baseline-host-support-manifest.json').read_text());assert len([p for p in (HERE/'host').rglob('*') if p.is_file()])==11
 for m in support['members']:assert ident(HERE/m['retained_path'])['sha256']==m['sha256']
 closure={'schema':1,'distribution':source_manifest,'host_support':support};manifest_bytes=json.dumps(closure,sort_keys=True,separators=(',',':')).encode();assert len(manifest_bytes)<=65536
 write(HERE/'source-manifest.json',source_manifest);write(HERE/'build-input-manifest.json',closure)
 scratch=Path(tempfile.mkdtemp(prefix='loader-host-',dir=HERE));logs=HERE/'logs';logs.mkdir(exist_ok=True);receipts=[];artifacts=[];layouts={};variants=[];scenarios_run=[];unsupported=[];session_observations=[]
 (HERE/'sessions').mkdir(exist_ok=True);(HERE/'source-preimages').mkdir(exist_ok=True)
 def run(label,argv,env,cwd=ROOT,expected=None):
  start=time.monotonic();out=logs/(label+'.stdout');err=logs/(label+'.stderr')
  with out.open('wb')as o,err.open('wb')as e:
   child=subprocess.Popen(argv,cwd=cwd,env=env,stdout=o,stderr=e);killed=None
   while True:
    try:code=child.wait(timeout=.05);break
    except subprocess.TimeoutExpired:
     if time.monotonic()-start>60:killed='time'
     if out.stat().st_size+err.stat().st_size>262144:killed='output'
     if killed:child.kill();child.wait();code=124;break
  stderr=err.read_text(errors='replace');stdout=out.read_text(errors='replace');passed=code==0 if expected is None else code!=0 and expected in stderr
  receipts.append({'label':label,'argv':[os.fsdecode(x) for x in argv],'argv_raw_hex':[os.fsencode(x).hex() for x in argv],'cwd_raw_hex':os.fsencode(cwd).hex(),'exit_code':code,'expected_diagnostic':expected,'expectation_met':passed,'elapsed_seconds':time.monotonic()-start,'timeout_seconds':60,'output_byte_limit':262144,'killed_for':killed,'terminally_waited':True,'stdout':ident(out),'stderr':ident(err)})
  write(HERE/'command-receipts.json',receipts);print(label+': '+('pass'if passed else 'FAIL'),flush=True)
  if not passed:raise AssertionError((label,stdout[-2500:],stderr[-4000:]))
  return stdout
 cleanenv={'PATH':'/usr/bin:/bin','TMPDIR':str(scratch),'CARGO_MANIFEST_DIR':str(SOURCE)}
 def flags(opt):
  args=[str(RUSTC),'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','opt-level='+opt,'-C','overflow-checks=yes','-C','panic=unwind']
  for feature in FEATURES:args+=['--cfg','feature="'+feature+'"']
  return args
 try:
  revision=run('revision',['git','rev-parse','HEAD'],cleanenv).strip();version=run('rustc-version',[str(RUSTC),'-vV'],cleanenv).encode();compiler=ident(RUSTC)
  sdk_headers=['usr/include/CommonCrypto/CommonDigest.h','usr/include/crt_externs.h','usr/include/mach-o/dyld.h','usr/include/unistd.h'];sdk=Path('/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk');headers=[ident(sdk/p)for p in sdk_headers]
  target_cfg=run('target-cfg',[str(RUSTC),'--print','cfg','--target','aarch64-apple-darwin'],cleanenv)
  runner_before=ident(Path(__file__));closure['orchestration']=[runner_before,ident(HERE/'prepare.py'),ident(HERE/'root-selection.json')]
  closure['tools']={'rustc':compiler,'rustc_version_sha256':sha(version).hex(),'python':ident(Path(sys.executable).resolve()),'python_version':sys.version,'SDK_headers':headers}
  manifest_bytes=json.dumps(closure,sort_keys=True,separators=(',',':')).encode();assert len(manifest_bytes)<=65536
  write(HERE/'build-input-manifest.json',closure)
  for mode,opt in [('debug','0'),('optimized','3')]:
   binary=scratch/('unit-'+mode);argv=flags(opt)+['--test',str(SOURCE/'src/lib.rs'),'-o',str(binary)]
   parts=[manifest_bytes,packed(argv),env_packed(cleanenv),version]
   compile_env=cleanenv|dict(zip(IDENTITY_NAMES,[sha(parts[0]).hex(),sha(parts[1]).hex(),sha(parts[2]).hex(),compiler['sha256'],sha(parts[3]).hex()]))
   run('compile-'+mode,argv,compile_env);artifacts.append(ident(binary));assert ident(RUSTC)==compiler
   build=build_record(parts,bytes.fromhex(compiler['sha256']),binary.read_bytes());(HERE/('build-preimage-'+mode+'.bin')).write_bytes(build)
   fixture=scratch/('fixture-'+mode+'.wasm');emit_env=cleanenv|{'MIXER_LOADER_FIXTURE_OUTPUT':str(fixture)}
   run('emit-fixture-'+mode,[str(binary),'--exact',PREFIX+'emit_genuine_validator_fixture','--nocapture','--test-threads=1'],emit_env);fixture_bytes=fixture.read_bytes();assert len(fixture_bytes)==1947;(HERE/'source-preimages'/'genuine.wasm').write_bytes(fixture_bytes)
   helper_env=cleanenv|{'MIXER_LOADER_SOURCE_FILE':str(fixture)}
   result=run('helpers-'+mode,[str(binary),PREFIX,'--skip','actual_selected_loader_child','--nocapture','--test-threads=1'],helper_env)
   assert '13 passed; 0 failed' in result
   layouts[mode]=[line[line.index('LOADER_LAYOUT\t'):].split('\t')[1:]for line in result.splitlines()if 'LOADER_LAYOUT\t' in line];assert len(layouts[mode])==23
   scenarios=['success','narrowed','raw-environment','raw-cwd','raw-executable','source-substitute','source-extent','build-tail','build-identity','binary-substitute','session-digest','nonce','argv','environment','cwd','offset','alias','nonregular','unreadable','zero-source','zero-metadata','zero-scratch','zero-work','zero-deadline','cancelled','malformed','large-malformed','build-overcap','session-overcap']+[p+'-'+f for p in ['drift','widen']for f in ['source','metadata','scratch','work','deadline']]
   for scenario in scenarios:
    case=scratch/(mode+'-'+scenario);case.mkdir();source_file=case/'original.wasm';source_file.write_bytes(fixture_bytes);source_digest=sha(fixture_bytes);case_build=bytearray(build)
    if scenario=='source-substitute':v=bytearray(fixture_bytes);v[-2]^=1;source_file.write_bytes(v)
    if scenario=='large-malformed':
     v=bytearray(8*1024*1024);v[:len(fixture_bytes)]=fixture_bytes;v[0]=255;source_file.write_bytes(v);source_digest=sha(v)
    if scenario=='malformed':v=bytearray(fixture_bytes);v[0]=255;source_file.write_bytes(v);source_digest=sha(v)
    if scenario=='build-tail':case_build[512]^=1
    if scenario=='build-identity':case_build[280]^=1
    if scenario=='binary-substitute':case_build[312]^=1
    build_file=case/'build.bin';session_file=case/'session.bin';build_file.write_bytes(case_build)
    executable=os.fsencode(binary)
    if scenario=='raw-executable':
     executable=os.fsencode(case)+b'/producer-\xff'
     try:shutil.copyfile(os.fsencode(binary),executable);os.chmod(executable,0o700)
     except OSError as error:
      if error.errno!=92:raise
      unsupported.append({'mode':mode,'scenario':scenario,'status':'host-filesystem-refused-before-loader','errno':error.errno,'message':str(error)});shutil.rmtree(case);continue
    cwd=os.fsencode(ROOT)
    if scenario=='raw-cwd':
     cwd=os.fsencode(case)+b'/cwd-\xff'
     try:os.mkdir(cwd)
     except OSError as error:
      if error.errno!=92:raise
      unsupported.append({'mode':mode,'scenario':scenario,'status':'host-filesystem-refused-before-loader','errno':error.errno,'message':str(error)});shutil.rmtree(case);continue
    child_argv=[executable,b'--exact',os.fsencode(PREFIX+'actual_selected_loader_child'),b'--nocapture',b'--test-threads=1']
    runtime=cleanenv|{'MIXER_LOADER_SOURCE_FILE':str(source_file),'MIXER_LOADER_BUILD_FILE':str(build_file),'MIXER_LOADER_SESSION_FILE':str(session_file),'MIXER_LOADER_SCENARIO':scenario}
    if scenario=='raw-environment':runtime['MIXER_LOADER_RAW']=b'value-\xff'
    nonce=secrets.token_bytes(32);budget=DEFAULT.copy()
    if scenario=='narrowed':budget=[1947,1_000_000,65536,1_000_000,10000]
    if scenario.startswith('zero-'):budget[['source','metadata','scratch','work','deadline'].index(scenario[5:])]=0
    ses=session_record(source_file,source_digest,bytes(case_build),binary.read_bytes(),nonce,budget,child_argv,runtime,cwd,scenario)
    session_file.write_bytes(ses);runtime['MIXER_LOADER_EXPECTED_SESSION_SHA256']=sha(ses).hex();runtime['MIXER_LOADER_EXPECTED_NONCE_HEX']=nonce.hex()
    if scenario=='session-digest':v=bytearray(ses);v[112]^=1;session_file.write_bytes(v)
    if scenario=='build-overcap':build_file.write_bytes(bytes(131073))
    if scenario=='session-overcap':session_file.write_bytes(bytes(65537))
    retained_session=HERE/'sessions'/(mode+'-'+scenario+'.bin');retained_session.write_bytes(session_file.read_bytes())
    if scenario in ['source-substitute','malformed','large-malformed']:(HERE/'source-preimages'/(scenario+'.wasm')).write_bytes(source_file.read_bytes())
    if bytes(case_build)!=build:(HERE/'sessions'/(mode+'-'+scenario+'-build.bin')).write_bytes(build_file.read_bytes())
    if scenario=='build-overcap':(HERE/'sessions'/(mode+'-'+scenario+'-build.bin')).write_bytes(build_file.read_bytes())
    session_observations.append({'mode':mode,'scenario':scenario,'source_identity_hex':identity_bytes(source_file).hex(),'source_sha256':ident(source_file)['sha256'],'source_preimage':'source-preimages/'+(scenario+'.wasm' if scenario in ['source-substitute','malformed','large-malformed']else 'genuine.wasm'),'build_sha256':ident(build_file)['sha256'],'session':ident(retained_session),'session_commitment_from_trusted_launcher':runtime['MIXER_LOADER_EXPECTED_SESSION_SHA256'],'nonce_from_OS_randomness_hex':nonce.hex(),'actual_argv_encoding_sha256':sha(packed(child_argv)).hex(),'actual_environment_encoding_sha256':sha(env_packed({k:v for k,v in runtime.items()if k not in ['MIXER_LOADER_EXPECTED_SESSION_SHA256','MIXER_LOADER_EXPECTED_NONCE_HEX']})).hex(),'actual_cwd_raw_hex':os.fsencode(cwd).hex(),'producer_binary_sha256':ident(binary)['sha256']})
    output=run(mode+'-'+scenario,child_argv,runtime,cwd);assert ('SELECTED\t' in output) if scenario in ['success','narrowed','raw-environment','raw-cwd','raw-executable']else ('REFUSED\t' in output)
    scenarios_run.append({'mode':mode,'scenario':scenario,'session_digest_expected':runtime['MIXER_LOADER_EXPECTED_SESSION_SHA256'],'owned_names_removed_after':True})
    shutil.rmtree(case)
   ordinary=scratch/('ordinary-'+mode+'.rlib');ordinary_args=flags(opt)+['--crate-type','rlib',str(SOURCE/'src/lib.rs'),'-o',str(ordinary)]
   run('ordinary-production-'+mode,ordinary_args,cleanenv);artifacts.append(ident(ordinary))
   for name,diagnostic in [('positive',None),('clone','E0599'),('private_proof','E0616'),('private_provenance','E0616'),('literal','due to private fields'),('source_escape','E0515'),('source_mutation','E0594'),('raw_proof_mint','E0308'),('deserialize','E0599')]:
    variant=scratch/'variant';shutil.copytree(SOURCE,variant);path=variant/'src/experimental_swift_reactor/mod.rs';delta=b'\n#[cfg(test)] mod loader_compile_contract { include!(env!("MIXER_LOADER_COMPILE_CASE")); }\n';path.write_bytes(path.read_bytes()+delta)
    fixture_case=HERE/'compile_cases'/(name+'.rs');fixture_env=cleanenv|{'CARGO_MANIFEST_DIR':str(variant),'MIXER_LOADER_COMPILE_CASE':str(fixture_case)}
    variants.append({'mode':mode,'fixture':ident(fixture_case),'source_tree_sha256':source_manifest['tree_sha256'],'variant_tree_sha256':manifest(variant)['tree_sha256'],'append_path':'src/experimental_swift_reactor/mod.rs','append_bytes':delta.decode(),'expected_diagnostic':diagnostic})
    run('contract-'+mode+'-'+name,flags(opt)+['--test','--emit=metadata',str(variant/'src/lib.rs'),'-o',str(scratch/'case.rmeta')],fixture_env,expected=diagnostic);shutil.rmtree(variant)
   type_names={'SelectedValidatedProfileV1':'SelectedValidatedProfileV1','LoaderProvenanceV1':'LoaderProvenanceV1','LoaderFailureV1':'LoaderFailureV1','LoaderOutcomeV1':'LoaderOutcomeV1','ReturnedLoaderFilesV1':'ReturnedLoaderFilesV1','LoaderUsageV1':'LoaderUsageV1','FileIdentityV1':'FileIdentityV1','BuildView':"BuildView<'static>",'SessionView':"SessionView<'static>",'ProcessObservationV1':'ProcessObservationV1','BytesProcess':'Bytes<PROCESS_CAP>','BytesPath':'Bytes<STR_CAP>','EnvironmentEntries':'[(usize,usize,usize);ENTRY_CAP]','ResultSelected':'Result<SelectedValidatedProfileV1,LoaderFailureV1>','ValidationResult':'Result<ValidatedSwiftReactor,SwiftValidationFailure>','VecHeader':'Vec<u8>','File':'File','OptionFile':'Option<File>','ValidationBudget':'SwiftValidationBudget','ValidationFailure':'SwiftValidationFailure','ObservationPlaces':'ObservationPlacesV1','LoaderPlaces':'LoaderPlacesV1','ReadHashPlaces':'ReadHashPlacesV1'}
   variant=scratch/'ordinary-layout-variant';shutil.copytree(SOURCE,variant);changed=variant/'src/experimental_swift_reactor/retained_profile_loader_v1.rs'
   delta='\nconst _: () = {\n'+''.join('assert!(std::mem::size_of::<'+type_names[name]+'>() == '+size+');\nassert!(std::mem::align_of::<'+type_names[name]+'>() == '+align+');\n'for name,size,align in layouts[mode])+'};\n'
   changed.write_text(changed.read_text()+delta);variants.append({'mode':mode,'purpose':'ordinary-production23-layouts-equal-measured-unit','source_tree_sha256':source_manifest['tree_sha256'],'variant_tree_sha256':manifest(variant)['tree_sha256'],'append_path':'src/experimental_swift_reactor/retained_profile_loader_v1.rs','append_bytes':delta,'expected_diagnostic':None})
   run('production-layout-'+mode,flags(opt)+['--crate-type','rlib','--emit=metadata',str(variant/'src/lib.rs'),'-o',str(scratch/'ordinary-layout.rmeta')],cleanenv|{'CARGO_MANIFEST_DIR':str(variant)});shutil.rmtree(variant)
   assert manifest(SOURCE)==source_manifest
   for member in support['members']:assert ident(HERE/member['retained_path'])['sha256']==member['sha256']
 finally:
  shutil.rmtree(scratch);write(HERE/'data-layouts.json',layouts);write(HERE/'compile-variants.json',variants);write(HERE/'scenarios.json',scenarios_run);write(HERE/'unsupported-path-cases.json',unsupported);write(HERE/'session-observations.json',session_observations);write(HERE/'cleanup.json',{'scratch_removed':not scratch.exists(),'all_children_terminally_waited':all(r['terminally_waited']for r in receipts),'native_runtime_simulator_emulator_UI_capture_or_process_inventory_used':False,'returned_File_drop_is_proven_close':False,'host_removed_owned_names_after_terminal_child':True})
 assert manifest(SOURCE)==source_manifest
 assert ident(Path(__file__))==runner_before
 report={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'actual-private-loader-carrier-host-controls-pass','git_revision_context':revision,'source_manifest_sha256':ident(HERE/'source-manifest.json')['sha256'],'source_tree_sha256':source_manifest['tree_sha256'],'distribution_members':144,'unchanged_host_support_members':11,'runner':runner_before,'orchestration':closure['orchestration'],'commands':len(receipts),'helper_methods_each_mode':13,'genuine_fixture_emission_each_mode':1,'real_loader_scenarios_each_mode':len(scenarios)-2,'non_UTF8_filesystem_path_cases_not_run_each_mode':2,'compile_positive_each_mode':1,'compile_negative_each_mode':8,'new_layouts_each_mode':23,'ordinary_production_layouts_compared_each_mode':23,'retained_exact_source_build_session_preimages':True,'ordinary_production_modes':['debug','optimized'],'rustc':compiler,'rustc_version':version.decode(),'target_cfg':target_cfg,'platform':platform.platform(),'python':ident(Path(sys.executable).resolve()),'python_version':sys.version,'SDK_headers':headers,'artifacts_measured_then_removed':artifacts,'host_scope':'macOS aarch64 trusted launcher, quiescent local correlation only','crypto':'platform CommonCrypto CC_SHA256; no custom primitive','runtime_adoption_sidecar_export_real_context_replay_native_FieldLog_OTA_GA_accepted':False,'original165_inventory_covers_loader':False,'no_canonical_index_git_mutation':True}
 write(HERE/'receipt.json',report);print(json.dumps({k:report[k]for k in ['status','commands','real_loader_scenarios_each_mode','source_tree_sha256']}))
if __name__=='__main__':main()
