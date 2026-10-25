#!/usr/bin/env python3
"""Remove only the four explicitly owned disposable directories after holder/group checks."""
from pathlib import Path
import datetime,hashlib,json,os,platform,shutil,subprocess
out=Path(__file__).resolve().parent;root=out.parent.parent
assert not(out/'cleanup.json').exists()
owned=[out/name for name in ('scratch','target','tmp','baseline-format')]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((out/'baseline-manifest.json').read_text())
assert all(sha(root/'vm'/p)==h for p,h in manifest.items())
# Hash the final executed all-feature binaries before retiring their build cache.
executables={}
for mode in ('debug','release'):
 stderr=(out/f'remaining-all-features-{mode}.stderr').read_text()
 import re
 for name,path in re.findall(r'Running ([^\n]+) \(([^\n]+)\)',stderr):
  p=Path(path)
  if p.is_file():executables[str(p)]={'sha256':sha(p),'bytes':p.stat().st_size,'observation':'Final candidate executable present after successful remaining-context command','lastObservedContext':mode}
(out/'final-executables.json').write_text(json.dumps(executables,sort_keys=True,indent=2)+'\n')
commands=[]
for p in sorted(out.glob('*.command.json')):
 r=json.loads(p.read_text())
 if 'processGroupId' in r:commands.append({'commandRef':p.name,'pid':r['pid'],'processGroupId':r['processGroupId'],'signalsSent':r['signalsSent']})
groups={r['processGroupId'] for r in commands}
ps=subprocess.run(['/bin/ps','-axo','pid=,ppid=,pgid=,stat=,command='],capture_output=True,text=True,check=True,timeout=10)
members=[]
for line in ps.stdout.splitlines():
 fields=line.strip().split(None,4)
 if len(fields)==5 and (int(fields[2]) in groups or any(str(p) in fields[4] for p in owned)) and int(fields[0]) not in (os.getpid(),os.getppid()):members.append(line.strip())
assert not members,members
holders=[]
for p in owned:
 r=subprocess.run(['/usr/sbin/lsof','-nP','+D',str(p)],capture_output=True,text=True,timeout=30)
 record={'argv':['/usr/sbin/lsof','-nP','+D',str(p)],'exitCode':r.returncode,'stdout':r.stdout,'stderr':r.stderr};holders.append(record)
 assert r.returncode==1 and not r.stdout and not r.stderr,record
sizes={}
for p in owned:
 r=subprocess.run(['/usr/bin/du','-sk',str(p)],capture_output=True,text=True,check=True,timeout=10)
 sizes[str(p)]={'argv':['/usr/bin/du','-sk',str(p)],'stdout':r.stdout,'stderr':r.stderr,'kib':int(r.stdout.split()[0])}
for p in owned:assert p.parent==out and p.name in ('scratch','target','tmp','baseline-format');shutil.rmtree(p)
assert all(not p.exists() for p in owned)
assert all(sha(root/'vm'/p)==h for p,h in manifest.items())
state={'createdAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'platform':platform.platform(),'uname':dict(zip(('sysname','nodename','release','version','machine'),os.uname())),'sourceRevision':subprocess.run(['/usr/bin/git','rev-parse','HEAD'],cwd=root,capture_output=True,text=True,check=True).stdout.strip(),'vmPorcelain':subprocess.run(['/usr/bin/git','status','--porcelain','--untracked-files=normal','--','vm'],cwd=root,capture_output=True,text=True,check=True).stdout,'liveBaselineSourceFiles':len(manifest),'live132SourceHashesUnchanged':True}
(out/'source-state.json').write_text(json.dumps(state,sort_keys=True,indent=2)+'\n')
record={'createdAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'ownedPaths':[str(p) for p in owned],'holderChecks':holders,'processInspectionArgv':['/bin/ps','-axo','pid=,ppid=,pgid=,stat=,command='],'processGroupMembers':members,'commandGroups':commands,'sizeBeforeCleanup':sizes,'ownedPathsAbsent':True,'live132SourceHashesUnchanged':True,'cleanupSignalsSent':[],'hostHarnessTimeoutSignalsRetainedSeparately':True,'otherProjectPathsChanged':False,'nativeInstancesCreated':0}
(out/'cleanup.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
print(json.dumps({'ownedPathsAbsent':True,'holders':0,'processGroupMembers':0,'live132SourceHashesUnchanged':True,'removedOwnedKiB':sum(x['kib'] for x in sizes.values())},indent=2))
