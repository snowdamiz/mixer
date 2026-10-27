#!/usr/bin/env python3
"""Read-only frozen packet and released-data replay. Optional pure tests."""
from pathlib import Path
import argparse,hashlib,json,sys,unittest
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;R=H.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--tests',action='store_true');args=parser.parse_args()
 seal=json.loads((H/'seal.json').read_text());members=seal['members'];actual=sorted(str(p.relative_to(H)) for p in H.rglob('*') if p.is_file() and p!=H/'seal.json')
 if actual!=sorted(r['path'] for r in members):raise ValueError('sealed membership changed')
 for row in members:
  b=(H/row['path']).read_bytes()
  if (len(b),sha(b))!=(row['bytes'],row['sha256']):raise ValueError('changed sealed member '+row['path'])
 import pipeline,checks
 ledger,observations,contract=pipeline.compute()
 for name,value in [('callee-ledger.json',ledger),('native-layout-observations.json',observations),('cost-interface.json',contract)]:
  if json.loads((H/name).read_text())!=value:raise ValueError('pure derivation mismatch '+name)
 for path,identity in ledger['input_bindings'].items():
  b=(R/path).read_bytes()
  if len(b)!=identity['bytes'] or sha(b)!=identity['sha256']:raise ValueError('changed released input '+path)
 checks.validate(ledger,contract)
 tested=0
 if args.tests:
  import test_cost
  result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(test_cost.CalleeCost));tested=result.testsRun
  if not result.wasSuccessful():raise SystemExit(1)
 print(json.dumps(dict(status='frozen-source146-callee-candidate-reproduced',members=len(members),bytes=sum(r['bytes'] for r in members),authored_bodies=38,concrete_exports=21,remaining_native_terms=13,typed_payload_imports=19,pure_test_methods_replayed=tested,compiler_invoked=False,actual_product_execution=False,complete_host_quote=False,operational_grant=False)))
if __name__=='__main__':main()
