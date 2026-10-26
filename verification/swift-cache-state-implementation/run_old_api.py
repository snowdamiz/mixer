#!/usr/bin/env python3
import json,pathlib,shutil
from run_host import ROOT,REPO,RUST,run,sha
old=REPO/'verification/swift-envelope-ci-pack/api';target=ROOT/'api/inherited';target.mkdir(exist_ok=True)
lib=ROOT/'evidence/libold_api.rlib';assert run('old-api-library',[RUST,'--edition=2021','--crate-type=lib','--crate-name','cache_fixture',ROOT/'source/library/analyzer.rs','-o',lib]).returncode==0
rows=[]
try:
 for source in sorted(old.glob('*.rs')):
  p=target/source.name;shutil.copy2(source,p);assert sha(p)==sha(source)
  out=target/(source.stem+'.binary');r=run('old-api-'+source.stem,[RUST,'--edition=2021','--extern',f'mixer_absence={lib}',p,'-o',out]);positive=source.name=='positive.rs';assert (r.returncode==0)==positive
  if positive:assert run('old-api-positive-execute',[out]).returncode==0
  out.unlink(missing_ok=True);rows.append({'source':str(source.relative_to(REPO)),'owned_copy':str(p.relative_to(ROOT)),'sha256':sha(p),'compile_success':r.returncode==0,'expected_success':positive})
finally:lib.unlink(missing_ok=True)
assert len(rows)==9
(ROOT/'evidence/old-api-summary.json').write_text(json.dumps({'actual_new_source_sha256':{p.name:sha(p)for p in (ROOT/'source/library').glob('*.rs')},'controls':rows,'passed':True},indent=2)+'\n')
