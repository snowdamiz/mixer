#!/usr/bin/env python3
"""Audit existing evidence and owned holders before the unchanged cleanup; never runs a guest."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda:f.read(1024*1024),b''):h.update(part)
    return h.hexdigest()
def read(path):return json.loads(Path(path).read_bytes())
def save(path,value):Path(path).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
spec=importlib.util.spec_from_file_location('existing_driver_for_owned_observation_only',HERE/'diagnostic.py')
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
assert not (HERE/'cleanup.json').exists() and not (HERE/'cleanup.stdout').exists()
assert not (HERE/'result-seal.json').exists()
prepared=read(HERE/'prepared-seal.json')
assert sha(HERE/'prepared-seal.json')=='73c63e969ca2087b7e798e065b4adf1200d54f186aa5ffeb5dcc5971f066946b'
for name,digest in prepared['files'].items():assert sha(HERE/name)==digest,name
for name,digest in prepared['externalFiles'].items():assert sha(ROOT/name)==digest,name
selected=read(HERE/'root-selection.json')
assert sha(HERE/'root-selection.json')==sha(ROOT/'verification/swift-exact-reactor-after-grouped-index-root-selection/execution.json')=='28465c0768a098eb34949beaebd6848ea9c4ee6c5690f6a17fce8b87357d674e'
assert selected['selectionRevisionContext']=='4a28261b333c28b4fce386f370a19b93e735c8d2'
assert selected['exactCommandSelected'] and selected['maxTargetAttempts']==1
assert len(list((HERE/'commands').glob('target-*')))==1
assert (HERE/'target-attempt-started.json').exists()
driver.assert_baseline();driver.assert_inputs()
binding=read(HERE/'binding.json')
command=read(HERE/'commands/target-once/receipt.json')
assert not command['passed'] and command['exitCode']==101 and not command['timedOut']
assert command['argv']==selected['argv'] and command['toolsBefore']==binding['compilerTools']
for key in ('sourceUnchanged','toolsUnchanged','allBoundInputsUnchanged','harnessUnchanged','driverUnchanged','argvFilesUnchanged','processGroupEmpty','rawStreamEOFConfirmed'):assert command[key],key
assert command['signalSent']==[] and command['finalGroupObservation']['state']=='absent'
assert sha(HERE/'bin/exact-tests')==selected['binarySHA256']
assert sha(HERE/'harness.rs')==selected['harnessSHA256'] and sha(HERE/'diagnostic.py')==selected['driverSHA256']
for info in binding['compilerTools'].values():
    if isinstance(info,dict):
        for name in ('actual','proxy'):
            if name in info:assert sha(info[name]['path'])==info[name]['sha256']
assert sha(binding['compilerTools']['python']['path'])==binding['compilerTools']['python']['sha256']
sysroot=binding['compilerTools']['sysroot']
for name,digest in sysroot['files'].items():assert sha(Path(sysroot['path'])/name)==digest,name
observations=[]
for path in sorted((HERE/'commands').glob('*/receipt.json')):
    recorded=read(path); observation=driver.observe_group(recorded['processGroup'])
    assert observation['state']=='absent',path
    for stream in ('stdout','stderr'):assert sha(path.parent/stream)==recorded[stream]['sha256']
    observations.append({'receipt':str(path.relative_to(HERE)),'pid':recorded['pid'],'processGroup':recorded['processGroup'],'observation':observation,'streamEOF':recorded['rawStreamEOFConfirmed']})
for path in sorted((HERE/'outer-preparation-commands').glob('*/receipt.json')):
    recorded=read(path);observation=driver.observe_group(recorded['processGroup'])
    assert observation['state']=='absent',path
    observations.append({'receipt':str(path.relative_to(HERE)),'pid':recorded['pid'],'processGroup':recorded['processGroup'],'observation':observation,'streamEOF':recorded['rawStreamEOFConfirmed']})
events=read(HERE/'target-once-events.json')
def event(name):return next(row['payload'] for row in events if row['event']==name)
first=read(HERE/'target-once-result.json')['firstFailure']['payload']
assert (first['stage'],first['kind'],first['code'],first['resource'],first['function'],first['offset'],first['attempted'],first['limit'])==('Cache','WorkExhausted','swift_run_work','CacheWork',3416,1077688,64000001,64000000)
final=event('final_cleanup_usage')
assert event('cleanup_reservations_and_live_empty') is True
assert final['cleanup_invariant'] is None and final['reservations']['live_tickets']==0
assert all(value['current']==0 for value in final['reservations'].values() if isinstance(value,dict))
assert all(value['current']==0 for value in final['live'].values())
assert event('cleanup_empty') is False
holder_checks=[]
for stem,path,arguments in [('result-precleanup-scratch-holders',HERE/'owned-scratch',['+D']),('result-precleanup-binary-holders',HERE/'bin/exact-tests',[])]:
    argv=['/usr/sbin/lsof','-nP',*arguments,str(path)]
    result=subprocess.run(argv,capture_output=True,timeout=30)
    (HERE/(stem+'.stdout')).write_bytes(result.stdout);(HERE/(stem+'.stderr')).write_bytes(result.stderr)
    assert result.returncode==1 and not result.stdout and not result.stderr
    stat=path.stat()
    holder_checks.append({'argv':argv,'exitCode':result.returncode,'pathIdentity':{'path':str(path),'device':stat.st_dev,'inode':stat.st_ino,'symlink':path.is_symlink()},'stdoutSHA256':sha(HERE/(stem+'.stdout')),'stderrSHA256':sha(HERE/(stem+'.stderr'))})
version=subprocess.run(['/usr/sbin/lsof','-v'],capture_output=True,timeout=30)
(HERE/'lsof-version.stdout').write_bytes(version.stdout);(HERE/'lsof-version.stderr').write_bytes(version.stderr)
save(HERE/'pre-cleanup-audit.json',{'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':sys.argv,'python':driver.identity(sys.executable),'pythonVersion':sys.version,'preparedInputsUnchanged':True,'sourceClosure':driver.CLOSURE,'sourceFiles':132,'targetAttempts':1,'noGuestOrNativeExecutionByAudit':True,'allOwnedGroupsAbsent':True,'ownedGroupObservations':observations,'targetPID':command['pid'],'targetProcessGroup':command['processGroup'],'targetRawStreamEOFConfirmed':True,'toolBinariesAndSysrootMatchRecordedBindings':True,'sourceBaselineAndBuildCopyMatchBindings':True,'consumingCleanupCurrentReservationsLiveAndTicketsZero':True,'successFailureFlagsPreserved':True,'holderChecks':holder_checks,'lsofTool':driver.identity('/usr/sbin/lsof'),'lsofVersionCommand':{'argv':['/usr/sbin/lsof','-v'],'exitCode':version.returncode,'stdoutSHA256':sha(HERE/'lsof-version.stdout'),'stderrSHA256':sha(HERE/'lsof-version.stderr')},'cleanupNotYetExecuted':True,'cleanupSelectedByRoot':True,'plannedCommand':['python3','-B',str((HERE/'diagnostic.py').relative_to(ROOT)),'cleanup']})
print(json.dumps({'auditPassed':True,'targetAttempts':1,'targetPID':command['pid'],'targetPGID':command['processGroup'],'currentLedgerZero':True,'allOwnedGroupsAbsent':True,'holderChecksEmpty':True,'targetRerun':False}))
