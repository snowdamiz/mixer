#!/usr/bin/env python3
"""Finite host command recorder with closed stream/process-group evidence."""
from pathlib import Path
import datetime,hashlib,json,os,platform,selectors,signal,subprocess,sys,time
H=Path(__file__).resolve().parent
label=sys.argv[1]; args=sys.argv[2:]; assert label.replace('-','').isalnum()
baseline=label.startswith('baseline-'); source=H/('baseline' if baseline else 'source')
assert args and args[0] in ('test','check','clippy','fmt')
assert not any('ignored' in x or 'target_once' in x or 'exact_reactor' in x for x in args)
cmd=['/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/cargo',*args]
N=1
while (H/'commands'/f'{label}-{N:03}').exists():N+=1
D=H/'commands'/f'{label}-{N:03}';D.mkdir(parents=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value):(D/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
paths=[source/'Cargo.toml',source/'Cargo.lock']+[p for top in ('include','src','tests') for p in (source/top).rglob('*') if p.is_file()]
manifest={str(p.relative_to(source)):sha(p) for p in sorted(paths)};save('source-manifest.json',manifest)
env={k:os.environ[k] for k in ('HOME','USER','LOGNAME') if k in os.environ}
env.update(PATH='/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',CARGO_NET_OFFLINE='true',CARGO_INCREMENTAL='0',CARGO_BUILD_JOBS='2',CARGO_TARGET_DIR=str(H/'owned-scratch'/'target'),TMPDIR=str(H/'owned-scratch'/'tmp'),RUST_TEST_THREADS='1')
(H/'owned-scratch'/'tmp').mkdir(parents=True,exist_ok=True)
if not (H/'tools.json').exists():
 tools={'pythonVersion':sys.version,'pythonExecutable':sys.executable,'machine':platform.platform()}
 for n,flags in [('rustc',['-vV']),('cargo',['-V'])]:
  p=Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')/n
  tools[n]={'path':str(p),'sha256':sha(p),'version':subprocess.check_output([str(p),*flags],env=env,text=True)}
 (H/'tools.json').write_text(json.dumps(tools,sort_keys=True,indent=2)+'\n')
r={'argv':cmd,'cwd':str(source),'environment':env,'sourceManifestSHA256':sha(D/'source-manifest.json'),'beganUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'timeoutSeconds':240,'signals':[],'fullTargetExecuted':False}
save('started.json',r);start=time.monotonic();p=subprocess.Popen(cmd,cwd=source,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);r.update(pid=p.pid,processGroup=p.pid);save('started.json',r)
sel=selectors.DefaultSelector(); streams={}
for name,stream in [('stdout',p.stdout),('stderr',p.stderr)]:
 os.set_blocking(stream.fileno(),False); f=(D/name).open('wb');sel.register(stream,selectors.EVENT_READ,(name,f));streams[name]=False
while sel.get_map() or p.poll() is None:
 elapsed=time.monotonic()-start
 if elapsed>240 and 'SIGTERM' not in r['signals']:
  r['signals'].append('SIGTERM');os.killpg(p.pid,signal.SIGTERM)
 if elapsed>245 and 'SIGKILL' not in r['signals']:
  r['signals'].append('SIGKILL');
  try:os.killpg(p.pid,signal.SIGKILL)
  except ProcessLookupError:pass
 if elapsed>252:raise RuntimeError('owned group/streams did not close after kill')
 for key,_ in sel.select(.1):
  data=os.read(key.fileobj.fileno(),65536); name,f=key.data
  if data:f.write(data)
  else:sel.unregister(key.fileobj);key.fileobj.close();f.close();streams[name]=True
code=p.wait();group=subprocess.run(['/bin/ps','-axo','pid=,pgid=,comm='],capture_output=True,text=True,check=True).stdout
members=[x for x in group.splitlines() if len(x.split())>=2 and x.split()[1]==str(p.pid)]
r.update(exitCode=code,durationSeconds=time.monotonic()-start,streamEOF=streams,ownedGroupMembers=members,ownedGroupAbsent=not members,timedOut=bool(r['signals']),stdoutSHA256=sha(D/'stdout'),stderrSHA256=sha(D/'stderr'),sourceUnchanged=manifest=={str(q.relative_to(source)):sha(q) for q in paths},passed=code==0 and not r['signals'] and not members and all(streams.values()))
save('receipt.json',r); print(json.dumps({'command':str(D.relative_to(H)),'passed':r['passed'],'exitCode':code,'seconds':r['durationSeconds'],'EOF':streams,'groupAbsent':not members}));print((D/'stdout').read_text()[-4000:]);print((D/'stderr').read_text()[-6000:]);sys.exit(code)
