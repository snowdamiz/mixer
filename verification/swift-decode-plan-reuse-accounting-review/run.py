#!/usr/bin/env python3
"""Bounded offline named host controls, with source/tool/process receipts."""
from pathlib import Path
import datetime,hashlib,json,os,platform,re,selectors,signal,subprocess,sys,time
H=Path(__file__).resolve().parent
lane,label,name,*extra=sys.argv[1:]
assert lane in ['baseline','candidate'] and label.replace('-','').isalnum()
assert name.startswith(('experimental_swift_reactor::cache_tests::','experimental::cache::tests::frozen_'))
assert not any(x in name for x in ['exact_reactor','target_once','reactor_target'])
D=H/'commands'/label;D.mkdir(parents=True,exist_ok=False);S=H/lane
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def manifest():return {str(p.relative_to(S)):sha(p) for p in sorted(S.rglob('*')) if p.is_file()}
m=manifest();save(D/'source-manifest.json',m)
T=Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
env={k:os.environ[k] for k in ['HOME','USER','LOGNAME'] if k in os.environ}
env.update(PATH=str(T)+':/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',CARGO_NET_OFFLINE='true',CARGO_INCREMENTAL='0',CARGO_BUILD_JOBS='2',CARGO_TARGET_DIR=str(H/'owned-scratch'/lane),TMPDIR=str(H/'owned-scratch'/'tmp'),RUST_TEST_THREADS='1')
(H/'owned-scratch'/'tmp').mkdir(parents=True,exist_ok=True)
if not (H/'tools.json').exists():
    ts={'python':{'path':sys.executable,'sha256':sha(Path(sys.executable)),'version':sys.version},'machine':platform.platform()}
    for n,flags in [('cargo',['-V']),('rustc',['-vV'])]:ts[n]={'path':str(T/n),'sha256':sha(T/n),'version':subprocess.check_output([str(T/n),*flags],env=env,text=True)}
    save(H/'tools.json',ts)
cmd=[str(T/'cargo'),'test','--offline','--locked','--lib','--all-features',*extra,name,'--','--exact','--nocapture','--test-threads=1']
r={'argv':cmd,'cwd':str(S),'environment':env,'sourceManifestSHA256':sha(D/'source-manifest.json'),'startedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'timeoutSeconds':180,'signals':[],'driverSHA256':sha(Path(__file__))}
save(D/'started.json',r);start=time.monotonic();p=subprocess.Popen(cmd,cwd=S,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
r.update(pid=p.pid,pgid=p.pid);save(D/'started.json',r)
sel=selectors.DefaultSelector();closed={}
for n,stream in [('stdout',p.stdout),('stderr',p.stderr)]:
    os.set_blocking(stream.fileno(),False);f=(D/n).open('wb');sel.register(stream,selectors.EVENT_READ,(n,f));closed[n]=False
while sel.get_map() or p.poll() is None:
    elapsed=time.monotonic()-start
    if elapsed>180 and not r['signals']:
        r['signals'].append('SIGTERM')
        try:os.killpg(p.pid,signal.SIGTERM)
        except ProcessLookupError:pass
    if elapsed>185 and len(r['signals'])==1:
        r['signals'].append('SIGKILL')
        try:os.killpg(p.pid,signal.SIGKILL)
        except ProcessLookupError:pass
    if elapsed>192:raise RuntimeError('owned process did not drain')
    for key,_ in sel.select(.1):
        n,f=key.data;data=os.read(key.fileobj.fileno(),65536)
        if data:f.write(data);f.flush()
        else:sel.unregister(key.fileobj);key.fileobj.close();f.close();closed[n]=True
code=p.wait();ps=subprocess.check_output(['/bin/ps','-axo','pid=,pgid=,comm='],text=True)
members=[x for x in ps.splitlines() if len(x.split())>=2 and x.split()[1]==str(p.pid)]
stdout=(D/'stdout').read_text();stderr=(D/'stderr').read_text();tests=re.findall(r'^test (\S+) \.\.\. ',stdout,re.M)
summaries=re.findall(r'test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored;',stdout)
passed=sum(int(x[1]) for x in summaries);failed=sum(int(x[2]) for x in summaries)
r.update(exitCode=code,durationSeconds=time.monotonic()-start,streamsClosed=closed,ownedGroupAbsent=not members,ownedGroupMembers=members,sourceUnchanged=manifest()==m,stdoutSHA256=sha(D/'stdout'),stderrSHA256=sha(D/'stderr'),executedNamedTests=tests,passedTests=passed,failedTests=failed,qualifyingPass=code==0 and passed>0 and failed==0 and not members and all(closed.values()) and not r['signals'])
r['binaries']=[]
for raw in re.findall(r'^\s*Running .* \((/[^)\n]+)\)$',stderr,re.M):
    b=Path(raw)
    if b.is_file():r['binaries'].append({'path':str(b),'sha256':sha(b),'bytes':b.stat().st_size})
save(D/'receipt.json',r);print(json.dumps({k:r[k] for k in ['exitCode','durationSeconds','executedNamedTests','passedTests','failedTests','qualifyingPass','ownedGroupAbsent']}));print(stdout[-9000:]);print(stderr[-2500:]);sys.exit(code)
