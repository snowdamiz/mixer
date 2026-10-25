#!/usr/bin/env python3
"""Read-only checks of the recorded attempt and cleanup; never compiles or runs a guest."""
import gzip
import hashlib
import json
import os
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ROOT_SELECTION=ROOT/'verification/swift-exact-reactor-after-plan-reuse-root-selection'
PRIOR=ROOT/'verification/swift-exact-reactor-after-grouped-index'
CLOSURE='16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd'
SELECTION_HASH='b81b166b9fe32c73daa128483150fd5fcd428e2f4b1328fd8042de4289f6f272'
PREPARED_HASH='3d7e1d2a163c63d48601c7fb4b599614c7578b8e3b8c119f8fb22ecf8bbcd39b'
HARNESS_HASH='d72da7bc7aaf4e31b7093fde497f357226d3a4dd954eb577909209102a0bfb00'
def sha(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):value.update(chunk)
    return value.hexdigest()
def read(name):return json.loads((HERE/name).read_bytes())
def strict(text):
    def pairs(items):
        result={}
        for key,value in items:
            assert key not in result,key
            result[key]=value
        return result
    return json.loads(text,object_pairs_hook=pairs,parse_constant=lambda value:(_ for _ in ()).throw(ValueError(value)))
def group_absent(pgid):
    try:os.killpg(pgid,0)
    except ProcessLookupError:return True
    return False

def check():
    assert not (HERE/'owned-scratch').exists() and not (HERE/'bin/exact-tests').exists()
    assert sha(HERE/'prepared-seal.json')==PREPARED_HASH
    assert sha(HERE/'root-selection.json')==SELECTION_HASH
    selected=read('root-selection.json');prepared=read('prepared-seal.json');binding=read('binding.json')
    with gzip.open(HERE/'bin/exact-tests.gz','rb') as stream:executable=stream.read()
    binary_hash=hashlib.sha256(executable).hexdigest()
    with gzip.open(HERE/'result-inputs/prepared-exact-tests.gz','rb') as stream:prepared_executable=stream.read()
    assert executable==prepared_executable
    assert selected['binarySHA256']==binary_hash and selected['binaryBytes']==len(executable)==4878784
    for name,digest in prepared['files'].items():
        actual=binary_hash if name=='bin/exact-tests' else sha(HERE/'result-inputs/prepared-exact-tests.gz') if name=='bin/exact-tests.gz' else sha(HERE/name)
        assert actual==digest,name
    for name,digest in prepared['externalFiles'].items():assert sha(ROOT/name)==digest,name
    baseline=read('baseline-manifest.json');copied=read('copied-build-manifest.json')
    assert len(baseline)==132 and sha(HERE/'baseline-manifest.json')==CLOSURE
    for name,digest in baseline.items():
        assert sha(HERE/'baseline'/name)==digest,name
        assert sha(ROOT/'vm'/name)==digest,name
    changed=[name for name in baseline if baseline[name]!=copied[name]]
    assert changed==['src/experimental_swift_reactor/lifecycle_tests.rs']
    append='\n// Isolated diagnostic only; baseline production bytes are unchanged.\ninclude!('+json.dumps(str(HERE/'harness.rs'))+');\n'
    expected=(HERE/'baseline'/changed[0]).read_bytes()+append.encode()
    assert hashlib.sha256(expected).hexdigest()==copied[changed[0]]
    assert (HERE/'result-inputs/copied-lifecycle-tests.rs').read_bytes()==expected
    for info in binding['inputs']:assert sha(info['path'])==info['sha256'],info['path']
    assert binding['baselineClosure']==CLOSURE
    assert sha(binding['target']['path'])==binding['target']['sha256']==selected['targetSHA256']
    assert Path(binding['target']['path']).stat().st_size==selected['targetBytes']==53777114
    tools=binding['compilerTools']
    for info in tools.values():
        if isinstance(info,dict):
            for name in ('actual','proxy'):
                if name in info:assert sha(info[name]['path'])==info[name]['sha256']
    assert sha(tools['python']['path'])==tools['python']['sha256']
    for name,digest in tools['sysroot']['files'].items():assert sha(Path(tools['sysroot']['path'])/name)==digest,name
    assert selected['exactCommandSelected'] and selected['maxTargetAttempts']==1 and selected['noBudgetChanges']
    assert selected['baselineClosure']==CLOSURE and selected['selectionRevisionContext']=='6403eea98031207f6e40a72b55dfd3bd4e7e6ec2'
    assert selected['preparedSealSHA256']==PREPARED_HASH and selected['preparedSelectionSHA256']==sha(HERE/'prepared-selection.json')
    assert selected['harnessSHA256']==sha(HERE/'harness.rs')==HARNESS_HASH
    assert selected['driverSHA256']==sha(HERE/'diagnostic.py') and selected['inputBindingSHA256']==sha(HERE/'binding.json')
    for name,digest in selected['boundEvidence'].items():assert sha(HERE/name)==digest,name
    commands=[]
    for path in sorted((HERE/'commands').glob('*/receipt.json')):
        command=json.loads(path.read_bytes())
        assert command['processGroupEmpty'] and command['finalGroupObservation']['state']=='absent'
        assert command['rawStreamEOFConfirmed'] and command['signalSent']==[] and not command['timedOut']
        assert command['toolsBefore']==tools and group_absent(command['processGroup'])
        for field in ('sourceUnchanged','toolsUnchanged','allBoundInputsUnchanged','harnessUnchanged','driverUnchanged','argvFilesUnchanged'):assert command[field],(path,field)
        for stream in ('stdout','stderr'):assert sha(path.parent/stream)==command[stream]['sha256']
        assert sha(path.parent/'harness.rs')==command['harnessSHA256']
        assert sha(path.parent/'diagnostic.py')==command['driverSHA256']
        assert command['baselineClosure']==CLOSURE and command['sourceClosure']==sha(HERE/'copied-build-manifest.json')
        assert json.loads((path.parent/'source-manifest.json').read_bytes())==copied
        for info in command['argvFileIdentities']:
            assert (binary_hash if info['path']==str(HERE/'bin/exact-tests') else sha(info['path']))==info['sha256']
        if path.parent.name!='target-once':assert command['passed'] and command['exitCode']==0
        commands.append(path.parent.name)
    assert commands==['build-001','control-001','control-002','driver-observation-controls','list-001','target-once']
    command=read('commands/target-once/receipt.json')
    assert command['argv']==selected['argv'] and command['timeoutSeconds']==170
    assert command['terminationGraceSeconds']==command['killWaitSeconds']==5
    assert command['exitCode']==101 and not command['passed'] and command['processGroup']==95928
    marker=read('target-attempt-started.json')
    assert marker['rootSelection']['sha256']==SELECTION_HASH
    assert marker['binary']['sha256']==binary_hash and marker['boundInputCopy']['sha256']==selected['targetSHA256']
    assert len(list((HERE/'commands').glob('target-*')))==1
    early=read('commands/target-once/before-process-cleanup.json')
    assert early['failureEvidencePrecedesHostCleanup'] and early['exitCode']==101 and not early['timedOut']
    for stream in ('stdout','stderr'):assert early[stream]['sha256']==command[stream]['sha256']
    result=read('target-once-result.json');events=read('target-once-events.json')
    raw=[]
    for line in (HERE/'commands/target-once/stdout').read_text().splitlines():
        at=line.find('MIXER_EXACT ')
        if at>=0:raw.append(strict(line[at+len('MIXER_EXACT '):]))
    assert raw==events
    def event(name):return next((row['payload'] for row in events if row['event']==name),None)
    failure_events=[row for row in events if row['event'] in ('validation_failure','adoption_failure','construction_failure','runtime_failure','guest_output_failure','phase_failed')]
    assert result['firstFailure']==failure_events[0] and result['firstFailure']['event']=='runtime_failure'
    assert result['targetAttempted'] and not result['commandPassed'] and not result['nativeParity']
    assert result['phasesBegun']==['validation','initialize','corpus_1']
    assert event('phase_reply')=='Initialized' and event('initialize')['lifecycle']=='Ready'
    assert event('corpus_2') is None and event('diagnostic_execution_complete') is False
    first=result['firstFailure']['payload'];final_failure=event('final_failure');final=event('final_cleanup_usage')
    assert (first['stage'],first['kind'],first['code'],first['resource'],first['function'],first['offset'],first['attempted'],first['limit'])==('Cache','WorkExhausted','swift_run_work','CacheWork',23610,4154038,64000001,64000000)
    assert first['at_failure']['instructions']==23358291 and first['at_failure']['elapsed_micros']==4840104
    assert first['at_failure']['cache_work']==64000000 and first['after_cleanup'] is None
    assert first['at_failure']['reservations']['live_tickets']==85 and first['at_failure']['reservations']['peak_tickets']==86
    assert all(final_failure[key]==first[key] for key in first if key!='after_cleanup')
    after=final_failure['after_cleanup']
    assert after['reservations']['live_tickets']==3 and after['reservations']['combined']['current']==271360
    assert after['reservations']['construction']['current']==269616 and after['reservations']['shared']['current']==1744
    assert all(value['current']==0 for value in final['reservations'].values() if isinstance(value,dict))
    assert final['reservations']['live_tickets']==0 and all(value['current']==0 for value in final['live'].values())
    assert final['cleanup_invariant'] is None and event('cleanup_reservations_and_live_empty') is True
    assert event('cleanup_empty') is False and result['ownedCleanupEmpty'] is False
    for row in events:
        value=row['payload']
        if isinstance(value,dict) and 'stdout_hex' in value:
            for stream in ('stdout','stderr'):assert value[stream]=='' and bytes.fromhex(value[stream+'_hex'])==b''
    prior_events=json.loads((PRIOR/'target-once-events.json').read_bytes())
    def prior_event(name):return next(row['payload'] for row in prior_events if row['event']==name)
    assert sha(PRIOR/'result-seal.json')=='91c71f2c6b6520e141b9226f7675a4578d0d37865aa1dfcfafc9e4dad31acb8c'
    for name in ('validation_budget','run_budget','wasi_budget','wasi_grants'):assert event(name)==prior_event(name)
    wrapper=json.loads((ROOT_SELECTION/'execution.json').read_bytes())
    assert wrapper['argv']==selected['outerCommand'] and wrapper['exitCode']==1
    assert strict((ROOT_SELECTION/'target.stdout').read_text())==result and (ROOT_SELECTION/'target.stderr').read_bytes()==b''
    snapshots=read('result-inputs/manifest.json')
    assert snapshots['archivedBeforeCleanup'] and snapshots['noGuestExecution']
    for row in snapshots['snapshots']:assert sha(HERE/row['snapshot'])==row['snapshotSHA256']==row['original']['sha256']
    assert snapshots['uncompressedExecutable']['sha256']==binary_hash
    assert snapshots['removedModuleCopy']['sha256']==snapshots['originalModule']['sha256']==selected['targetSHA256']
    audit=read('pre-cleanup-audit.json')
    assert audit['preparedInputsUnchanged'] and audit['allOwnedGroupsAbsent'] and audit['toolBinariesAndSysrootMatchRecordedBindings']
    assert audit['sourceBaselineAndBuildCopyMatchBindings'] and audit['consumingCleanupCurrentReservationsLiveAndTicketsZero']
    assert audit['resultInputsManifestSHA256']==sha(HERE/'result-inputs/manifest.json')
    for row in audit['ownedGroupObservations']:assert row['observation']['state']=='absent' and row['streamEOF'] and group_absent(row['processGroup'])
    for row in audit['holderChecks']:assert row['exitCode']==1 and not row['pathIdentity']['symlink']
    cleanup_command=read('cleanup-command.json');cleanup=read('cleanup.json')
    assert cleanup_command['passed'] and cleanup_command['exitCode']==0 and not cleanup_command['timedOut']
    assert cleanup_command['argv'][1:]==['-B','verification/swift-exact-reactor-after-plan-reuse/diagnostic.py','cleanup']
    assert cleanup_command['timeoutSeconds']==90 and cleanup_command['terminationGraceSeconds']==cleanup_command['killWaitSeconds']==5
    assert cleanup_command['signalsSent']==[] and cleanup_command['rawStreamEOFConfirmed']
    assert cleanup_command['finalGroupObservation']['state']=='absent' and group_absent(cleanup_command['processGroup'])
    assert cleanup_command['preCleanupAuditSHA256']==sha(HERE/'pre-cleanup-audit.json')
    for stream in ('stdout','stderr'):assert sha(HERE/('cleanup.'+stream))==cleanup_command[stream]['sha256']
    assert cleanup['removed'] and cleanup['holderExitCode']==1
    assert cleanup['retainedExecutable']['uncompressed']['sha256']==binary_hash
    assert sha(HERE/'bin/exact-tests.gz')==cleanup['retainedExecutable']['gzip']['sha256']
    assert (HERE/'cleanup.stderr').read_bytes()==b''
    assert all((HERE/(name+'.stdout')).read_bytes()==b'' and (HERE/(name+'.stderr')).read_bytes()==b'' for name in ('scratch-holders','binary-holders'))
    return {'selected':selected,'prepared':prepared,'binding':binding,'command':command,'result':result,'events':events,
        'event':event,'first':first,'finalFailure':final_failure,'final':final,'cleanup':cleanup,'cleanupCommand':cleanup_command,
        'binaryHash':binary_hash,'commands':commands,'priorEvent':prior_event,'wrapper':wrapper,'snapshots':snapshots}
