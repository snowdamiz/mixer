#!/usr/bin/env python3
"""Root-authorized remaining regression contexts: 4 threads, <=450s each/900s aggregate."""
from pathlib import Path
import datetime,hashlib,json,os,re,signal,subprocess,time
out=Path(__file__).resolve().parent;assert not(out/'continuation-summary.json').exists()
prior=json.loads((out/'matrix-summary.json').read_text());node=Path(json.loads((out/'additional-tools.json').read_text())['node']['path']);commands=[]
def completed(path):
 s=path.read_text();m=list(re.finditer(r'^test (\S+) \.\.\. ',s,re.M));done=[]
 for i,x in enumerate(m):
  part=s[x.end():m[i+1].start() if i+1<len(m) else len(s)]
  if re.search(r'(^|\n)ok\n\s*$',part) or part.strip()=='ok' or part.startswith('ok\n'):done.append(x.group(1))
 return done
for parent in prior:
 if parent['exitCode']==0 or parent['label'] in ('fmt','clippy'):continue
 base=parent['argv'][:parent['argv'].index('--')];env=parent['environment'].copy();env['PATH']=str(node.parent)+':'+env['PATH']
 if parent['label'].startswith('compatibility'):
  stderr=(out/('matrix-'+parent['label']+'.stderr')).read_text();assert 'to rerun pass `--test span_execution_oracle`' in stderr
  targets=json.loads((out/'suffix-targets.json').read_text())['targets']
  commands.append(('suffix-'+parent['label']+'-tests',base+[flag for t in targets for flag in ('--test',t)]+['--','--nocapture','--test-threads=4'],env,parent['label'],[]))
  commands.append(('suffix-'+parent['label']+'-doc',base+['--doc','--','--nocapture','--test-threads=4'],env,parent['label'],[]))
 else:
  assert parent['label'].startswith('all-features')
  done=completed(out/('matrix-'+parent['label']+'.stdout'))
  assert len(done)==(321 if parent['label'].endswith('debug') else 396)
  (out/('completed-'+parent['label']+'.json')).write_text(json.dumps(done,indent=2)+'\n')
  commands.append(('remaining-'+parent['label'],base+['--','--nocapture','--test-threads=4',*[flag for name in done for flag in ('--skip',name)]],env,parent['label'],done))
records=[];aggregate_start=time.monotonic()
for stem,argv,env,parent,skipped in commands:
 assert not(out/f'{stem}.command.json').exists()
 remaining=900-(time.monotonic()-aggregate_start);assert remaining>0,'root additional aggregate exhausted'
 bound=min(450,remaining);manifest_ref=f'{stem}.source-manifest.json';(out/manifest_ref).write_bytes((out/'candidate-source-manifest.json').read_bytes())
 start=time.monotonic();began=datetime.datetime.now(datetime.timezone.utc).isoformat();signals=[]
 with(out/f'{stem}.stdout').open('wb') as stdout,(out/f'{stem}.stderr').open('wb') as stderr:
  p=subprocess.Popen(argv,cwd=out/'scratch',env=env,stdout=stdout,stderr=stderr,start_new_session=True);timed_out=False
  try:code=p.wait(timeout=bound)
  except subprocess.TimeoutExpired:
   timed_out=True;signals.append('SIGTERM');os.killpg(p.pid,signal.SIGTERM)
   try:code=p.wait(timeout=3)
   except subprocess.TimeoutExpired:signals.append('SIGKILL');os.killpg(p.pid,signal.SIGKILL);code=p.wait(timeout=3)
 stdout=(out/f'{stem}.stdout').read_text();totals=[tuple(map(int,m)) for m in re.findall(r'test result: \w+\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out',stdout)]
 record={'label':stem,'parentCommand':f'matrix-{parent}.command.json','argv':argv,'cwd':str(out/'scratch'),'environment':env,'beganAt':began,'elapsedSeconds':time.monotonic()-start,'exitCode':code,'timeoutSeconds':bound,'aggregateLimitSeconds':900,'aggregateElapsedSeconds':time.monotonic()-aggregate_start,'timedOut':timed_out,'pid':p.pid,'processGroupId':p.pid,'signalsSent':signals,'sourceManifestRef':manifest_ref,'sourceManifestSHA256':hashlib.sha256((out/manifest_ref).read_bytes()).hexdigest(),'stdoutSHA256':hashlib.sha256((out/f'{stem}.stdout').read_bytes()).hexdigest(),'stderrSHA256':hashlib.sha256((out/f'{stem}.stderr').read_bytes()).hexdigest(),'testsPassed':sum(t[0] for t in totals),'testsFailed':sum(t[1] for t in totals),'testsIgnored':sum(t[2] for t in totals),'testsFiltered':sum(t[4] for t in totals),'previouslyCompletedExactNames':skipped,'testResultGroups':len(totals)}
 (out/f'{stem}.command.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n');records.append(record)
 print(json.dumps({k:record[k] for k in('label','exitCode','elapsedSeconds','testsPassed','testsFailed','testsIgnored','testsFiltered','timedOut')}),flush=True)
(out/'continuation-summary.json').write_text(json.dumps(records,sort_keys=True,indent=2)+'\n');raise SystemExit(any(r['exitCode']!=0 for r in records))
