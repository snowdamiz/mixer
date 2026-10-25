from pathlib import Path
import datetime,hashlib,json,os,platform,shutil,subprocess,sys
root=Path(__file__).resolve().parents[2];packet=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run=packet/'runs'/stamp;run.mkdir(parents=True)
def write(name,d):(run/name).write_text(json.dumps(d,indent=2)+'\n')
def verify():
 entries=json.loads((packet/'input-manifest.json').read_text())['checks'];changed=[]
 for e in entries:
  p=root/e['path'];b=p.read_bytes()
  if sha(b)!=e['sha256'] or len(b)!=e['bytes']:changed.append(e['path'])
 return {'checks':len(entries),'allUnchanged':not changed,'changed':changed}
write('inputs-before.json',verify());assert verify()['allUnchanged']
entries=[];closureManifests={}
for closure in ['candidate','independent-candidate','boundary-candidate']:
 subset=[]
 for p in sorted((packet/closure).rglob('*')):
  if p.is_file() and 'dist' not in p.relative_to(packet/closure).parts:
   b=p.read_bytes();rel=p.relative_to(packet);dest=run/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
   entries.append({'path':str(rel),'sha256':sha(b),'bytes':len(b)});subset.append({'path':str(p.relative_to(packet/closure)),'sha256':sha(b),'bytes':len(b)})
 closureManifests[closure]={'sourceDigest':sha(''.join(f"{e['path']}\0{e['sha256']}\0{e['bytes']}\n" for e in subset).encode()),'entries':subset}
digest=sha(''.join(f"{e['path']}\0{e['sha256']}\0{e['bytes']}\n" for e in entries).encode());write('source-manifest.json',{'algorithm':'sha256','sourceDigest':digest,'entries':entries,'closures':closureManifests})
node=str(Path(shutil.which('node')).resolve());python=str(Path(sys.executable).resolve())
versionCode="""const{createRequire}=require('node:module');const{spawnSync}=require('node:child_process');const r=createRequire(process.cwd()+'/hosted-worker-controller/package.json');console.log(JSON.stringify({node:process.version,nodeExecutable:process.execPath,platform:process.platform,architecture:process.arch,miniflare:r('miniflare/package.json').version,typescript:r('typescript/package.json').version,workersTypes:r('@cloudflare/workers-types/package.json').version,workerd:spawnSync(r('workerd').default,['--version'],{encoding:'utf8'}).stdout.trim(),workerdExecutable:r('workerd').default}));"""
versions=json.loads(subprocess.check_output([node,'-e',versionCode],cwd=root,text=True));versions.update(python=platform.python_version(),pythonExecutable=python);versions['nodeExecutableSHA256']=sha(Path(node).read_bytes());versions['workerdExecutableSHA256']=sha(Path(versions['workerdExecutable']).read_bytes());write('tool-versions.json',versions)
suites=[('build-producer','candidate/build.mjs',None),('prior81','candidate/test/run.mjs','MIXER_PENDING_ENGINE_REPORT'),('review40','candidate/test/review.mjs','MIXER_TRACK_REVIEW_REPORT'),('terminal279','candidate/test/terminal-consistency.mjs','MIXER_TERMINAL_REPORT'),('independent78','candidate/test/independent.mjs','MIXER_INDEPENDENT_REPORT'),('migration210','candidate/test/migration-history.mjs','MIXER_MIGRATION_REPORT'),('build-independent','independent-candidate/build.mjs',None),('independent69','independent-candidate/test/independent-review.mjs','REVIEW_REPORT'),('build-boundary','boundary-candidate/build.mjs',None),('boundary12','boundary-candidate/test/outbox-boundary.mjs','OUTBOX_BOUNDARY_REPORT')]
commands=[]
for name,script,reportvar in suites:
 env=os.environ.copy()
 for key in ['MIXER_PENDING_TRACK_CASE','MIXER_TRACK_REVIEW_CASE','MIXER_TERMINAL_CASE','MIXER_INDEPENDENT_FILTER','MIXER_MIGRATION_FILTER','REVIEW_ONLY']:env.pop(key,None)
 if reportvar:env[reportvar]=str(run/(name+'-report.json'))
 command=[node,str(packet/script)];started=datetime.datetime.now(datetime.timezone.utc).isoformat()
 with (run/(name+'.stdout.log')).open('w') as out,(run/(name+'.stderr.log')).open('w') as err:
  proc=subprocess.run(command,cwd=root,env=env,stdout=out,stderr=err)
 commands.append({'name':name,'command':command,'cwd':str(root),'startedUTC':started,'finishedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exitCode':proc.returncode if proc.returncode>=0 else None,'signal':-proc.returncode if proc.returncode<0 else None,'stdout':str((run/(name+'.stdout.log')).relative_to(root)),'stderr':str((run/(name+'.stderr.log')).relative_to(root)),'stdoutEOF':True,'stderrEOF':True,'environment':{reportvar:env[reportvar]} if reportvar else {}});write('commands.json',commands);print(json.dumps(commands[-1]),flush=True)
 if name.startswith('build-') and proc.returncode:break
write('inputs-after.json',verify());reports={}
for name,script,var in suites:
 p=run/(name+'-report.json')
 if var and p.exists():
  r=json.loads(p.read_text());reports[name]={'status':r['status'],'run':sum(x['status'] in ['passed','failed'] for x in r['results']),'passed':sum(x['status']=='passed' for x in r['results'])}
summary={'status':'passed' if len(commands)==len(suites) and all(c['exitCode']==0 for c in commands) and verify()['allUnchanged'] and all(r['status']=='passed' for r in reports.values()) else 'failed','sourceDigest':digest,'completeMatrix':len(commands)==len(suites),'counts':reports,'producerGroups':sum(reports.get(n,{}).get('passed',0) for n in ['prior81','review40','terminal279','independent78','migration210']),'reviewGroups':reports.get('independent69',{}).get('passed',0),'boundaryGroups':reports.get('boundary12',{}).get('passed',0)}
write('summary.json',summary);(packet/'latest-run.json').write_text(json.dumps({'run':str(run.relative_to(root)),**summary},indent=2)+'\n');print(json.dumps(summary),flush=True);raise SystemExit(0 if summary['status']=='passed' else 1)
