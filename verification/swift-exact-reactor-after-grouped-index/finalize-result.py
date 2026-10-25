#!/usr/bin/env python3
"""Classify and seal one already-recorded target failure after owned cleanup; no execution."""
import datetime
import gzip
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRIOR=ROOT/'verification/swift-exact-reactor-after-resident-index'
ROOT_SELECTION=ROOT/'verification/swift-exact-reactor-after-grouped-index-root-selection'
SELECTION_HASH='28465c0768a098eb34949beaebd6848ea9c4ee6c5690f6a17fce8b87357d674e'
CLOSURE='3ffa1055e462be74c10ee9830bf891bbd196a896dfc7a66dc6befe2a6d9bb70f'
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda:stream.read(1024*1024),b''):h.update(part)
    return h.hexdigest()
def read(name):return json.loads((HERE/name).read_bytes())
def save(name,value):(HERE/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def main():
    assert not (HERE/'result-seal.json').exists()
    assert not (HERE/'owned-scratch').exists() and not (HERE/'bin/exact-tests').exists()
    command=read('commands/target-once/receipt.json');result=read('target-once-result.json')
    cleanup=read('cleanup.json');selected=read('root-selection.json');prepared=read('prepared-seal.json');binding=read('binding.json')
    events=read('target-once-events.json')
    def event(name):return next((row['payload'] for row in events if row['event']==name),None)
    assert sha(HERE/'root-selection.json')==sha(ROOT_SELECTION/'execution.json')==SELECTION_HASH
    assert selected['selectionRevisionContext']=='4a28261b333c28b4fce386f370a19b93e735c8d2'
    assert selected['baselineClosure']==CLOSURE and selected['maxTargetAttempts']==1
    assert len(list((HERE/'commands').glob('target-*')))==1
    with gzip.open(HERE/'bin/exact-tests.gz','rb') as stream:executable=stream.read()
    binary_hash=hashlib.sha256(executable).hexdigest()
    assert binary_hash==selected['binarySHA256'] and len(executable)==selected['binaryBytes']
    for name,digest in prepared['files'].items():assert (binary_hash if name=='bin/exact-tests' else sha(HERE/name))==digest,name
    for name,digest in prepared['externalFiles'].items():assert sha(ROOT/name)==digest,name
    assert command['argv']==selected['argv'] and command['processGroupEmpty'] and command['rawStreamEOFConfirmed']
    assert command['exitCode']==101 and not command['timedOut'] and not command['passed'] and command['signalSent']==[]
    assert result['phasesBegun']==['validation','initialize','corpus_1']
    assert event('phase_reply')=='Initialized' and event('initialize')['lifecycle']=='Ready'
    assert event('corpus_2') is None and event('diagnostic_execution_complete') is False
    first=result['firstFailure']['payload']
    assert (first['stage'],first['kind'],first['code'],first['resource'],first['function'],first['offset'],first['attempted'],first['limit'])==('Cache','WorkExhausted','swift_run_work','CacheWork',3416,1077688,64000001,64000000)
    assert first['at_failure']['instructions']==15753076
    assert first['at_failure']['reservations']['live_tickets']==85 and first['at_failure']['reservations']['peak_tickets']==86
    final_failure=event('final_failure');final=event('final_cleanup_usage')
    assert all(final_failure[key]==first[key] for key in first if key!='after_cleanup')
    empty=all(value['current']==0 for value in final['reservations'].values() if isinstance(value,dict)) and final['reservations']['live_tickets']==0 and all(value['current']==0 for value in final['live'].values())
    assert empty and final['cleanup_invariant'] is None and event('cleanup_reservations_and_live_empty') is True
    assert event('cleanup_empty') is False and result['ownedCleanupEmpty'] is False
    preselection=json.loads((ROOT_SELECTION/'preselection-failure.json').read_bytes())
    assert preselection['guestStarted'] is False and preselection['targetMarkerPresent'] is False
    assert preselection['dispatchExitCode']==preselection['rootCheckExitCode']==1
    cleanup_command=read('cleanup-command.json')
    assert cleanup_command['passed'] and cleanup_command['exitCode']==0 and not cleanup_command['timedOut'] and cleanup_command['rawStreamEOFConfirmed']
    assert cleanup_command['finalGroupObservation']['state']=='absent' and cleanup_command['signalsSent']==[]
    assert cleanup['removed'] and cleanup['holderExitCode']==1
    save('target-once-classification.json',{'schema':1,'classification':'bounded-real-typed-cache-work-exhaustion-after-grouped-index-reservation','targetAttempts':1,'retryAttempted':False,'rawResultSHA256':sha(HERE/'target-once-result.json'),'rawStderrSHA256':sha(HERE/'commands/target-once/stderr'),'initializeCompleted':True,'corpus1Attempted':True,'corpus1Completed':False,'corpus2Attempted':False,'firstTypedFailure':first,'historicalFailurePreservedInFinalFailure':True,'consumingOwnerCleanupObserved':True,'finalCleanupReservationsAndLiveEmpty':empty,'finalCleanupInvariant':final['cleanup_invariant'],'rawHarnessCleanupEmpty':event('cleanup_empty'),'rawDriverOwnedCleanupEmpty':result['ownedCleanupEmpty'],'cleanupFlagExplanation':'The original CacheWork failure remains in final_failure. The unchanged success-oriented cleanup_empty also requires no retained failure; final consuming reservations/live/tickets are separately all zero with no cleanup invariant.','failurePhaseObservation':{'phase':'corpus_1','stage':first['stage'],'function':first['function'],'sourceOffset':first['offset'],'instructions':first['at_failure']['instructions'],'chargedCacheWork':first['at_failure']['cache_work'],'attemptedCacheWork':first['attempted'],'cacheWorkLimit':first['limit'],'liveTicketsAtFailure':85,'peakTicketsAtFailure':86,'cacheEntriesAtFailure':first['at_failure']['live']['cache_entries']['current'],'activePinsAtFailure':first['at_failure']['live']['active_pins']['current'],'framesAtFailure':first['at_failure']['live']['frames']['current']},'rootPreselectionCheckFailures':1,'rootRefusedPreselectionDispatches':1,'preselectionDispatchesCountAsGuestAttempts':False,'preselectionFailureReference':{'path':str((ROOT_SELECTION/'preselection-failure.json').relative_to(ROOT)),'sha256':sha(ROOT_SELECTION/'preselection-failure.json'),'record':preselection},'nativeParityObserved':False,'productionBaselineModifiedByDiagnostic':False,'budgetsChanged':False,'fullSLMatrixAccepted':False,'nativeSignedPublicAccepted':False,'gaAccepted':False})
    pre_final=final_failure['after_cleanup']
    assert pre_final['reservations']['live_tickets']==3 and pre_final['reservations']['combined']['current']==271168
    assert pre_final['reservations']['construction']['current']==269424 and pre_final['reservations']['shared']['current']==1744
    save('consuming-cleanup-audit.json',{'schema':1,'sourceEventsSHA256':sha(HERE/'target-once-events.json'),'firstFailurePreserved':True,'finalFailureAfterCleanupSnapshot':pre_final,'finalConsumingUsage':final,'finalCurrentReservationCategories':{key:value['current'] for key,value in final['reservations'].items() if isinstance(value,dict)},'finalCurrentLiveCategories':{key:value['current'] for key,value in final['live'].items()},'finalLiveTickets':0,'cleanupInvariant':None,'rawHarnessCleanupEmpty':False,'rawDriverOwnedCleanupEmpty':False,'foundationBoundaryExplanation':'ExecutionCleanupTail.complete drops caller return storage and the execution header, then record_cleanup copies the failure observation while the three foundation tickets are still charged. finish_owned_cleanup consumes the RuntimeControl foundation closure and returns the final usage. The retained failure.after_cleanup snapshot therefore has three tickets, construction 269424 plus shared 1744 = combined 271168; final_cleanup_usage has zero current ledger reservations, tickets and live counts.','historicalWasiSubmeterExplanation':'final_cleanup_usage.wasi is the copied final WASI submeter observation; its reservation fields retain historical component values. The authoritative runtime ledger reservations.wasi.current is zero after actual component cleanup.','sourceBindings':{'baseline/src/experimental_swift_reactor/execution.rs':sha(HERE/'baseline/src/experimental_swift_reactor/execution.rs'),'baseline/src/experimental_swift_reactor/control.rs':sha(HERE/'baseline/src/experimental_swift_reactor/control.rs'),'harness.rs':sha(HERE/'harness.rs')},'sourceBoundaryLocations':{'executionTailComplete':'baseline/src/experimental_swift_reactor/execution.rs:231','recordCleanup':'baseline/src/experimental_swift_reactor/control.rs:1685','finishOwnedCleanup':'baseline/src/experimental_swift_reactor/control.rs:1699','unchangedHarnessCleanup':'harness.rs:228'},'noNewDiagnosticOrGuestExecution':True})
    keys=['cache_work','execution_work','instruction_fuel','instructions','host_calls']
    snapshots=[]
    for name in ('constructed','initialize','corpus_1'):
        value=event(name);usage=value['usage']
        snapshots.append({'event':name,'cache':value['cache'],'reservations':usage['reservations'],'live':usage['live'],'work':{key:usage[key] for key in keys},'lifecycle':value['lifecycle'],'memoryBytes':value['memory_bytes']})
    save('phase-counters.json',{'schema':1,'sourceEventsSHA256':sha(HERE/'target-once-events.json'),'scope':'raw cumulative count and ownership snapshots only; corpus_1 is terminal after failure/drain, distinct from the internal failure checkpoint; no timing or performance comparison','snapshots':snapshots})
    previous_events=json.loads((PRIOR/'target-once-events.json').read_bytes())
    assert sha(PRIOR/'result-seal.json')=='05d31bc936466d9dd6c2b21c411e30e75087396e6f6903a0e6fc597f401948fd'
    def previous_event(name):return next(row['payload'] for row in previous_events if row['event']==name)
    for name in ('validation_budget','run_budget','wasi_budget','wasi_grants'):assert event(name)==previous_event(name)
    comparisons=[]
    for name in ('constructed','initialize'):
        old=previous_event(name);new=event(name)
        assert old['usage']['live']==new['usage']['live'] and old['memory_bytes']==new['memory_bytes']
        assert {key:old['usage'][key] for key in keys}=={key:new['usage'][key] for key in keys}
        assert {key:value for key,value in old['cache'].items() if key!='fixed_reserved'}=={key:value for key,value in new['cache'].items() if key!='fixed_reserved'}
        def observation(value):
            reservations=value['usage']['reservations']
            return {'fixedCacheReservation':value['cache']['fixed_reserved'],'liveTickets':reservations['live_tickets'],'peakTickets':reservations['peak_tickets'],'cacheCurrent':reservations['cache']['current'],'constructionCurrent':reservations['construction']['current'],'stateCurrent':reservations['state']['current'],'combinedCurrent':reservations['combined']['current']}
        a=observation(old);b=observation(new)
        comparisons.append({'event':name,'prior':a,'current':b,'delta':{key:b[key]-a[key] for key in a},'sameGuestCountersAndLiveShape':True})
    save('ownership-comparison.json',{'schema':1,'scope':'only directly comparable constructed and successful Initialize ownership checkpoints; identical harness, module, budgets, guest counters and live shapes; no Corpus1 failure-point comparison, CPU, timing, performance or completion claim','priorEventsSHA256':sha(PRIOR/'target-once-events.json'),'currentEventsSHA256':sha(HERE/'target-once-events.json'),'priorResultSealSHA256':sha(PRIOR/'result-seal.json'),'snapshots':comparisons})
    save('result-receipt.json',{'schema':1,'status':'sealed-single-attempt-typed-cache-work-exhaustion','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sourceRevisionContext':binding['sourceRevisionContext'],'selectionRevisionContext':selected['selectionRevisionContext'],'sourceRevisionMeaning':binding['sourceRevisionMeaning'],'baselineClosure':CLOSURE,'sourceFiles':132,'rootSelectionSHA256':SELECTION_HASH,'preparedSealSHA256':sha(HERE/'prepared-seal.json'),'preparedInputsUnchanged':True,'preparedExecutableRepresentation':'original byte-identical executable retained losslessly as bin/exact-tests.gz after owned cleanup','harnessSHA256':selected['harnessSHA256'],'driverSHA256':selected['driverSHA256'],'binarySHA256':binary_hash,'inputBindingSHA256':selected['inputBindingSHA256'],'compilerTools':binding['compilerTools'],'target':binding['target'],'targetAttempts':1,'rootPreselectionCheckFailures':1,'rootRefusedPreselectionDispatches':1,'preselectionDispatchesCountAsGuestAttempts':False,'preselectionFailureReference':str((ROOT_SELECTION/'preselection-failure.json').relative_to(ROOT)),'retryAttempted':False,'targetChildExitCode':command['exitCode'],'targetDriverExitCodeReportedByRoot':1,'timedOut':False,'signalsSent':[],'argv':command['argv'],'targetPID':command['pid'],'targetProcessGroup':command['processGroup'],'commandReceipt':'commands/target-once/receipt.json','validationUsage':event('validation_usage'),'validationObservations':event('validation_observations'),'inputOverlap':event('input_overlap'),'initializeCompleted':True,'firstFailure':result['firstFailure'],'phasesBegun':result['phasesBegun'],'failurePhaseObservation':read('target-once-classification.json')['failurePhaseObservation'],'cleanupCommandReceipt':'cleanup-command.json','cleanupCommandExecutions':1,'cleanupCommandExitCode':0,'consumingOwnerCleanupObserved':True,'finalCleanupReservationsAndLiveEmpty':True,'rawHarnessCleanupEmpty':False,'rawDriverOwnedCleanupEmpty':False,'finalCleanupUsage':final,'phaseCounters':read('phase-counters.json'),'ownershipComparison':read('ownership-comparison.json'),'processGroupEmpty':True,'rawStreamEOFConfirmed':True,'scratchRemoved':True,'logicalBytesRemoved':cleanup['logicalBytesRemoved'],'retainedExecutable':cleanup['retainedExecutable'],'nativeParity':False,'productionBaselineModifiedByDiagnostic':False,'budgetWidened':False,'fullSLMatrixAccepted':False,'productionAccountingAccepted':False,'nativeSignedPublicAccepted':False,'performanceSizeMemoryAccepted':False,'fieldLogPublishedPackageQualified':False,'physicalPhonesAttempted':False,'gaAccepted':False})
    (HERE/'result.md').write_text(f'''# Exact full Swift reactor after grouped-index reservation: result

Root selected one unchanged host diagnostic at commit
`{selected['selectionRevisionContext']}`, exact 132-file VM closure `{CLOSURE}`.
Its selection SHA-256 is `{SELECTION_HASH}`. The original 53,777,114-byte module,
original harness/workload, 86-ticket limit, 64 residents and all other budgets,
hooks, counters and cancellation contracts remained unchanged. The fresh
4,746,352-byte executable SHA-256 is `{binary_hash}`. Source-freeze context
`{binding['sourceRevisionContext']}` remains distinct from root's later commit.
The prepared packet and historical preparation document remain frozen.

The sole guest attempt failed in Corpus 1: `Cache / WorkExhausted /
swift_run_work / CacheWork`, attempted 64,000,001 against limit 64,000,000,
function 3416, byte offset 1077688. It had charged 64,000,000 cache work and
15,753,076 instructions, with 85 live and 86 peak tickets. Validation and
Initialize completed. Corpus 2 did not run. Guest stdout and stderr remained
empty; native parity and full diagnostic completion did not pass. The child
exited 101 and the unchanged driver returned failure. No timeout, process signal
or retry occurred. Counts are scope evidence, without a CPU or performance claim.

Root's earlier label audit omitted the word `cache` in human-label normalization.
The subsequent dispatch refused absent selection before a marker or guest child.
That check failure and rejected dispatch are preserved in root's
`preselection-failure.json` as nonattempts. Root then compared the actual function
ASTs, split dependent calls and separately selected the one recorded attempt.
There is exactly one target marker and one `commands/target-once` receipt.
The unrelated failed static preparation assembly also remains preserved.

The first typed CacheWork failure remains identical in `final_failure`, apart
from its appended cleanup observation. `cleanup_empty=false` and
`ownedCleanupEmpty=false` remain unchanged success-oriented flags because the
failure is retained. The final consuming snapshot separately reports every
current reservation category, live count and ticket zero, with no cleanup
invariant. `final_failure.after_cleanup` was copied before foundation consumption:
it retains three foundation tickets, construction 269,424 plus shared 1,744 =
combined 271,168 bytes. `finish_owned_cleanup` then consumes the actual foundation
closure and returns the final zero ledger. The nested final WASI submeter is a
historical copied observation; the runtime ledger's WASI current reservation is
zero. [Cleanup audit](consuming-cleanup-audit.json) binds that boundary to the
unchanged source and harness.

Only constructed and successful Initialize checkpoints are compared with the
immediate prior run. Their guest counters, live shapes and cache behavior match.
Constructed tickets are 21 versus 22; Initialize tickets are 85 versus 86. At
both checkpoints the observed fixed cache reservation is 89,232 versus 89,376
bytes, and combined current reservations are 1,608 bytes lower. These are exact
ownership observations. The two Corpus 1 failures occurred at different cursors
and are not compared as equivalent ownership or performance checkpoints.
[Ownership comparison](ownership-comparison.json) retains the arithmetic.

Target PID/PGID `{command['pid']}` is absent. All earlier owned groups are absent;
raw stdout/stderr reached EOF and their pre-signal failure evidence is preserved.
Source, input, tool binaries/sysroot, driver, harness and executable bindings were
rechecked. Before removal, exact owned path/inode and empty holder checks passed.
The unchanged cleanup command ran once, removed {cleanup['logicalBytesRemoved']:,}
logical bytes of owned scratch and retained the executable losslessly as
`bin/exact-tests.gz` ({cleanup['retainedExecutable']['gzip']['bytes']:,} bytes,
SHA-256 `{cleanup['retainedExecutable']['gzip']['sha256']}`). Its decompressed
bytes match the selected original executable. No other project's process or data
was touched.

[Result receipt](result-receipt.json), [classification](target-once-classification.json)
and [result seal](result-seal.json) bind raw evidence, exact commands, tools,
PID/PGID/EOF, source, root selection and cleanup. Verify read-only:

```sh
python3 -B verification/swift-exact-reactor-after-grouped-index/verify-result.py
```

No new diagnostic, target, compiler, native, UI, phone, provider, hosted or Git
operation was used to classify this result. Guest parity, full completion, full
SL matrix, public/signed/native execution, production accounting/caller stack,
size/startup/memory/performance, immutable published FieldLog packages consumed
from a separate repository, physical phones, store, customer/operational and GA
acceptance remain pending. Physical phones remain disconnected and deferred.
''')
    files={str(path.relative_to(HERE)):sha(path) for path in sorted(HERE.rglob('*')) if path.is_file() and path.name!='result-seal.json'}
    external={str(path.relative_to(ROOT)):sha(path) for path in [ROOT/'docs/swift-exact-reactor-after-grouped-index.md',ROOT_SELECTION/'execution.json',ROOT_SELECTION/'preselection-failure.json',ROOT_SELECTION/'root-review.json',ROOT_SELECTION/'verify.stdout',ROOT_SELECTION/'verify.stderr',ROOT_SELECTION/'verify-2.stdout',ROOT_SELECTION/'verify-2.stderr',Path(binding['target']['path'])]}
    save('result-seal.json',{'schema':1,'status':'single-attempt-typed-cache-work-exhaustion','targetAttempts':1,'files':files,'externalFiles':external})
    print(json.dumps({'sealedMembers':len(files),'externalBindings':len(external),'resultSealSHA256':sha(HERE/'result-seal.json'),'firstTypedFailure':'CacheWork','finalCleanupReservationsAndLiveEmpty':True,'scratchRemoved':True,'targetAttempts':1,'gaAccepted':False}))
if __name__=='__main__':main()
