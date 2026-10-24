#!/usr/bin/env python3
"""Host-only source contract creation; never dispatch native commands."""
import hashlib,sys
import support
import run

def main():
    folder=support.HERE/'supplement-1';receipt=support.read(folder/'receipt.json')
    _,original,_=support.old_runner()
    contract={'schema':1,'candidate':'supplement-1','sourceClosureSHA256':receipt['sourceClosureSHA256'],'apk':receipt['apk'],'originalConcreteSHA256':hashlib.sha256(original.encode()).hexdigest(),'originalRunnerSeal':support.bind(support.RUNNER/'packet-seal.json'),'sourceUnchanged':False,'nativeDispatchAuthorizedByHost':False}
    source,deltas=run.derive(original,contract);contract['concreteSHA256']=hashlib.sha256(source.encode()).hexdigest();contract['sourceDeltas']=deltas
    contract['implementationBindings']={n:support.bind(support.HERE/n) for n in ('run.py','support.py','diagnostics.py','freeze.py')}
    original_contract=support.read(support.RUNNER/'runner-contract.json');contract['toolBindings']={p:support.bind(p) for p in original_contract['toolBindings']}
    contract['toolBindings'][str(support.JDK/'bin/java')]=support.bind(support.JDK/'bin/java');contract['toolBindings'][str(support.JDK/'bin/javac')]=support.bind(support.JDK/'bin/javac')
    support.save(support.HERE/'runner-contract.json',contract);(support.HERE/'derived-runner.py').write_text(source)
    _,_,diff=run.load_runner();(support.HERE/'derived-runner.diff').write_text(diff)
    print('frozen exact finite repair source contract; native NOT RUN')
if __name__=='__main__':main()
