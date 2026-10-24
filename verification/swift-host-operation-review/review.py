#!/usr/bin/env python3
from pathlib import Path
import datetime,gzip,hashlib,json,os,shutil,subprocess,sys,tarfile,uuid
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PACKET=ROOT/'verification/swift-host-operation'
sha=lambda b:hashlib.sha256(b).hexdigest()
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def save(n,x):
 p=HERE/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(enc(x))
def load(n):return json.loads((HERE/n).read_text())
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def manifest(p):return {str(x.relative_to(p)):sha(x.read_bytes())for x in sorted(p.rglob('*'))if x.is_file()and not any(z in ['target','.git'] for z in x.relative_to(p).parts)}
def tree(p):return sha(enc(manifest(p)))
def scratch():return Path(load('session.json')['scratch'])
def command(name,argv,cwd=None,env_extra=None,expect=0,source=None,timeout=600):
 d=HERE/'commands'/name;d.mkdir(parents=True,exist_ok=False)
 env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'])
 for k in ['RUSTFLAGS','RUSTC_BOOTSTRAP','CARGO_ENCODED_RUSTFLAGS','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_BUILD_RUSTFLAGS']:env.pop(k,None)
 env.update(env_extra or {});before=tree(source)if source else None;start=now();timed=False
 try:p=subprocess.run(argv,cwd=cwd or ROOT,env=env,stdin=subprocess.DEVNULL,capture_output=True,timeout=timeout)
 except subprocess.TimeoutExpired as e:
  timed=True;p=type('P',(),dict(returncode=-1,stdout=e.stdout or b'',stderr=e.stderr or b''))()
 for n in ['stdout','stderr']:
  with gzip.open(d/(n+'.gz'),'wb')as z:z.write(getattr(p,n))
 r=dict(argv=argv,cwd=str(cwd or ROOT),startedUTC=start,completedUTC=now(),exitCode=p.returncode,expectedExitCode=expect,timedOut=timed,sourceBefore=before,sourceAfter=tree(source)if source else None,stdoutSHA256=sha(p.stdout),stderrSHA256=sha(p.stderr),environment={k:env[k]for k in ['PATH','CARGO_TARGET_DIR','RUSTC_BOOTSTRAP','RUSTFLAGS']if k in env})
 save('commands/'+name+'/receipt.json',r);print(name,p.returncode,flush=True)
 assert r['sourceBefore']==r['sourceAfter'],name
 assert p.returncode==expect,(name,p.stderr[-4000:]);return p,r

def setup():
 assert not(HERE/'session.json').exists();s=Path('/tmp/mixer-host-operation-review-'+str(uuid.uuid4()));s.mkdir();st=s.stat()
 save('session.json',dict(startedUTC=now(),scratch=str(s),device=st.st_dev,inode=st.st_ino,requestedRevision='11133e60551c46c9ea3aa4eac7356ea32d44fc72',environment='macOS aarch64 Rust host only; no native/device/process discovery'))
 for label,expected in [('baseline','a0bbe77aca3021e48f1fb76dc97cfbc0406c24e5ba7eacdd33d5dabe8f998d9b'),('candidate','7ee6194584a5029ff2bbbcb94f8286295411cb3441a04db30c8fd4036d851329')]:
  m=json.loads((PACKET/(label+'-source-manifest.json')).read_text());assert sha(enc(m))==expected
  shutil.copy2(PACKET/(label+'-source-manifest.json'),HERE/(label+'-source-manifest.json'));shutil.copy2(PACKET/(label+'-source.tar.gz'),HERE/(label+'-source.tar.gz'))
  dest=s/label;dest.mkdir();seen=set()
  with tarfile.open(HERE/(label+'-source.tar.gz'))as t:
   for member in t:
    assert member.isfile()and member.name in m and member.name not in seen and not Path(member.name).is_absolute()and '..'not in Path(member.name).parts
    seen.add(member.name);data=t.extractfile(member).read();assert sha(data)==m[member.name];p=dest/member.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
  assert seen==set(m)and manifest(dest)==m
 save('input-identity.json',dict(candidateFiles=len(manifest(s/'candidate')),candidateClosure=tree(s/'candidate'),candidateArchiveSHA256=sha((HERE/'candidate-source.tar.gz').read_bytes()),producerSealSHA256=sha((PACKET/'seal.json').read_bytes()),baselineFiles=len(manifest(s/'baseline')),baselineClosure=tree(s/'baseline')))
 for name,argv in [('rustc',['rustc','-Vv']),('cargo',['cargo','-V']),('python',['python3','--version'])]:command('tool-'+name,argv)
 command('producer-offline-verifier',['python3','-B',str(PACKET/'verify.py')],timeout=600)
 print(s,flush=True)
if __name__=='__main__':globals()[sys.argv[1]]()

def build_candidate():
 vm=scratch()/'candidate';target=scratch()/'target-exact-all-debug';assert not target.exists();target.mkdir()
 env={'CARGO_TARGET_DIR':str(target),'RUSTC_BOOTSTRAP':'1','RUSTFLAGS':'--emit=mir,link -Zmir-include-spans=yes'}
 p,r=command('exact-all-debug-build',['cargo','test','--lib','--no-run','--all-features','--offline','--locked','--message-format=json-render-diagnostics'],cwd=vm,env_extra=env,source=vm)
 artifacts=[json.loads(l)for l in p.stdout.decode().splitlines()if l.startswith('{')];a=[a for a in artifacts if a.get('reason')=='compiler-artifact'and a['target']['name']=='mixer_vm'and a['profile']['test']and a.get('executable')];assert len(a)==1 and not a[0]['fresh'];a=a[0];exe=Path(a['executable']);data=exe.read_bytes();d=HERE/'artifacts/exact-all-debug';d.mkdir(parents=True)
 with gzip.open(d/'executable.gz','wb')as z:z.write(data)
 save('artifacts/exact-all-debug/cargo-artifact.json',a)
 ls,_=command('exact-all-debug-list',[str(exe),'--list'],cwd=vm,env_extra=env,source=vm);tests=[l[:-6]for l in ls.stdout.decode().splitlines()if l.endswith(': test')];assert len(tests)==265
 save('artifacts/exact-all-debug/test-list.json',tests)
 save('artifacts/exact-all-debug/identity.json',dict(executableSHA256=sha(data),executableBytes=len(data),exactExecutablePath=str(exe),sourceClosure=tree(vm),targetInitiallyEmpty=True,fresh=a['fresh'],listedTests=len(tests)))
 ms=list(target.glob('debug/deps/*.mir'));assert len(ms)==1
 with gzip.open(HERE/'independent-unit.mir.gz','wb')as z:z.write(ms[0].read_bytes())
 command('exact-all-debug-host',[str(exe),'host_tests::h','--nocapture','--test-threads=1'],cwd=vm,env_extra=env,source=vm)
 assert sha(exe.read_bytes())==sha(data)
 command('exact-all-debug-full',[str(exe),'--test-threads=1'],cwd=vm,env_extra=env,source=vm)
 assert sha(exe.read_bytes())==sha(data)
 save('artifacts/exact-all-debug/after.json',dict(executableSHA256=sha(exe.read_bytes()),sourceClosure=tree(vm),passedHost=16,passedFull=265))

def adversarial():
 version="adversarial-v2"
 vm=scratch()/version;shutil.copytree(scratch()/'candidate',vm);file=vm/'src/experimental_swift_reactor/host_operation_tests.rs';file.write_bytes(file.read_bytes()+b'\n'+(HERE/'adversarial-tests.rs').read_bytes());m=manifest(vm);save((version+'-source-manifest.json'),m)
 with tarfile.open(HERE/(version+'-source.tar.gz'),'w:gz')as t:
  for n in m:t.add(vm/n,arcname=n)
 target=scratch()/'target-adversarial-v2-all-release';assert not target.exists();target.mkdir();env={'CARGO_TARGET_DIR':str(target)}
 p,r=command('adversarial-v2-all-release-build',['cargo','test','--lib','--no-run','--release','--all-features','--offline','--locked','--message-format=json-render-diagnostics'],cwd=vm,env_extra=env,source=vm)
 aa=[json.loads(l)for l in p.stdout.decode().splitlines()if l.startswith('{')];aa=[a for a in aa if a.get('reason')=='compiler-artifact'and a['target']['name']=='mixer_vm'and a['profile']['test']and a.get('executable')];assert len(aa)==1 and aa[0]['fresh']is False;a=aa[0];exe=Path(a['executable']);data=exe.read_bytes();d=HERE/'artifacts/adversarial-v2-all-release';d.mkdir(parents=True)
 save('artifacts/adversarial-v2-all-release/cargo-artifact.json',a)
 with gzip.open(d/'executable.gz','wb')as z:z.write(data)
 p,_=command('adversarial-v2-all-release-list',[str(exe),'--list'],cwd=vm,env_extra=env,source=vm);tests=[l[:-6]for l in p.stdout.decode().splitlines()if l.endswith(': test')];assert len(tests)==270;save('artifacts/adversarial-v2-all-release/test-list.json',tests)
 save('artifacts/adversarial-v2-all-release/identity.json',dict(executableSHA256=sha(data),executableBytes=len(data),sourceClosure=tree(vm),exactExecutablePath=str(exe),targetInitiallyEmpty=True,fresh=a['fresh'],listedTests=len(tests)))
 command('adversarial-v2-all-release-reviewer',[str(exe),'reviewer_r','--nocapture','--test-threads=1'],cwd=vm,env_extra=env,source=vm)
 assert sha(exe.read_bytes())==sha(data)
 command('adversarial-v2-all-release-host',[str(exe),'host_tests::h','--nocapture','--test-threads=1'],cwd=vm,env_extra=env,source=vm)
 assert sha(exe.read_bytes())==sha(data)
 save('artifacts/adversarial-v2-all-release/after.json',dict(executableSHA256=sha(exe.read_bytes()),sourceClosure=tree(vm),passedReviewer=5,passedHost=16))

def compiler_identity():
 import re
 hashes={}
 for label in ['baseline','candidate']:
  vm=scratch()/label;target=scratch()/('target-expanded-'+label);assert not target.exists();target.mkdir()
  p,r=command('expanded-'+label,['cargo','rustc','--lib','--offline','--locked','--all-features','--','-Zunpretty=expanded'],cwd=vm,env_extra={'CARGO_TARGET_DIR':str(target),'RUSTC_BOOTSTRAP':'1'},source=vm)
  text=p.stdout.decode();start=text.index('impl SpanInstance {');brace=text.index('{',start);depth=1;end=brace+1
  while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
  body=text[start:end];methods={}
  for m in re.finditer(r'^\s+(?:pub )?fn (\w+)\(',body,re.M):
   a=m.start();b=body.index('{',a);d=1;e=b+1
   while d:d+=(body[e]=='{')-(body[e]=='}');e+=1
   assert m[1]not in methods;methods[m[1]]=sha(body[a:e].strip().encode())
  assert len(methods)==39;hashes[label]=methods
 assert hashes['baseline']==hashes['candidate'];save('independent-frozen-expansion.json',dict(methodCount=39,methods=hashes['candidate'],baselineEqualsCandidate=True))
 vm=scratch()/'candidate';target=scratch()/'target-exact-production-mir';assert not target.exists();target.mkdir()
 p,r=command('exact-production-mir-build',['cargo','rustc','--lib','--all-features','--offline','--locked','--message-format=json-render-diagnostics','--','--emit=mir','-Zmir-include-spans=yes'],cwd=vm,env_extra={'CARGO_TARGET_DIR':str(target),'RUSTC_BOOTSTRAP':'1'},source=vm)
 files=list(target.glob('debug/deps/*.mir'));assert len(files)==1
 with gzip.open(HERE/'independent-production.mir.gz','wb')as z:z.write(files[0].read_bytes())
 aa=[json.loads(l)for l in p.stdout.decode().splitlines()if l.startswith('{')];aa=[a for a in aa if a.get('reason')=='compiler-artifact'and a['target']['name']=='mixer_vm'and not a['profile']['test']];assert len(aa)==1 and aa[0]['fresh']is False;save('independent-production-mir-artifact.json',aa[0])
