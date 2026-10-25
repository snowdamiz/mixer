#!/usr/bin/env python3
"""One bounded source-copy cache fixture; never runs the FieldLog reactor."""
from pathlib import Path
import datetime,hashlib,json,os,signal,subprocess,time
out=Path(__file__).resolve().parent
scratch=out/'scratch'
assert scratch.is_dir()
assert not (out/'fixture-command.json').exists(), 'finite fixture already collected'
toolchain=Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
env={k:os.environ[k] for k in ('HOME','USER','LOGNAME') if k in os.environ}
env.update(PATH=str(toolchain)+':/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin', CARGO_TARGET_DIR=str(out/'target'), CARGO_BUILD_JOBS='2', CARGO_NET_OFFLINE='true', CARGO_INCREMENTAL='0', RUST_TEST_THREADS='1', TMPDIR=str(out/'tmp'))
(out/'tmp').mkdir(exist_ok=True)
versions={}
for name,args in [('rustc',['--version','--verbose']),('cargo',['--version'])]:
 tool=toolchain/name
 r=subprocess.run([str(tool),*args],env=env,capture_output=True,text=True,timeout=10,check=True)
 versions[name]={'path':str(tool),'sha256':hashlib.sha256(tool.read_bytes()).hexdigest(),'stdout':r.stdout,'stderr':r.stderr}
versions['python']={'version':os.sys.version,'path':os.sys.executable}
(out/'tool-versions.json').write_text(json.dumps(versions,sort_keys=True,indent=2)+'\n')
argv=[str(toolchain/'cargo'),'test','--lib','--locked','--offline','--no-default-features','--features','experimental-swift-reactor','--release','experimental_swift_reactor::cache_tests::diagnostic_cache_work_fixture','--','--exact','--nocapture','--test-threads=1']
start=time.monotonic()
began=datetime.datetime.now(datetime.timezone.utc).isoformat()
with (out/'fixture.stdout').open('wb') as stdout,(out/'fixture.stderr').open('wb') as stderr:
 p=subprocess.Popen(argv,cwd=scratch,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
 timed_out=False
 try: code=p.wait(timeout=120)
 except subprocess.TimeoutExpired:
  timed_out=True;os.killpg(p.pid,signal.SIGTERM)
  try:code=p.wait(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);code=p.wait(timeout=3)
record={'argv':argv,'cwd':str(scratch),'environment':env,'beganAt':began,'elapsedSeconds':time.monotonic()-start,'exitCode':code,'timeoutSeconds':120,'timedOut':timed_out,'pid':p.pid,'sourceManifestSHA256':hashlib.sha256((out/'copied-source-manifest.json').read_bytes()).hexdigest(),'stdoutSHA256':hashlib.sha256((out/'fixture.stdout').read_bytes()).hexdigest(),'stderrSHA256':hashlib.sha256((out/'fixture.stderr').read_bytes()).hexdigest()}
(out/'fixture-command.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
print(json.dumps(record,indent=2))
print((out/'fixture.stdout').read_text()[-7000:])
print((out/'fixture.stderr').read_text()[-3000:])
raise SystemExit(code)
