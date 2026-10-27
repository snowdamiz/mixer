#!/usr/bin/env python3
"""Host-only independent test recorder, writes only this owned review lane."""
from pathlib import Path
import contextlib,datetime,hashlib,io,json,os,sys,time,unittest
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import test_independent
begin=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat();out=io.StringIO()
with contextlib.redirect_stdout(out),contextlib.redirect_stderr(out):
 result=unittest.TextTestRunner(stream=out,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_independent))
d=out.getvalue().encode();(HERE/'independent.stdout').write_bytes(d);(HERE/'independent.stderr').write_bytes(b'')
r={'schema':1,'argv':[sys.executable,*sys.argv],'cwd':os.getcwd(),'python_version':sys.version,'started_at':start,'elapsed_seconds':time.monotonic()-begin,'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'success':result.wasSuccessful(),'stdout_sha256':hashlib.sha256(d).hexdigest(),'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'test_sha256':hashlib.sha256((HERE/'test_independent.py').read_bytes()).hexdigest(),'candidate_source146_tree':'acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d','scope':'Synthetic pure-byte oracle plus frozen source input, no Rust candidate invocation','compiler_invocations':0,'product_loader_runtime_UI_capture_or_global_process_inventory':False,'operational_grant':False,'all_three_selectors':'Pending','native_FieldLog_OTA_GA':False,'cleanup':'No child/native/scratch resources created'}
(HERE/'independent-receipt.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');print(json.dumps(r));raise SystemExit(0 if result.wasSuccessful() else 1)
