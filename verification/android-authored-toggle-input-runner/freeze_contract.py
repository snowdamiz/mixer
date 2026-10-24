#!/usr/bin/env python3
"""Developer host-only derivation capture. Does not grant dispatch or native acceptance."""
import hashlib
from pathlib import Path
import support


def main():
    wrapper=support.load('authored_freeze_wrapper',support.HERE/'run.py')
    inherited,prior=support.prior()
    contract={'schema':1,'status':'prepared-root-review-required-native-NOT-RUN','nativeDispatchAuthorizedByThisContract':False,'sourceRevisionContext':'18378bb802259a86dff43d31bf881a6d171bb8f0','sourceRevisionAuthority':'verified by root; contextual only, not a claim the changed candidate exists in that Git tree','candidateImplementationPredecessorRevisionContext':'8c634c49fa701c27b975789b15c0aabff3f047d6','sourceTree':support.CLOSURE,'sourceTreeAlgorithm':'sha256 canonical106-input manifest, not Git tree','sourceClosureSHA256':support.CLOSURE,'sourceInputs':106,'liveBaselineNativeSDKInputs':88,'baselineActions':20,'baselineArtifactPayload':183,'componentArtifactPayload':183,'productionClasses':159,'baselineFixtureClasses':4,'supplementClasses':4,'libraries':18,'priorConcreteSHA256':support.CONCRETE,'correctedOracleSHA256':support.sha(support.TIMING/'oracle.py'),'producerSealSHA256':support.PRODUCER_SEAL,'producerFiles':555,'variants':{},'implementationBindings':{},'toolBindings':{},'priorReviewBindings':{}}
    contract.update(componentCases=45, componentWorkerSendPointerSyncRequests=18, componentKnownUncountedHistoricalMotionEvents=1, componentConstructedMotionEventBound=512)
    for variant in ('baseline','supplement'):
        concrete,deltas=wrapper.derive(prior,variant)
        path=support.HERE/('derived-'+variant+'.py');path.write_text(concrete)
        diff=''.join(__import__('difflib').unified_diff(prior.splitlines(keepends=True),concrete.splitlines(keepends=True),fromfile='reviewed-candidate5-concrete.py',tofile=path.name))
        (support.HERE/('derived-'+variant+'.diff')).write_text(diff)
        contract['variants'][variant]={'concreteFile':path.name,'concreteSHA256':hashlib.sha256(concrete.encode()).hexdigest(),'sourceDeltas':deltas,'sourceUnchanged':False,'apkSHA256':support.APK if variant=='baseline'else support.SUPPLEMENT_APK,'sourceClosureSHA256':support.CLOSURE if variant=='baseline'else support.SUPPLEMENT_CLOSURE,'nativeScope':'unchanged20action authoritative ordinary join fixture'if variant=='baseline'else'component fixtureInput only; no engine/coordinator commit authority'}
    for name in ('support.py','supplement_oracle.py','verify.py','test_host.py','review_supplement.py'):contract['implementationBindings'][name]=support.sha(support.HERE/name)
    old=support.read(support.TIMING/'runner-contract.json')
    contract['toolBindings']=old['toolBindings']
    producer=support.read(support.SUPPLEMENT/'receipt.json')
    for path,value in producer['tools'].items():contract['toolBindings'][path]=value['sha256']
    for name in ('verification/android-pointer-timing-correction/run.py','verification/android-pointer-timing-correction/support.py','verification/android-pointer-timing-correction/oracle.py','verification/android-pointer-timing-correction/runner-contract.json','verification/android-authored-toggle-input-review/baseline-2/receipt.json'):
        contract['priorReviewBindings'][name]=support.sha(support.ROOT/name)
    review=support.ROOT/'verification/android-authored-toggle-input-review'
    review_seal=support.read(review/'seal.json')
    for name in review_seal['files']:contract['priorReviewBindings'][str((review/name).relative_to(support.ROOT))]=support.sha(review/name)
    for name in review_seal['documentation']:contract['priorReviewBindings'][name]=support.sha(support.ROOT/name)
    contract['priorReviewBindings']['verification/android-authored-toggle-input-review/seal.json']=support.sha(review/'seal.json')
    contract['changedProductionInputs']={name:support.bind(support.CANDIDATE/'inputs'/name)for name in sorted(support.CHANGED|{support.ADDED})}
    support.save(support.HERE/'runner-contract.json',contract)
    digest=support.sha(support.HERE/'runner-contract.json')
    path=support.HERE/'run.py';text=path.read_text();text=__import__('re').sub(r"CONTRACT_SHA256 = '[A-Za-z0-9]+'","CONTRACT_SHA256 = '"+digest+"'",text,count=1);path.write_text(text)
    print(__import__('json').dumps({'contractSHA256':digest,'variants':{n:c['concreteSHA256']for n,c in contract['variants'].items()},'nativeRuntime':'NOT RUN'},indent=2))

if __name__=='__main__':main()
