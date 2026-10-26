#!/usr/bin/env python3
import json,os,pathlib,shutil
from run_host import ROOT,REPO,RUST,run,sha,remove_product
results=[]
for mode,opts in [('debug',[]),('optimized',['-O'])]:
 for label,source,cfg in [('producer',ROOT/'source/regression/independent_tests.rs','inherited_transport'),('independent',ROOT/'source/library/analyzer.rs','inherited_review')]:
  name=f'regression-{label}-{mode}';exe=ROOT/'evidence'/name
  r=run(name+'-compile',[RUST,'--edition=2021','--test','--cfg',cfg,*opts,source,'-o',exe]);assert r.returncode==0
  scratch=ROOT/('.scratch-'+name);scratch.mkdir()
  env=dict(os.environ,MIXER_ANALYZER_LIBRARY_TEST_SCRATCH=str(scratch),MIXER_ENVELOPE_SCRATCH=str(scratch),MIXER_REVIEW_SCRATCH=str(scratch),REVIEW_SCRATCH=str(scratch),MIXER_ANALYZER_LIBRARY_HISTORICAL=str(REPO/'verification/swift-envelope-ci-pack/inputs/historical'))
  try:r=run(name+'-tests',[exe,'--test-threads=1','--nocapture'],env);assert r.returncode==0
  finally:shutil.rmtree(scratch);remove_product(exe)
  results.append({'name':name,'source_sha256':sha(source),'production_source_sha256':{p.name:sha(p)for p in (ROOT/'source/library').glob('*.rs')},'passed':True})
(ROOT/'evidence/regression-summary.json').write_text(json.dumps({'runs':results,'count_mapping':{'embedded_old_producer':54,'separate_old_public_fixture_methods':17,'separate_old_private_transport_methods':7,'old_producer_total':78,'old_independent_envelope_methods':14,'new_cache_state_methods':27},'production_source_paths':[str(ROOT/'source/library/analyzer.rs'),str(ROOT/'source/library/envelope.rs'),str(ROOT/'source/library/cache_state.rs')],'test_only_wiring':'one original import path changed in producer independent_tests; cfg includes old private transport and independent envelope tests; no expected values changed'},indent=2)+'\n')
