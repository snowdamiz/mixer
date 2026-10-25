from pathlib import Path
import subprocess,json,os,time,datetime,hashlib,signal,re,sys
H=Path(__file__).resolve().parent;S=H/'owned-scratch'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def manifest(p):return {str(x.relative_to(p)):sha(x) for x in sorted(p.rglob('*')) if x.is_file()}
label,kind=sys.argv[1:3];args=sys.argv[3:];d=H/'commands'/label;d.mkdir(parents=True,exist_ok=False);cwd=S/kind
m=manifest(cwd);save(d/'source-manifest.json',m)
cargo=Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/cargo')
env={k:os.environ[k] for k in ('HOME','USER','LOGNAME') if k in os.environ}
env.update({'PATH':str(cargo.parent)+':/Users/andreyyurlov/.local/share/fnm/node-versions/v22.23.3/installation/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin','CARGO_TARGET_DIR':str(S/'targets'/kind),'CARGO_BUILD_JOBS':'2','CARGO_INCREMENTAL':'0','CARGO_NET_OFFLINE':'true','RUST_TEST_THREADS':'1','TMPDIR':str(S/'tmp')})
argv=[str(cargo)]+args;began=datetime.datetime.now(datetime.timezone.utc).isoformat();start=time.monotonic();signals=[];timeout=240
p=subprocess.Popen(argv,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
save(d/'started.json',{'pid':p.pid,'processGroup':p.pid,'argv':argv,'cwd':str(cwd),'beganUTC':began,'environment':env,'timeoutSeconds':timeout})
timed=False
try:out,err=p.communicate(timeout=timeout)
except subprocess.TimeoutExpired:
 timed=True;os.killpg(p.pid,signal.SIGTERM);signals.append('SIGTERM')
 try:out,err=p.communicate(timeout=5)
 except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);signals.append('SIGKILL');out,err=p.communicate()
(d/'stdout').write_bytes(out);(d/'stderr').write_bytes(err)
ps=subprocess.run(['/bin/ps','-axo','pid=,pgid=,comm='],capture_output=True,text=True,check=True)
members=[l.strip() for l in ps.stdout.splitlines() if len(l.split())>=2 and l.split()[1]==str(p.pid)]
identities=[]
for line in err.decode(errors='replace').splitlines():
 if 'Running ' in line:
  match=re.search(r'\(([^)]+)\)',line)
  if match:
   binary=Path(match[1]);binary=binary if binary.is_absolute() else cwd/binary
   if binary.is_file():identities.append({'path':str(binary),'sha256':sha(binary),'bytes':binary.stat().st_size})
r={'label':label,'argv':argv,'cwd':str(cwd),'environment':env,'beganUTC':began,'durationSeconds':time.monotonic()-start,'pid':p.pid,'processGroup':p.pid,'exitCode':p.returncode,'timedOut':timed,'signals':signals,'stdoutSHA256':sha(d/'stdout'),'stderrSHA256':sha(d/'stderr'),'streamEOF':{'stdout':True,'stderr':True},'ownedGroupAbsent':not members,'ownedGroupMembers':members,'sourceManifestSHA256':sha(d/'source-manifest.json'),'sourceUnchanged':manifest(cwd)==m,'executedBinaryIdentities':identities,'driverSHA256':sha(Path(__file__)),'nativeOrFullTargetExecuted':False,'passed':p.returncode==0 and not timed and not members}
save(d/'receipt.json',r)
print(json.dumps(r));sys.exit(0 if r['passed'] else 1)
