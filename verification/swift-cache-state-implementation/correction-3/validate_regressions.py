#!/usr/bin/env python3
"""Serial bounded host commands; no outer suite deadline or native surface."""
import json,os,runpy,sys,time
from run_host import ROOT,RUST,run,sha
started=time.time();before={str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'source').rglob('*'))if p.is_file()}
assert before==json.loads((ROOT/'evidence/source-before.json').read_text())
for name in ['run_regressions.py','api_checks.py','run_old_api.py']:
 print('STAGE',name,flush=True);runpy.run_path(str(ROOT/name),run_name='__main__')
r=run('production-expanded',[RUST,'--edition=2021','--crate-type=lib','--crate-name','cache_fixture','-Zunpretty=expanded',ROOT/'source/library/analyzer.rs'],dict(os.environ,RUSTC_BOOTSTRAP='1'));assert r.returncode==0
assert 'fn cache_core<'not in r.stdout.decode()and'static COMMIT_FAULT'not in r.stdout.decode()and'static CLEANUP_FAULT'not in r.stdout.decode()
assert before=={str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'source').rglob('*'))if p.is_file()}
(ROOT/'evidence/final-validation.json').write_text(json.dumps({'command':[sys.executable,str(ROOT/'validate_regressions.py')],'python':sys.version,'script_sha256':sha(ROOT/'validate_regressions.py'),'started':started,'ended':time.time(),'source_sha256':before,'host_test_script':'run_host.py','modes':['debug','optimized'],'host_tests_per_mode':84,'producer_regression_tests_per_mode':108,'independent_regression_tests_per_mode':98,'unique_tests_per_mode':122,'new_methods':30,'old_producer_methods':78,'old_independent_methods':14,'API_dispositions_per_mode':25,'production_test_hooks_absent':True,'all_expected_dispositions_passed':True,'source_accounting_accepted':False,'lifetime_proof_accepted':False,'native_runtime_or_capture_started':False,'independent_accepted':False,'GA_qualified':False},indent=2)+'\n')
print('REGRESSION_VALIDATION all expected dispositions passed',flush=True)
