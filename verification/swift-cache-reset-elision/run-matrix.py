#!/usr/bin/env python3
"""Original contract regression contexts, bounded; isolated VM sources only."""
from pathlib import Path
import datetime,hashlib,json,os,re,signal,subprocess,time
out=Path(__file__).resolve().parent;assert not (out/'matrix-summary.json').exists()
toolchain=Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
env={k:os.environ[k] for k in ('HOME','USER','LOGNAME') if k in os.environ}
env.update(PATH=str(toolchain)+':/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',CARGO_TARGET_DIR=str(out/'target'),CARGO_BUILD_JOBS='2',CARGO_NET_OFFLINE='true',CARGO_INCREMENTAL='0',RUST_TEST_THREADS='1',TMPDIR=str(out/'tmp'))
(out/'tmp').mkdir(exist_ok=True)
features='experimental-stream-validation,experimental-function-cache,experimental-span-execution,experimental-swift-wasi'
commands=[]
for context,flags in [('default',[]),('compatibility',['--features',features]),('all-features',['--all-features'])]:
 for mode,release in [('debug',[]),('release',['--release'])]:
  commands.append((f'{context}-{mode}',[str(toolchain/'cargo'),'test','--locked','--offline','--no-default-features',*release,*flags,'--','--nocapture','--test-threads=1']))
commands += [('clippy',[str(toolchain/'cargo'),'clippy','--locked','--offline','--no-default-features','--lib','--features','experimental-swift-reactor,experimental-span-execution','--','-D','warnings']),('fmt',[str(toolchain/'cargo'),'fmt','--','--check'])]
records=[]
for label,argv in commands:
 stem='matrix-'+label;assert not (out/f'{stem}.command.json').exists()
 manifest_ref=f'{stem}.source-manifest.json';(out/manifest_ref).write_bytes((out/'candidate-source-manifest.json').read_bytes())
 began=datetime.datetime.now(datetime.timezone.utc).isoformat();start=time.monotonic();signals=[]
 with (out/f'{stem}.stdout').open('wb') as stdout,(out/f'{stem}.stderr').open('wb') as stderr:
  p=subprocess.Popen(argv,cwd=out/'scratch',env=env,stdout=stdout,stderr=stderr,start_new_session=True)
  timed_out=False
  try:code=p.wait(timeout=180)
  except subprocess.TimeoutExpired:
   timed_out=True;signals.append('SIGTERM');os.killpg(p.pid,signal.SIGTERM)
   try:code=p.wait(timeout=3)
   except subprocess.TimeoutExpired:signals.append('SIGKILL');os.killpg(p.pid,signal.SIGKILL);code=p.wait(timeout=3)
 stdout=(out/f'{stem}.stdout').read_text();totals=[tuple(map(int,m)) for m in re.findall(r'test result: \w+\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out',stdout)]
 record={'label':label,'argv':argv,'cwd':str(out/'scratch'),'environment':env,'beganAt':began,'elapsedSeconds':time.monotonic()-start,'exitCode':code,'timeoutSeconds':180,'timedOut':timed_out,'pid':p.pid,'processGroupId':p.pid,'signalsSent':signals,'sourceManifestRef':manifest_ref,'sourceManifestSHA256':hashlib.sha256((out/manifest_ref).read_bytes()).hexdigest(),'stdoutSHA256':hashlib.sha256((out/f'{stem}.stdout').read_bytes()).hexdigest(),'stderrSHA256':hashlib.sha256((out/f'{stem}.stderr').read_bytes()).hexdigest(),'testsPassed':sum(t[0] for t in totals),'testsFailed':sum(t[1] for t in totals),'testsIgnored':sum(t[2] for t in totals),'testsFiltered':sum(t[4] for t in totals),'testResultGroups':len(totals)}
 (out/f'{stem}.command.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n');records.append(record)
 print(json.dumps({k:record[k] for k in ('label','exitCode','elapsedSeconds','testsPassed','testsFailed','testsIgnored','timedOut')}),flush=True)
(out/'matrix-summary.json').write_text(json.dumps(records,sort_keys=True,indent=2)+'\n')
raise SystemExit(any(r['exitCode']!=0 for r in records))
