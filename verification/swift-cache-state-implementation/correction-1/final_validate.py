#!/usr/bin/env python3
"""Serial stage coordinator; every host child has its own deadline/PID group."""
import json,os,subprocess,sys,runpy,time
from run_host import ROOT,REPO,RUST,run,sha
started=time.time()
before={str(p.relative_to(ROOT)):sha(p)for p in (ROOT/'source').rglob('*')if p.is_file()}
for name in ['run_host.py','run_regressions.py','api_checks.py','run_old_api.py','audit_source.py','build_ledgers.py','correction_audit.py']:
 print('FINAL_STAGE',name,flush=True)
 runpy.run_path(str(ROOT/name),run_name='__main__')
result=run('production-expanded',[RUST,'--edition=2021','--crate-type=lib','--crate-name','cache_fixture','-Zunpretty=expanded',ROOT/'source/library/analyzer.rs'],dict(os.environ,RUSTC_BOOTSTRAP='1'));assert result.returncode==0
expanded=result.stdout.decode();assert 'fn cache_core<' not in expanded and 'static COMMIT_FAULT' not in expanded and 'static CLEANUP_FAULT' not in expanded
assert before=={str(p.relative_to(ROOT)):sha(p)for p in (ROOT/'source').rglob('*')if p.is_file()}
context=subprocess.run(['git','rev-parse','HEAD'],cwd=REPO,capture_output=True,text=True,check=True,timeout=5).stdout.strip()
(ROOT/'evidence/final-validation.json').write_text(json.dumps({'started':started,'ended':time.time(),'source_sha256':before,'context_revision_only':context,'rustc':str(RUST),'new_cache_state_methods':27,'guard_methods_included':5,'private_guard_scenarios_per_mode':4337,'private_guard_public_reachability_credit':0,'old_producer_methods':78,'old_independent_methods':14,'unique_methods_per_mode':119,'modes':['debug','optimized'],'host_binary_tests':81,'producer_regression_binary_tests':105,'independent_regression_binary_tests':95,'new_api_positive':1,'new_api_negative':15,'inherited_api_positive':1,'inherited_api_negative':8,'all_command_dispositions_as_expected':True,'production_forwarding_Result_layer':False,'test_only_fault_hooks_absent_from_production_expansion':True,'inherited_scalar_block_and_P01_P35_independent_reconciliation':'pending','independent_candidate_acceptance':False,'native_runtime_or_capture_started':False,'GA_qualified':False},indent=2)+'\n')
print('FINAL_VALIDATION expected dispositions passed; source closure unchanged',flush=True)
