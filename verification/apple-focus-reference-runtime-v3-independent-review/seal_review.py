#!/usr/bin/env python3
"""Seal/verify rejected review using data and hashes only; never import producer."""
import datetime
import json
from pathlib import Path
import sys
import bindings

BASE=bindings.BASE;ROOT=bindings.ROOT;sha=bindings.sha;stable=bindings.stable

def verify_outputs(folder,receipt):
    assert sha(stable(receipt['outputs']))==receipt['outputTreeSHA256']
    for name,row in receipt['outputs'].items():assert bindings.row(folder/name)==row,name

def freeze():
    path=BASE/'handoff.json';assert not path.exists()
    frozen=bindings.verify()
    attempt=BASE/'attempt-1';receipt=json.loads((attempt/'receipt.json').read_bytes())
    precision=BASE/'precision-reproduction-1';reproduction=json.loads((precision/'receipt.json').read_bytes())
    verify_outputs(attempt,receipt);verify_outputs(precision,reproduction)
    assert receipt['suiteResults']['producer']['testsRun']==111 and receipt['suiteResults']['producer']['passed'] is True
    assert receipt['suiteResults']['repair']['testsRun']==25 and receipt['suiteResults']['repair']['passed'] is True
    independent=receipt['suiteResults']['independent']
    assert independent['testsRun']==37 and len(independent['failures'])==3 and not independent['errors'] and not independent['skipped']
    assert receipt['historicalReview']['controlsPassed']==32 and receipt['historicalReview']['expectedReplayOutcome'] is True
    assert reproduction['controls']==8 and reproduction['controlsFailed']==3 and reproduction['controlsPassed']==5
    assert receipt['cleanup']['ownedTemporaryDirectoriesAbsent'] and reproduction['cleanup']['ownedAdapterScratchAbsent']
    assert not list(BASE.glob('precision-adapter-*'))
    members={str(p.relative_to(ROOT)):bindings.row(p) for p in sorted(BASE.rglob('*')) if p.is_file()}
    document=ROOT/'docs/apple-focus-reference-runtime-v3-independent-review.md';members[str(document.relative_to(ROOT))]=bindings.row(document)
    value={'schema':'mixer.apple-focus-reference-runtime-v3-independent-review-handoff.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(Path(__file__).resolve()),'freeze'],'status':'rejected-for-native-dispatch-exact-arithmetic-repair-required','accepted':False,'reviewerModel':'gpt-6.1-sol','reasoningEffort':'xhigh','producerHandoffSHA256':bindings.EXPECTED_HANDOFF,'packetSHA256':bindings.EXPECTED_PACKET,'members':members,'memberTreeSHA256':sha(stable(members)),'frozenInputCount':len(frozen['bindings']),'frozenInputTreeSHA256':frozen['bindingTreeSHA256'],'producerControls':{'run':111,'passed':111},'repairControls':{'run':25,'passed':25},'historicalControls':{'run':33,'passed':32,'retainedInvalidDirectCommitFixtureFailures':1},'independentControls':{'run':37,'passed':34,'failed':3,'errors':0,'skipped':0},'additionalActualAdapterPrecisionReproduction':{'run':8,'passed':5,'failed':3},'independentComposedInventoryControls':{'run':25,'passed':25},'findings':[{'id':'R1','scope':'production-importer-synthetic-consistency','severity':'dispatch-blocker','source':'verification/apple-focus-reference-runtime-v3/importer.py','line':71,'meaning':'Ambient Decimal multiplication rounds away fractional nanoseconds before integrality/order checks; a signature later than original raw premise can pass','failedIndependentControls':3,'actualAdapterReproductions':3,'nativeProvenanceExploitClaimed':False}],'nativeExecuted':False,'runtimeSelected':False,'runPassed':False,'completeCaseSet':False,'cursorCompletionCredit':False,'fullSixCaseQualification':False,'nativeKeyboardQualification':False,'carrierAccepted':False,'gaAccepted':False,'physicalPhones':'disconnected-deferred','productAndOracleUnchanged':True,'hostedLaneReadImportedOrExecuted':False,'cleanup':receipt['cleanup'],'scope':'Independent host review only. Valid auxiliary composition accepted; production importer precision rejected. Root must select any future native run separately after a versioned repair is reviewed.'}
    with path.open('xb') as stream:stream.write(stable(value))
    print(json.dumps({'handoffSHA256':sha(path.read_bytes()),'memberTreeSHA256':value['memberTreeSHA256'],'members':len(members),'accepted':False,'status':value['status']},sort_keys=True))

def verify():
    path=BASE/'handoff.json';value=json.loads(path.read_bytes())
    assert sha(stable(value['members']))==value['memberTreeSHA256']
    for name,row in value['members'].items():assert bindings.row(ROOT/name)==row,name
    frozen=bindings.verify();assert len(frozen['bindings'])==value['frozenInputCount'] and frozen['bindingTreeSHA256']==value['frozenInputTreeSHA256']
    print(json.dumps({'handoffSHA256':sha(path.read_bytes()),'memberTreeSHA256':value['memberTreeSHA256'],'members':len(value['members']),'accepted':False,'status':value['status'],'scope':'File/hash verification only'},sort_keys=True))

if __name__=='__main__':
    assert len(sys.argv)==2
    if sys.argv[1]=='freeze':freeze()
    elif sys.argv[1]=='verify':verify()
    else:raise ValueError('Unknown action')
