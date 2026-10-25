#!/usr/bin/env python3
"""File-only seal/verification of the independent rejected-v2 review."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import stat
import sys

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
DOC=ROOT/'docs/apple-focus-reference-runtime-v2-independent-review.md'
HANDOFF=BASE/'handoff.json'
sha=lambda data:hashlib.sha256(data).hexdigest()
stable=lambda value:(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()


def row(path):
    info=path.lstat()
    assert path.resolve()==path and stat.S_ISREG(info.st_mode) and not path.is_symlink(),str(path)
    raw=path.read_bytes()
    return {'kind':'file','mode':stat.S_IMODE(info.st_mode),'bytes':len(raw),'sha256':sha(raw)}


def frozen_inputs():
    before=json.loads((BASE/'attempt-2/frozen-inputs-before.json').read_bytes())
    after=json.loads((BASE/'attempt-2/frozen-inputs-after.json').read_bytes())
    assert before==after
    for name,item in before.items():
        path=ROOT/name
        resolved=path.resolve()
        if path!=resolved:
            assert str(path)=='/Applications/Xcode_26.6.app/Contents/Developer/Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator26.5.sdk/SDKSettings.json'
            assert str(resolved)=='/Applications/Xcode_26.6.app/Contents/Developer/Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator.sdk/SDKSettings.json'
        assert row(resolved)['sha256']==item['sha256'],name
    return before


def freeze():
    assert not HANDOFF.exists(),'Preserve existing seal'
    before=frozen_inputs()
    receipt=json.loads((BASE/'attempt-2/receipt.json').read_bytes())
    assert receipt['allFrozenInputsUnchanged'] is True
    assert receipt['results']['producer']['testsRun']==111 and receipt['results']['producer']['passed'] is True
    assert receipt['results']['independent']['testsRun']==33
    assert len(receipt['results']['independent']['failures'])==10 and not receipt['results']['independent']['errors']
    assert receipt['cleanup']['allOwnedTemporaryDirectoriesAbsent'] is True
    assert row(BASE/'run_review.py')['sha256']==receipt['reviewerSourceSHA256']
    members={str(path.relative_to(ROOT)):row(path) for path in sorted([DOC]+[p for p in BASE.rglob('*') if p.is_file()])}
    value={'schema':'mixer.apple-focus-reference-runtime-independent-review-handoff.1',
           'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'status':'rejected-v2-native-dispatch-held','approvedForNativeDispatch':False,
           'command':[sys.executable,'-B',str(Path(__file__)),'freeze'],'python':sys.version,
           'reviewedHandoffSHA256':receipt['handoffSHA256'],'reviewedPacketSHA256':receipt['packetSHA256'],
           'reviewReceiptSHA256':row(BASE/'attempt-2/receipt.json')['sha256'],
           'sourceTreeSHA256':receipt['sourceTreeSHA256'],'productArchiveSHA256':receipt['productArchiveSHA256'],
           'sourceRevisionLabel':receipt['sourceRevisionLabel'],'frozenInputCount':len(before),
           'frozenInputObservationSHA256':row(BASE/'attempt-2/frozen-inputs-before.json')['sha256'],
           'producerControls':111,'producerControlsPassed':111,'independentControls':33,
           'independentControlsPassed':23,'independentFailures':10,'independentErrors':0,
           'findings':[{'id':'R1','severity':'dispatch-blocker','failedControls':1,'meaning':'Actual composed bridge and Settings store emit normal files rejected by application capture inventory'},
                       {'id':'R2','severity':'synthetic-consistency','failedControls':1,'meaning':'Floating commandGeneration accepted as exact integer generation'},
                       {'id':'R3','severity':'synthetic-consistency','failedControls':7,'meaning':'Malformed application signature inode/length/digest metadata accepted'},
                       {'id':'R4','severity':'synthetic-consistency','failedControls':1,'meaning':'Baseline file mtime after premise attachment accepted'}],
           'members':members,'memberTreeSHA256':sha(stable(members)),'cleanup':receipt['cleanup'],
           'historicalAttemptOnePreserved':True,'allFrozenInputsUnchanged':True,'syntheticOnly':True,
           'nativeExecuted':False,'runtimeSelected':False,'runPassed':False,'completeCaseSet':False,
           'cursorCompletionCredit':False,'fullSixCaseQualification':False,'nativeKeyboardQualification':False,
           'carrierAccepted':False,'gaAccepted':False,'physicalPhones':'disconnected-deferred',
           'scope':'Independent host review only; native dispatch held pending separately reviewed versioned repair; no native provenance or GA acceptance'}
    with HANDOFF.open('xb') as stream:stream.write(stable(value))
    return verify()


def verify():
    value=json.loads(HANDOFF.read_bytes())
    assert value['status']=='rejected-v2-native-dispatch-held' and value['approvedForNativeDispatch'] is False
    assert sha(stable(value['members']))==value['memberTreeSHA256']
    for name,item in value['members'].items():assert row(ROOT/name)==item,name
    frozen_inputs()
    return {'handoffSHA256':row(HANDOFF)['sha256'],'membersVerified':len(value['members']),
            'status':value['status'],'nativeExecuted':False,'allFrozenInputsUnchanged':True}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['freeze','verify'])
    args=parser.parse_args();print(json.dumps(freeze() if args.action=='freeze' else verify(),sort_keys=True))
