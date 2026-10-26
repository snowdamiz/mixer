#!/usr/bin/env python3
"""Append one cfg(test) module to an exact source copy; run actual Rust controls."""
import json,shutil,datetime
from run_host import ROOT,REPO,RUST,run,sha,remove_product
D=ROOT/'controls/derived-source';assert not D.exists();shutil.copytree(ROOT/'source',D)
module=b'\n#[cfg(test)]\n#[path = "../selected_controls.rs"]\nmod selected_scalar_controls;\n'
p=D/'library/cache_state.rs';original=p.read_bytes();p.write_bytes(original+module)
shutil.copy2(ROOT/'controls/selected_controls.rs',D/'selected_controls.rs')
rows=[]
for source in sorted((ROOT/'source').rglob('*')):
 if not source.is_file():continue
 target=D/source.relative_to(ROOT/'source');same=source.read_bytes()==target.read_bytes()
 assert same or source.name=='cache_state.rs'
 if not same:assert target.read_bytes()==source.read_bytes()+module
 rows.append({'path':str(source.relative_to(ROOT/'source')),'base_sha256':sha(source),'derived_sha256':sha(target),'only_cfg_test_suffix':not same})
(ROOT/'proofs/derivative-custody.json').write_text(json.dumps({'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_rows':rows,'appended_suffix':module.decode(),'selected_source_remains_exact':sha(ROOT/'source/library/cache_state.rs'),'controls_source_sha256':sha(ROOT/'controls/selected_controls.rs'),'no_product_behavior_edits':True},indent=2)+'\n')
results=[]
for mode,opts in [('debug',[]),('optimized',['-O'])]:
 name='changed-controls-'+mode;exe=ROOT/'evidence'/name
 compiled=run(name+'-compile',[RUST,'--edition=2021','--test',*opts,D/'library/analyzer.rs','-o',exe])
 try:
  assert compiled.returncode==0
  result=run(name+'-tests',[exe,'selected_scalar_controls::','--test-threads=1','--nocapture'])
  results.append({'mode':mode,'compile_exit':compiled.returncode,'test_exit':result.returncode,'stdout_sha256':sha(ROOT/'evidence'/f'{name}-tests.stdout')})
  assert result.returncode==0
 finally:remove_product(exe)
(ROOT/'proofs/changed-controls.json').write_text(json.dumps({'schema':1,'runs':results,'actual_selected_source_with_only_cfg_test_suffix':True,'public_reachability_credit':0,'conditional_preconditions_remain':True},indent=2)+'\n')
