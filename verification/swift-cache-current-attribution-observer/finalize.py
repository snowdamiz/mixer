#!/usr/bin/env python3
"""Record finite observations; archive source only; clean exact owned scratch."""
from pathlib import Path
import datetime,gzip,hashlib,json,os,shutil,subprocess,tarfile
H=Path(__file__).resolve().parent;S=H/'owned-source';B=H/'owned-target';T=H/'owned-tmp';P=H.parent/'swift-plan-cache-remaining-work-diagnosis'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(n,v):(H/n).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
assert not (H/'cleanup.json').exists()
command=json.loads((H/'command.json').read_text());assert command['exitCode']==0 and not command['timedOut']
text=(H/'finite.stdout').read_text();rows=[];other={}
for line in text.splitlines():
 for marker,key in [('ATTR_CASE ','observations'),('ATTR_BOUNDARY ','boundary'),('ATTR_PREFIX ','prefixes'),('ATTR_LAYOUT ','layout'),('ATTR_MAX_SNAPSHOT ','maxSnapshot')]:
  if marker in line:
   row=json.loads(line.split(marker,1)[1]);
   if key=='observations':rows.append(row)
   else:assert key not in other;other[key]=row
assert len(rows)==13 and all(k in other for k in ['boundary','prefixes','layout','maxSnapshot'])
original=json.loads((P/'finite-observations.json').read_text())['observations']
for a,b in zip(rows,original):
 for key in ['case','work','credits','calls','plans','completed','hits','misses','decodes','evictions']:assert a[key]==b[key],key
 assert sum(a['credits'])==a['work'] and a['distinct']+a['repeated']==a['completed']
 assert sum(a['scan_credits'])==a['credits'][6] and sum(a['scan_calls'])==a['calls'][6]
 assert sum(a['build_credits'])==a['credits'][13] and sum(a['build_calls'])==a['calls'][13]
 assert sum(a['scan_published'])==a['plans'][3]
save('finite-observations.json',{'observations':rows,**other})
source=json.loads((H/'copied-source-manifest.json').read_text());assert {n:sha(S/n) for n in source}==source
with (H/'isolated-source.tar.gz').open('wb') as out:
 with gzip.GzipFile(filename='',mode='wb',fileobj=out,mtime=0) as gz:
  with tarfile.open(fileobj=gz,mode='w') as archive:
   for n in source:
    info=tarfile.TarInfo(n);info.size=(S/n).stat().st_size;info.mode=0o644
    with (S/n).open('rb') as file:archive.addfile(info,file)
commands=[json.loads((H/n/'command.json').read_text()) for n in ['attempt-1','attempt-2','attempt-3']]+[command]
psargv=['/bin/ps','-axo','pid=,pgid=,comm='];p=subprocess.run(psargv,capture_output=True,text=True,check=True,timeout=10)
groups={str(c['processGroup']):[r.strip() for r in p.stdout.splitlines() if len(r.split())>=2 and int(r.split()[1])==c['processGroup']] for c in commands}
assert not any(groups.values())
holders={}
for d in [S,B,T]:
 argv=['/usr/sbin/lsof','-nP','+D',str(d)];q=subprocess.run(argv,capture_output=True,text=True,timeout=20)
 holders[str(d)]={'argv':argv,'exitCode':q.returncode,'stdout':q.stdout,'stderr':q.stderr}
assert all(v['exitCode']==1 and not v['stdout'] and not v['stderr'] for v in holders.values())
ident=json.loads((H/'cleanup-identities.json').read_text())
current={str(d):{'device':d.stat().st_dev,'inode':d.stat().st_ino} for d in [S,B,T]};assert current==ident
save('cleanup-preflight.json',{'processScanArgv':psargv,'processScanExitCode':p.returncode,'ownedProcessGroups':groups,'holders':holders,'identitiesBeforeRemoval':current,'signalsRequired':False})
logical=sum(f.stat().st_size for d in [S,B,T] for f in d.rglob('*') if f.is_file())
for d in [S,B,T]:
 assert {'device':d.stat().st_dev,'inode':d.stat().st_ino}==ident[str(d)];shutil.rmtree(d)
save('cleanup.json',{'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'ownedPathsAbsent':all(not d.exists() for d in [S,B,T]),'allOwnedProcessGroupsAbsent':not any(groups.values()),'holderChecksEmpty':True,'deviceInodeChecksPassed':True,'signalsSent':[],'logicalBytesRemoved':logical,'nativeInstancesUsed':False,'otherProjectsTouched':False,'archiveContainsSourceOnly':True,'liveVmQueried':False})
for n,args in [('ps',[]),('lsof',['-v'])]:
 path='/bin/ps' if n=='ps' else '/usr/sbin/lsof'
 info={'path':path,'sha256':sha(path),'versionMeaning':'system utility version is bound by binary SHA256 and platform version'}
 if args:
  q=subprocess.run([path,*args],capture_output=True,text=True,timeout=10);info.update(versionArgv=[path,*args],exitCode=q.returncode,stdout=q.stdout,stderr=q.stderr)
 other[n]=info
save('cleanup-tools.json',{k:other[k] for k in ['ps','lsof']})
print(json.dumps({'finiteTestsPassed':4,'observations':len(rows),'workPrefixes':other['prefixes']['work_prefixes'],'cancellationPrefixes':other['prefixes']['cancellation_prefixes'],'layout':other['layout'],'sourceArchiveSHA256':sha(H/'isolated-source.tar.gz'),'sourceArchiveBytes':(H/'isolated-source.tar.gz').stat().st_size,'cleanupComplete':True,'logicalBytesRemoved':logical},sort_keys=True))
