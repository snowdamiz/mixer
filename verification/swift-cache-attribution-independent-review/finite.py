#!/usr/bin/env python3
"""Run only the three independent finite cache controls, offline and bounded."""
from pathlib import Path
import datetime, hashlib, json, os, platform, signal, subprocess, sys, time
H=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
dump=lambda p,x:p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
toolbin=Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
tools={'platform':platform.platform(),'python':{'path':sys.executable,'version':sys.version,'sha256':sha(Path(sys.executable).resolve())}}
for name,flags in [('cargo',['--version']),('rustc',['-vV'])]:
    p=toolbin/name
    result=subprocess.run([str(p),*flags],capture_output=True,text=True,timeout=10,check=True)
    tools[name]={'path':str(p),'sha256':sha(p),'stdout':result.stdout,'stderr':result.stderr}
dump(H/'tools.json',tools)
env={k:os.environ[k] for k in ['HOME','USER','LOGNAME'] if k in os.environ}
env.update({'PATH':str(toolbin)+':/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin','CARGO_NET_OFFLINE':'true',
    'CARGO_BUILD_JOBS':'2','CARGO_INCREMENTAL':'0','RUST_TEST_THREADS':'1',
    'CARGO_TARGET_DIR':str(H/'owned-target'),'TMPDIR':str(H/'owned-tmp')})
argv=[str(toolbin/'cargo'),'test','--lib','--locked','--offline','--no-default-features','--features','experimental-swift-reactor',
    '--release','experimental_swift_reactor::cache_tests::independent_attribution_','--','--nocapture','--test-threads=1']
source=H/'owned-source'
manifest={str(p.relative_to(source)):sha(p) for p in sorted(source.rglob('*')) if p.is_file()}
assert manifest==json.loads((H/'review-source-manifest.json').read_text())
assert not (H/'command.json').exists()
start=time.monotonic()
record={'argv':argv,'cwd':str(source),'environment':env,'timeoutSeconds':120,
    'beganUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'sourceManifestSHA256':sha(H/'review-source-manifest.json'),'signalsSent':[],'timedOut':False}
with (H/'finite.stdout').open('wb') as out,(H/'finite.stderr').open('wb') as err:
    proc=subprocess.Popen(argv,cwd=source,env=env,stdout=out,stderr=err,start_new_session=True)
    record.update({'pid':proc.pid,'processGroup':proc.pid})
    dump(H/'started.json',record)
    try:
        record['exitCode']=proc.wait(timeout=120)
    except subprocess.TimeoutExpired:
        record['timedOut']=True
        os.killpg(proc.pid,signal.SIGTERM);record['signalsSent'].append('SIGTERM')
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL);record['signalsSent'].append('SIGKILL');proc.wait(timeout=5)
        record['exitCode']=proc.returncode
record['elapsedSeconds']=time.monotonic()-start
record['stdoutSHA256']=sha(H/'finite.stdout');record['stderrSHA256']=sha(H/'finite.stderr')
dump(H/'command.json',record)
print(json.dumps(record,sort_keys=True))
print((H/'finite.stdout').read_text())
print((H/'finite.stderr').read_text())
sys.exit(record['exitCode'])
