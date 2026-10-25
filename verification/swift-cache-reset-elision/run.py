#!/usr/bin/env python3
"""Bounded synthetic cache/legacy tests only; never runs FieldLog or native UI."""
from pathlib import Path
import datetime,hashlib,json,os,signal,subprocess,time,sys
out=Path(__file__).resolve().parent; mode=sys.argv[1]
assert mode in ('baseline','candidate','legacy','legacy-unit','legacy-swift','precedence','malformed')
toolchain=Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
env={k:os.environ[k] for k in ('HOME','USER','LOGNAME') if k in os.environ}
env.update(PATH=str(toolchain)+':/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',CARGO_TARGET_DIR=str(out/'target'),CARGO_BUILD_JOBS='2',CARGO_NET_OFFLINE='true',CARGO_INCREMENTAL='0',RUST_TEST_THREADS='1',TMPDIR=str(out/'tmp'))
(out/'tmp').mkdir(exist_ok=True)
versions={}
for name,args in [('rustc',['--version','--verbose']),('cargo',['--version'])]:
 tool=toolchain/name;r=subprocess.run([str(tool),*args],env=env,capture_output=True,text=True,timeout=10,check=True)
 versions[name]={'path':str(tool),'sha256':hashlib.sha256(tool.read_bytes()).hexdigest(),'stdout':r.stdout,'stderr':r.stderr}
versions['python']={'version':os.sys.version,'path':os.sys.executable}
version_path=out/'tool-versions.json'
if version_path.exists(): assert json.loads(version_path.read_text())==versions
else:version_path.write_text(json.dumps(versions,sort_keys=True,indent=2)+'\n')
base=[str(toolchain/'cargo'),'test','--locked','--offline','--no-default-features','--release']
if mode=='baseline':argv=base+['--lib','--features','experimental-swift-reactor','experimental_swift_reactor::cache_tests::reset_elision_observation_fixture','--','--exact','--nocapture','--test-threads=1']
elif mode=='candidate':argv=base+['--lib','--features','experimental-swift-reactor','experimental_swift_reactor::cache_tests::','--','--nocapture','--test-threads=1']
elif mode=='legacy':argv=base+['--features','experimental-function-cache','--test','span_function_cache','--test','span_function_cache_allocations','--','--nocapture','--test-threads=1']
elif mode in ('legacy-unit','legacy-swift'):
 features='experimental-function-cache'+(',experimental-swift-reactor' if mode=='legacy-swift' else '')
 argv=base+['--lib','--features',features,'experimental::cache::tests::','--','--nocapture','--test-threads=1']
else:
 test='reset_elision_boundary_precedence_and_sticky' if mode=='precedence' else 'reset_elision_hostile_inactive_malformed_controls'
 argv=base+['--lib','--features','experimental-swift-reactor','experimental_swift_reactor::cache_tests::'+test,'--','--exact','--nocapture','--test-threads=1']
# Retries are explicit new receipts, preserving every prior output/failure.
ordinal=1
while (out/f'{mode}-{ordinal}.command.json').exists():ordinal+=1
stem=f'{mode}-{ordinal}'
manifest='baseline' if mode=='baseline' else 'candidate'
manifest_ref=f'{stem}.source-manifest.json'
(out/manifest_ref).write_bytes((out/f'{manifest}-source-manifest.json').read_bytes())
start=time.monotonic();began=datetime.datetime.now(datetime.timezone.utc).isoformat()
with (out/f'{stem}.stdout').open('wb') as stdout,(out/f'{stem}.stderr').open('wb') as stderr:
 p=subprocess.Popen(argv,cwd=out/'scratch',env=env,stdout=stdout,stderr=stderr,start_new_session=True)
 timed_out=False;signals=[]
 try:code=p.wait(timeout=180)
 except subprocess.TimeoutExpired:
  timed_out=True;signals.append('SIGTERM');os.killpg(p.pid,signal.SIGTERM)
  try:code=p.wait(timeout=3)
  except subprocess.TimeoutExpired:signals.append('SIGKILL');os.killpg(p.pid,signal.SIGKILL);code=p.wait(timeout=3)
manifest='baseline' if mode=='baseline' else 'candidate'
record={'argv':argv,'cwd':str(out/'scratch'),'environment':env,'beganAt':began,'elapsedSeconds':time.monotonic()-start,'exitCode':code,'timeoutSeconds':180,'timedOut':timed_out,'pid':p.pid,'processGroupId':p.pid,'signalsSent':signals,'sourceManifestRef':manifest_ref,'sourceManifestSHA256':hashlib.sha256((out/manifest_ref).read_bytes()).hexdigest(),'stdoutSHA256':hashlib.sha256((out/f'{stem}.stdout').read_bytes()).hexdigest(),'stderrSHA256':hashlib.sha256((out/f'{stem}.stderr').read_bytes()).hexdigest()}
(out/f'{stem}.command.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
print(json.dumps(record,indent=2));print((out/f'{stem}.stdout').read_text()[-11000:]);print((out/f'{stem}.stderr').read_text()[-5000:]);raise SystemExit(code)
