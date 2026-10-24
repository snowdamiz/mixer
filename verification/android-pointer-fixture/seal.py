#!/usr/bin/env python3
"""Seal the current owned packet, including every nested receipt/seal; no native commands."""
import datetime
import hashlib
import json
from pathlib import Path
import sys
import common
import run
import verify_candidate


def files():
    own=[p for p in common.HERE.rglob('*') if p.is_file() and p!=common.HERE/'packet-seal.json']+[common.ROOT/'docs/android-pointer-fixture.md']
    if any(p.is_symlink() for p in common.HERE.rglob('*')):raise ValueError('packet contains symlink')
    if any(p.name=='.build' and p.is_dir() for p in common.HERE.rglob('*')):raise ValueError('owned scratch remains')
    return {str(p.relative_to(common.ROOT)):{'bytes':p.stat().st_size,'sha256':common.sha(p)} for p in sorted(own)}

def main():
    target=common.HERE/'packet-seal.json'
    if target.exists():raise ValueError('root packet seal already exists')
    runner,source,_=run.load_runner();built=common.HERE/'candidate-4';candidate=runner.bind_candidate(built)
    host=json.loads((common.HERE/'host-review-5/receipt.json').read_text())
    if host['status']!='passed-host-only-pointer-fixture-controls-and-identity' or host['scratchCleanup']['status']!='removed':raise ValueError('current passing host review with cleanup required')
    for name,value in host['implementationBindings'].items():
        if common.sha(common.HERE/name)!=value:raise ValueError('host-tested source drift '+name)
    review=verify_candidate.check();commands=[]
    for name,argv in [('final-source-revision',['git','rev-parse','HEAD']),('final-source-tree',['git','rev-parse','HEAD^{tree}']),('final-source-status',['git','status','--short']),('final-python-version',[sys.executable,'--version']),('final-open-holders',['/usr/sbin/lsof','-nP','+D',str(common.HERE)])]:
        start=datetime.datetime.now(datetime.timezone.utc).isoformat();result=runner.execute(argv,cwd=common.ROOT,timeout=30);log=common.HERE/(name+'.log');log.write_bytes(result.stdout)
        commands.append({'name':name,'argv':argv,'cwd':str(common.ROOT),'startedUTC':start,'finishedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exitCode':result.returncode,'output':log.name,'sha256':common.sha(log),'ownedCommandGroupCleanup':result.groupCleanup})
        if result.returncode!=(1 if name=='final-open-holders' else 0) or (name=='final-open-holders' and result.stdout):raise ValueError('final command failed or packet still open '+name)
    packet={'schema':1,'status':'sealed-host-candidate-root-review-and-native-dispatch-pending','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'candidate':'candidate-4','nativeRuntime':'NOT RUN','nativeAcceptance':False,'gaAcceptance':False,'physicalTargetsQueried':False,'nativeInstancesStarted':0,
        'commands':commands,'sourceRevision':candidate['sourceRevision'],'sourceTree':candidate['sourceTree'],'sourceClosureSHA256':candidate['sourceClosureSHA256'],'apkSHA256':candidate['apkSHA256'],'builtArchiveSHA256':candidate['builtArchiveSHA256'],
        'runnerWrapperSHA256':common.sha(common.HERE/'run.py'),'runnerContractSHA256':common.sha(run.CONTRACT),'concreteRunnerSHA256':hashlib.sha256(source.encode()).hexdigest(),'artifactReview':review,
        'hostReview':'host-review-5','hostTestCount':22,'directNativeCallbackCount':None,'gestureActions':20,'nominalInjectedMotionEvents':124,'maxInjectedMotionEvents':320,
        'externalAPK':candidate['externalAPK'],'allOwnedScratchRemoved':True,'finalOpenHolders':0,'nativeDispatchAuthorizedByThisPacket':False,
        'nextRootCommand':['python3','-B','verification/android-pointer-fixture/run.py','--build','candidate-4','--attempt','runtime-1','--execute-native'],
        'limitations':['host build/oracle only; root must independently review before one native dispatch','internal callbacks unobserved/null','physical phones disconnected/deferred; IME/accessibility/full lifecycle/public/signed OTA/FieldLog/store/customer/operations/GA pending'],
        'historicalSealException':'host-review-2/artifact-seal.json records the failed-cleanup snapshot; its generated scratch was later removed by cleanup-host-review-2 and its exact original receipt/seal bytes remain retained'}
    common.save(common.HERE/'packet.json',packet)
    common.save(target,{'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'all current owned packet files and document, including every nested seal/receipt; exclude only exact verification/android-pointer-fixture/packet-seal.json','files':files()})
    print(json.dumps({'status':packet['status'],'packetSealSHA256':common.sha(target),'packetSHA256':common.sha(common.HERE/'packet.json'),'concreteRunnerSHA256':packet['concreteRunnerSHA256'],'fileCount':len(json.loads(target.read_text())['files']),'nativeInstancesStarted':0},sort_keys=True))

if __name__=='__main__':main()
