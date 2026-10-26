#!/usr/bin/env python3
"""Fresh selected test qualification with explicit bounded coverage partitions."""
import json,os,re,shutil,time
from run_host import ROOT, REPO, RUST, run, sha, remove_product
started=time.time();rows=[];method_union=set()
for mode,opts in [('debug',[]),('optimized',['-O'])]:
 for label,source,cfg in [('producer',ROOT/'source/regression/independent_tests.rs','inherited_transport'),('independent',ROOT/'source/library/analyzer.rs','inherited_review')]:
  name=f'regression-{label}-{mode}';exe=ROOT/'evidence'/name
  compiled=run(name+'-compile',[RUST,'--edition=2021','--test','--cfg',cfg,*opts,source,'-o',exe]);assert compiled.returncode==0
  try:
   listed=run(name+'-list',[exe,'--list']);assert listed.returncode==0
   inventory=re.findall(r'^([^\s]+): test$',listed.stdout.decode(),re.M);assert len(inventory)==(108 if label=='producer' else 98)
   if label=='producer' and mode=='debug':
    root_methods=[m for m in inventory if not m.startswith('product::')];embedded=[m for m in inventory if m.startswith('product::')]
    assert len(root_methods)==17 and len(embedded)==91
    # Measure the pending timeout method first, then all remaining root methods.
    pending='failure_record_closed_payload_and_bounds';assert pending in root_methods
    ordered=[pending]+[m for m in root_methods if m!=pending]
    groups=[(f'root-{i:02}',[m,'--exact'],[m]) for i,m in enumerate(ordered)]+[('embedded',['product::'],embedded)]
   else:groups=[('all',[],inventory)]
   observed=[];group_rows=[]
   for group,args,expected in groups:
    scratch=ROOT/('.scratch-'+name+'-'+group);scratch.mkdir()
    env=dict(os.environ,MIXER_ANALYZER_LIBRARY_TEST_SCRATCH=str(scratch),MIXER_ENVELOPE_SCRATCH=str(scratch),MIXER_REVIEW_SCRATCH=str(scratch),REVIEW_SCRATCH=str(scratch),MIXER_ANALYZER_LIBRARY_HISTORICAL=str(REPO/'verification/swift-envelope-ci-pack/inputs/historical'))
    try:
     result=run(name+'-'+group+'-tests',[exe,*args,'--test-threads=1','--nocapture'],env)
     output=result.stdout.decode();actual=re.findall(r'^test ([^\s]+) \.\.\.',output,re.M)
     match=re.search(r'test result: ok\. (\d+) passed; 0 failed;',output)
     group_rows.append({'group':group,'expected':expected,'actual':actual,'exit':result.returncode,'summary':match.group(0)if match else None})
     assert result.returncode==0 and match and int(match.group(1))==len(expected) and sorted(actual)==sorted(expected)
     observed.extend(actual)
    finally:shutil.rmtree(scratch)
   assert len(observed)==len(set(observed))==len(inventory) and set(observed)==set(inventory)
   normalized=[m.removeprefix('product::')for m in inventory];method_union.update(normalized)
   rows.append({'mode':mode,'label':label,'inventory':inventory,'groups':group_rows,'complete_disjoint_coverage':True,'method_count':len(inventory),'single_full_60s_command_claim':not(label=='producer'and mode=='debug')})
  finally:remove_product(exe)
(ROOT/'evidence/selected-regression-summary.json').write_text(json.dumps({'schema':1,'started':started,'ended':time.time(),'wall_seconds':time.time()-started,'runs':rows,'union_methods':sorted(method_union),'union_count':len(method_union),'all_expected_dispositions_passed':True,'prior_full_producer_Debug_timeout_remains_failure':True,'no_performance_equivalence_claim':True},indent=2)+'\n')
print('SELECTED_REGRESSIONS_SUCCESS',len(method_union),'distinct methods')
