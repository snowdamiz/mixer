#!/usr/bin/env python3
import json,pathlib,shutil
from run_host import ROOT,REPO,RUST,run,sha,remove_product
old=REPO/'verification/swift-envelope-ci-pack/api';target=ROOT/'api/inherited';target.mkdir(exist_ok=True)
rows=[]
for mode,opts in [('debug',[]),('optimized',['-O'])]:
 lib=ROOT/'evidence'/f'libold_api-{mode}.rlib';assert run('old-api-library-'+mode,[RUST,'--edition=2021',*opts,'--crate-type=lib','--crate-name','cache_fixture',ROOT/'source/library/analyzer.rs','-o',lib]).returncode==0
 try:
  for source in sorted(old.glob('*.rs')):
   p=target/source.name;shutil.copy2(source,p);assert sha(p)==sha(source)
   out=target/(source.stem+'-'+mode+'.binary');r=run('old-api-'+source.stem+'-'+mode,[RUST,'--edition=2021',*opts,'--extern',f'mixer_absence={lib}',p,'-o',out]);positive=source.name=='positive.rs';assert (r.returncode==0)==positive
   if positive:assert run('old-api-positive-execute-'+mode,[out]).returncode==0
   remove_product(out);rows.append({'mode':mode,'source':str(source.relative_to(REPO)),'owned_copy':str(p.relative_to(ROOT)),'sha256':sha(p),'compile_success':r.returncode==0,'expected_success':positive})
 finally:remove_product(lib)
assert len(rows)==18
(ROOT/'evidence/old-api-summary.json').write_text(json.dumps({'actual_new_source_sha256':{p.name:sha(p)for p in (ROOT/'source/library').glob('*.rs')},'controls':rows,'controls_per_mode':9,'modes':['debug','optimized'],'passed':True},indent=2)+'\n')
