#!/usr/bin/env python3
"""Freeze/verify the host-only V4 packet, controls and retained historical failures."""
import argparse
import datetime
import json
import sys
import prepare


def verify_outputs(base,receipt):
    prepare.require(prepare.sha(prepare.stable(receipt['outputs']))==receipt['outputTreeSHA256'],'Host output tree digest differs')
    for name,expected in receipt['outputs'].items():
        prepare.require(prepare.row(base/name)==expected,'Host output changed: '+name)


def freeze(attempt):
    path=prepare.BASE/'handoff.json';prepare.require(not path.exists(),'Preserve frozen handoff')
    packet=prepare.verify()
    base=prepare.BASE/f'host-attempt-{attempt}';receipt=json.loads((base/'receipt.json').read_bytes())
    verify_outputs(base,receipt)
    prepare.require(receipt['passed'] is True and receipt['testsRun']==111,'Exact V4 host acceptance required')
    prepare.require(receipt['historicalReview']=={'controls':33,'passed':32,'retainedHistoricalFixtureFailures':1,'sourceSHA256':'84f7d1c5dbe0cbe17d60c34675de1c3d17107c17964062ea74ebdf5982a195db','expectedReplayOutcome':True},'Preserve exact invalid historical fixture failure')
    prepare.require(receipt['repairControls']=={'testsRun':25,'passed':True},'Retained focused controls differ')
    prepare.require(receipt['v3ReviewReplay']=={'testsRun':37,'passed':37,'unchangedControlBodiesMutationsAssertions':True,'composedInventoryControls':{'run':25,'passed':25}},'Frozen V3 reviewer replay differs')
    prepare.require(receipt['precisionControls']=={'testsRun':19,'passed':True,'actualAdapterCases':35},'Exact-time controls differ')
    prepare.require(receipt['frozenV3ActualAdapterReplay']=={'controls':8,'passed':8,'failed':0},'Frozen actual-adapter replay differs')
    prepare.require(receipt['ownedSources']=={n:prepare.row(prepare.BASE/n) for n in prepare.OWNED},'Host-tested source differs')
    prepare.require(receipt['inputBindings']==prepare.inputs()[3],'Host-tested frozen inputs differ')
    prepare.require(receipt['cleanup']['allFrozenInputsUnchanged'] and receipt['cleanup']['ownedHostTemporaryDirectoriesAbsent'],'Host cleanup differs')
    paths=[prepare.ROOT/'docs/apple-focus-reference-runtime-v4.md']+[p for p in prepare.BASE.rglob('*') if p.is_file()]
    prepare.require(not any(p.is_symlink() for p in prepare.BASE.rglob('*')),'Symlink in owned handoff')
    members={str(p.relative_to(prepare.ROOT)):prepare.row(p) for p in sorted(paths)}
    value={'schema':'mixer.apple-focus-reference-runtime-frozen-handoff.4','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(prepare.BASE/'freeze.py'),'freeze','--attempt',str(attempt)],'python':sys.version,'packetSHA256':packet['packetSHA256'],'members':members,'memberTreeSHA256':prepare.sha(prepare.stable(members)),'hostAttempt':attempt,'retainedProducerControls':{'run':111,'passed':111},'focusedRepairControls':{'run':25,'passed':25},'historicalIndependentControls':{'run':33,'passed':32,'retainedMalformedDirectTransactionStoreFixtureFailures':1,'originalControlBodiesMutationsAssertionsUnchanged':True},'v3ReviewerReplay':{'run':37,'passed':37,'originalControlBodiesMutationsAssertionsUnchanged':True,'composedInventorySubset':{'run':25,'passed':25}},'newExactTimestampControls':{'run':19,'passed':19,'actualAdapterCases':35},'frozenV3ActualAdapterPrecisionReplay':{'run':8,'passed':8},'frozenV3ProducerHandoffSHA256':prepare.frozen_inputs.V3_HANDOFF,'frozenV3RejectedIndependentReviewHandoffSHA256':prepare.frozen_inputs.V3_REVIEW_HANDOFF,'frozenV3PacketSHA256':prepare.frozen_inputs.V3_PACKET,'historicalV3ReviewAccepted':False,'historicalV3ReviewPrecisionFailuresPreserved':3,'historicalV2ReviewAccepted':False,'historicalV2ReviewFailedControlsPreserved':10,'historicalV1FailuresPreserved':True,'independentV4ReviewPending':True,'sourceRevisionLabel':receipt['sourceRevisionLabel'],'sourceTreeSHA256':prepare.SOURCE,'productArchiveSHA256':prepare.PRODUCT,'observerV2Unchanged':True,'originalOracleActionBudgetTimingProductsUnchanged':True,'scope':'Host-only exact timestamp repair. Conservative sub-nanosecond rejection, frozen failures, source/products and native qualification boundaries retained. Fresh independent V4 review and root selection required before dispatch.','nativeExecuted':False,'runtimeSelected':False,'runnableSourcePacketPrepared':True,'compileRerun':False,'gitMutationPerformed':False,'uiOrCapturePerformed':False,'hostedCatalogAuthorityOrWorkerReviewReadImportedOrExecuted':False,'runPassed':False,'completeCaseSet':False,'cursorCompletionCredit':False,'fullSixCaseQualification':False,'nativeKeyboardQualification':False,'carrierAccepted':False,'gaAccepted':False,'physicalPhones':'disconnected-deferred','cleanup':receipt['cleanup']}
    with path.open('xb') as stream:stream.write(prepare.stable(value))
    print(json.dumps({'handoffSHA256':prepare.row(path)['sha256'],'packetSHA256':packet['packetSHA256'],'memberTreeSHA256':value['memberTreeSHA256'],'nativeExecuted':False,'independentV4ReviewPending':True},sort_keys=True))


def verify():
    path=prepare.BASE/'handoff.json';value=json.loads(path.read_bytes())
    prepare.require(prepare.sha(prepare.stable(value['members']))==value['memberTreeSHA256'],'Handoff digest differs')
    for name,expected in value['members'].items():prepare.require(prepare.row(prepare.ROOT/name)==expected,'Frozen member changed: '+name)
    packet=prepare.verify();prepare.require(packet['packetSHA256']==value['packetSHA256'],'Frozen packet differs')
    return {'handoffSHA256':prepare.row(path)['sha256'],'packetSHA256':value['packetSHA256'],'memberTreeSHA256':value['memberTreeSHA256'],'nativeExecuted':False,'scope':'File/hash verification only; no dispatch authorization'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','verify']);p.add_argument('--attempt',type=int,default=1);args=p.parse_args()
    if args.action=='freeze':freeze(args.attempt)
    else:print(json.dumps(verify(),sort_keys=True))
