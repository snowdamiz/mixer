#!/usr/bin/env python3
"""One-time runner source freeze; imports only, never dispatches native work."""
import hashlib
import json
import common
import run

HERE=common.HERE

def main():
    path=run.CONTRACT
    if path.exists():raise ValueError('existing runner contract immutable')
    adapter,_,original,_=common.accepted();built=HERE/'candidate-5';receipt=json.loads((built/'receipt.json').read_text())
    bind=original[original.index('def bind_candidate(built):'):original.index('class ExtractionCleanupRefused')]
    export=original[original.index("            for name, packet in native['packets'].items():"):original.index('        else:\n            raise RuntimeError(\'no actual native result')]
    old=json.loads((common.PARENT.parent/'runner-contract.json').read_text())
    names=('receipt.json','source-lock.json','built-artifacts.json','built-artifacts.tar.gz','artifact-seal.json','artifact-delta.json','apk-entry-delta.json','apk-entries.json','pre-sign-packaging.json','post-sign-packaging.json','pre-sign-official-zipalign.log','post-sign-official-zipalign.log','private-debug-signature-cert.log')
    contract={'schema':1,'candidate':'candidate-5','acceptedConcreteRunnerSHA256':hashlib.sha256(original.encode()).hexdigest(),'acceptedBuildBindings':old['buildBindings'],
        'sourceClosureSHA256':receipt['sourceClosureSHA256'],'frozenAPK_SHA256':receipt['apkSHA256'],'buildBindings':{n:common.sha(built/n) for n in names},
        'acceptedBindSource':bind,'acceptedExportSource':export,
        'implementationBindings':{n:common.sha(HERE/n) for n in ('common.py','bounded_output.py','oracle.py','build.py','CoordinatorJoinActivity.java','CoordinatorJoinInstrumentation.java','operations.json')},
        'toolBindings':{p:v['sha256'] for p,v in receipt['tools'].items()},'scope':'exact twenty private actual-pointer actions, at most320 events; root dispatch only; no physical or GA acceptance',
        'bounds':json.loads((HERE/'operations.json').read_text()),'nativeRuntime':'NOT RUN','directNativeCallbackCount':None}
    source,deltas=run.transform(original,contract);contract.update({'transformedRunnerSHA256':hashlib.sha256(source.encode()).hexdigest(),'sourceDeltas':deltas});common.save(path,contract)
    wrapper=HERE/'run.py';text=wrapper.read_text();needle="CONTRACT_SHA256='PENDING'"
    if text.count(needle)!=1:raise ValueError('exact pending contract site required')
    wrapper.write_text(text.replace(needle,"CONTRACT_SHA256='"+common.sha(path)+"'",1))
    fresh=common.load('pointer_frozen_wrapper',wrapper);runner,source,diff=fresh.load_runner();runner.bind_candidate(built)
    out=HERE/'runner-source-3';out.mkdir();(out/'accepted_packaging_concrete.py').write_text(original);(out/'transformed_runner.py').write_text(source);(out/'runner.diff').write_text(diff);common.save(out/'source-deltas.json',deltas)
    print(json.dumps({'status':'frozen-private-pointer-runner-source-only','wrapperSHA256':common.sha(wrapper),'contractSHA256':common.sha(path),'transformedRunnerSHA256':contract['transformedRunnerSHA256'],'sourceDeltas':len(deltas),'nativeInstancesStarted':0},sort_keys=True))

if __name__=='__main__':main()
