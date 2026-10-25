#!/usr/bin/env python3
"""Bounded independent finite review commands only; no full-target route."""
from pathlib import Path
import datetime,hashlib,importlib.util,json,os,platform,shutil,signal,subprocess,sys,time
H=Path(__file__).resolve().parent;R=H.parent.parent;P=H.parent/'swift-current-attribution-full-preparation'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
assert len(sys.argv)==2
name=sys.argv[1]
actions={
 'prepare':([sys.executable,'-B',str(H/'prepare-review.py')],R,30),
 'verify-prepared':([sys.executable,'-B',str(P/'verify.py')],R,30),
 'finite-cache':(['/opt/homebrew/opt/rustup/bin/cargo','test','--lib','--locked','--offline','--no-default-features','--features','experimental-swift-reactor','--release','experimental_swift_reactor::cache_tests::independent_full_attribution_','--','--nocapture','--test-threads=1'],H/'owned-source',120),
 'host-controls':([sys.executable,'-B',str(H/'host-controls.py')],H,30),
 'host-controls-corrected':([sys.executable,'-B',str(H/'host-controls.py')],H,30),
 'parser-contract':([sys.executable,'-B',str(H/'parser-contract.py')],H,30),
}
assert name in actions;argv,cwd,timeout=actions[name]
directory=H/'commands'/name;assert not directory.exists();directory.mkdir(parents=True)
shutil.copyfile(Path(__file__),directory/'runner.py')
argv_files=[]
for arg in argv:
    path=Path(arg)
    if path.is_absolute() and path.is_file():
        argv_files.append({'path':str(path),'bytes':path.stat().st_size,'sha256':sha(path)})
        if path.suffix=='.py':shutil.copyfile(path,directory/'executed-file.py')
env={k:os.environ[k] for k in ('HOME','USER','LOGNAME') if k in os.environ}
env.update(PATH='/opt/homebrew/opt/rustup/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',RUSTUP_TOOLCHAIN='stable-aarch64-apple-darwin',CARGO_INCREMENTAL='0',CARGO_NET_OFFLINE='true',CARGO_BUILD_JOBS='2',CARGO_TARGET_DIR=str(H/'owned-target'),TMPDIR=str(H/'owned-tmp'),PYTHONDONTWRITEBYTECODE='1')
toolinfo={'python':{'path':sys.executable,'sha256':sha(sys.executable),'version':sys.version},'system':platform.platform(),'machine':platform.machine()}
for tool,flags in [('cargo',['-V']),('rustc',['-vV'])]:
    actual=subprocess.check_output(['/opt/homebrew/opt/rustup/bin/rustup','which',tool],env=env,text=True,timeout=10).strip()
    toolinfo[tool]={'path':actual,'sha256':sha(actual),'version':subprocess.check_output([actual,*flags],env=env,text=True,timeout=10).strip()}
seal_before=sha(P/'prepared-seal.json')
def manifest():
    root=H/'owned-source'
    if not root.exists():return None
    files=[root/'Cargo.toml',root/'Cargo.lock']+[p for top in ('include','src','tests') for p in (root/top).rglob('*') if p.is_file()]
    return {str(p.relative_to(root)):sha(p) for p in sorted(files)}
source_before=manifest();started=time.monotonic();signals=[]
with (directory/'stdout').open('wb') as out,(directory/'stderr').open('wb') as err:
    child=subprocess.Popen(argv,cwd=cwd,env=env,stdout=out,stderr=err,start_new_session=True)
    base={'argv':argv,'argvFiles':argv_files,'runnerSHA256':sha(directory/'runner.py'),'cwd':str(cwd),'environment':env,'timeoutSeconds':timeout,'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':child.pid,'processGroup':child.pid,'tools':toolinfo,'sourceRevisionContext':'6b8aba350224ed19f678669bdbea6b359d8de68b','sourceRevisionMeaning':'root supplied; exact source manifest authoritative; no Git query','preparedSealSHA256':seal_before,'fullTargetSelected':False}
    save(directory/'started.json',base)
    timed=False
    try:child.wait(timeout=timeout)
    except subprocess.TimeoutExpired:timed=True
    def group_absent():
        try:os.killpg(child.pid,0);return False
        except ProcessLookupError:return True
        except OSError:return False
    cleanup_start=time.monotonic()
    if not group_absent():
        for sig,deadline in [(signal.SIGTERM,cleanup_start+5),(signal.SIGKILL,cleanup_start+10)]:
            try:os.killpg(child.pid,sig);signals.append(sig.name)
            except ProcessLookupError:break
            while not group_absent() and time.monotonic()<deadline:child.poll();time.sleep(.05)
            if group_absent():break
    child.poll();empty=group_absent()
source_after=manifest()
receipt=base|{'exitCode':child.returncode,'timedOut':timed,'durationSeconds':time.monotonic()-started,'signalsSent':signals,'processGroupEmpty':empty,'stdoutSHA256':sha(directory/'stdout'),'stderrSHA256':sha(directory/'stderr'),'preparedSealUnchanged':seal_before==sha(P/'prepared-seal.json'),'sourceManifestSHA256':sha(H/'review-source-manifest.json') if (H/'review-source-manifest.json').exists() else None,'sourceUnchanged':source_before is None or source_before==source_after,'rawStreamEOFConfirmed':empty,'passed':child.returncode==0 and not timed and empty and not signals,'fullTargetAttempts':0,'realTargetValidations':0,'realTargetInitializeCalls':0,'realTargetCorpusCalls':0}
save(directory/'receipt.json',receipt)
print(json.dumps({'command':name,'passed':receipt['passed'],'exitCode':child.returncode,'durationSeconds':receipt['durationSeconds'],'receipt':str(directory/'receipt.json'),'stdout':(directory/'stdout').read_text(),'stderr':(directory/'stderr').read_text()},sort_keys=True))
raise SystemExit(0 if receipt['passed'] else 1)
