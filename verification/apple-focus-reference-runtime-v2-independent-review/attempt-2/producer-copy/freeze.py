#!/usr/bin/env python3
"""Freeze/verify the exact host preparation; no runtime imports or native tools."""
import argparse
import datetime
import json
import sys
import prepare


def freeze(attempt):
    path=prepare.BASE/'handoff.json';prepare.require(not path.exists(),'Preserve frozen handoff')
    verified=prepare.verify()
    receipt_path=prepare.BASE/f'host-attempt-{attempt}/receipt.json'
    receipt=json.loads(receipt_path.read_bytes());prepare.require(receipt['passed'] is True,'Passing host attempt required')
    prepare.require(receipt['ownedSources']=={name:prepare.row(prepare.BASE/name) for name in prepare.OWNED},'Host-tested source differs')
    paths=[prepare.ROOT/'docs/apple-focus-reference-runtime-v2.md']+[p for p in prepare.BASE.rglob('*') if p.is_file()]
    prepare.require(not any(p.is_symlink() for p in paths),'Symlink in handoff')
    members={str(p.relative_to(prepare.ROOT)):prepare.row(p) for p in sorted(paths)}
    value={'schema':'mixer.apple-focus-reference-runtime-frozen-handoff.2','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(prepare.BASE/'freeze.py'),'freeze','--attempt',str(attempt)],'python':sys.version,'packetSHA256':verified['packetSHA256'],'members':members,'memberTreeSHA256':prepare.sha(prepare.stable(members)),'testsRun':receipt['testsRun'],'hostAttempt':attempt,'sourceRevisionLabel':receipt['sourceRevisionLabel'],'sourceTreeSHA256':prepare.SOURCE,'productArchiveSHA256':prepare.PRODUCT,'historicalV1FailuresPreserved':True,'observerV2Unchanged':True,'scope':'Host-reviewed preparation/importer; independent review and root dispatch are still required','nativeExecuted':False,'runtimeSelected':False,'runnableSourcePacketPrepared':True,'compileRerun':False,'runPassed':False,'completeCaseSet':False,'cursorCompletionCredit':False,'fullSixCaseQualification':False,'nativeKeyboardQualification':False,'carrierAccepted':False,'gaAccepted':False,'physicalPhones':'disconnected-deferred','cleanup':receipt['cleanup']}
    with path.open('xb') as stream:stream.write(prepare.stable(value))
    print(json.dumps({'handoffSHA256':prepare.row(path)['sha256'],'packetSHA256':verified['packetSHA256'],'testsRun':receipt['testsRun'],'nativeExecuted':False},sort_keys=True))


def verify():
    path=prepare.BASE/'handoff.json';value=json.loads(path.read_bytes())
    prepare.require(prepare.sha(prepare.stable(value['members']))==value['memberTreeSHA256'],'Handoff digest differs')
    for name,row in value['members'].items():prepare.require(prepare.row(prepare.ROOT/name)==row,'Frozen member changed: '+name)
    prepared=prepare.verify();prepare.require(prepared['packetSHA256']==value['packetSHA256'],'Frozen packet differs')
    return {'handoffSHA256':prepare.row(path)['sha256'],'packetSHA256':value['packetSHA256'],'testsRun':value['testsRun'],'nativeExecuted':False,'scope':'File/hash verification only'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','verify']);p.add_argument('--attempt',type=int,default=1);args=p.parse_args()
    if args.action=='freeze':freeze(args.attempt)
    else:print(json.dumps(verify(),sort_keys=True))
