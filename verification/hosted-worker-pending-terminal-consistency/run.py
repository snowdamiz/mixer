from pathlib import Path
import subprocess,datetime,json,hashlib,shutil,os
root=Path(__file__).resolve().parents[2];packet=Path(__file__).resolve().parent;candidate=packet/'candidate';stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run=packet/'runs'/stamp;run.mkdir(parents=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
def write(name,value): (run/name).write_text(json.dumps(value,indent=2)+'\n')
def verify():
 checks=json.loads((packet/'input-manifest.json').read_text())['checks'];bad=[]
 for e in checks:
  p=root/e['path'];b=p.read_bytes()
  if sha(b)!=e['sha256'] or len(b)!=e['bytes']:bad.append(e['path'])
 return {'checks':len(checks),'changed':bad,'allUnchanged':not bad}
write('inputs-before.json',verify());assert verify()['allUnchanged']
entries=[]
for p in sorted(candidate.rglob('*')):
 if p.is_file() and 'dist' not in p.relative_to(candidate).parts:
  b=p.read_bytes();rel=p.relative_to(candidate);dest=run/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b);entries.append({'path':str(rel),'sha256':sha(b),'bytes':len(b)})
digest=sha(''.join(f"{e['path']}\0{e['sha256']}\0{e['bytes']}\n" for e in entries).encode());write('source-manifest.json',{'algorithm':'sha256','sourceDigest':digest,'entries':entries})
node=subprocess.check_output(['which','node'],text=True).strip();commands=[]
for name,script,reportvar in [('build','build.mjs',None),('prior81','test/run.mjs','MIXER_PENDING_ENGINE_REPORT'),('review40','test/review.mjs','MIXER_TRACK_REVIEW_REPORT'),('terminal','test/terminal-consistency.mjs','MIXER_TERMINAL_REPORT')]:
 env=os.environ.copy()
 for key in ['MIXER_PENDING_TRACK_CASE','MIXER_TRACK_REVIEW_CASE','MIXER_TERMINAL_CASE']:env.pop(key,None)
 if reportvar:env[reportvar]=str(run/(name+'-report.json'))
 started=datetime.datetime.now(datetime.timezone.utc).isoformat();cmd=[node,str(candidate/script)]
 with (run/(name+'.stdout.log')).open('w') as out,(run/(name+'.stderr.log')).open('w') as err:
  try:r=subprocess.run(cmd,cwd=root,env=env,stdout=out,stderr=err,timeout=120);exitcode=r.returncode;error=None
  except subprocess.TimeoutExpired:exitcode=None;error='timeout_120_seconds'
 commands.append({'name':name,'command':cmd,'cwd':str(root),'startedUTC':started,'finishedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exitCode':exitcode,'signal':-exitcode if exitcode is not None and exitcode<0 else None,'error':error,'stdout':str((run/(name+'.stdout.log')).relative_to(root)),'stderr':str((run/(name+'.stderr.log')).relative_to(root)),'stdoutEOF':True,'stderrEOF':True})
 print(json.dumps(commands[-1]),flush=True)
 if name=='build' and exitcode!=0:break
write('commands.json',commands);write('inputs-after.json',verify())
reports={n:json.loads((run/(n+'-report.json')).read_text()) for n in ['prior81','review40','terminal'] if (run/(n+'-report.json')).exists()}
write('summary.json',{'status':'passed' if len(commands)==4 and all(c['exitCode']==0 for c in commands) and verify()['allUnchanged'] else 'failed','sourceDigest':digest,'reports':{n:{k:d.get(k) for k in ['status','cases','groupsDefined','groupsRun','groupsPassed','definedCases','trackRecheckPassed','prior54Passed']} for n,d in reports.items()}})
(packet/'latest-run.json').write_text(json.dumps({'run':str(run.relative_to(root)),'sourceDigest':digest,'status':json.loads((run/'summary.json').read_text())['status']},indent=2)+'\n')
print((run/'summary.json').read_text(),flush=True)
