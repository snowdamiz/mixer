#!/usr/bin/env python3
from pathlib import Path
import datetime,hashlib,json,os,platform,selectors,signal,subprocess,sys,time,re
H=Path(__file__).resolve().parent
lane,label,*args=sys.argv[1:]
assert lane in ('source','baseline') and label.replace('-','').isalnum()
assert args and args[0] in ('test','check','rustfmt')
assert not any(x in ' '.join(args) for x in ('--ignored','exact_reactor','target_once','reactor_target'))
# cargo test is restricted to named finite diagnostic/cache controls.
if args[0]=='test':assert '--lib' in args and any(x.startswith(('plan_reuse_', 'experimental_swift_reactor::cache_tests::','experimental::cache::tests::frozen_')) for x in args)
S=H/lane;D=H/'commands'/label;D.mkdir(parents=True,exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
paths=[S/'Cargo.toml',S/'Cargo.lock']+[p for t in ('src','include','tests') for p in (S/t).rglob('*') if p.is_file()]
manifest={str(p.relative_to(S)):sha(p) for p in sorted(paths)};save(D/'source-manifest.json',manifest)
base=json.loads((H/'baseline-manifest.json').read_text())
for name,digest in manifest.items():
 if base.get(name)!=digest:
  p=D/'changed-source'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((S/name).read_bytes())
(D/'driver.py').write_bytes(Path(__file__).read_bytes())
T=Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
cmd=[str(T/('rustfmt' if args[0]=='rustfmt' else 'cargo')),* (args[1:] if args[0]=='rustfmt' else args)]
env={k:os.environ[k] for k in ('HOME','USER','LOGNAME') if k in os.environ}
env.update(PATH=str(T)+':/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',CARGO_NET_OFFLINE='true',CARGO_INCREMENTAL='0',CARGO_BUILD_JOBS='2',CARGO_TARGET_DIR=str(H/'owned-scratch'/lane),TMPDIR=str(H/'owned-scratch'/'tmp'),RUST_TEST_THREADS='1')
(H/'owned-scratch'/'tmp').mkdir(parents=True,exist_ok=True)
if not (H/'tools.json').exists():
 tools={'pythonVersion':sys.version,'pythonExecutable':sys.executable,'machine':platform.platform()}
 for n,flags in [('rustc',['-vV']),('cargo',['-V']),('rustfmt',['-V'])]:
  p=T/n;tools[n]={'path':str(p),'sha256':sha(p),'version':subprocess.check_output([str(p),*flags],env=env,text=True)}
 save(H/'tools.json',tools)
r={'argv':cmd,'cwd':str(S),'environment':env,'sourceManifestSHA256':sha(D/'source-manifest.json'),'beganUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'timeoutSeconds':180,'signals':[],'fullTargetExecuted':False,'driverSHA256':sha(D/'driver.py')}
save(D/'started.json',r);start=time.monotonic();p=subprocess.Popen(cmd,cwd=S,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);r.update(pid=p.pid,processGroup=p.pid);save(D/'started.json',r)
sel=selectors.DefaultSelector();streams={}
for name,stream in [('stdout',p.stdout),('stderr',p.stderr)]:
 os.set_blocking(stream.fileno(),False);f=(D/name).open('wb');sel.register(stream,selectors.EVENT_READ,(name,f));streams[name]=False
while sel.get_map() or p.poll() is None:
 elapsed=time.monotonic()-start
 if elapsed>180 and not r['signals']:r['signals'].append('SIGTERM');os.killpg(p.pid,signal.SIGTERM)
 if elapsed>185 and len(r['signals'])==1:
  r['signals'].append('SIGKILL')
  try:os.killpg(p.pid,signal.SIGKILL)
  except ProcessLookupError:pass
 if elapsed>192:raise RuntimeError('owned group/streams failed to close')
 for key,_ in sel.select(.1):
  data=os.read(key.fileobj.fileno(),65536);name,f=key.data
  if data:f.write(data);f.flush()
  else:sel.unregister(key.fileobj);key.fileobj.close();f.close();streams[name]=True
code=p.wait();group=subprocess.check_output(['/bin/ps','-axo','pid=,pgid=,comm='],text=True)
members=[x for x in group.splitlines() if len(x.split())>=2 and x.split()[1]==str(p.pid)]
r.update(exitCode=code,durationSeconds=time.monotonic()-start,streamEOF=streams,ownedGroupMembers=members,ownedGroupAbsent=not members,timedOut=bool(r['signals']),stdoutSHA256=sha(D/'stdout'),stderrSHA256=sha(D/'stderr'),sourceUnchanged=manifest=={str(q.relative_to(S)):sha(q) for q in paths},passed=code==0 and not r['signals'] and not members and all(streams.values()))
r['executedBinaryIdentities']=[]
for n in re.findall(r'^\s*Running .* \((/[^)\n]+)\)$',(D/'stderr').read_text(),re.M):
 q=Path(n)
 if q.is_file():r['executedBinaryIdentities'].append({'path':str(q),'bytes':q.stat().st_size,'sha256':sha(q)})
save(D/'receipt.json',r);print(json.dumps({'command':label,'passed':r['passed'],'exitCode':code,'seconds':r['durationSeconds'],'EOF':streams,'groupAbsent':not members}));print((D/'stdout').read_text()[-4500:]);print((D/'stderr').read_text()[-6000:]);sys.exit(code)
