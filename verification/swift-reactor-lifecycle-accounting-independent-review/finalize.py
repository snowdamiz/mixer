#!/usr/bin/env python3
"""Seal only the independent review's newly owned evidence and document."""
import datetime, hashlib, json
from pathlib import Path
import audit

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
save=lambda n,x:(P/n).write_bytes(x if isinstance(x,bytes)else enc(x))

def main():
    producer=ROOT/'verification/swift-reactor-lifecycle-accounting'
    audit.snapshot('final-source-check')
    assert json.loads((P/'execution.json').read_bytes())['success']
    assert not (P/'audit.stderr').read_bytes()
    for source,name in [('seal.json','producer-seal.json'),('candidate-final-manifest.json','candidate-source-manifest.json'),
                        ('baseline-manifest.json','live-source-manifest.json'),('authored-coverage.json','authored-coverage-unchanged.json'),
                        ('planned-matrix-unchanged.json','planned-matrix-unchanged.json')]:
        save(name,(producer/source).read_bytes())
    paths=['AGENTS.md','mixer-product-plan.md','docs/swift-reactor-lifecycle-contract.md',
        'docs/swift-reactor-lifecycle-accounting.md','verification/swift-reactor-lifecycle-contract/seal.json',
        'verification/swift-reactor-lifecycle-implementation/seal.json',
        'verification/swift-reactor-lifecycle-contract-root-review/selection.json',
        'verification/swift-reactor-lifecycle-contract-root-review/accounting-selection.json',
        'verification/swift-reactor-lifecycle-contract-root-review/finite-position-selection.json',
        'verification/swift-reactor-lifecycle-contract-root-review/additional-finite-position-selection.json',
        'verification/swift-reactor-lifecycle-contract-root-review/preparation-seam-amendment.json']
    save('review-input-bindings.json',{p:sha((ROOT/p).read_bytes())for p in paths})
    save('audit-command.json',{'argv':['python3','-B','verification/swift-reactor-lifecycle-accounting-independent-review/audit.py'],
        'cwd':str(ROOT),'exitCode':0,'scriptSHA256':sha((P/'audit.py').read_bytes()),
        'stdoutSHA256':sha((P/'audit.stdout').read_bytes()),'stderrSHA256':sha((P/'audit.stderr').read_bytes()),
        'scope':'Read-only source/archive/raw compiler evidence audit and version probes; no compilation/test body/VM/native/full-target.'})
    doc='docs/swift-reactor-lifecycle-accounting-independent-review.md'
    receipt={'schema':'mixer.swift-lifecycle.independent-accounting-review.1',
        'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'accountableReviewer':'/root/swift_lifecycle_accounting_independent_review',
        'status':'no-blocking-findings-in-scoped-source-and-accounting-review',
        'independentReviewPassed':True,'findings':[],
        'producerSealSHA256':audit.SEAL,'producerPacketFiles':1905,
        'producerPacketClosure':'aafd88cf053743e2560788bfb877adbabdbdece86f3fb77e972baf100dc2dd2d',
        'candidateFiles':132,'candidateClosure':audit.FINAL,'unchangedLiveFiles':130,'liveClosure':audit.BASE,
        'runtimeBodies':268,'disjointRolePositions':21364,'exactTypedAndNeverWitnesses':21416,
        'exactZeroByteFnDefOccurrences':526,'exactSelectedFinitePositions':256,
        'fullBodySHAChangesPreserved':96,'sourceInfoChangesPreserved':7216,
        'actualTypeOrLayoutChanges':0,'runtimePositionAdditionsOrRemovals':0,
        'individualExactParentFieldCTFEProofs':384,'ctfeRuntimeByteCredit':0,
        'finalRawCompilerContextsAudited':8,'pairedCompilerLayoutsAudited':16,
        'originalGrowthPositionsExact':True,'other129BaselineFilesExact':True,'expandedFrozenMethodsExact':39,
        'State':134217728,'Combined':268435456,'maximumTickets':86,'FrozenBound':2912,
        'productionHeader':6464992,'productionFrame':15847432,'unitHeader':11694120,'unitFrame':31278808,
        'aggregateHeadroomClaimed':False,
        'independentExecution':{'compilations':0,'testBodies':0,'VMCalls':0,'testListBinaries':0,
            'nativeInstances':0,'fullTargetReadHashedOrRun':False,'scratchCreated':False,
            'readOnlyProducerLiveReplays':2,'rawCompilerSourceAndAccountingAudit':True},
        'producerEvidenceReconciled':{'commands':57,'preservedFailures':4,'listOnlyBinaries':4,
            'SwiftTotalTestsListed':335,'allFeatureTotalTestsListed':365,'lifecycleTestsEach':23,
            'testBodiesExecuted':0,'VMCalls':0,'productionClippy':2,'formatChecks':1,
            'ownedTargetsOverlaysComponentAndListCopiesRemoved':True},
        'sourceReview':['Lifecycle-only refusal before control access; corrupt Terminal stays blocked',
            'Fixed Initialize35 void once and Corpus62i32 on the original owner',
            'Actual outer Result plus stored result shape and final observed original control/WASI check',
            'Sticky actual first cause; cumulative owner/budget/deadline preservation',
            'Actual retained growth authority and original inner clean/completion barrier',
            'No fallible gap from inner Completed to Ready; scalar withheld until full completion',
            'Preserve wrappers retain existing caller behavior; no new public API/C ABI or dependency'],
        'limitations':['No runtime assertions or complete SL01-SL23 row is qualified',
            'SL09 first five authored cases assert a typed-family union, not exact per-dimension kind',
            'SL12 guest table mutation unsupported and unrun; unchanged-table reads are not mutation evidence',
            'Missing unique control remains inherited constructor expect precondition',
            'All remaining cases are preserved in full unchanged original matrix/coverage ledger',
            'Physical phones disconnected and deferred; no native runtime qualification',
            'Separate-repository immutable published FieldLog packages and product/GA gates remain required'],
        'rootAccountingAccepted':False,'runtimeSelected':False,'runtimeQualified':False,'liveIntegrationSelected':False,
        'gaAccepted':False,'document':doc,'documentSHA256':sha((ROOT/doc).read_bytes()),
        'cleanup':'No scratch/build target/overlay/binary copy/native instance was created by the reviewer; producer scratch cleanup independently replayed.',
        'reviewerScriptDevelopmentFailuresPreserved':['first-audit-command.json','second-audit-command.json']}
    save('receipt.json',receipt)
    files=audit.manifest(P)
    files.pop('seal.json',None)
    save('seal.json',{'schema':'mixer.swift-lifecycle.independent-accounting-review-seal.1',
        'files':files,'closureSHA256':sha(enc(files)),'document':doc,'documentSHA256':receipt['documentSHA256'],
        'producerSealSHA256':audit.SEAL,'independentReviewPassed':True,'rootAccountingAccepted':False,
        'runtimeSelected':False,'vmExecutions':0,'testBodiesExecuted':0})
    print(json.dumps({'reviewSealSHA256':sha((P/'seal.json').read_bytes()),'reviewFiles':len(files),
        'reviewClosure':sha(enc(files)),'independentReviewPassed':True,'rootAccountingAccepted':False,
        'runtimeSelected':False,'findings':0},indent=2))

if __name__=='__main__':main()
