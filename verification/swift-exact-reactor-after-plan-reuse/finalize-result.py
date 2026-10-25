#!/usr/bin/env python3
"""Classify and seal the one existing attempt after its one cleanup; no guest execution."""
import datetime
import json
from pathlib import Path
import result_evidence as evidence
HERE=evidence.HERE
ROOT=evidence.ROOT
DOC=ROOT/'docs/swift-exact-reactor-after-plan-reuse-result.md'
def save(name,value):(HERE/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def main():
    assert not (HERE/'result-seal.json').exists(),'seal once; preserve failures'
    data=evidence.check()
    event=data['event'];first=data['first'];final=data['final'];selected=data['selected'];command=data['command'];cleanup=data['cleanup']
    after=data['finalFailure']['after_cleanup'];binding=data['binding']
    save('target-once-classification.json',{'schema':1,'classification':'bounded-real-typed-cache-work-exhaustion-after-decode-plan-reuse',
        'targetAttempts':1,'retryAttempted':False,'rawResultSHA256':evidence.sha(HERE/'target-once-result.json'),
        'rawStdoutSHA256':evidence.sha(HERE/'commands/target-once/stdout'),'rawStderrSHA256':evidence.sha(HERE/'commands/target-once/stderr'),
        'initializeCompleted':True,'corpus1Attempted':True,'corpus1Completed':False,'corpus2Attempted':False,
        'firstTypedFailure':first,'causalFailurePreservedInFinalFailure':True,
        'finalCleanupReservationsAndLiveEmpty':True,'finalCleanupInvariant':None,
        'rawHarnessCleanupEmpty':False,'rawDriverOwnedCleanupEmpty':False,
        'cleanupFlagExplanation':'Retained failure makes success-oriented cleanup flags false; final consuming runtime ledger separately has zero current categories/live counts/tickets.',
        'failurePhaseObservation':{'phase':'corpus_1','stage':first['stage'],'function':first['function'],'sourceOffset':first['offset'],
            'instructions':first['at_failure']['instructions'],'elapsedMicros':first['at_failure']['elapsed_micros'],
            'chargedCacheWork':first['at_failure']['cache_work'],'attemptedCacheWork':first['attempted'],'cacheWorkLimit':first['limit'],
            'liveTicketsAtFailure':85,'peakTicketsAtFailure':86,'cacheEntriesAtFailure':64,'activePinsAtFailure':17,'framesAtFailure':16},
        'budgetsChanged':False,'sourceUnchanged':True,'nativeParityObserved':False,
        'fullSLMatrixAccepted':False,'productionAccountingAccepted':False,'nativeSignedPublicAccepted':False,'gaAccepted':False})
    save('consuming-cleanup-audit.json',{'schema':1,'sourceEventsSHA256':evidence.sha(HERE/'target-once-events.json'),
        'firstFailurePreserved':True,'firstTypedFailure':first,'finalFailure':data['finalFailure'],
        'finalFailureAfterCleanupSnapshot':after,'finalConsumingUsage':final,
        'finalCurrentReservationCategories':{key:value['current'] for key,value in final['reservations'].items() if isinstance(value,dict)},
        'finalCurrentLiveCategories':{key:value['current'] for key,value in final['live'].items()},
        'finalLiveTickets':0,'cleanupInvariant':None,'rawHarnessCleanupEmpty':False,'rawDriverOwnedCleanupEmpty':False,
        'foundationBoundaryExplanation':'ExecutionCleanupTail.complete drops return storage and execution header, then record_cleanup copies the retained failure with three foundation tickets still charged. finish_owned_cleanup consumes the RuntimeControl foundation closure. The copied failure.after_cleanup has construction 269616 plus shared 1744 = combined 271360; final_cleanup_usage has all current ledger categories, live counts and tickets zero.',
        'historicalWasiSubmeterExplanation':'The nested WASI reservation submeter is a historical copied component observation; authoritative runtime ledger reservations.wasi.current is zero after consuming cleanup.',
        'sourceBindings':{name:evidence.sha(HERE/name) for name in ('baseline/src/experimental_swift_reactor/execution.rs','baseline/src/experimental_swift_reactor/control.rs','harness.rs')},
        'sourceBoundaryLocations':{'executionTailComplete':'baseline/src/experimental_swift_reactor/execution.rs:231','recordCleanup':'baseline/src/experimental_swift_reactor/control.rs:1685','finishOwnedCleanup':'baseline/src/experimental_swift_reactor/control.rs:1699','unchangedHarnessCleanup':'harness.rs:228'},
        'noNewDiagnosticOrGuestExecution':True})
    keys=['cache_work','execution_work','instruction_fuel','instructions','host_calls']
    snapshots=[]
    for name in ('constructed','initialize','corpus_1'):
        value=event(name);usage=value['usage']
        snapshots.append({'event':name,'cache':value['cache'],'reservations':usage['reservations'],'live':usage['live'],
            'work':{key:usage[key] for key in keys},'lifecycle':value['lifecycle'],'memoryBytes':value['memory_bytes']})
    save('phase-counters.json',{'schema':1,'sourceEventsSHA256':evidence.sha(HERE/'target-once-events.json'),
        'scope':'raw cumulative counters; corpus_1 is terminal after failure/drain and differs from causal failure checkpoint; cache plan hit counters are not exposed; no performance qualification',
        'snapshots':snapshots,'causalFailureUsage':first['at_failure'],'finalConsumingUsage':final})
    comparisons=[]
    for name in ('constructed','initialize'):
        old=data['priorEvent'](name);new=event(name)
        assert old['usage']['live']==new['usage']['live'] and old['memory_bytes']==new['memory_bytes']
        assert {key:old['usage'][key] for key in keys if key!='cache_work'}=={key:new['usage'][key] for key in keys if key!='cache_work'}
        assert {key:value for key,value in old['cache'].items() if key!='fixed_reserved'}=={key:value for key,value in new['cache'].items() if key!='fixed_reserved'}
        def ownership(value):
            r=value['usage']['reservations']
            return {'fixedCacheReservation':value['cache']['fixed_reserved'],'cacheWork':value['usage']['cache_work'],
                'liveTickets':r['live_tickets'],'peakTickets':r['peak_tickets'],'cacheCurrent':r['cache']['current'],
                'constructionCurrent':r['construction']['current'],'stateCurrent':r['state']['current'],'combinedCurrent':r['combined']['current']}
        a=ownership(old);b=ownership(new)
        comparisons.append({'event':name,'prior':a,'current':b,'delta':{key:b[key]-a[key] for key in a},
            'sameGuestCountersExceptCacheWorkAndSameLiveShape':True})
    prior_first=json.loads((evidence.PRIOR/'target-once-result.json').read_bytes())['firstFailure']['payload']
    save('ownership-comparison.json',{'schema':1,'priorResultSealSHA256':evidence.sha(evidence.PRIOR/'result-seal.json'),
        'priorEventsSHA256':evidence.sha(evidence.PRIOR/'target-once-events.json'),'currentEventsSHA256':evidence.sha(HERE/'target-once-events.json'),
        'scope':'constructed and successful Initialize only; original module/harness/budgets, guest counters and live shapes match except cache work; Corpus1 failures are different cursors and are not equivalent performance or ownership checkpoints',
        'snapshots':comparisons,'priorFailureCursor':{key:prior_first[key] for key in ('function','offset','resource','attempted','limit')},
        'currentFailureCursor':{key:first[key] for key in ('function','offset','resource','attempted','limit')},
        'priorFailureInstructions':prior_first['at_failure']['instructions'],'currentFailureInstructions':first['at_failure']['instructions'],
        'noCPUPerformanceOrCompletionClaim':True})
    old_gzip=evidence.sha(HERE/'result-inputs/prepared-exact-tests.gz');new_gzip=evidence.sha(HERE/'bin/exact-tests.gz')
    save('prepared-transformations.json',{'schema':1,'preparedSealSHA256':evidence.PREPARED_HASH,
        'preparedDocumentUnchanged':True,'preparedManifestBytesUnchanged':True,
        'rawExecutableRemovedAfterAudit':True,'uncompressedExecutableSHA256':data['binaryHash'],
        'originalPreparedGzipSHA256':old_gzip,'currentGzipSHA256':new_gzip,'gzipBytesUnchanged':old_gzip==new_gzip,
        'originalPreparedGzipRetainedAt':'result-inputs/prepared-exact-tests.gz',
        'historicalPreparedVerification':'raw executable member is checked by decompressed bytes; prepared gzip member is checked against archived original gzip; all other prepared members remain byte-identical',
        'runtimeScratchRemovedAfterAudit':True,'compilerTargetAlreadyRemovedDuringPreparation':True,
        'cleanupCommandExecutions':1,'targetAttempts':1})
    save('result-receipt.json',{'schema':1,'status':'sealed-single-attempt-typed-cache-work-exhaustion',
        'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sourceRevisionContext':binding['sourceRevisionContext'],
        'selectionRevisionContext':selected['selectionRevisionContext'],'baselineClosure':evidence.CLOSURE,'sourceFiles':132,
        'sourceUnchanged':True,'sourceRevisionMeaning':'root-supplied source context and later committed integration; exact content closure authoritative; no Git query',
        'rootSelectionSHA256':evidence.SELECTION_HASH,'preparedSealSHA256':evidence.PREPARED_HASH,'preparedInputsUnchanged':True,
        'preparedExecutableRepresentation':'selected raw bytes retained losslessly in gzip after authorized one-time cleanup',
        'harnessSHA256':selected['harnessSHA256'],'driverSHA256':selected['driverSHA256'],'binarySHA256':data['binaryHash'],
        'inputBindingSHA256':selected['inputBindingSHA256'],'compilerTools':binding['compilerTools'],'target':binding['target'],
        'targetAttempts':1,'retryAttempted':False,'targetChildExitCode':101,'targetDriverExitCode':1,'timedOut':False,'signalsSent':[],
        'argv':command['argv'],'targetPID':command['pid'],'targetProcessGroup':command['processGroup'],
        'commandReceipt':'commands/target-once/receipt.json','rawStdout':command['stdout'],'rawStderr':command['stderr'],
        'rootWrapperExecution':data['wrapper'],'validationUsage':event('validation_usage'),'validationObservations':event('validation_observations'),
        'inputOverlap':event('input_overlap'),'initializeCompleted':True,'firstFailure':data['result']['firstFailure'],
        'phasesBegun':data['result']['phasesBegun'],'failurePhaseObservation':json.loads((HERE/'target-once-classification.json').read_bytes())['failurePhaseObservation'],
        'cleanupCommandReceipt':'cleanup-command.json','cleanupCommandExecutions':1,'cleanupCommandExitCode':0,
        'consumingOwnerCleanupObserved':True,'finalCleanupReservationsAndLiveEmpty':True,'rawHarnessCleanupEmpty':False,'rawDriverOwnedCleanupEmpty':False,
        'finalFailureAfterCleanupSnapshot':after,'finalCleanupUsage':final,'phaseCounters':snapshots,
        'allOwnedGroupsAbsent':True,'processGroupEmpty':True,'rawStreamEOFConfirmed':True,'scratchRemoved':True,
        'logicalBytesRemoved':cleanup['logicalBytesRemoved'],'retainedExecutable':cleanup['retainedExecutable'],
        'preparedGzipBytesUnchanged':old_gzip==new_gzip,'resultInputsArchivedBeforeCleanup':True,'resultInputSnapshots':len(data['snapshots']['snapshots']),
        'nativeParity':False,'productionBaselineModifiedByDiagnostic':False,'budgetWidened':False,'fullSLMatrixAccepted':False,
        'productionAccountingAccepted':False,'nativeSignedPublicAccepted':False,'performanceSizeMemoryAccepted':False,
        'fieldLogPublishedPackageQualified':False,'physicalPhonesAttempted':False,'gaAccepted':False})
    text=f'''# Exact full Swift reactor after decode-plan reuse: result

The one selected full host attempt fails Corpus 1 at the original CacheWork
ceiling: `Cache / WorkExhausted / swift_run_work / CacheWork`, attempted
64,000,001 / 64,000,000, function 23610, offset 4154038. Validation and Initialize
pass; Corpus 2 is unrun. The causal failure records 23,358,291 instructions and
4,840,104 elapsed microseconds in the cumulative 30-second runtime window.
These are raw counters at this failure cursor, not performance qualification.
Guest stdout/stderr remain empty, native parity is false and full completion
has not passed. The guest child exits 101; the original driver exits 1. There
is no timeout, signal or retry.

Root selected commit `{selected['selectionRevisionContext']}`, exact 132-file
source closure `{evidence.CLOSURE}`, with selection SHA-256
`{evidence.SELECTION_HASH}`. The 53,777,114-byte module remains
`24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994`.
The original harness, oracle, workloads, counters and limits are unchanged:
86 tickets, 64 residents/pins, 16-MiB cache, 8-MiB entry, 64-million cache work,
256-MiB combined memory, validation 120 seconds, runtime/WASI cumulative
30 seconds each, and outer 170 seconds plus five-second TERM/KILL waits.
Source, tools/sysroot, module, commands and streams are rechecked; product
sources and both preparation document/seal remain byte-identical.

| Named checkpoint | Instructions | Cache work | Live/peak tickets | Cache hits/misses/decodes/evictions |
| --- | ---: | ---: | ---: | --- |
| Constructed | 0 | 4,928 | 21 / 21 | 0 / 0 / 0 / 0 |
| Initialize | 37,328 | 160,343 | 85 / 85 | 324 / 135 / 135 / 71 |
| Corpus 1 terminal after drain | 23,358,291 | 64,000,000 | 84 / 86 | 537,576 / 61,628 / 61,627 / 61,564 |

The causal failure precedes that terminal snapshot: it holds 85 tickets,
64 entries, 17 active pins and 16 frames. The fixed IR-cache reservation is
118,240 bytes; Corpus 1 terminal resident payload is 498,274 bytes, with
1,847,979 peak resident and 1,238,071 peak pinned bytes. Plan-hit counters are
not exposed by this observer. All complete raw phase usage and cache records
are retained in `phase-counters.json`. The prior run stops at a different
cursor after 15,753,076 instructions. Only constructed and successful Initialize
are compared as equivalent checkpoints: guest counters/live shapes match
apart from cache work; fixed cache reservation rises 29,008 bytes and combined
current reservation rises 30,472 bytes. These counts do not predict completion.

The original causal failure is retained unchanged in `final_failure`, apart
from its appended cleanup observation. Its copied `after_cleanup` snapshot is
before foundation consumption: three tickets, construction 269,616 plus shared
1,744 = combined 271,360 bytes. `finish_owned_cleanup` then consumes that actual
foundation closure. The final consuming runtime ledger has **every current
reservation category, every live count and live tickets zero**, with no cleanup
invariant. The nested WASI submeter remains a copied historical component
observation; runtime ledger WASI current reservation is zero.
`cleanup_empty=false` and `ownedCleanupEmpty=false` are success-oriented flags
that retain the original failure. They are distinct from current-ledger emptiness.
`consuming-cleanup-audit.json` binds this boundary to the unchanged source/harness.

Before host removal, 28 exact result-input snapshots were archived. Target
PID/PGID 95928 and all preparation groups are absent; complete raw streams
reached EOF. Raw child stdout is 18,074 bytes, SHA-256
`49e4a54e37fcbf6998d9beed000a79781b10eda8606e2389edb8c7cce5284f42`;
stderr is 429 bytes, SHA-256
`ffe32c4e3c489b20709247b1b33bdf266068d52c205f7743de2d9e6227897110`.
Root wrapper stdout/stderr and execution metadata are archived separately.

The existing `diagnostic.py cleanup` ran exactly once under a bounded wrapper.
Empty recursive holders and exact path/device/inode checks passed. Cleanup
PID/PGID {data['cleanupCommand']['pid']} is absent, exit 0, without signals.
Only owned runtime scratch ({cleanup['logicalBytesRemoved']:,} logical bytes)
and the raw executable were removed. The compiler target was already removed
in preparation. The original 4,878,784-byte executable is retained losslessly as
`bin/exact-tests.gz` ({cleanup['retainedExecutable']['gzip']['bytes']:,} bytes,
SHA-256 `{new_gzip}`). Its decompressed SHA-256 is
`{data['binaryHash']}`. Recompression preserves the prepared gzip bytes exactly;
the pre-cleanup gzip is also archived. `prepared-transformations.json` explicitly
accounts for the removed raw executable and historical preparation bindings.
Other projects' processes and data are untouched.

The result receipt, raw evidence, input archive, cleanup audit and result seal
are retained in this packet. Verify read-only, without compiler or guest runs:

```sh
python3 -B verification/swift-exact-reactor-after-plan-reuse/verify-result.py
```

No further target, compile, synthetic surrogate, native/UI/device/phone, provider,
network, hosted frozen-lane, Git or release operation was used for finalization.
The prepared-only verifier remains historical and must not be treated as a
post-cleanup verifier. Root review precedes any separately bounded offline
cache diagnosis; no retry is selected. Guest parity, full completion, standards
matrix, production accounting/caller stack, signed/public/native execution,
performance/size/memory/startup, immutable published FieldLog packages consumed
from a separate repository, phones, store, customer/operational and accountable
GA acceptance remain pending. Phones remain disconnected and deferred. The
whole product goal remains active.
'''
    (HERE/'result.md').write_text(text)
    DOC.write_text(text.replace('retained in this packet.','retained in [the result packet](../verification/swift-exact-reactor-after-plan-reuse/result-receipt.json).'))
    files={str(path.relative_to(HERE)):evidence.sha(path) for path in sorted(HERE.rglob('*')) if path.is_file() and path.name!='result-seal.json'}
    external={str(path.relative_to(ROOT)):evidence.sha(path) for path in [ROOT/'docs/swift-exact-reactor-after-plan-reuse.md',DOC,Path(binding['target']['path']),*sorted(evidence.ROOT_SELECTION.iterdir())] if path.is_file()}
    save('result-seal.json',{'schema':1,'status':'single-attempt-typed-cache-work-exhaustion','targetAttempts':1,'files':files,'externalFiles':external})
    print(json.dumps({'sealedMembers':len(files),'preparedMembers':len(data['prepared']['files']),
        'resultSealSHA256':evidence.sha(HERE/'result-seal.json'),'receiptSHA256':evidence.sha(HERE/'result-receipt.json'),
        'classificationSHA256':evidence.sha(HERE/'target-once-classification.json'),
        'currentReservationsLiveAndTicketsZero':True,'targetAttempts':1,'scratchRemoved':True,'noTargetRerun':True}))
if __name__=='__main__':main()
