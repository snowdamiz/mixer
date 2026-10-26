#!/usr/bin/env python3
"""Execute unchanged inherited methods; preserve failures rather than reclassify."""
import json, os, re, shutil
from run_host import ROOT, REPO, RUST, run, sha, remove_product
rows=[]
for mode,opts in [('debug',[]),('optimized',['-O'])]:
    for label,source,cfg in [('producer',ROOT/'source/regression/independent_tests.rs','inherited_transport'),('independent',ROOT/'source/library/analyzer.rs','inherited_review')]:
        name=f'regression-{label}-{mode}';exe=ROOT/'evidence'/name
        compile_result=run(name+'-compile',[RUST,'--edition=2021','--test','--cfg',cfg,*opts,source,'-o',exe])
        row={'name':name,'compile_exit':compile_result.returncode,'source_sha256':sha(source)}
        try:
            if compile_result.returncode==0:
                scratch=ROOT/('.scratch-'+name);scratch.mkdir()
                env=dict(os.environ,MIXER_ANALYZER_LIBRARY_TEST_SCRATCH=str(scratch),MIXER_ENVELOPE_SCRATCH=str(scratch),MIXER_REVIEW_SCRATCH=str(scratch),REVIEW_SCRATCH=str(scratch),MIXER_ANALYZER_LIBRARY_HISTORICAL=str(REPO/'verification/swift-envelope-ci-pack/inputs/historical'))
                try:
                    result=run(name+'-tests',[exe,'--test-threads=1','--nocapture'],env)
                    output=result.stdout.decode();match=re.search(r'test result: (\w+)\. (\d+) passed; (\d+) failed;',output)
                    row.update(test_exit=result.returncode,summary=match.groups() if match else None,failed_method_ids=re.findall(r'^    ([\w:]+)$',output,re.M))
                finally:shutil.rmtree(scratch)
        finally:remove_product(exe)
        rows.append(row)
(ROOT/'evidence/frozen-regression-summary.json').write_text(json.dumps({'schema':1,'runs':rows,'frozen_expected_values_changed':False,'failures_not_reclassified_as_passes':True},indent=2)+'\n')
print(json.dumps(rows,indent=2))
