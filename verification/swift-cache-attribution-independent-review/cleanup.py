#!/usr/bin/env python3
"""Remove only this review's identified scratch after scoped holder checks."""
from pathlib import Path
import datetime, hashlib, json, shutil, subprocess
H=Path(__file__).resolve().parent
dump=lambda p,x:p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
load=lambda p:json.loads(p.read_text())
command=load(H/'command.json')
assert command['exitCode']==0 and not command['timedOut'] and not command['signalsSent']
psargv=['/bin/ps','-axo','pid=,pgid=,comm=']
def groups():
    rows=subprocess.run(psargv,capture_output=True,text=True,check=True,timeout=10)
    return [r for r in rows.stdout.splitlines() if len(r.split())>=2 and int(r.split()[1])==command['processGroup']]
pre={'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'processCheckArgv':psargv,'ownedProcessGroup':command['processGroup'],'matchingOwnedProcesses':groups(),'holders':{},'identities':{}}
assert not pre['matchingOwnedProcesses']
ids=load(H/'cleanup-identities.json')
total=0
for n,identity in ids.items():
    p=H/n
    assert p.is_dir() and not p.is_symlink()
    observed={'device':p.stat().st_dev,'inode':p.stat().st_ino}
    pre['identities'][n]={'expected':identity,'observed':observed}
    assert observed==identity
    argv=['/usr/sbin/lsof','-nP','+D',str(p)]
    r=subprocess.run(argv,capture_output=True,text=True,timeout=20)
    pre['holders'][n]={'argv':argv,'exitCode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
    assert r.returncode==1 and not r.stdout and not r.stderr
    total+=sum(q.stat().st_size for q in p.rglob('*') if q.is_file())
dump(H/'cleanup-preflight.json',pre)
# Recheck group and identities immediately before the scoped removal.
assert not groups()
for n,identity in ids.items():
    p=H/n
    assert {'device':p.stat().st_dev,'inode':p.stat().st_ino}==identity
    shutil.rmtree(p)
post={'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'logicalBytesRemoved':total,'ownedPathsAbsent':all(not (H/n).exists() for n in ids),
    'allOwnedProcessGroupsAbsent':not groups(),'holderChecksEmpty':True,'deviceInodeChecksPassed':True,
    'signalsSent':[],'nativeInstancesUsed':False,'otherProjectsTouched':False,'liveVmQueried':False}
assert post['ownedPathsAbsent'] and post['allOwnedProcessGroupsAbsent']
dump(H/'cleanup.json',post)
dump(H/'cleanup-tools.json',{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path('/bin/ps'),Path('/usr/sbin/lsof')]})
print(json.dumps(post,sort_keys=True))
