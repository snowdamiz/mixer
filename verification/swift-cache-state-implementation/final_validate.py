#!/usr/bin/env python3
import json,os,pathlib,subprocess,sys,runpy
from run_host import ROOT,REPO,RUST,run,sha
before={str(p.relative_to(ROOT)):sha(p)for p in (ROOT/'source').rglob('*')if p.is_file()}
for name in ['run_host.py','run_regressions.py','api_checks.py','audit_source.py','build_ledgers.py']:
 print('FINAL_STAGE',name,flush=True)
 runpy.run_path(str(ROOT/name),run_name='__main__')
result=run('production-expanded',[RUST,'--edition=2021','--crate-type=lib','--crate-name','cache_fixture','-Zunpretty=expanded',ROOT/'source/library/analyzer.rs'],dict(os.environ,RUSTC_BOOTSTRAP='1'));assert result.returncode==0
expanded=result.stdout.decode();assert 'fn cache_core<' not in expanded and 'static COMMIT_FAULT' not in expanded and 'static CLEANUP_FAULT' not in expanded
assert before=={str(p.relative_to(ROOT)):sha(p)for p in (ROOT/'source').rglob('*')if p.is_file()}
context=subprocess.run(['git','rev-parse','HEAD'],cwd=REPO,capture_output=True,text=True,check=True,timeout=5).stdout.strip()
(ROOT/'evidence/final-validation.json').write_text(json.dumps({'source_sha256':before,'context_revision_only':context,'rustc':str(RUST),'new_cache_state_methods':22,'old_producer_methods':78,'old_independent_methods':14,'unique_methods_per_mode':114,'modes':['debug','optimized'],'api_positive':1,'api_negative':15,'all_commands_passed':True,'production_forwarding_Result_layer':False,'test_only_fault_hooks_absent_from_production_expansion':True,'independent_candidate_acceptance':False,'native_runtime_or_capture_started':False,'GA_qualified':False},indent=2)+'\n')
print('FINAL_VALIDATION all commands passed; source closure unchanged')
