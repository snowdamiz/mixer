#!/usr/bin/env python3
"""Read-only exact packet replay, or explicit host packet sealing. Never dispatches native work."""
import argparse
import hashlib
import json
from pathlib import Path
import support

def check(require_seal=True):
    if require_seal:
        if support.files()!=support.read(support.HERE/'packet-seal.json')['files']:raise ValueError('exact authored runner packet drift')
    contract=support.read(support.HERE/'runner-contract.json')
    for name,digest in contract['implementationBindings'].items():
        if support.sha(support.HERE/name)!=digest:raise ValueError('implementation drift '+name)
    for name,digest in contract['toolBindings'].items():
        if support.sha(name)!=digest:raise ValueError('tool drift '+name)
    for name,digest in contract['priorReviewBindings'].items():
        if support.sha(support.ROOT/name)!=digest:raise ValueError('prior review binding drift '+name)
    wrapper=support.load('authored_verifier_run',support.HERE/'run.py')
    baseline,source,_=wrapper.load_runner('baseline')
    supplemental,supplement_source,_=wrapper.load_runner('supplement')
    if baseline._pointer_validate_native.__code__.co_filename!=str(support.TIMING/'oracle.py'):raise ValueError('corrected oracle not inherited exactly')
    if supplemental._pointer_validate_native is not baseline._pointer_validate_native:
        # Separate prior loads construct functions independently; byte and filename identity are authoritative.
        if supplemental._pointer_validate_native.__code__.co_code!=baseline._pointer_validate_native.__code__.co_code:raise ValueError('oracle differs')
    producer=support.frozen('baseline');component=support.frozen('supplement')
    attempts=[]
    for p in sorted(support.HERE.glob('host-[1-9]*')):
        if not p.is_dir():raise ValueError('host attempt path')
        support.exact_seal(p)
        receipt=support.read(p/'receipt.json')
        if not receipt['cleanup']['absent'] or not receipt['cleanup']['allCommandGroupsEmpty']:raise ValueError('host cleanup incomplete')
        attempts.append((p.name,receipt))
    passed=[(name,r) for name,r in attempts if r['status']=='passed-independent-four-class-exact-DEX-supplement-review-and-host-controls']
    if not passed:raise ValueError('fresh successful host review required')
    latest,receipt=passed[-1]
    if receipt['upstreamControls']!=55 or receipt['freshSupplementClasses']!=4 or receipt['productionClasses']!=159:raise ValueError('host review counts drift')
    used=support.HERE/latest/'source-used'
    for p in used.glob('*.py'):
        if support.sha(p)!=support.sha(support.HERE/p.name):raise ValueError('post-review source drift '+p.name)
    if support.sha(used/'runner-contract.json')!=support.sha(support.HERE/'runner-contract.json'):raise ValueError('post-review contract drift')
    return {'schema':1,'status':'passed-read-only-authored-runner-source-and-host-packet-replay','files':len(support.files()),'hostAttempt':latest,'upstreamSyntheticControls':55,'authoredSyntheticControls':receipt['authoredControls'],'baselineAPK':producer['apkSHA256'],'componentAPK':component['apkSHA256'],'sourceClosureSHA256':support.CLOSURE,'newConcreteSHA256':hashlib.sha256(source.encode()).hexdigest(),'componentConcreteSHA256':hashlib.sha256(supplement_source.encode()).hexdigest(),'nativeRuntime':'NOT RUN by host packet; runtime receipts live in explicitly excluded runtime subtree','nativeDispatchAuthorizedByThisPacket':False,'physicalPhones':'deferred disconnected','gaAccepted':False}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--seal',action='store_true');args=parser.parse_args()
    result=check(require_seal=not args.seal)
    if args.seal:
        support.save(support.HERE/'receipt.json',result)
        result['files']=len(support.files())
        support.save(support.HERE/'receipt.json',result)
        support.save(support.HERE/'packet-seal.json',{'schema':1,'excludedExactPath':str((support.HERE/'packet-seal.json').relative_to(support.ROOT)),'excludedMutableRuntimeSubtree':str((support.HERE/'runtime').relative_to(support.ROOT)),'files':support.files()})
        result=check()
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=='__main__':main()
