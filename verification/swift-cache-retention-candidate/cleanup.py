#!/usr/bin/env python3
"""Retire only this lane's exact build/tmp/source copies after archive checks."""
from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess,tarfile
H=Path(__file__).resolve().parent
for label,manifest_name in [('baseline','baseline-test-manifest.json'),('candidate','candidate-manifest.json')]:
    expected=json.loads((H/manifest_name).read_text())
    with tarfile.open(H/f'{label}-source.tar.gz','r:gz') as archive:
        members=archive.getmembers()
        assert len(members)==len(expected) and all(m.isfile() for m in members)
        actual={m.name:hashlib.sha256(archive.extractfile(m).read()).hexdigest() for m in members}
    assert actual==expected
roots=[H/n for n in ['owned-target','owned-tmp','baseline','candidate']]
assert all(p.is_dir() and not p.is_symlink() for p in roots)
identities={str(p):[p.stat().st_dev,p.stat().st_ino] for p in roots}
ps=subprocess.check_output(['/bin/ps','-axo','pid,ppid,command'],text=True)
owned=[line for line in ps.splitlines() if any(str(p) in line for p in roots)]
assert not owned,owned
holders=[]
for p in roots:
    argv=['/usr/sbin/lsof','-nP','+D',str(p)]
    observed=subprocess.run(argv,text=True,capture_output=True,timeout=45)
    holders.append({'argv':argv,'exitCode':observed.returncode,'stdout':observed.stdout,'stderr':observed.stderr})
    assert observed.returncode in (0,1) and not observed.stdout.strip(),holders[-1]
logical=0;files=0
for p in roots:
    for q in p.rglob('*'):
        if q.is_file() and not q.is_symlink():logical+=q.stat().st_size;files+=1
(H/'cleanup-preflight.json').write_text(json.dumps({'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'identities':identities,'ownedProcesses':owned,'holderChecks':holders,'regularFiles':files,'logicalBytes':logical,'archivesVerified':True},indent=2,sort_keys=True)+'\n')
for p in roots:
    assert [p.stat().st_dev,p.stat().st_ino]==identities[str(p)]
    shutil.rmtree(p)
assert all(not p.exists() for p in roots)
(H/'cleanup.json').write_text(json.dumps({'schema':1,'completedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'removed':[str(p) for p in roots],'removedRegularFiles':files,'removedLogicalBytes':logical,'ownedProcessesAbsent':True,'holdersAbsent':True,'deviceInodeChecksPassed':True,'sourceArchivesPreserved':True,'liveVMUnmodified':True,'otherProcessesOrDataModified':False,'scope':'Owned host build/tmp/source scratch only; no simulator/emulator/physical-device activity.'},indent=2,sort_keys=True)+'\n')
print(json.dumps({'removedLogicalBytes':logical,'regularFiles':files,'sourceArchivesPreserved':True}))
