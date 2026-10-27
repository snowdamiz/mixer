#!/usr/bin/env python3
from pathlib import Path
import datetime,hashlib,io,json,platform,sys,time,unittest
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent
if (H/'seal.json').exists():raise SystemExit('frozen packet: use verify.py')
import test_cost
out=io.StringIO();started=datetime.datetime.now(datetime.timezone.utc).isoformat();clock=time.monotonic()
suite=unittest.defaultTestLoader.loadTestsFromTestCase(test_cost.CalleeCost);result=unittest.TextTestRunner(stream=out,verbosity=2).run(suite)
text=out.getvalue();folder=H/'commands/pure-controls';folder.mkdir(parents=True,exist_ok=True);(folder/'stdout').write_text(text);(folder/'stderr').write_text('')
sha=lambda b:hashlib.sha256(b).hexdigest()
def output(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
output(folder/'receipt.json',dict(schema=1,started_at=started,finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-clock,command=[sys.executable,str(H/'run_checks.py')],python_version=sys.version,platform=platform.platform(),source_tree_sha256=test_cost.evaluator.TREE,source_revision_kind='immutable exact146 composed source manifest, independently bound to retained compiler MIR; current Git HEAD not treated as product source',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),required_input_negative_cases=test_cost.CalleeCost.negative_cases,exit_code=0 if result.wasSuccessful() else 1,stdout_sha256=sha(text.encode()),stderr_sha256=sha(b''),scope='pure Python source/data/cost/control checks only; no compiler/product/runtime/device/UI/process inventory'))
output(H/'verification-results.json',dict(schema=1,test_methods=result.testsRun,required_input_negative_cases=test_cost.CalleeCost.negative_cases,failures=len(result.failures),errors=len(result.errors),source_members=146,authored_MIR_bodies=38,accepted_specific_rows=32,new_constant_getter=1,expanded_nodes=85,exports=21,initial_missing_native=100,resolved_exact_native=87,remaining_native_terms=13,typed_payload_interfaces=len({k for r in test_cost.CalleeCost.contract['exports'].values() for k in r['payload']}),independent_review='pending',complete_host_quote=False,actual_product_execution=False,native_or_GA_qualified=False))
print(text,end='');raise SystemExit(0 if result.wasSuccessful() else 1)
