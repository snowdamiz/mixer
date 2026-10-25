#!/usr/bin/env python3
"""Remove only this review's disposable source/build/temp after exact scoped checks."""
from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess
H=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
save=lambda n,v:(H/n).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
owned=[H/n for n in ('owned-source','owned-target','owned-tmp')]
commands=[json.loads(p.read_text()) for p in sorted((H/'commands').glob('*/receipt.json'))]
assert commands and all(c['processGroupEmpty'] and not c['signalsSent'] for c in commands)
pgids={c['processGroup'] for c in commands}
psargv=['/bin/ps','-axo','pid=,pgid=,comm=']
processes=subprocess.check_output(psargv,text=True,timeout=10)
matches=[row for row in processes.splitlines() if len(row.split())>=2 and int(row.split()[1]) in pgids]
assert not matches
holders={};identities={};logical=0;executables=[]
for path in owned:
    assert path.is_dir() and not path.is_symlink() and path.parent==H
    info=path.stat();identities[path.name]={'device':info.st_dev,'inode':info.st_ino}
    for file in path.rglob('*'):
        if file.is_file():
            logical+=file.stat().st_size
            if file.parent==H/'owned-target/release/deps' and file.name.startswith('mixer_vm-') and file.suffix=='':executables.append({'path':str(file),'bytes':file.stat().st_size,'sha256':sha(file)})
    argv=['/usr/sbin/lsof','-nP','+D',str(path)]
    result=subprocess.run(argv,capture_output=True,timeout=30)
    (H/(path.name+'-holders.stdout')).write_bytes(result.stdout);(H/(path.name+'-holders.stderr')).write_bytes(result.stderr)
    holders[path.name]={'argv':argv,'exitCode':result.returncode,'stdoutSHA256':hashlib.sha256(result.stdout).hexdigest(),'stderrSHA256':hashlib.sha256(result.stderr).hexdigest(),'empty':not result.stdout and not result.stderr}
    assert result.returncode==1 and not result.stdout and not result.stderr
save('cleanup-preflight.json',{'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'ownedProcessGroups':sorted(pgids),'processQueryArgv':psargv,'processQuerySHA256':hashlib.sha256(processes.encode()).hexdigest(),'matchingOwnedProcesses':matches,'holders':holders,'deviceInodes':identities,'logicalBytesToRemove':logical,'compiledExecutables':executables,'scope':'only independent review source/target/tmp; no candidate, production, native instance or other project data'})
for path in owned:
    current=path.stat();assert {'device':current.st_dev,'inode':current.st_ino}==identities[path.name]
    assert path.is_dir() and not path.is_symlink()
    shutil.rmtree(path)
assert all(not p.exists() for p in owned)
save('cleanup.json',{'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'ownedPathsAbsent':True,'allOwnedProcessGroupsAbsent':True,'holderChecksEmpty':True,'deviceInodeChecksPassed':True,'logicalBytesRemoved':logical,'signalsSent':[],'nativeInstancesUsed':False,'liveVmQueried':False,'otherProjectsTouched':False,'candidateScratchRestored':False,'rootSelectionOrAttemptMarkerCreated':False,'fullTargetAttempts':0})
print(json.dumps({'ownedPathsAbsent':True,'logicalBytesRemoved':logical,'signalsSent':[],'candidateUntouched':True},sort_keys=True))
