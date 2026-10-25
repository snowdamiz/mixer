from pathlib import Path
import hashlib,json,subprocess,datetime,os
packet=Path(__file__).resolve().parent;root=packet.parents[1];candidate=packet/'candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
entries=[{'path':str(p.relative_to(candidate)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(candidate.rglob('*')) if p.is_file() and 'dist' not in p.relative_to(candidate).parts]
digest=hashlib.sha256(''.join(f"{e['path']}\0{e['sha256']}\0{e['bytes']}\n" for e in entries).encode()).hexdigest()
(packet/'source-manifest.json').write_text(json.dumps({'algorithm':'sha256','sourceDigest':digest,'entries':entries},indent=2)+'\n')
commands=[]
for label,cmd in [('build',['node',str(candidate/'build.mjs')]),('test',['node',str(candidate/'test/review.mjs')])]:
 start=datetime.datetime.now(datetime.timezone.utc).isoformat()
 with (packet/(label+'.stdout.log')).open('w') as stdout,(packet/(label+'.stderr.log')).open('w') as stderr:
  r=subprocess.run(cmd,cwd=root,stdout=stdout,stderr=stderr,timeout=180)
 commands.append({'name':label,'command':cmd,'cwd':str(root),'startedUTC':start,'finishedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exitCode':r.returncode,'stdout':str((packet/(label+'.stdout.log')).relative_to(root)),'stderr':str((packet/(label+'.stderr.log')).relative_to(root)),'stdoutEOF':True,'stderrEOF':True})
 if r.returncode:break
(packet/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
print(json.dumps({'commands':commands,'sourceDigest':digest}))
if (packet/'report.json').exists():
 r=json.loads((packet/'report.json').read_text()); print(json.dumps({'status':r['status'],'groupsRun':r['groupsRun'],'groupsPassed':r['groupsPassed'],'failures':[x for x in r['results'] if x['status']!='passed']}))
