#!/usr/bin/env python3
"""Verify sealed recorded evidence read-only; no build, target, native or UI execution."""
import json
from pathlib import Path
import result_evidence as evidence
HERE=evidence.HERE
ROOT=evidence.ROOT

def main():
    seal=evidence.read('result-seal.json')
    actual={str(path.relative_to(HERE)) for path in HERE.rglob('*') if path.is_file() and path.name!='result-seal.json'}
    assert actual==set(seal['files']),'final inventory changed'
    for name,digest in seal['files'].items():assert evidence.sha(HERE/name)==digest,name
    for name,digest in seal['externalFiles'].items():assert evidence.sha(ROOT/name)==digest,name
    data=evidence.check()
    first=data['first'];final=data['final'];event=data['event']
    classification=evidence.read('target-once-classification.json')
    assert classification['firstTypedFailure']==first and classification['finalCleanupReservationsAndLiveEmpty']
    assert classification['rawResultSHA256']==evidence.sha(HERE/'target-once-result.json')
    assert classification['rawStdoutSHA256']==evidence.sha(HERE/'commands/target-once/stdout')
    assert classification['rawStderrSHA256']==evidence.sha(HERE/'commands/target-once/stderr')
    assert classification['targetAttempts']==1 and not classification['retryAttempted'] and not classification['budgetsChanged']
    consuming=evidence.read('consuming-cleanup-audit.json')
    assert consuming['firstTypedFailure']==first and consuming['finalFailure']==data['finalFailure']
    assert consuming['finalFailureAfterCleanupSnapshot']==data['finalFailure']['after_cleanup']
    assert consuming['finalConsumingUsage']==final and consuming['sourceEventsSHA256']==evidence.sha(HERE/'target-once-events.json')
    assert consuming['finalLiveTickets']==0 and consuming['cleanupInvariant'] is None
    assert all(value==0 for value in consuming['finalCurrentReservationCategories'].values())
    assert all(value==0 for value in consuming['finalCurrentLiveCategories'].values())
    assert consuming['rawHarnessCleanupEmpty'] is False and consuming['rawDriverOwnedCleanupEmpty'] is False
    for name,digest in consuming['sourceBindings'].items():assert evidence.sha(HERE/name)==digest
    counters=evidence.read('phase-counters.json')
    assert counters['sourceEventsSHA256']==evidence.sha(HERE/'target-once-events.json')
    assert counters['causalFailureUsage']==first['at_failure'] and counters['finalConsumingUsage']==final
    assert [row['event'] for row in counters['snapshots']]==['constructed','initialize','corpus_1']
    for row in counters['snapshots']:
        original=event(row['event']);usage=original['usage']
        assert row['cache']==original['cache'] and row['reservations']==usage['reservations'] and row['live']==usage['live']
        assert row['work']=={key:usage[key] for key in row['work']}
        assert row['lifecycle']==original['lifecycle'] and row['memoryBytes']==original['memory_bytes']
    compare=evidence.read('ownership-comparison.json')
    assert compare['priorResultSealSHA256']==evidence.sha(evidence.PRIOR/'result-seal.json')
    assert compare['priorEventsSHA256']==evidence.sha(evidence.PRIOR/'target-once-events.json')
    assert compare['currentEventsSHA256']==evidence.sha(HERE/'target-once-events.json')
    assert [row['event'] for row in compare['snapshots']]==['constructed','initialize']
    def ownership(value):
        r=value['usage']['reservations']
        return {'fixedCacheReservation':value['cache']['fixed_reserved'],'cacheWork':value['usage']['cache_work'],
            'liveTickets':r['live_tickets'],'peakTickets':r['peak_tickets'],'cacheCurrent':r['cache']['current'],
            'constructionCurrent':r['construction']['current'],'stateCurrent':r['state']['current'],'combinedCurrent':r['combined']['current']}
    for row in compare['snapshots']:
        assert row['prior']==ownership(data['priorEvent'](row['event'])) and row['current']==ownership(event(row['event']))
        assert row['delta']=={key:row['current'][key]-row['prior'][key] for key in row['prior']}
        assert row['delta']['liveTickets']==0 and row['delta']['fixedCacheReservation']==29008 and row['delta']['combinedCurrent']==30472
        assert row['delta']['cacheWork']==(4096 if row['event']=='constructed' else 1807)
    transforms=evidence.read('prepared-transformations.json')
    assert transforms['preparedSealSHA256']==evidence.PREPARED_HASH
    assert transforms['originalPreparedGzipSHA256']==evidence.sha(HERE/'result-inputs/prepared-exact-tests.gz')
    assert transforms['currentGzipSHA256']==evidence.sha(HERE/'bin/exact-tests.gz')
    assert transforms['gzipBytesUnchanged']==(transforms['originalPreparedGzipSHA256']==transforms['currentGzipSHA256'])
    assert transforms['rawExecutableRemovedAfterAudit'] and transforms['runtimeScratchRemovedAfterAudit']
    receipt=evidence.read('result-receipt.json')
    assert receipt['firstFailure']==data['result']['firstFailure'] and receipt['finalCleanupUsage']==final
    assert receipt['finalFailureAfterCleanupSnapshot']==data['finalFailure']['after_cleanup']
    assert receipt['targetAttempts']==seal['targetAttempts']==transforms['targetAttempts']==1
    assert receipt['cleanupCommandExecutions']==transforms['cleanupCommandExecutions']==1 and receipt['cleanupCommandExitCode']==0
    assert receipt['rootSelectionSHA256']==evidence.SELECTION_HASH and receipt['preparedSealSHA256']==evidence.PREPARED_HASH
    assert receipt['targetChildExitCode']==101 and receipt['targetDriverExitCode']==1 and receipt['targetPID']==receipt['targetProcessGroup']==95928
    assert receipt['preparedInputsUnchanged'] and receipt['sourceUnchanged'] and receipt['scratchRemoved'] and receipt['rawStreamEOFConfirmed']
    assert receipt['compilerTools']==data['binding']['compilerTools'] and receipt['binarySHA256']==data['binaryHash']
    assert receipt['resultInputSnapshots']==len(data['snapshots']['snapshots'])==28
    assert receipt['logicalBytesRemoved']==data['cleanup']['logicalBytesRemoved']==73032845
    assert not receipt['gaAccepted'] and not receipt['nativeParity'] and not receipt['retryAttempted'] and not receipt['budgetWidened']
    print(json.dumps({'integrityVerified':True,'sealedMembers':len(seal['files']),'preparedMembersVerified':len(data['prepared']['files']),
        'archivedInputSnapshots':28,'sourceFiles':132,'sourceClosure':evidence.CLOSURE,'sourceUnchanged':True,
        'targetAttempts':1,'targetCommandPassed':False,'firstFailure':{key:first[key] for key in ('stage','kind','code','resource','function','offset','attempted','limit')},
        'instructions':first['at_failure']['instructions'],'initializeCompleted':True,'corpus2Attempted':False,
        'finalCurrentReservations':consuming['finalCurrentReservationCategories'],'finalCurrentLive':consuming['finalCurrentLiveCategories'],'finalLiveTickets':0,
        'cleanupInvariant':None,'rawCleanupEmpty':False,'ownedScratchRemoved':True,'preparedGzipBytesUnchanged':transforms['gzipBytesUnchanged'],'gaAccepted':False}))

if __name__=='__main__':main()
