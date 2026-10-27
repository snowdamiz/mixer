from pathlib import Path
import datetime, hashlib, importlib.util, json, os, re, secrets, shutil, struct, subprocess, sys, time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
CANDIDATE=REPO/'verification/swift-guarded-snapshot-encoder-implementation'
PRE=HERE.parent
SOURCE=HERE/'source/vm'
SUPPORT=HERE/'support'
WORK=HERE/'work'
RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
FEATURES=('experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache')
METHOD='experimental_swift_reactor::cache::initial_profile_v1::tests::snapshot_encoder_host::independent_encoder_review'
KEYS=('MIXER_LOADER_MANIFEST_SHA256','MIXER_LOADER_COMMAND_SHA256','MIXER_LOADER_COMPILE_ENV_SHA256','MIXER_LOADER_COMPILER_SHA256','MIXER_LOADER_COMPILER_VERSION_SHA256')
def sha(data):return hashlib.sha256(data).hexdigest()
def save(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
def desc(path):return {'path':str(path),'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())}
def manifest(path):
 members=[{'path':str(p.relative_to(path)),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}for p in sorted(path.rglob('*'))if p.is_file()]
 return {'members':members,'member_count':len(members),'tree_sha256':sha(json.dumps(members,sort_keys=True,separators=(',',':')).encode())}
def env():return {'PATH':'/usr/bin:/bin','TMPDIR':str(WORK),'CARGO_MANIFEST_DIR':str(SOURCE)}
def run(name,args,environment=None,allowed=None):
 folder=HERE/'commands'/name;folder.mkdir(parents=True,exist_ok=False);started=time.monotonic();e=env()if environment is None else environment
 with(folder/'stdout').open('wb')as out,(folder/'stderr').open('wb')as err:
  child=subprocess.Popen(list(map(str,args)),cwd=REPO,env=e,stdout=out,stderr=err)
  try:code=child.wait(timeout=55)
  except subprocess.TimeoutExpired:child.kill();child.wait();code=124
 output=(folder/'stdout').read_text(errors='replace');errors=(folder/'stderr').read_text(errors='replace');codes=set(re.findall(r'error\[(E\d+)\]',errors))
 okay=code==0 if allowed is None else code not in(0,124)and bool(codes)and codes<=set(allowed)
 receipt={'argv':list(map(str,args)),'cwd':str(REPO),'environment':e,'exit':code,'allowed_diagnostics':allowed,'diagnostics':sorted(codes),'passed':okay,'child_reaped':True,'elapsed_seconds':time.monotonic()-started,'stdout':desc(folder/'stdout'),'stderr':desc(folder/'stderr')}
 save(folder/'receipt.json',receipt);print(name+': '+('pass'if okay else'FAIL'),flush=True)
 if not okay:raise AssertionError(errors[-5000:]+output[-1500:])
 return output
def packed(items):
 items=[os.fsencode(x)for x in items];return struct.pack('<Q',len(items))+b''.join(struct.pack('<Q',len(x))+x for x in items)
def envpacked(items):return packed([os.fsencode(k)+b'='+os.fsencode(v)for k,v in sorted(items.items())])
def identity(path):
 s=path.stat();return struct.pack('<QQQQqqqq',s.st_dev,s.st_ino,s.st_size,s.st_mode,s.st_mtime_ns//10**9,s.st_mtime_ns%10**9,s.st_ctime_ns//10**9,s.st_ctime_ns%10**9)
def custody():
 pins=[(REPO/'verification/swift-semantic-adapter-root-review/guarded-snapshot-encoder-independent-release.json','c890fe98abc7b6a2a5ef4a33a9fd87f129c5c1433180a8a0120bf444141c6d76'),(CANDIDATE/'seal.json','eadbe533d23459573ead21c7a9bac54ae929b98cdbc76dd47aebe34b5ceb2b1f'),(PRE/'preaccess-seal.json','c0f8b4987c32a8416aea0d16cbec183498a51b2588a26b13ad3efd8697eb0780')]
 for p,h in pins:assert sha(p.read_bytes())==h
 for directory,sealname in[(CANDIDATE,'seal.json'),(PRE,'preaccess-seal.json')]:
  seal=json.loads((directory/sealname).read_text())
  for item in seal['members']:
   p=directory/item['path'];assert p.stat().st_size==item['bytes']and sha(p.read_bytes())==item['sha256'],str(p)
  assert sha(json.dumps(seal['members'],sort_keys=True,separators=(',',':')).encode())==seal['tree_sha256']
 save(HERE/'custody.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pins':[desc(p)for p,h in pins],'candidate_members':1256,'candidate_bytes':150237357,'preaccess_members':18,'verified':True})
def prepare():
 custody();assert not SOURCE.exists();shutil.copytree(CANDIDATE/'source/vm',SOURCE);shutil.copytree(CANDIDATE/'host',SUPPORT);WORK.mkdir()
 # Keep exactly eleven actual support members. Replaced observer/supervisor/oracle
 # members are real evidence inputs, and all are hashed in each new preimage.
 shutil.copyfile(__file__,SUPPORT/'runner.py');shutil.copyfile(HERE/'host_observer.rs',SUPPORT/'host.rs');shutil.copyfile(PRE/'wire_oracle.py',SUPPORT/'oracle.py')
 p=SOURCE/'src/experimental_swift_reactor/cache/initial_profile_v1/tests.rs';s=p.read_text();marker='#[cfg(any(test,mixer_snapshot_encoder_host))]\npub(super) mod snapshot_encoder_host {';assert s.count(marker)==1;p.write_text(s.split(marker)[0]+marker+'\n'+(HERE/'host_observer.rs').read_text()+'\n}\n')
 p=SOURCE/'src/experimental/swift.rs';p.write_text(p.read_text()+'\n'+(HERE/'observe_fields.rs').read_text())
 p=SOURCE/'src/experimental/account.rs';p.write_text(p.read_text()+'''\n#[cfg(any(test,mixer_snapshot_encoder_host))]impl<T:Copy> Buffer<T>{pub(super)fn independent_inventory(&self)->(usize,usize,usize,usize,Resource){(self.values.len(),self.values.capacity(),std::mem::size_of::<T>(),self.charged,self.category)}}\n''')
 p=SOURCE/'src/experimental_wasi/accounted.rs';p.write_text(p.read_text()+'''\n#[cfg(any(test,mixer_snapshot_encoder_host))]impl AccountedWasi{pub(crate)fn independent_configuration(&self)->(WasiBudget,WasiGrants){(self.context.budget,self.context.grants)}}\n''')
 p=SOURCE/'src/experimental_swift_reactor/retained_profile_loader_v1.rs';p.write_text(p.read_text()+'''\n#[cfg(any(test,mixer_snapshot_encoder_host))]impl LoaderProvenanceV1{pub(crate)fn independent_provenance_fields(&self)->String{
 let b=&self.validation_budget;let limits=[b.source_bytes as u64,b.metadata_bytes as u64,b.scratch_bytes as u64,b.work_credits,b.deadline_ms];
 let values:Vec<String>=[&self.source,&self.manifest,&self.build,&self.session,&self.executable,&self.nonce].iter().map(|v|format!("\\\"{}\\\"",v.iter().map(|b|format!("{b:02x}")).collect::<String>())).collect();
 let ids:Vec<String>=self.identities.iter().map(|v|format!("[{},{},{},{},{},{},{},{}]",v.dev,v.inode,v.bytes,v.mode,v.mtime,v.mtime_ns,v.ctime,v.ctime_ns)).collect();
 format!("\\\"provenance_extent\\\":{},\\\"validation_limits\\\":{:?},\\\"provenance_limits\\\":{:?},\\\"retained_values\\\":[{}],\\\"identities\\\":[{}]",self.source_extent,limits,limits,values.join(","),ids.join(","))}}
''')
 assert manifest(SOURCE)['member_count']==144 and manifest(SUPPORT)['member_count']==11
 save(HERE/'independent-source-manifest.json',manifest(SOURCE));save(HERE/'independent-support-manifest.json',manifest(SUPPORT))
def flags(mode):return [RUSTC,'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','opt-level='+('0'if mode=='debug'else'3'),'-C','overflow-checks=yes','-C','panic=unwind']+sum((['--cfg','feature="'+f+'"']for f in FEATURES),[])
def compile_(kind,mode):
 version=run(kind+'-'+mode+'-version',[RUSTC,'-vV']);binary=WORK/(kind+'-'+mode)
 args=flags(mode)+(['--test']if kind=='unit'else['--crate-type','bin','--cfg','mixer_initial_profile_component_host','--cfg','mixer_snapshot_encoder_host'])+[SOURCE/'src/lib.rs','-o',binary]
 context={'source':manifest(SOURCE),'support':manifest(SUPPORT),'candidate_seal':desc(CANDIDATE/'seal.json'),'compiler':desc(RUSTC),'observer':desc(HERE/'observe_fields.rs'),'preaccess_oracle':desc(PRE/'wire_oracle.py')}
 parts=[json.dumps(context,sort_keys=True,separators=(',',':')).encode(),packed(args),envpacked(env()),version.encode()];assert len(parts[0])<=65536
 e=env()|dict(zip(KEYS,[sha(parts[0]),sha(parts[1]),sha(parts[2]),sha(RUSTC.read_bytes()),sha(parts[3])]))
 run(kind+'-'+mode+'-compile',args,e);head=bytearray(512);head[:8]=b'MIXLBD01'
 for at,n in[(8,1),(16,512),(24,512+sum(map(len,parts))),(32,144),(40,11),(80,binary.stat().st_size)]:struct.pack_into('<Q',head,at,n)
 for i,p in enumerate(parts):struct.pack_into('<Q',head,48+i*8,len(p));head[152+i*32:184+i*32]=bytes.fromhex(sha(p))
 head[88:108]=b'aarch64-apple-darwin';head[280:312]=bytes.fromhex(sha(RUSTC.read_bytes()));head[312:344]=bytes.fromhex(sha(binary.read_bytes()))
 build=HERE/'builds'/(kind+'-'+mode+'.build');build.parent.mkdir(exist_ok=True);build.write_bytes(bytes(head)+b''.join(parts));save(build.with_suffix('.json'),{'binary':desc(binary),'build':desc(build),'context':context})
def childargs(kind,mode):return [WORK/(kind+'-'+mode)]+(['--exact',METHOD,'--nocapture','--test-threads=1']if kind=='unit'else[])
def oracle(directory):
 spec=importlib.util.spec_from_file_location('frozen_independent_oracle',PRE/'wire_oracle.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 observed=json.loads((directory/'observed.json').read_text());observed['source']=bytes.fromhex(observed['source']);observed['retained_values']=[bytes.fromhex(v)for v in observed['retained_values']];observed['identities']=[tuple(v)for v in observed['identities']]
 observed['capacities']=[v[1]for v in observed['inventories']]
 types={'I32':1,'I64':2,'F32':3,'F64':4,'None':0};types|={'Some('+k+')':v for k,v in list(types.items())if k!='None'}
 for row in observed['sections'][0]:row[2]=types[row[2]]
 for row in observed['sections'][1]:row[0]=types[row[0]]
 for row in observed['sections'][4]:row[0]=types[row[0]]
 observed['resolved']=tuple(m.WASI_IDS.index(v)+1 for v in observed.pop('resolved_names'))
 assert observed['policy']=='swift-reactor-experiment-v1'
 image=(directory/'actual.mixsnb02').read_bytes();result=m.compare_actual(image,observed)
 for index,inventory in enumerate(observed['inventories'],1):
  d=m.words(image,1600+64*index,8);assert list(d[1:5])==inventory[:4]and inventory[4]=='Metadata'
 assert observed['source']==(directory/'source.wasm').read_bytes()
 context=json.loads((directory/'context.json').read_text());values=[sha((directory/'source.wasm').read_bytes()),context['manifest_sha256'],sha((directory/'build.bin').read_bytes()),sha((directory/'session.bin').read_bytes()),context['executable_sha256'],context['nonce_hex']]
 assert [v.hex()for v in observed['retained_values']]==values
 assert observed['identities']==[tuple(struct.unpack('<QQQQqqqq',bytes.fromhex(context[key])))for key in('source_identity','build_identity','session_identity','executable_identity')]
 save(directory/'comparison.json',{'status':'fresh-genuine-independent-byte-semantic-custody-match','bytes':len(image),'image_sha256':sha(image),'counts':result['counts'],'blocks':result['blocks'],'inventories':observed['inventories'],'wasi':observed['runtime']['wasi']})
def selected(kind,mode,fixture,wasi):
 directory=HERE/'runs'/f'{kind}-{mode}-{fixture}-{wasi}';directory.mkdir(parents=True)
 original=CANDIDATE/'runs'/'host-debug-selected-baseline-none'/'source.wasm'if fixture=='baseline'else CANDIDATE/'runs'/'host-debug-selected-segments-none'/'source.wasm'
 source=directory/'source.wasm';source.write_bytes(original.read_bytes());build=directory/'build.bin';build.write_bytes((HERE/'builds'/(kind+'-'+mode+'.build')).read_bytes());session=directory/'session.bin';args=childargs(kind,mode)
 e=env()|{'MIXER_REVIEW_DIR':str(directory),'MIXER_REVIEW_ACTION':'selected','MIXER_REVIEW_WASI':wasi}
 parts=[identity(source),packed(args),envpacked(e),os.fsencode(REPO)];nonce=secrets.token_bytes(32);head=bytearray(512);head[:8]=b'MIXLSE01'
 for at,n in[(8,1),(16,512),(24,512+sum(map(len,parts))),(32,source.stat().st_size)]:struct.pack_into('<Q',head,at,n)
 for i,p in enumerate(parts):struct.pack_into('<Q',head,40+i*8,len(p));head[240+i*32:272+i*32]=bytes.fromhex(sha(p))
 for i,n in enumerate((67108864,16777216,1048576,512000000,120000)):struct.pack_into('<Q',head,72+i*8,n)
 executable=WORK/(kind+'-'+mode);head[112:144]=nonce;head[144:176]=bytes.fromhex(sha(source.read_bytes()));head[176:208]=bytes.fromhex(sha(build.read_bytes()));head[208:240]=bytes.fromhex(sha(executable.read_bytes()));session.write_bytes(bytes(head)+b''.join(parts))
 e|={'MIXER_LOADER_EXPECTED_SESSION_SHA256':sha(session.read_bytes()),'MIXER_LOADER_EXPECTED_NONCE_HEX':nonce.hex()}
 compiled=json.loads((HERE/'builds'/(kind+'-'+mode+'.json')).read_text());assert desc(executable)==compiled['binary']
 context={'source_identity':identity(source).hex(),'build_identity':identity(build).hex(),'session_identity':identity(session).hex(),'executable_identity':identity(executable).hex(),'manifest_sha256':sha(build.read_bytes()[512:512+struct.unpack_from('<Q',build.read_bytes(),48)[0]]),'executable_sha256':sha(executable.read_bytes()),'nonce_hex':nonce.hex()}
 save(directory/'context.json',context);run(directory.name,args,e);oracle(directory)
def ordinary(kind,mode):
 directory=HERE/'runs'/f'{kind}-{mode}-ordinary';directory.mkdir(parents=True);run(directory.name,childargs(kind,mode),env()|{'MIXER_REVIEW_DIR':str(directory),'MIXER_REVIEW_ACTION':'ordinary','MIXER_REVIEW_WASI':'none'})
def layouts(kind,mode):
 text=run(kind+'-'+mode+'-layouts',childargs(kind,mode),env()|{'MIXER_REVIEW_ACTION':'layouts'})
 rows=[{'name':' '.join(n.split()),'bytes':int(b),'alignment':int(a)}for n,b,a in re.findall(r'INDEPENDENT_LAYOUT\t(.*?)\t(\d+)\t(\d+)',text,re.S)];assert len(rows)==52;save(HERE/'layouts'/f'{kind}-{mode}.json',rows)
if __name__=='__main__':
 action=sys.argv[1]
 if action=='prepare':prepare()
 elif action=='compile':compile_(*sys.argv[2:])
 elif action=='selected':selected(*sys.argv[2:])
 elif action=='ordinary':ordinary(*sys.argv[2:])
 elif action=='layouts':layouts(*sys.argv[2:])
 elif action=='custody':custody()
 else:raise ValueError(action)
