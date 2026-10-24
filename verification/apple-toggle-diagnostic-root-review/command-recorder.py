import pathlib,sys,subprocess,json,datetime,hashlib
root=pathlib.Path('/Users/andreyyurlov/Documents/dev/mixer');out=root/'verification/apple-toggle-diagnostic-root-review/commands';out.mkdir(exist_ok=True)
label=sys.argv[1];assert label.replace('-','').isalnum();target=out/(label+'.json');assert not target.exists()
runner=root/'verification/apple-toggle-diagnostic-runtime-retry/runtime.py';argv=[sys.executable,'-B',str(runner),*sys.argv[2:]];start=datetime.datetime.now(datetime.timezone.utc).isoformat();r=subprocess.run(argv,cwd=root,capture_output=True,text=True,timeout=40);row={'argv':argv,'python':sys.version,'runnerSHA256':hashlib.sha256(runner.read_bytes()).hexdigest(),'startedUTC':start,'finishedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exitCode':r.returncode,'stdout':r.stdout,'stderr':r.stderr};target.write_text(json.dumps(row,indent=2)+'\n')
if r.returncode:print(r.stderr);sys.exit(r.returncode)
try:j=json.loads(r.stdout)
except ValueError:print(r.stdout);sys.exit()
if isinstance(j,dict):
 obs=j.get('after',j.get('observations',{}));print(json.dumps({'candidate':j.get('candidate'),'command':j.get('command'),'checksPassed':j.get('checksPassed'),'checks':j.get('checks'),'stage':obs.get('stage'),'state':obs.get('state'),'reference':obs.get('reference'),'traceEntries':len(obs.get('trace',{}).get('entries',[])) if isinstance(obs.get('trace'),dict)else None,'keys':list(obs)},indent=2))
else:print(j)
