#!/usr/bin/env python3
"""Bounded owned host-only evidence steps. Each child <=60s, terminally reaped."""
from pathlib import Path
import datetime,hashlib,json,os,platform,secrets,shutil,struct,subprocess,sys,time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];SOURCE=HERE/'source/vm'
WORK=HERE/'owned-work';WORK.mkdir(exist_ok=True)
RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
FEATURES=['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']
PREFIX='experimental_swift_reactor::retained_profile_loader_v1::tests::'
INITIAL='experimental_swift_reactor::cache::initial_profile_v1::tests::'
IDENTITIES=['MIXER_LOADER_MANIFEST_SHA256','MIXER_LOADER_COMMAND_SHA256','MIXER_LOADER_COMPILE_ENV_SHA256','MIXER_LOADER_COMPILER_SHA256','MIXER_LOADER_COMPILER_VERSION_SHA256']
def sha(b):return hashlib.sha256(b).hexdigest()
def ident(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def manifest(folder):
 files=sorted(p for p in folder.rglob('*') if p.is_file());assert not any(p.is_symlink() for p in folder.rglob('*'))
 members=[{'path':str(p.relative_to(folder)),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}for p in files]
 return {'schema':1,'member_count':len(members),'members':members,'tree_sha256':sha(json.dumps(members,sort_keys=True,separators=(',',':')).encode())}
def packed(v):
 v=[os.fsencode(x)for x in v];return struct.pack('<Q',len(v))+b''.join(struct.pack('<Q',len(x))+x for x in v)
def envpacked(v):return packed([os.fsencode(k)+b'='+os.fsencode(x)for k,x in sorted(v.items(),key=lambda p:os.fsencode(p[0]))])
def identity(p):
 s=os.stat(p);return struct.pack('<QQQQqqqq',s.st_dev,s.st_ino,s.st_size,s.st_mode,s.st_mtime_ns//10**9,s.st_mtime_ns%10**9,s.st_ctime_ns//10**9,s.st_ctime_ns%10**9)
def flags(mode):
 args=[str(RUSTC),'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','opt-level='+('0'if mode=='debug'else'3'),'-C','overflow-checks=yes','-C','panic=unwind']
 for feature in FEATURES:args+=['--cfg','feature="'+feature+'"']
 return args
def cleanenv():return {'PATH':'/usr/bin:/bin','TMPDIR':str(WORK),'CARGO_MANIFEST_DIR':str(SOURCE)}
def run(label,argv,env=None,expected=None,allow_failure=False,cwd=REPO):
 records=HERE/'commands';records.mkdir(exist_ok=True)
 folder=records/f'{len(list(records.iterdir()))+1:04d}-{label}';folder.mkdir()
 started=time.monotonic();killed=None
 with (folder/'stdout').open('wb')as out,(folder/'stderr').open('wb')as err:
  child=subprocess.Popen([str(x)for x in argv],env=env or cleanenv(),cwd=cwd,stdout=out,stderr=err)
  while True:
   try:code=child.wait(timeout=.05);break
   except subprocess.TimeoutExpired:
    if time.monotonic()-started>55:killed='time'
    if (folder/'stdout').stat().st_size+(folder/'stderr').stat().st_size>1048576:killed='output'
    if killed:child.kill();child.wait();code=124;break
 stdout=(folder/'stdout').read_text(errors='replace');stderr=(folder/'stderr').read_text(errors='replace')
 passed=code==0 if expected is None else code!=0 and expected in stderr
 receipt={'label':label,'argv':[str(x)for x in argv],'cwd':str(cwd),'environment':env or cleanenv(),'exit_code':code,'expected_diagnostic':expected,'expectation_met':passed,'allow_failure_for_measurement':allow_failure,'timeout_seconds':55,'output_byte_limit':1048576,'supervisor_killed_for':killed,'elapsed_seconds':time.monotonic()-started,'terminally_waited':True,'source_tree_sha256':manifest(SOURCE)['tree_sha256'],'runner':ident(__file__),'stdout':ident(folder/'stdout'),'stderr':ident(folder/'stderr')}
 write(folder/'receipt.json',receipt);print(label+': '+('pass'if passed else'FAIL'),flush=True)
 if not passed and not allow_failure:raise AssertionError((label,stdout[-1000:],stderr[-3000:]))
 return stdout,stderr,receipt
def closure():
 source=manifest(SOURCE);assert source['member_count']==144
 host=manifest(HERE/'host');assert host['member_count']==11
 version,_,_=run('rustc-version',[RUSTC,'-vV'])
 revision,_,_=run('revision',['git','rev-parse','HEAD'])
 sdk=Path('/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk')
 headers=[ident(sdk/p)for p in ['usr/include/CommonCrypto/CommonDigest.h','usr/include/crt_externs.h','usr/include/mach-o/dyld.h','usr/include/unistd.h']]
 context={'schema':1,'distribution':source,'host_support':host,'orchestration':[ident(HERE/p)for p in ['evidence.py','selection.json','implement_selected.py','extend_roster.py']],'tools':{'rustc':ident(RUSTC),'rustc_version_sha256':sha(version.encode()),'python':ident(Path(sys.executable).resolve()),'python_version':sys.version,'SDK_headers':headers},'git_revision_context':revision.strip(),'platform':platform.platform()}
 write(HERE/'build-input-manifest.json',context);write(HERE/'source-manifest.json',source)
 return context,version.encode()
def compile(mode,host=False):
 if host:
  binary=WORK/f'host-{mode}.dylib'
  run('compile-host-'+mode,flags(mode)+['--crate-type','cdylib','--cfg','mixer_initial_profile_component_host',SOURCE/'src/lib.rs','-o',binary]);return
 context,version=closure();binary=WORK/f'unit-{mode}'
 argv=flags(mode)+['--test',str(SOURCE/'src/lib.rs'),'-o',str(binary)]
 parts=[json.dumps(context,sort_keys=True,separators=(',',':')).encode(),packed(argv),envpacked(cleanenv()),version];assert len(parts[0])<=65536
 compiler=ident(RUSTC);env=cleanenv()|dict(zip(IDENTITIES,[sha(parts[0]),sha(parts[1]),sha(parts[2]),compiler['sha256'],sha(parts[3])]))
 run('compile-unit-'+mode,argv,env)
 data=binary.read_bytes();head=bytearray(512);head[:8]=b'MIXLBD01'
 for at,n in [(8,1),(16,512),(24,512+sum(map(len,parts))),(32,144),(40,11),(80,len(data))]:struct.pack_into('<Q',head,at,n)
 for i,p in enumerate(parts):struct.pack_into('<Q',head,48+8*i,len(p));head[152+32*i:184+32*i]=bytes.fromhex(sha(p))
 head[88:108]=b'aarch64-apple-darwin';head[280:312]=bytes.fromhex(compiler['sha256']);head[312:344]=bytes.fromhex(sha(data))
 (HERE/f'build-preimage-{mode}.bin').write_bytes(bytes(head)+b''.join(parts))
 write(HERE/f'compiled-{mode}.json',{'binary':ident(binary),'context':context,'compile_argv':argv,'compile_environment':env,'build_preimage':ident(HERE/f'build-preimage-{mode}.bin')})
def test(mode,method,env=None,allow_failure=False):
 return run(mode+'-'+method.split('::')[-1],[WORK/f'unit-{mode}','--exact',method,'--nocapture','--test-threads=1'],env,allow_failure=allow_failure)
def measure(mode,host=False):
 if host:
  binary=WORK/f'host-{mode}.dylib';env=cleanenv()|{'MIXER_MEASURED_LIBRARY_SHA256':ident(binary)['sha256']}
  stdout,_,_=run('host-layout-'+mode,[sys.executable,__file__,'invoke',mode,'9'],env)
 else:
  test(mode,PREFIX+'complete_adoption_layout_inventory_v1')
  stdout,_,_=test(mode,INITIAL+'selected_layout_and_places',allow_failure=True)
 rows=[]
 for line in stdout.splitlines():
  if line.startswith('TYPE\t'):
   _,i,name,bytes_,alignment=line.split('\t');rows.append({'id':int(i),'name':name,'bytes':int(bytes_),'alignment':int(alignment)})
 values=next(line[line.index('VALUES '):]for line in stdout.splitlines()if 'VALUES ' in line)
 assert len(rows)==201 and [x['id']for x in rows]==list(range(1,202))
 write(HERE/'layouts'/f'{"production"if host else"unit"}-{mode}.json',{'source_tree_sha256':manifest(SOURCE)['tree_sha256'],'rows':rows,'values':{k:int(v)for k,v in [x.split('=')for x in values.split()[1:]]},'configuration':'production-host'if host else'unit','mode':mode})
def invoke(mode,method):
 import ctypes
 binary=WORK/f'host-{mode}.dylib';assert ident(binary)['sha256']==os.environ['MIXER_MEASURED_LIBRARY_SHA256']
 fn=ctypes.CDLL(str(binary)).mixer_initial_profile_component_host_v1;fn.argtypes=[ctypes.c_uint32];fn.restype=ctypes.c_uint32
 raise SystemExit(fn(int(method)))
def selected(mode,cases):
 binary=WORK/f'unit-{mode}';compiled=json.loads((HERE/f'compiled-{mode}.json').read_text());assert ident(binary)==compiled['binary'];assert manifest(SOURCE)==compiled['context']['distribution']
 fixture=WORK/f'fixture-{mode}.wasm';emit=cleanenv()|{'MIXER_LOADER_FIXTURE_OUTPUT':str(fixture)}
 if not fixture.exists():test(mode,PREFIX+'emit_genuine_validator_fixture',emit)
 sourcebytes=fixture.read_bytes();assert len(sourcebytes)==1947
 (HERE/'source-preimages').mkdir(exist_ok=True);(HERE/'source-preimages/genuine.wasm').write_bytes(sourcebytes)
 build=(HERE/f'build-preimage-{mode}.bin').read_bytes();observations=[]
 for case in cases:
  scenario='adopt-'+case;directory=WORK/f'{mode}-{scenario}';directory.mkdir()
  source=directory/'source.wasm';source.write_bytes(sourcebytes);buildfile=directory/'build.bin';buildfile.write_bytes(build);session=directory/'session.bin';outdir=directory/'profile';outdir.mkdir()
  argv=[str(binary),'--exact',PREFIX+'actual_selected_loader_child','--nocapture','--test-threads=1']
  env=cleanenv()|{'MIXER_LOADER_SOURCE_FILE':str(source),'MIXER_LOADER_BUILD_FILE':str(buildfile),'MIXER_LOADER_SESSION_FILE':str(session),'MIXER_LOADER_SCENARIO':scenario,'MIXER_INITIAL_PROFILE_EVIDENCE_DIR':str(outdir)}
  parts=[identity(source),packed(argv),envpacked(env),os.fsencode(REPO)];nonce=secrets.token_bytes(32);head=bytearray(512);head[:8]=b'MIXLSE01'
  for at,n in [(8,1),(16,512),(24,512+sum(map(len,parts))),(32,len(sourcebytes))]:struct.pack_into('<Q',head,at,n)
  for i,p in enumerate(parts):struct.pack_into('<Q',head,40+8*i,len(p));head[240+32*i:272+32*i]=bytes.fromhex(sha(p))
  for i,n in enumerate([67108864,16777216,1048576,512000000,120000]):struct.pack_into('<Q',head,72+8*i,n)
  head[112:144]=nonce;head[144:176]=bytes.fromhex(sha(sourcebytes));head[176:208]=bytes.fromhex(sha(build));head[208:240]=bytes.fromhex(ident(binary)['sha256']);data=bytes(head)+b''.join(parts);session.write_bytes(data)
  env['MIXER_LOADER_EXPECTED_SESSION_SHA256']=sha(data);env['MIXER_LOADER_EXPECTED_NONCE_HEX']=nonce.hex()
  (HERE/'sessions').mkdir(exist_ok=True);retained=HERE/'sessions'/f'{mode}-{scenario}.bin';retained.write_bytes(data)
  stdout,_,_=run(mode+'-'+scenario,argv,env);assert 'SELECTED_OUTCOME\t'+case in stdout
  observations.append({'case':case,'mode':mode,'session':ident(retained),'source_identity_hex':parts[0].hex(),'source_sha256':sha(sourcebytes),'build_sha256':sha(build),'producer_binary':compiled['binary'],'argv':argv,'environment':env,'cwd':str(REPO),'nonce_from_OS_randomness_hex':nonce.hex(),'Files_dropped_is_close_success':False})
  shutil.rmtree(directory)
 previous=HERE/f'selected-observations-{mode}.json';old=json.loads(previous.read_text())if previous.exists()else[];write(previous,old+observations)
def main():
 command=sys.argv[1];mode=sys.argv[2]if len(sys.argv)>2 else'debug'
 if command=='compile':compile(mode)
 elif command=='compile-host':compile(mode,True)
 elif command=='measure':measure(mode)
 elif command=='measure-host':measure(mode,True)
 elif command=='invoke':invoke(mode,sys.argv[3])
 elif command=='selected':selected(mode,sys.argv[3:])
 elif command=='test':
  for method in sys.argv[3:]:test(mode,method)
 elif command=='helpers':
  directory=WORK/f'helpers-{mode}';directory.mkdir();env=cleanenv()|{'MIXER_LOADER_HELPER_DIR':str(directory)}
  run(mode+'-loader-helpers',[WORK/f'unit-{mode}',PREFIX,'--skip','actual_selected_loader_child','--nocapture','--test-threads=1'],env);shutil.rmtree(directory)
 else:raise AssertionError(command)
if __name__=='__main__':
 try:main()
 except Exception:
  import traceback
  failures=HERE/'runner-failures';failures.mkdir(exist_ok=True)
  (failures/f'{len(list(failures.iterdir()))+1:03d}.stderr').write_text(traceback.format_exc())
  raise

