#!/usr/bin/env python3
"""Bounded named actual-cache controls only. No full-module driver exists here."""
from pathlib import Path
import datetime,hashlib,json,os,platform,signal,subprocess,sys,time
H=Path(__file__).resolve().parent;S=H/'owned-source';B=H/'owned-target';T=H/'owned-tmp'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(n,v):(H/n).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def group(g):
 p=subprocess.check_output(['/bin/ps','-axo','pid=,pgid=,comm='],text=True,timeout=10)
 return [r.strip() for r in p.splitlines() if len(r.split())>=2 and int(r.split()[1])==g]
assert not (H/'command.json').exists();T.mkdir(exist_ok=True)
manifest=json.loads((H/'copied-source-manifest.json').read_text());assert {n:sha(S/n) for n in manifest}==manifest
identity=lambda p:{'device':p.stat().st_dev,'inode':p.stat().st_ino}
save('cleanup-identities.json',{str(p):identity(p) for p in (S,T)})
toolchain=Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
env={k:os.environ[k] for k in ('HOME','USER','LOGNAME') if k in os.environ}
env.update(PATH=str(toolchain)+':/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',CARGO_TARGET_DIR=str(B),CARGO_BUILD_JOBS='2',CARGO_NET_OFFLINE='true',CARGO_INCREMENTAL='0',RUST_TEST_THREADS='1',TMPDIR=str(T))
versions={'python':{'path':sys.executable,'resolvedSHA256':sha(Path(sys.executable).resolve()),'version':sys.version},'platform':platform.platform()}
for name,args in [('rustc',['-vV']),('cargo',['-V'])]:
 q=subprocess.run([str(toolchain/name),*args],capture_output=True,text=True,check=True,timeout=10,env=env)
 versions[name]={'path':str(toolchain/name),'sha256':sha(toolchain/name),'stdout':q.stdout,'stderr':q.stderr}
save('tools.json',versions)
argv=[str(toolchain/'cargo'),'test','--lib','--locked','--offline','--no-default-features','--features','experimental-swift-reactor','--release','experimental_swift_reactor::cache_tests::current_attribution_','--','--nocapture','--test-threads=1']
start=time.monotonic();began=datetime.datetime.now(datetime.timezone.utc).isoformat();signals=[]
with (H/'finite.stdout').open('wb') as out,(H/'finite.stderr').open('wb') as err:
 q=subprocess.Popen(argv,cwd=S,env=env,stdout=out,stderr=err,start_new_session=True)
 save('started.json',{'argv':argv,'cwd':str(S),'environment':env,'pid':q.pid,'processGroup':q.pid,'beganUTC':began,'timeoutSeconds':120})
 try:code=q.wait(timeout=120);timed=False
 except subprocess.TimeoutExpired:
  timed=True;assert group(q.pid);os.killpg(q.pid,signal.SIGTERM);signals.append('SIGTERM')
  try:code=q.wait(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(q.pid,signal.SIGKILL);signals.append('SIGKILL');code=q.wait(timeout=3)
record={'argv':argv,'cwd':str(S),'environment':env,'beganUTC':began,'elapsedSeconds':time.monotonic()-start,'exitCode':code,'timedOut':timed,'pid':q.pid,'processGroup':q.pid,'signalsSent':signals,'timeoutSeconds':120,'sourceManifestSHA256':sha(H/'copied-source-manifest.json'),'stdoutSHA256':sha(H/'finite.stdout'),'stderrSHA256':sha(H/'finite.stderr')}
save('command.json',record)
ident=json.loads((H/'cleanup-identities.json').read_text())
if B.exists():ident[str(B)]=identity(B)
save('cleanup-identities.json',ident)
print(json.dumps(record));raise SystemExit(code)
