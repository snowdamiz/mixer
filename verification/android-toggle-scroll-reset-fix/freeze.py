#!/usr/bin/env python3
"""Freeze finite root-only fresh-container reset candidate source. No native dispatch."""
import hashlib
import support,run
def main():
    receipt=support.read(support.HERE/'supplement-1/receipt.json');_,original,_=support.repair_runner()
    contract={'schema':1,'candidate':'supplement-1','sourceClosureSHA256':receipt['sourceClosureSHA256'],'apk':receipt['apk'],'upstreamConcreteSHA256':hashlib.sha256(original.encode()).hexdigest(),'frozenScrollSeal':support.bind(support.SCROLL/'packet-seal.json'),'sourceUnchanged':False,'nativeDispatchAuthorizedByHost':False,'mode':'original-protocol-fixture-reset-fix'}
    source,deltas=run.derive(original,contract);contract.update(concreteSHA256=hashlib.sha256(source.encode()).hexdigest(),sourceDeltas=deltas)
    contract['implementationBindings']={name:support.bind(support.HERE/name) for name in ('run.py','support.py','freeze.py')};contract['toolBindings']=support.read(support.SCROLL/'runner-contract.json')['toolBindings']
    support.save(support.HERE/'runner-contract.json',contract);(support.HERE/'derived-runner.py').write_text(source);_,_,diff=run.load_runner();(support.HERE/'derived-runner.diff').write_text(diff)
    print('frozen fixture-only minimum scroll fresh-container reset candidate; native NOT RUN')
if __name__=='__main__':main()
