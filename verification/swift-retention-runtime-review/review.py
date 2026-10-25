#!/usr/bin/env python3
"""Independent read-only audit of one retained failed reactor diagnostic."""
from pathlib import Path,PurePosixPath
import datetime,hashlib,json,subprocess,sys
H=Path(__file__).resolve().parent;ROOT=H.parent.parent
R=ROOT/'verification/swift-retention-runtime';P=ROOT/'verification/swift-retention-target-preparation';B=ROOT/'verification/swift-exact-reactor-after-plan-reuse'
F=ROOT/'verification/swift-cache-retention-review';PR=ROOT/'verification/swift-retention-target-preparation-review'
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def strict(text):
    def pairs(values):
        out={}
        for k,v in values:assert k not in out;out[k]=v
        return out
    return json.loads(text,object_pairs_hook=pairs,parse_constant=lambda v:(_ for _ in ()).throw(ValueError(v)))
read=lambda p:strict(Path(p).read_text())
write=lambda p,d:p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
def member(base,name,digest):
    n=PurePosixPath(name);assert not n.is_absolute()and '..'not in n.parts
    assert sha(base/name)==digest,name
assert sha(R/'seal.json')=='e2fe9807c8ff83d1bea08f62b1504e7b50b9e9801af24ca57beb766398f97e64'
root_seal=read(R/'seal.json')
assert len(root_seal['files'])==26
for item in root_seal['files']:
    member(ROOT,item['path'],item['sha256']);assert (ROOT/item['path']).stat().st_size==item['bytes']
assert sha(P/'prepared-seal.json')=='1411f9d65c9e74193707378e044436a2152f451b41b6ac86429cf1a362ca4bea'
prepared=read(P/'prepared-seal.json')
for name,digest in prepared['files'].items():member(P,name,digest)
for name,digest in prepared['externalFiles'].items():member(ROOT,name,digest)
assert sha(F/'seal.json')=='0d9c15a69baff78ff097f50c0fa8edaa402a6147811742407bdb76fd04c1868f'
assert sha(PR/'seal.json')=='30e79244baaa28432e976fba2d6d396827d0dec12941e02ab4c35c0800f5c60b'
for name in ['root-selection.json','target-attempt-started.json','target-once-events.json','target-once-result.json']:
    assert (R/name).read_bytes()==(P/name).read_bytes()
files=[p for p in (R/'target-command').rglob('*')if p.is_file()]
assert len(files)==8
for path in files:assert path.read_bytes()==(P/'commands/target-once'/path.relative_to(R/'target-command')).read_bytes()
assert [d.name for d in (P/'commands').iterdir()if d.is_dir()and d.name.startswith('target')]==['target-once']
selection=read(R/'root-selection.json');marker=read(R/'target-attempt-started.json');command=read(R/'target-command/receipt.json')
assert selection['exactCommandSelected']is True and selection['templateIsNotSelection']is False and selection['maxTargetAttempts']==1
assert marker['rootSelection']['sha256']==sha(R/'root-selection.json')==read(R/'selection-acceptance.json')['root_selection_sha256']
assert selection['preparedSealSHA256']==sha(P/'prepared-seal.json') and selection['reviewSealSHA256']==sha(F/'seal.json') and selection['preparationReviewSealSHA256']==sha(PR/'seal.json')
at=datetime.datetime.fromisoformat(selection['selectedUTC'])
assert at.tzinfo is not None and all(at>datetime.datetime.fromisoformat(read(path)['sealedUTC'])for path in [P/'prepared-seal.json',F/'seal.json',PR/'seal.json'])
assert datetime.datetime.fromisoformat(command['UTC'])>at
proposal=read(P/'proposed-command.json')
assert command['argv']==selection['argv']==proposal['argv'] and command['cwd']==proposal['childCwd'] and command['environment']==proposal['childEnvironment']
assert command['timeoutSeconds']==170 and command['terminationGraceSeconds']==command['killWaitSeconds']==5
assert command['sourceClosure']==sha(P/'copied-build-manifest.json')==sha(R/'target-command/source-manifest.json')==selection['sourceManifestSHA256']
assert command['baselineClosure']==selection['candidateManifestSHA256']=='d840933a706131e64c50b74812af771ead622912d57575336770434387f5b99d'
assert command['harnessSHA256']==sha(R/'target-command/harness.rs')==sha(B/'harness.rs')=='d72da7bc7aaf4e31b7093fde497f357226d3a4dd954eb577909209102a0bfb00'
assert command['driverSHA256']==sha(P/'diagnostic.py')==sha(R/'target-command/diagnostic.py')
assert command['toolsBefore']==selection['compilerTools']==read(P/'binding.json')['compilerTools']
assert command['exitCode']==101 and command['passed']is False and command['timedOut']is False and command['signalSent']==[]
assert command['started'] and command['commandFailurePreserved'] and command['processGroupEmpty'] and command['rawStreamEOFConfirmed']
assert all(command[k]for k in ['sourceUnchanged','toolsUnchanged','allBoundInputsUnchanged','harnessUnchanged','driverUnchanged','argvFilesUnchanged'])
assert command['groupBeforeCleanup']['state']==command['finalGroupObservation']['state']=='absent'
for stream in ['stdout','stderr']:assert sha(R/'target-command'/stream)==command[stream]['sha256']
before=read(R/'target-command/before-process-cleanup.json');assert before['exitCode']==101 and not before['timedOut']and before['failureEvidencePrecedesHostCleanup']
def events(path):
    out=[]
    for line in path.read_text().splitlines():
        at=line.find('MIXER_EXACT ')
        if at>=0:out.append(strict(line[at+len('MIXER_EXACT '):]))
    assert out
    return out
observed=events(R/'target-command/stdout');assert observed==read(R/'target-once-events.json')
baseline=events(B/'commands/target-once/stdout');assert baseline==read(B/'target-once-events.json')
baseline_seal=read(B/'result-seal.json')
for name in ['harness.rs','target-once-events.json','target-once-result.json','result-receipt.json','commands/target-once/stdout','commands/target-once/stderr','commands/target-once/receipt.json']:
    member(B,name,baseline_seal['files'][name])
def one(stream,name):
    values=[e['payload']for e in stream if e['event']==name];assert len(values)==1,name
    return values[0]
for name in ['validation_budget','run_budget','wasi_budget','wasi_grants']:assert one(observed,name)==one(baseline,name)
assert [e['payload']for e in observed if e['event']=='phase_begin']==['validation','initialize','corpus_1']
assert one(observed,'phase_reply')=='Initialized'and one(observed,'initialize')['lifecycle']=='Ready'
assert one(observed,'initialize')['usage']['instructions']==one(baseline,'initialize')['usage']['instructions']==37328
assert one(observed,'corpus_1')['lifecycle']=='Terminal'and one(observed,'phase_failed')=='corpus_1'
assert not any(e['event']=='corpus_2'for e in observed)
failure=one(observed,'runtime_failure');bf=one(baseline,'runtime_failure')
assert all(type(failure[n])is int for n in ['attempted','limit','function','offset'])
assert {n:failure[n]for n in ['stage','kind','resource','code','attempted','limit','function','offset']}=={'stage':'Cache','kind':'WorkExhausted','resource':'CacheWork','code':'swift_run_work','attempted':64000001,'limit':64000000,'function':22920,'offset':4029857}
assert failure['at_failure']['cache_work']==64000000 and failure['at_failure']['instructions']==8746437
assert bf['at_failure']['instructions']==23358291 and bf['attempted']==64000001 and bf['limit']==64000000 and bf['resource']=='CacheWork'
final_failure=one(observed,'final_failure');assert {k:v for k,v in final_failure.items()if k!='after_cleanup'}=={k:v for k,v in failure.items()if k!='after_cleanup'}
assert final_failure['after_cleanup']['reservations']['combined']['current']==271360
assert final_failure['after_cleanup']['reservations']['live_tickets']==3
final=one(observed,'final_cleanup_usage')
reservation_currents={k:v['current']for k,v in final['reservations'].items()if isinstance(v,dict)}
live_currents={k:v['current']for k,v in final['live'].items()}
assert len(reservation_currents)==8 and len(live_currents)==6 and all(v==0 for v in [*reservation_currents.values(),*live_currents.values(),final['reservations']['live_tickets']])
assert final['cleanup_invariant']is None and final['cache_work']==failure['at_failure']['cache_work']and final['instructions']==8746437
assert one(observed,'cleanup_reservations_and_live_empty')is True and one(observed,'cleanup_empty')is False and one(observed,'diagnostic_execution_complete')is False
result=read(R/'target-once-result.json');assert read(R/'outer.stdout')==result and (R/'outer.stderr').read_bytes()==b''
assert result['firstFailure']=={'event':'runtime_failure','payload':failure}and result['ownedCleanupEmpty']is False and result['commandPassed']is False and result['diagnosticCompleted']is False
for k in ['nativeParity','fullSLMatrixAccepted','productionAccountingAccepted','nativeSignedPublicAccepted','performanceSizeMemoryAccepted','GAaccepted']:assert result[k]is False
summary=read(R/'result-summary.json')
assert summary['classification']=='candidate_rejected_for_live_integration_after_same_budget_regression'
assert summary['actualTargetAttempts']==1 and summary['outerExitCode']==1 and summary['childExitCode']==101 and not summary['timedOut']and not summary['signalSent']
assert summary['failure']=={k:v for k,v in failure.items()if k not in ['at_failure','after_cleanup']}
assert summary['candidateInstructionsAtFailure']==8746437 and summary['baselineInstructionsAtFailure']==23358291 and summary['progressRatio']==8746437/23358291
assert summary['candidateCacheAtFailedPhase']==one(observed,'corpus_1')['cache']and summary['baselineCacheAtFailedPhase']==one(baseline,'corpus_1')['cache']
assert summary['finalReservationsAndLiveZero']and summary['originalFailurePreserved']and not summary['rawCleanupEmpty']and summary['finalCleanupInvariant']is None
assert not summary['liveIntegrationAccepted']and not summary['gaAccepted']and not summary['retrySelected']
cleanup=read(R/'cleanup.json')
assert cleanup['processGroup']==command['processGroup']and cleanup['processGroupAbsent']and cleanup['signalSent']==[]
assert cleanup['logicalBytesRemoved']==78039492 and cleanup['filesRemoved']==134
assert cleanup['deviceInodesStable']and cleanup['ownedScratchAbsent']and cleanup['restoredBinaryAbsent']and cleanup['existingGzipUnchanged']and cleanup['sealedPreparationMembersUnchanged']
assert all(x['exitCode']==1 and x['holders']==0 for x in cleanup['holderChecks'])
for name in ['binary-holders.stdout','binary-holders.stderr','scratch-holders.stdout','scratch-holders.stderr']:assert (R/name).read_bytes()==b''
assert not(P/'owned-scratch').exists()and not(P/'bin/exact-tests').exists()
assert sha(P/'bin/exact-tests.gz')==cleanup['existingGzipSHA256']=='57e650d4e2a3d0c77cf5b7a936af9c1695b3fb0b3ce2ec9abea5bf2e475c6b1d'
sizes=read(PR/'source-and-command-audit.json')['preparedSourceBytes']+marker['boundInputCopy']['bytes']+marker['binary']['bytes']
assert sizes==cleanup['logicalBytesRemoved']
target=Path(marker['targetOriginal']['path']);assert target.stat().st_size==53777114
assert sha(target)==marker['targetOriginal']['sha256']==marker['boundInputCopy']['sha256']==selection['targetSHA256']=='24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994'
assert result['targetBytesUnchangedAfterAttempt']is True
live=read(P/'live-baseline-manifest.json');assert len(live)==132 and all(sha(ROOT/'vm'/n)==digest for n,digest in live.items())
ps_argv=['/bin/ps','-axo','pid=,pgid=,stat=,command='];ps=subprocess.run(ps_argv,capture_output=True,text=True,timeout=10)
assert ps.returncode==0 and not ps.stderr
matching=[line for line in ps.stdout.splitlines()if line.strip()and int(line.split(None,3)[1])==command['processGroup']]
assert not matching
write(H/'process-observation.json',{'schema':1,'argv':ps_argv,'exitCode':ps.returncode,'ownedProcessGroup':command['processGroup'],'matchingRows':matching,'state':'absent','signalsSent':[]})
bindings={str(p.relative_to(ROOT)):sha(p)for p in [R/'seal.json',R/'result-summary.json',R/'cleanup.json',R/'finish.py',R/'root-selection.json',R/'target-attempt-started.json',R/'target-once-events.json',R/'target-once-result.json',R/'target-command/receipt.json',R/'target-command/stdout',R/'target-command/stderr',R/'outer.stdout',R/'outer.stderr',B/'result-seal.json',B/'target-once-events.json',B/'target-once-result.json',P/'prepared-seal.json',F/'seal.json',PR/'seal.json']}
write(H/'audit.json',{'schema':1,'auditedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rootResultSealSHA256':sha(R/'seal.json'),'rootSummarySHA256':sha(R/'result-summary.json'),'bindings':bindings,'actualTargetAttempts':1,'independentNewAttempts':0,'phaseSequence':['validation','initialize','corpus_1'],'typedFailure':summary['failure'],'candidateInstructions':8746437,'baselineInstructions':23358291,'progressRatio':8746437/23358291,'fourBudgetAndGrantEventsEqual':True,'initializeInstructionsEqual':37328,'finalCurrentReservations':reservation_currents,'finalCurrentLive':live_currents,'finalTickets':0,'finalCleanupInvariant':None,'originalFailurePreservedExcludingAfterCleanup':True,'legacyCleanupEmptyPreserved':False,'rawOwnedCleanupEmptyPreserved':False,'outerExitCode':1,'outerExitCodeBasis':'Exact unchanged driver returns 1 when preserved commandPassed is false; sealed root summary records 1.','childExitCode':101,'timedOut':False,'signalSent':[],'rawEvidenceCopiesByteIdentical':True,'preparationSealedMembersUnchanged':len(prepared['files']),'gzipUnchanged':True,'targetBytesUnchanged':True,'all132LiveVMFilesOriginal':True,'ownedPGIDAbsent':True,'cleanupLogicalBytes':78039492,'cleanupRegularFiles':134,'candidateRejectedForLiveIntegration':True,'retrySelected':False,'gaAccepted':False,'sourceRestoredByReview':False,'compilerGuestNativeNetworkRunByReview':False,'scope':'Independent retained-result review only; no attempt, restore, product change or historical-output rewrite.'})
print(json.dumps({'reviewed':True,'candidateRejectedForLiveIntegration':True,'attempts':1,'candidateInstructions':8746437,'baselineInstructions':23358291,'finalCurrentLedgerAndLiveZero':True,'legacyFailureFlagsPreserved':True,'preparationMembersUnchanged':len(prepared['files']),'cleanupBytes':78039492,'liveVMOriginal':True,'newAttempts':0}))
