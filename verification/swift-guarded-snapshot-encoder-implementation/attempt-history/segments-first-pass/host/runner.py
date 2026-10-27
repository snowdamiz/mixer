#!/usr/bin/env python3
"""Fresh bounded host supervisor. No frozen orchestration is imported/executed."""
from pathlib import Path
import datetime,hashlib,importlib.util,json,os,re,secrets,shutil,struct,subprocess,sys,time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;OUT=HERE.parent;REPO=OUT.parents[1]
SOURCE=OUT/'source/vm';BASE=OUT.parent/'swift-guarded-snapshot-export-preparation/inputs/accepted-source/vm'
WORK=OUT/'owned-work';WORK.mkdir(exist_ok=True)
RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
FEATURES=['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']
METHOD='experimental_swift_reactor::cache::initial_profile_v1::tests::snapshot_encoder_host::actual_encoder_child_v2'
IDENTITIES=['MIXER_LOADER_MANIFEST_SHA256','MIXER_LOADER_COMMAND_SHA256','MIXER_LOADER_COMPILE_ENV_SHA256','MIXER_LOADER_COMPILER_SHA256','MIXER_LOADER_COMPILER_VERSION_SHA256']
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def description(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def manifest(p):
 members=[{'path':str(f.relative_to(p)),'bytes':f.stat().st_size,'sha256':sha(f.read_bytes())}for f in sorted(p.rglob('*'))if f.is_file()]
 return {'members':members,'member_count':len(members),'tree_sha256':sha(json.dumps(members,sort_keys=True,separators=(',',':')).encode())}
def packed(v):
 b=[os.fsencode(x)for x in v];return struct.pack('<Q',len(b))+b''.join(struct.pack('<Q',len(x))+x for x in b)
def envpacked(v):return packed([os.fsencode(k)+b'='+os.fsencode(v)for k,v in sorted(v.items())])
def identity(p):
 s=Path(p).stat();return struct.pack('<QQQQqqqq',s.st_dev,s.st_ino,s.st_size,s.st_mode,s.st_mtime_ns//10**9,s.st_mtime_ns%10**9,s.st_ctime_ns//10**9,s.st_ctime_ns%10**9)
def cleanenv():return {'PATH':'/usr/bin:/bin','TMPDIR':str(WORK),'CARGO_MANIFEST_DIR':str(SOURCE)}
def run(label,argv,env=None,allowed=None,cwd=REPO):
 env=cleanenv()if env is None else env;log=OUT/'commands';log.mkdir(exist_ok=True)
 folder=log/f'{len(list(log.iterdir()))+1:04d}-{label}';folder.mkdir();started=time.monotonic();killed=None
 with(folder/'stdout').open('wb')as stdout,(folder/'stderr').open('wb')as stderr:
  child=subprocess.Popen([str(x)for x in argv],cwd=cwd,env=env,stdout=stdout,stderr=stderr)
  while True:
   try:code=child.wait(timeout=.05);break
   except subprocess.TimeoutExpired:
    if time.monotonic()-started>55:killed='55-second limit'
    if (folder/'stdout').stat().st_size+(folder/'stderr').stat().st_size>1048576:killed='1MiB output limit'
    if killed:child.kill();child.wait();code=124;break
 text=(folder/'stdout').read_text(errors='replace');err=(folder/'stderr').read_text(errors='replace');codes=set(re.findall(r'error\[(E\d+)\]',err))
 passed=code==0 if allowed is None else code!=0 and bool(codes) and codes<=set(allowed)
 receipt={'label':label,'argv':list(map(str,argv)),'cwd':str(cwd),'environment':env,'exit_code':code,'expectation_met':passed,
 'allowed_diagnostics':allowed,'actual_diagnostics':sorted(codes),'timeout_seconds':55,'output_byte_cap':1048576,'killed':killed,
 'child_reaped':True,'elapsed_seconds':time.monotonic()-started,'source':manifest(SOURCE)if SOURCE.exists()else None,
 'host_support':manifest(HERE),'runner':description(__file__),'artifact':description(argv[0])if Path(str(argv[0])).is_file()else None,
 'stdout':description(folder/'stdout'),'stderr':description(folder/'stderr')}
 save(folder/'receipt.json',receipt);print(label+(': pass'if passed else': FAILED'),flush=True)
 if not passed:raise AssertionError((label,text[-1500:],err[-5000:]))
 return text,receipt
def flags(mode):
 return [RUSTC,'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','opt-level='+('0'if mode=='debug'else'3'),'-C','overflow-checks=yes','-C','panic=unwind']+sum((['--cfg','feature="'+f+'"']for f in FEATURES),[])
def closure():
 baseline=manifest(BASE);assert baseline['member_count']==144 and baseline['tree_sha256']=='9fbdabbc5122f71809483b3b0a0e95a71b9813def61572f366bcebc8ac6d08fb'
 source=manifest(SOURCE);support=manifest(HERE);assert source['member_count']==144 and support['member_count']==11
 return {'schema':1,'source':source,'support':support,'baseline':baseline,'root_selection':description(REPO/'verification/swift-semantic-adapter-root-review/guarded-snapshot-encoder-component-selection.json')}
def compile_(kind,mode):
 context=closure();version,_=run('rustc-version',[RUSTC,'-vV']);revision,_=run('source-revision',['git','rev-parse','HEAD'])
 binary=WORK/f'{kind}-{mode}'
 argv=flags(mode)+(['--test']if kind=='unit'else['--crate-type','bin','--cfg','mixer_initial_profile_component_host','--cfg','mixer_snapshot_encoder_host'])+[SOURCE/'src/lib.rs','-o',binary]
 context|={'compiler':description(RUSTC),'python':description(Path(sys.executable).resolve()),'rustc_version':version,'source_revision_context':revision.strip()}
 parts=[json.dumps(context,sort_keys=True,separators=(',',':')).encode(),packed(argv),envpacked(cleanenv()),version.encode()]
 assert len(parts[0])<=65536
 env=cleanenv()|dict(zip(IDENTITIES,[sha(parts[0]),sha(parts[1]),sha(parts[2]),sha(RUSTC.read_bytes()),sha(parts[3])]))
 run('compile-'+kind+'-'+mode,argv,env)
 b=binary.read_bytes();head=bytearray(512);head[:8]=b'MIXLBD01'
 for at,n in [(8,1),(16,512),(24,512+sum(map(len,parts))),(32,144),(40,11),(80,len(b))]:struct.pack_into('<Q',head,at,n)
 for i,p in enumerate(parts):struct.pack_into('<Q',head,48+8*i,len(p));head[152+i*32:184+i*32]=bytes.fromhex(sha(p))
 head[88:108]=b'aarch64-apple-darwin';head[280:312]=bytes.fromhex(sha(RUSTC.read_bytes()));head[312:344]=bytes.fromhex(sha(b))
 build=OUT/'preimages'/f'{kind}-{mode}.build';build.parent.mkdir(exist_ok=True);build.write_bytes(bytes(head)+b''.join(parts))
 save(OUT/'compiled'/f'{kind}-{mode}.json',{'context':context,'binary':description(binary),'build':description(build),'manifest_sha256':sha(parts[0]),'compile_argv':list(map(str,argv)),'compile_environment':env})
def childargv(kind,mode):return [WORK/f'{kind}-{mode}']+(['--exact',METHOD,'--nocapture','--test-threads=1']if kind=='unit'else[])
def simple(kind,mode,action,fixture='baseline'):
 directory=OUT/'runs'/f'{kind}-{mode}-{action}-{fixture}';directory.mkdir(parents=True)
 env=cleanenv()|{'MIXER_ENCODER_ACTION':action,'MIXER_ENCODER_DIR':str(directory),'MIXER_ENCODER_FIXTURE':fixture}
 text,receipt=run(f'{kind}-{mode}-{action}-{fixture}',childargv(kind,mode),env)
 if action=='layouts':
  rows=[]
  for line in text.splitlines():
   if 'ENCODER_LAYOUT\t' in line:
    _,name,bytes_,alignment=line[line.index('ENCODER_LAYOUT\t'):].split('\t');rows.append({'name':name,'bytes':int(bytes_),'alignment':int(alignment)})
  assert len(rows)==47;save(OUT/'layouts'/f'{kind}-{mode}.json',{'rows':rows,'receipt':receipt})
 return directory
def selected(kind,mode,fixture,wasi='none'):
 fixturepath=OUT/'runs'/f'{kind}-{mode}-emit-{fixture}'/'fixture.wasm'
 if not fixturepath.exists():simple(kind,mode,'emit',fixture)
 directory=OUT/'runs'/f'{kind}-{mode}-selected-{fixture}-{wasi}';directory.mkdir(parents=True)
 source=directory/'source.wasm';source.write_bytes(fixturepath.read_bytes());build=directory/'build.bin';compiled=json.loads((OUT/'compiled'/f'{kind}-{mode}.json').read_text())
 assert description(WORK/f'{kind}-{mode}')==compiled['binary'];assert closure()['source']==compiled['context']['source'];assert closure()['support']==compiled['context']['support']
 build.write_bytes(Path(compiled['build']['path']).read_bytes());session=directory/'session.bin';argv=childargv(kind,mode)
 env=cleanenv()|{'MIXER_ENCODER_ACTION':'selected','MIXER_ENCODER_DIR':str(directory),'MIXER_ENCODER_FIXTURE':fixture,'MIXER_ENCODER_WASI':wasi}
 parts=[identity(source),packed(argv),envpacked(env),os.fsencode(REPO)];nonce=secrets.token_bytes(32);head=bytearray(512);head[:8]=b'MIXLSE01'
 for at,n in [(8,1),(16,512),(24,512+sum(map(len,parts))),(32,source.stat().st_size)]:struct.pack_into('<Q',head,at,n)
 for i,p in enumerate(parts):struct.pack_into('<Q',head,40+i*8,len(p));head[240+i*32:272+i*32]=bytes.fromhex(sha(p))
 for i,n in enumerate([67108864,16777216,1048576,512000000,120000]):struct.pack_into('<Q',head,72+i*8,n)
 head[112:144]=nonce;head[144:176]=bytes.fromhex(sha(source.read_bytes()));head[176:208]=bytes.fromhex(sha(build.read_bytes()));head[208:240]=bytes.fromhex(compiled['binary']['sha256'])
 session.write_bytes(bytes(head)+b''.join(parts));env|={'MIXER_LOADER_EXPECTED_SESSION_SHA256':sha(session.read_bytes()),'MIXER_LOADER_EXPECTED_NONCE_HEX':nonce.hex()}
 context={'source_identity_hex':identity(source).hex(),'build_identity_hex':identity(build).hex(),'session_identity_hex':identity(session).hex(),'executable_identity_hex':identity(WORK/f'{kind}-{mode}').hex(),'nonce_hex':nonce.hex(),'manifest_sha256':compiled['manifest_sha256'],'executable_sha256':compiled['binary']['sha256']}
 save(directory/'context.json',context);run(f'{kind}-{mode}-selected-{fixture}',argv,env)
 import oracle
 comparison=oracle.build(directory,context)
 spec=importlib.util.spec_from_file_location('corrected_wire_model',REPO/'verification/swift-guarded-snapshot-export-contract-correction/format_model.py');model=importlib.util.module_from_spec(spec);spec.loader.exec_module(model)
 parsed=model.parse((directory/'actual.mixsnb02').read_bytes());assert parsed['total']==comparison['bytes']
 save(directory/'oracle-comparison.json',comparison);print('independent exact byte oracle: pass',flush=True)
def privacy(mode):
 path=WORK/f'privacy-{mode}';shutil.copytree(SOURCE,path)
 base=(path/'src/lib.rs').read_text();api='crate::experimental::swift::snapshot_encoder_v2';guard='crate::experimental_swift_reactor::InitialProfileBorrowV1'
 cases={
 'positive':(None,f"fn check(g:&{guard}<'_>){{let v={api}::borrow_snapshot_v2(g).unwrap();let mut c=v.into_cursor().unwrap();let mut b=[0u8;4096];let _=c.next_block(&mut b);}}"),
 'raw-proof':(['E0308'],f"fn check(g:&crate::experimental_swift_reactor::ValidatedSwiftReactor){{let _={api}::borrow_snapshot_v2(g);}}"),
 'foreign-source':(['E0061'],f"fn check(g:&{guard}<'_>,p:&[u8]){{let _={api}::borrow_snapshot_v2(g,p);}}"),
 'digest':(['E0308'],f"fn check(){{let _={api}::borrow_snapshot_v2(&[0u8;32]);}}"),
 'bool':(['E0308'],f"fn check(){{let _={api}::borrow_snapshot_v2(&true);}}"),
 'callback':(['E0061'],f"fn check(g:&{guard}<'_>){{let _={api}::borrow_snapshot_v2(g,|_:&[u8]|{{}});}}"),
 'guard-literal':(['E0451'],f"fn check(){{let _={guard}{{}};}}"),
 'guard-clone':(['E0599'],f"fn check(g:{guard}<'_>){{let _=g.clone();}}"),
 'view-literal':(['E0451'],f"fn check(){{let _={api}::SnapshotViewV2{{}};}}"),
 'cursor-literal':(['E0451'],f"fn check(){{let _={api}::SnapshotCursorV2{{}};}}"),
 'cursor-clone':(['E0599'],f"fn check(c:{api}::SnapshotCursorV2<'_>){{let _=c.clone();}}"),
 'block-literal':(['E0451'],f"fn check(){{let _={api}::SnapshotBlockV2{{}};}}"),
 'guard-move':(['E0505'],f"fn check(g:{guard}<'_>){{let v={api}::borrow_snapshot_v2(&g).unwrap();drop(g);let _=v.into_cursor();}}"),
 'guard-escape':(['E0515'],f"fn check<'a>(g:{guard}<'a>)->{api}::SnapshotCursorV2<'a>{{{api}::borrow_snapshot_v2(&g).unwrap().into_cursor().unwrap()}}"),
 'source-mutation':(['E0594'],f"fn check(g:&{guard}<'_>){{g.snapshot_proof_v2().source()[0]=1;}}"),
 'transfer-reborrow':(['E0499'],f"fn check(c:&mut {api}::SnapshotCursorV2<'_>){{let mut b=[0u8;4096];let first=c.next_block(&mut b).unwrap().unwrap();let _=c.next_block(&mut b);let _=first.bytes();}}"),
 }
 results=[]
 try:
  for name,(allowed,source)in cases.items():
   (path/'src/lib.rs').write_text(base+'\nmod encoder_privacy_probe{'+source+'}\n')
   _,receipt=run(mode+'-privacy-'+name,flags(mode)+['--crate-type','rlib','--emit=metadata',path/'src/lib.rs','-o',WORK/'privacy.rmeta'],cleanenv()|{'CARGO_MANIFEST_DIR':str(path)},allowed)
   receipt['probe_source']=source;results.append(receipt)
 finally:
  shutil.rmtree(path)
  (WORK/'privacy.rmeta').unlink(missing_ok=True)
 save(OUT/'privacy'/f'{mode}.json',results)
def ordinary(mode):
 run('ordinary-production-'+mode,flags(mode)+['--crate-type','rlib','--emit=metadata',SOURCE/'src/lib.rs','-o',WORK/f'ordinary-{mode}.rmeta'])
 run('unit-enums-'+mode,[WORK/f'unit-{mode}','--exact','experimental::swift::snapshot_encoder_v2::encoder_unit::finite_enum_and_option_mappings_v2','--nocapture','--test-threads=1'])
def main():
 command=sys.argv[1]
 if command=='prepare':
  run('prepare-source',[sys.executable,'-B',HERE/'implement.py']);save(OUT/'input-custody-before.json',closure())
 elif command=='compile':compile_(sys.argv[2],sys.argv[3])
 elif command=='simple':simple(*sys.argv[2:])
 elif command=='selected':selected(*sys.argv[2:])
 elif command=='privacy':privacy(sys.argv[2])
 elif command=='ordinary':ordinary(sys.argv[2])
 else:raise AssertionError(command)
if __name__=='__main__':
 try:main()
 except Exception:
  import traceback
  failures=OUT/'runner-failures';failures.mkdir(exist_ok=True);(failures/f'{len(list(failures.iterdir()))+1:03d}.stderr').write_text(traceback.format_exc());raise
