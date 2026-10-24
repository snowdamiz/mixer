#!/usr/bin/env python3
"""Freeze host-only repair evidence and root command; dispatch is never performed by this tool."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import common
import run
import verify_candidate
import check_packet


def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--attempt',required=True);args=parser.parse_args()
    if not re.fullmatch(r'finalization-[1-9][0-9]*',args.attempt):parser.error('fresh finalization-N required')
    if (common.HERE/'packet-seal.json').exists():raise ValueError('immutable host packet already sealed')
    out=common.HERE/args.attempt;out.mkdir();runner,source,_=run.load_runner();commands=[]
    result={'schema':1,'status':'sealing-host-only-repair','startedUTC':now(),'commands':commands,'nativeRuntime':'NOT RUN','nativeInstancesStarted':0,'physicalTargetsQueried':False,'scriptSHA256':common.sha(__file__)}
    def command(name,argv,allowed=0):
        start=now();completed=runner.execute(argv,cwd=common.ROOT,timeout=60);log=out/(name+'.log');log.write_bytes(completed.stdout);commands.append({'name':name,'argv':argv,'cwd':str(common.ROOT),'startedUTC':start,'finishedUTC':now(),'exitCode':completed.returncode,'output':log.name,'sha256':common.sha(log),'ownedCommandGroupCleanup':completed.groupCleanup})
        if completed.returncode!=allowed or completed.groupCleanup['after']:raise ValueError('final host command failed '+name)
        return completed.stdout.decode().strip()
    try:
        host=json.loads((common.HERE/'host-review-3/receipt.json').read_text());replay=json.loads((common.HERE/'build-replay-1/receipt.json').read_text());candidate=runner.bind_candidate(common.HERE/'candidate-5')
        if host['status']!='passed-host-only-pointer-fixture-controls-and-identity' or host['hostTestCount']!=42 or host['scratchCleanup']['status']!='removed':raise ValueError('latest42 passing host tests and cleanup required')
        for name,value in host['implementationBindings'].items():
            if common.sha(common.HERE/name)!=value:raise ValueError('host-tested source drift '+name)
        if replay['status']!='passed-fresh-empty-context-source-class-dex-and-official-packaging-replay' or replay['freshPrivateClassesByteExact']!=4 or replay['scratchCleanup']['status']!='removed' or replay['sourceClosureSHA256']!=candidate['sourceClosureSHA256'] or replay['apkSHA256']!=candidate['apkSHA256']:raise ValueError('fresh exact source/class/DEX replay identity differs')
        for folder in ('candidate-5','host-review-1','host-review-2','host-review-3','build-replay-1','cleanup-generated-1'):common.validate_seal(common.HERE/folder)
        for snapshot in ('runner-freeze-1','runner-freeze-2','runner-freeze-3'):
            expected=json.loads((common.HERE/snapshot/'source-bindings.json').read_text())
            for name,digest in expected.items():
                if common.sha(common.HERE/snapshot/name)!=digest:raise ValueError('historical frozen source drift')
        review=verify_candidate.check();bindings=check_packet.upstream()
        # Reconstruct the precise predecessor APK-entry mapping before sealing it.
        old=json.loads((common.PRIOR/'candidate-4/apk-entries.json').read_text());new=json.loads((common.HERE/'candidate-5/apk-entries.json').read_text());delta={n:{'candidate4':old.get(n),'candidate5':new.get(n)} for n in sorted(set(old)|set(new)) if old.get(n)!=new.get(n)}
        if delta!=json.loads((common.HERE/'candidate4-apk-entry-delta.json').read_text()) or set(delta)!={'META-INF/DEBUG.RSA','META-INF/DEBUG.SF','META-INF/MANIFEST.MF','classes.dex'}:raise ValueError('candidate4 APK entry delta differs')
        context_revision=command('source-revision',['git','rev-parse','HEAD']);context_tree=command('source-tree',['git','rev-parse','HEAD^{tree}']);command('source-status',['git','status','--short']);command('python-version',[sys.executable,'--version']);command('immutable-predecessor-packet-replay',[sys.executable,'-B',str(common.PRIOR/'check_packet.py')])
        if command('open-holders',['/usr/sbin/lsof','-nP','+D',str(common.HERE)],allowed=1):raise ValueError('owned host packet still held')
        packet={'schema':1,'status':'sealed-host-only-candidate5-oracle-repair-root-review-pending','observedUTC':now(),'candidate':'candidate-5','nativeRuntime':'NOT RUN','nativeAcceptance':False,'gaAcceptance':False,'nativeInstancesStarted':0,'physicalTargetsQueried':False,'nativeDispatchAuthorizedByThisPacket':False,'sourceRevision':candidate['sourceRevision'],'sourceTree':candidate['sourceTree'],'latestRepositoryContextRevision':context_revision,'latestRepositoryContextTree':context_tree,'sourceClosureSHA256':candidate['sourceClosureSHA256'],'apkSHA256':candidate['apkSHA256'],'builtArchiveSHA256':candidate['builtArchiveSHA256'],'upstream':bindings,'runnerWrapperSHA256':common.sha(common.HERE/'run.py'),'runnerContract':run.CONTRACT.name,'runnerContractSHA256':common.sha(run.CONTRACT),'concreteRunnerSHA256':hashlib.sha256(source.encode()).hexdigest(),'oracleSHA256':common.sha(common.HERE/'oracle.py'),'sourceDeltas':len(json.loads(run.CONTRACT.read_text())['sourceDeltas']),'hostTestCount':42,'hostReview':'host-review-3','freshBuildReplay':'build-replay-1','artifactReview':review,'gestureActions':20,'nominalInjectedMotionEvents':124,'maxInjectedMotionEvents':320,'directNativeCallbackCount':None,'allOwnedScratchRemoved':True,'runtimeOutputPolicy':check_packet.RUNTIME_POLICY,'runtimeSubtreeExcluded':'verification/android-pointer-oracle-repair/runtime','nextRootCommand':['python3','-B','verification/android-pointer-oracle-repair/run.py','--build','candidate-5','--attempt','runtime-1','--execute-native'],'nextRuntimeDirectory':'verification/android-pointer-oracle-repair/runtime/runtime-1','retainedSignedAPK':candidate['externalAPK'],'limitations':['host-only finite parser/build/packaging controls; root independent source/runner/packet acceptance required before native dispatch','internal checked-change callback counts remain null/unobserved','physical phones disconnected/deferred; real IME, accessibility, broader lifecycle, shared design parity, public V2, signed OTA, immutable separately published FieldLog packages, stores, customers, operations and accountable GA acceptance pending']}
        common.save(common.HERE/'packet.json',packet);result['status']='passed-host-only-finalization';result['upstream']=bindings;result['hostTestCount']=42
    except BaseException as failure:result.update({'status':'failed-host-finalization-retained','failure':repr(failure)});raise
    finally:result['finishedUTC']=now();common.save(out/'receipt.json',result);common.save(out/'artifact-seal.json',common.exact_seal(out))
    target=common.HERE/'packet-seal.json';common.save(target,{'schema':1,'scope':'all repair-owned host files and document including every nested seal and receipt; exclude only this exact host root seal and designated runtime subtree','runtimeSubtreeExcluded':'verification/android-pointer-oracle-repair/runtime','files':check_packet.files()})
    print(json.dumps(check_packet.check(),sort_keys=True))

if __name__=='__main__':main()
