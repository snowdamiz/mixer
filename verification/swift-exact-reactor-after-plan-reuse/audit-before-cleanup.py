#!/usr/bin/env python3
"""Audit and archive this already-recorded attempt before existing cleanup; no guest run."""
import datetime
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ROOT_SELECTION=ROOT/'verification/swift-exact-reactor-after-plan-reuse-root-selection'
SELECTION_HASH='b81b166b9fe32c73daa128483150fd5fcd428e2f4b1328fd8042de4289f6f272'
PREPARED_HASH='3d7e1d2a163c63d48601c7fb4b599614c7578b8e3b8c119f8fb22ecf8bbcd39b'
spec=importlib.util.spec_from_file_location('existing_driver_observation_only',HERE/'diagnostic.py')
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
sha=driver.sha
read=driver.read

def save(name,value):driver.save(name,value)

def main():
    assert not (HERE/'pre-cleanup-audit.json').exists()
    assert not (HERE/'cleanup.json').exists() and not (HERE/'cleanup.stdout').exists()
    assert not (HERE/'result-seal.json').exists() and not (HERE/'result-inputs').exists()
    prepared=read(HERE/'prepared-seal.json')
    assert sha(HERE/'prepared-seal.json')==PREPARED_HASH
    for name,digest in prepared['files'].items():assert sha(HERE/name)==digest,name
    for name,digest in prepared['externalFiles'].items():assert sha(ROOT/name)==digest,name
    selected=read(HERE/'root-selection.json')
    assert sha(HERE/'root-selection.json')==SELECTION_HASH
    assert selected['selectionRevisionContext']=='6403eea98031207f6e40a72b55dfd3bd4e7e6ec2'
    assert selected['exactCommandSelected'] and selected['maxTargetAttempts']==1
    assert selected['preparedSealSHA256']==PREPARED_HASH and selected['noBudgetChanges']
    assert len(list((HERE/'commands').glob('target-*')))==1
    marker=read(HERE/'target-attempt-started.json')
    assert marker['rootSelection']['sha256']==SELECTION_HASH
    driver.assert_baseline();driver.assert_inputs()
    binding=read(HERE/'binding.json');command=read(HERE/'commands/target-once/receipt.json')
    wrapper=read(ROOT_SELECTION/'execution.json')
    assert wrapper['argv']==selected['outerCommand'] and wrapper['exitCode']==1
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
    for pattern in ('commands/*/receipt.json','outer-preparation-commands/*/receipt.json'):
        for path in sorted(HERE.glob(pattern)):
            recorded=read(path);observation=driver.observe_group(recorded['processGroup'])
            assert observation['state']=='absent',path
            assert recorded['rawStreamEOFConfirmed']
            if path.parent.parent.name=='commands':
                for stream in ('stdout','stderr'):assert sha(path.parent/stream)==recorded[stream]['sha256']
            observations.append({'receipt':str(path.relative_to(HERE)),'pid':recorded['pid'],'processGroup':recorded['processGroup'],'observation':observation,'streamEOF':recorded['rawStreamEOFConfirmed']})
    events=read(HERE/'target-once-events.json')
    assert events==driver.events(HERE/'commands/target-once/stdout')
    def event(name):return next((row['payload'] for row in events if row['event']==name),None)
    result=read(HERE/'target-once-result.json');first=result['firstFailure']['payload']
    assert (first['stage'],first['kind'],first['code'],first['resource'],first['function'],first['offset'],first['attempted'],first['limit'])==('Cache','WorkExhausted','swift_run_work','CacheWork',23610,4154038,64000001,64000000)
    assert first['at_failure']['instructions']==23358291 and first['at_failure']['elapsed_micros']==4840104
    assert result['phasesBegun']==['validation','initialize','corpus_1']
    assert event('phase_reply')=='Initialized' and event('initialize')['lifecycle']=='Ready'
    assert event('corpus_2') is None and event('diagnostic_execution_complete') is False
    final_failure=event('final_failure');final=event('final_cleanup_usage')
    assert all(final_failure[key]==first[key] for key in first if key!='after_cleanup')
    assert first['after_cleanup'] is None
    assert final_failure['after_cleanup']['reservations']['live_tickets']==3
    assert final_failure['after_cleanup']['reservations']['combined']['current']==271360
    assert event('cleanup_reservations_and_live_empty') is True and final['cleanup_invariant'] is None
    assert final['reservations']['live_tickets']==0
    assert all(value['current']==0 for value in final['reservations'].values() if isinstance(value,dict))
    assert all(value['current']==0 for value in final['live'].values())
    assert event('cleanup_empty') is False and result['ownedCleanupEmpty'] is False
    assert not (HERE/'owned-scratch/target').exists(),'compiler target must remain removed'
    assert sha(HERE/'owned-scratch/fieldlog-reactor.wasm')==binding['target']['sha256']
    holder_checks=[]
    for stem,path,args in [('result-precleanup-scratch-holders',HERE/'owned-scratch',['+D']),('result-precleanup-binary-holders',HERE/'bin/exact-tests',[])]:
        argv=['/usr/sbin/lsof','-nP',*args,str(path)]
        query=subprocess.run(argv,capture_output=True,timeout=30)
        (HERE/(stem+'.stdout')).write_bytes(query.stdout);(HERE/(stem+'.stderr')).write_bytes(query.stderr)
        assert query.returncode==1 and not query.stdout and not query.stderr
        stat=path.stat();assert not path.is_symlink()
        holder_checks.append({'argv':argv,'exitCode':query.returncode,'pathIdentity':{'path':str(path),'resolvedPath':str(path.resolve()),'device':stat.st_dev,'inode':stat.st_ino,'symlink':False},'stdoutSHA256':sha(HERE/(stem+'.stdout')),'stderrSHA256':sha(HERE/(stem+'.stderr'))})
    # Archive immutable copies of result inputs before removal or recompression.
    archive=HERE/'result-inputs';archive.mkdir()
    snapshots=[]
    def snapshot(source,destination):
        target=archive/destination;target.parent.mkdir(parents=True,exist_ok=True)
        original=driver.identity(source);shutil.copyfile(source,target)
        assert sha(target)==original['sha256']
        snapshots.append({'original':original,'snapshot':str(target.relative_to(HERE)),'snapshotSHA256':sha(target)})
    for name in ('prepared-seal.json','root-selection.json','target-attempt-started.json','target-once-events.json','target-once-result.json','baseline-manifest.json','copied-build-manifest.json','binding.json','binary.json','prepared-selection.json','proposed-command.json','diagnostic.py','harness.rs'):
        snapshot(HERE/name,'packet/'+name)
    for path in sorted((HERE/'commands/target-once').iterdir()):
        if path.is_file():snapshot(path,'packet/commands/target-once/'+path.name)
    for path in sorted(ROOT_SELECTION.iterdir()):
        if path.is_file():snapshot(path,'root-selection/'+path.name)
    snapshot(ROOT/'docs/swift-exact-reactor-after-plan-reuse.md','prepared-original.md')
    snapshot(HERE/'owned-scratch/vm/src/experimental_swift_reactor/lifecycle_tests.rs','copied-lifecycle-tests.rs')
    snapshot(HERE/'bin/exact-tests.gz','prepared-exact-tests.gz')
    with gzip.open(archive/'prepared-exact-tests.gz','rb') as stream:binary=stream.read()
    assert len(binary)==selected['binaryBytes'] and hashlib.sha256(binary).hexdigest()==selected['binarySHA256']
    save('result-inputs/manifest.json',{'schema':1,'archivedBeforeCleanup':True,'snapshots':snapshots,
        'uncompressedExecutable':driver.identity(HERE/'bin/exact-tests'),
        'originalModule':driver.identity(binding['target']['path']),
        'removedModuleCopy':driver.identity(HERE/'owned-scratch/fieldlog-reactor.wasm'),
        'sourceRepresentation':'all 132 baseline source files retained; copied manifest plus exact appended lifecycle source archived; tools and sysroot hash bound',
        'noGuestExecution':True})
    version=subprocess.run(['/usr/sbin/lsof','-v'],capture_output=True,timeout=30)
    (HERE/'result-lsof-version.stdout').write_bytes(version.stdout);(HERE/'result-lsof-version.stderr').write_bytes(version.stderr)
    save('pre-cleanup-audit.json',{'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'argv':sys.argv,'python':driver.identity(sys.executable),'pythonVersion':sys.version,
        'preparedInputsUnchanged':True,'preparedSealSHA256':PREPARED_HASH,'rootSelectionSHA256':SELECTION_HASH,
        'sourceClosure':driver.CLOSURE,'sourceFiles':132,'targetAttempts':1,'noGuestOrNativeExecutionByAudit':True,
        'allOwnedGroupsAbsent':True,'ownedGroupObservations':observations,'targetPID':command['pid'],'targetProcessGroup':command['processGroup'],
        'targetRawStreamEOFConfirmed':True,'toolBinariesAndSysrootMatchRecordedBindings':True,
        'sourceBaselineAndBuildCopyMatchBindings':True,'consumingCleanupCurrentReservationsLiveAndTicketsZero':True,
        'successFailureFlagsPreserved':True,'holderChecks':holder_checks,'lsofTool':driver.identity('/usr/sbin/lsof'),
        'lsofVersionCommand':{'argv':['/usr/sbin/lsof','-v'],'exitCode':version.returncode,'stdoutSHA256':sha(HERE/'result-lsof-version.stdout'),'stderrSHA256':sha(HERE/'result-lsof-version.stderr')},
        'resultInputsArchivedBeforeCleanup':True,'resultInputsManifestSHA256':sha(HERE/'result-inputs/manifest.json'),
        'preparedCompressedExecutable':driver.identity(HERE/'bin/exact-tests.gz'),
        'cleanupNotYetExecuted':True,'cleanupSelectedByRoot':True,
        'plannedCommand':['python3','-B',str((HERE/'diagnostic.py').relative_to(ROOT)),'cleanup']})
    print(json.dumps({'auditPassed':True,'targetAttempts':1,'targetPID':command['pid'],'targetPGID':command['processGroup'],
        'currentLedgerZero':True,'allOwnedGroupsAbsent':True,'holderChecksEmpty':True,'archivedInputSnapshots':len(snapshots),'targetRerun':False}))

if __name__=='__main__':main()
