from pathlib import Path
import os,subprocess,json,hashlib,datetime,shutil
root=Path(__file__).resolve().parents[2];packet=Path(__file__).resolve().parent
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run=packet/'runs'/stamp;run.mkdir(parents=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
files=[]
for p in sorted((packet/'candidate').rglob('*')):
 if p.is_file() and 'dist' not in p.relative_to(packet/'candidate').parts:
  b=p.read_bytes();rel=p.relative_to(packet/'candidate');files.append({'path':str(rel),'sha256':sha(b),'bytes':len(b)});q=run/'source'/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
manifest={'algorithm':'sha256','sourceDigest':sha(json.dumps(files,sort_keys=True,separators=(',',':')).encode()),'entries':files};(run/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
commands=[]
for name,args in [('build',['node',str(packet/'candidate/build.mjs')]),('independent',['node',str(packet/'candidate/test/independent-review.mjs')])]:
 env=os.environ.copy();env['REVIEW_REPORT']=str(run/'independent-report.json')
 c={'name':name,'command':args,'cwd':str(root),'startedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'environment':{k:env[k] for k in ['REVIEW_ONLY','REVIEW_REPORT'] if k in env}}
 with (run/(name+'.stdout.log')).open('w') as out,(run/(name+'.stderr.log')).open('w') as err:
  proc=subprocess.run(args,cwd=root,env=env,stdout=out,stderr=err)
 c.update(finishedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),exitCode=proc.returncode if proc.returncode>=0 else None,signal=-proc.returncode if proc.returncode<0 else None,stdout=str((run/(name+'.stdout.log')).relative_to(root)),stderr=str((run/(name+'.stderr.log')).relative_to(root)),stdoutEOF=True,stderrEOF=True);commands.append(c)
 if name=='build' and proc.returncode:break
(run/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
r=json.loads((run/'independent-report.json').read_text()) if (run/'independent-report.json').exists() else {'status':'build-failed'}
summary={'run':str(run.relative_to(root)),'status':r['status'],'groupsRun':r.get('groupsRun',0),'groupsPassed':r.get('groupsPassed',0),'sourceDigest':manifest['sourceDigest'],'commands':commands};(run/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(packet/'latest-run.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
