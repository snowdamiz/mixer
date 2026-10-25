#!/usr/bin/env python3
"""Bounded offline ordinary host suite/check runner with immutable input snapshots."""
from pathlib import Path
import datetime, hashlib, json, os, platform, re, selectors, signal, subprocess, sys, time
H = Path(__file__).resolve().parent
label, context, action, *extra = sys.argv[1:]
assert label.replace('-', '').isalnum()
assert context in ('swift-debug', 'swift-release', 'full-debug', 'full-release')
assert action in ('suite', 'named', 'observe', 'fmt', 'baselinefmt', 'fixturefmt', 'clippy')
assert not any(x in ' '.join(extra) for x in ('--ignored', 'exact_reactor', 'target_once', 'reactor_target'))
D = H/'commands'/label
D.mkdir(parents=True, exist_ok=False)
S = H.parent/'swift-decode-plan-reuse-diagnosis/baseline' if action=='baselinefmt' else H/'source'
T = Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v): p.write_text(json.dumps(v, indent=2, sort_keys=True)+'\n')
def manifest(): return {str(p.relative_to(S)):sha(p) for p in sorted(S.rglob('*')) if p.is_file()}
m = manifest()
save(D/'source-manifest.json',m)
O = H/'source-objects'; O.mkdir(exist_ok=True)
for n,v in m.items():
    obj=O/v
    if not obj.exists(): obj.write_bytes((S/n).read_bytes())
    assert sha(obj)==v
(D/'driver.py').write_bytes(Path(__file__).read_bytes())
features = 'experimental-swift-reactor' if context.startswith('swift') else 'experimental-stream-validation,experimental-function-cache,experimental-span-execution,experimental-swift-wasi,experimental-swift-reactor,experimental-capability-native'
env = {k:os.environ[k] for k in ['HOME','USER','LOGNAME'] if k in os.environ}
node=json.loads((H/'node-oracle-tools.json').read_text()) if (H/'node-oracle-tools.json').exists() else None
if node:assert sha(Path(node['path']))==node['sha256']
env.update(PATH=str(T)+(':'+str(Path(node['path']).parent) if node else '')+':/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin', CARGO_NET_OFFLINE='true', CARGO_INCREMENTAL='0', CARGO_BUILD_JOBS='2', CARGO_TARGET_DIR=str(H/'owned-scratch'/context), TMPDIR=str(H/'owned-scratch'/'tmp'), RUST_TEST_THREADS='1')
(H/'owned-scratch'/'tmp').mkdir(parents=True,exist_ok=True)
if not (H/'tools.json').exists():
    ts={'python':{'path':sys.executable,'sha256':sha(Path(sys.executable)),'version':sys.version},'machine':platform.platform()}
    for n,flags in [('cargo',['-V']),('rustc',['-vV']),('rustfmt',['-V']),('clippy-driver',['-V'])]: ts[n]={'path':str(T/n),'sha256':sha(T/n),'version':subprocess.check_output([str(T/n),*flags],env=env,text=True)}
    save(H/'tools.json',ts)
cmd=[str(T/'cargo')]
if action in ('suite','named','observe'):
    cmd += ['test','--offline','--locked','--manifest-path',str(S/'Cargo.toml'),'--features',features]
    if context.endswith('release'): cmd+=['--release']
    if action=='suite': cmd+=['--no-fail-fast']
    else: cmd+=['--lib',*extra]
    cmd+=['--','--nocapture','--test-threads=1']
    if action=='named':cmd+=['--exact']
elif action in ('fmt','baselinefmt'): cmd+=['fmt','--manifest-path',str(S/'Cargo.toml'),'--','--check']
elif action=='fixturefmt':cmd=[str(T/'rustfmt'),'--edition','2021','--check',*[str(p) for p in sorted((H/'fixtures').glob('*.rs'))]]
else: cmd+=['clippy','--offline','--locked','--manifest-path',str(S/'Cargo.toml'),'--lib','--features',features,'--','-D','warnings']
r={'argv':cmd,'cwd':str(S),'context':context,'action':action,'environment':env,'sourceManifestSHA256':sha(D/'source-manifest.json'),'startedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'timeoutSeconds':600,'signals':[],'driverSHA256':sha(D/'driver.py')}
save(D/'started.json',r)
start=time.monotonic(); p=subprocess.Popen(cmd,cwd=S,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
r.update(pid=p.pid,pgid=p.pid);save(D/'started.json',r)
sel=selectors.DefaultSelector();closed={}
for n,stream in [('stdout',p.stdout),('stderr',p.stderr)]:
    os.set_blocking(stream.fileno(),False); f=(D/n).open('wb');sel.register(stream,selectors.EVENT_READ,(n,f));closed[n]=False
while sel.get_map() or p.poll() is None:
    elapsed=time.monotonic()-start
    if elapsed>600 and not r['signals']:
        r['signals'].append('SIGTERM')
        try: os.killpg(p.pid,signal.SIGTERM)
        except ProcessLookupError: pass
    if elapsed>605 and len(r['signals'])==1:
        r['signals'].append('SIGKILL')
        try:os.killpg(p.pid,signal.SIGKILL)
        except ProcessLookupError:pass
    if elapsed>612: raise RuntimeError('owned child group did not drain')
    for key,_ in sel.select(.1):
        n,f=key.data; data=os.read(key.fileobj.fileno(),65536)
        if data:f.write(data);f.flush()
        else:sel.unregister(key.fileobj);key.fileobj.close();f.close();closed[n]=True
code=p.wait()
ps=subprocess.check_output(['/bin/ps','-axo','pid=,pgid=,comm='],text=True)
members=[x for x in ps.splitlines() if len(x.split())>=2 and x.split()[1]==str(p.pid)]
stdout=(D/'stdout').read_text(); stderr=(D/'stderr').read_text()
named=[]
for block in re.finditer(r'^test ([^\n]+?) \.\.\. ([\s\S]*?)(?=^test [^\n]+? \.\.\. |^failures:|^test result:|\Z)',stdout,re.M):
    name,body=block.groups()
    status=re.search(r'^(ok|FAILED|ignored[^\n]*)\s*$',body,re.M)
    if status:named.append((name,status.group(1)))
summaries=re.findall(r'test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out;',stdout)
r.update(exitCode=code,durationSeconds=time.monotonic()-start,streamsClosed=closed,ownedGroupAbsent=not members,ownedGroupMembers=members,sourceUnchanged=manifest()==m,stdoutSHA256=sha(D/'stdout'),stderrSHA256=sha(D/'stderr'),namedTests=[{'name':n,'result':v} for n,v in named],summaries=summaries,passedTests=sum(int(x[1]) for x in summaries),failedTests=sum(int(x[2]) for x in summaries),ignoredTests=sum(int(x[3]) for x in summaries))
r['qualifyingPass']=code==0 and not r['signals'] and not members and all(closed.values()) and r['sourceUnchanged'] and (action not in ('suite','named','observe') or (r['passedTests']>0 and r['failedTests']==0))
r['binaries']=[]
for raw in re.findall(r'^\s*Running .* \((/[^)\n]+)\)$',stderr,re.M):
    b=Path(raw)
    if b.is_file():r['binaries'].append({'path':str(b),'sha256':sha(b),'bytes':b.stat().st_size})
save(D/'receipt.json',r)
print(json.dumps({k:r[k] for k in ['exitCode','durationSeconds','passedTests','failedTests','ignoredTests','qualifyingPass','ownedGroupAbsent']}))
print('Failures:',[x for x in r['namedTests'] if x['result']=='FAILED'])
print(stderr[-16000:] if code else stderr[-1500:])
sys.exit(code)
