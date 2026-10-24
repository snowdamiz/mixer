#!/usr/bin/env python3
"""Freeze exact root-only diagnostic source. No native dispatch."""
import hashlib
import support
import run
def main():
    receipt=support.read(support.HERE/'supplement-1/receipt.json');_,original,_=support.repair_runner()
    contract={'schema':1,'candidate':'supplement-1','sourceClosureSHA256':receipt['sourceClosureSHA256'],'apk':receipt['apk'],'repairConcreteSHA256':hashlib.sha256(original.encode()).hexdigest(),'frozenRepairSeal':support.bind(support.REPAIR/'packet-seal.json'),'sourceUnchanged':False,'nativeDispatchAuthorizedByHost':False,'mode':'original-protocol'}
    source,deltas=run.derive(original,contract);contract.update(concreteSHA256=hashlib.sha256(source.encode()).hexdigest(),sourceDeltas=deltas)
    contract['implementationBindings']={name:support.bind(support.HERE/name) for name in ('run.py','support.py','diagnostics.py','freeze.py')}
    contract['toolBindings']=support.read(support.REPAIR/'runner-contract.json')['toolBindings']
    support.save(support.HERE/'runner-contract.json',contract);(support.HERE/'derived-runner.py').write_text(source)
    _,_,diff=run.load_runner();(support.HERE/'derived-runner.diff').write_text(diff)
    print('frozen original-protocol scroll diagnostic; native NOT RUN')
if __name__=='__main__':main()
