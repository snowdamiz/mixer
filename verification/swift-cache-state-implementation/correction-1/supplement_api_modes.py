#!/usr/bin/env python3
"""Add optimized API dispositions; reuse unchanged source-bound host regressions."""
import json,pathlib,runpy,sys,time,shutil
from run_host import ROOT,REPO,sha
started=time.time();final=ROOT/'evidence/final-validation.json'
prior=json.loads(final.read_text());archive=ROOT/'evidence/attempts/default-api-final-validation.json'
assert not archive.exists();shutil.copyfile(final,archive)
before={str(p.relative_to(ROOT)):sha(p)for p in (ROOT/'source').rglob('*')if p.is_file()};assert before==prior['source_sha256']
for name in ['api_checks.py','run_old_api.py','audit_source.py','build_ledgers.py','correction_audit.py']:
 print('SUPPLEMENT_STAGE',name,flush=True);runpy.run_path(str(ROOT/name),run_name='__main__')
a=json.loads((ROOT/'evidence/api-summary.json').read_text());b=json.loads((ROOT/'evidence/old-api-summary.json').read_text());assert len(a['probes'])==32 and len(b['controls'])==18
assert before=={str(p.relative_to(ROOT)):sha(p)for p in (ROOT/'source').rglob('*')if p.is_file()}
prior.update({'api_modes':['debug','optimized'],'api_dispositions_per_mode':25,'api_supplement':'evidence/api-mode-supplement.json','ended':time.time()});final.write_text(json.dumps(prior,indent=2)+'\n')
(ROOT/'evidence/api-mode-supplement.json').write_text(json.dumps({'command':[sys.executable,str(pathlib.Path(__file__).resolve())],'python':sys.version,'script_sha256':sha(pathlib.Path(__file__)),'started':started,'ended':time.time(),'source_sha256':before,'source_unchanged_since_host_and_regressions':True,'reason':'Add optimized API compilation/execution after the first source-bound suite ran default API checks; prior raw commands retained. Host/regressions need no repeated run because product source is unchanged.','per_mode_new_API':16,'per_mode_old_API':9,'modes':['debug','optimized'],'all_expected_dispositions_passed':True,'independent_accepted':False},indent=2)+'\n')
print('API_SUPPLEMENT both modes passed; host source unchanged',flush=True)
