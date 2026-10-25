from pathlib import Path
import datetime, hashlib, json, os, subprocess, time, signal, re, sys
H=Path(__file__).resolve().parent; S=H/'owned-scratch'
TOOL=Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def enc(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def manifest(kind):
    names=json.loads((H/'input-source-manifest.json').read_text())
    return {n:sha(S/kind/n) for n in names}
def members(group):
    p=subprocess.run(['/bin/ps','-axo','pid=,pgid=,command='],capture_output=True,text=True,check=True)
    return [l.strip() for l in p.stdout.splitlines() if len(l.split())>=2 and l.split()[1]==str(group)]
kind,label,filter_name=sys.argv[1:]
out=H/'commands'/label;out.mkdir(parents=True,exist_ok=False)
env={k:v for k,v in os.environ.items() if k in ('HOME','USER','LOGNAME')}
env.update(PATH=str(TOOL)+':/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',CARGO_TARGET_DIR=str(S/'targets'/kind),CARGO_INCREMENTAL='0',CARGO_BUILD_JOBS='2',CARGO_NET_OFFLINE='true',RUST_TEST_THREADS='1',TMPDIR=str(S/'tmp'))
argv=[str(TOOL/'cargo'),'test','--locked','--offline','--no-default-features','--features','experimental-swift-reactor','--lib',filter_name,'--','--nocapture','--test-threads=1']
before=manifest(kind);(out/'source-manifest.json').write_bytes(enc(before))
begin=datetime.datetime.now(datetime.timezone.utc).isoformat();start=time.monotonic()
with (out/'stdout').open('wb') as so,(out/'stderr').open('wb') as se:
    p=subprocess.Popen(argv,cwd=S/kind,env=env,stdout=so,stderr=se,start_new_session=True)
    (out/'started.json').write_bytes(enc({'argv':argv,'cwd':str(S/kind),'environment':env,'pid':p.pid,'processGroup':p.pid,'beganUTC':begin}))
    timeout=False;signals=[]
    try: code=p.wait(timeout=120)
    except subprocess.TimeoutExpired:
        timeout=True;signals.append('SIGTERM');os.killpg(p.pid,signal.SIGTERM)
        try:code=p.wait(timeout=5)
        except subprocess.TimeoutExpired:signals.append('SIGKILL');os.killpg(p.pid,signal.SIGKILL);code=p.wait(timeout=5)
output=(out/'stdout').read_text(); binaries=[]
for x in (S/'targets'/kind/'debug/deps').glob('mixer_vm-*'):
    if x.is_file() and os.access(x,os.X_OK):binaries.append({'path':str(x),'sha256':sha(x),'bytes':x.stat().st_size})
receipt={'argv':argv,'cwd':str(S/kind),'environment':env,'beganUTC':begin,'durationSeconds':time.monotonic()-start,'pid':p.pid,'processGroup':p.pid,'exitCode':code,'timedOut':timeout,'signals':signals,'ownedGroupMembers':members(p.pid),'streamEOF':{'stdout':True,'stderr':True},'sourceManifestSHA256':sha(out/'source-manifest.json'),'sourceUnchanged':before==manifest(kind),'stdoutSHA256':sha(out/'stdout'),'stderrSHA256':sha(out/'stderr'),'executedBinaries':binaries,'testResults':re.findall(r'test result: (\w+)\. (\d+) passed; (\d+) failed',output),'fullTargetOrNative':False}
(out/'receipt.json').write_bytes(enc(receipt))
print(json.dumps({k:receipt[k] for k in ('exitCode','durationSeconds','testResults','timedOut','ownedGroupMembers','sourceUnchanged')}))
print('\n'.join(l for l in output.splitlines() if 'DIAG_' in l))
sys.exit(code)
