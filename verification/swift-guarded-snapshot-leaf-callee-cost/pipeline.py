"""Deterministic pure generation; no compiler or product runner import."""
import sys
sys.dont_write_bytecode=True
import derive,evaluator,layouts

def compute():
 ledger=derive.finish(derive.derive());unsubstituted=evaluator.interface(ledger);observations=layouts.reconcile(ledger,unsubstituted)
 ledger=layouts.substitute(ledger,observations)
 ledger['full_source146_layout_binding']=observations['compiler_binding']
 contract=evaluator.interface(ledger)
 return ledger,observations,contract
if __name__=='__main__':
 if (derive.HERE/'seal.json').exists():raise SystemExit('frozen packet: use verify.py')
 ledger,observations,contract=compute()
 derive.out('callee-ledger.json',ledger);derive.out('native-layout-observations.json',observations);derive.out('cost-interface.json',contract)
 print('authored/accepted nodes:',len(ledger['nodes']),'concrete exports:',len(contract['exports']),'remaining native keys:',len({t for r in contract['exports'].values() for t in r['native']}))
