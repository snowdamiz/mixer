#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys
H=Path(__file__).resolve().parent
common=['named_shapes_and_default_ceilings','constructor_ordinals_and_consuming_zero','cold_cached_collision_ir_and_work','exact_phase_helper','header_retained_through_return_storage']
candidate=['plan_inventory_disjoint_layout','understated_counts_and_sticky_failure','successful_scan_retained_after_build_refusal','cache_proof_scope_and_cancel_before_effect']
jobs=[]
for lane in ['baseline','candidate']:
    for n in common+(candidate if lane=='candidate' else []):jobs.append((lane,lane+'-review-'+n.replace('_','-'),'experimental_swift_reactor::cache_tests::independent_review_'+n,[]))
    for n in ['frozen_ir_parity_for_all_supported_opcode_shapes','frozen_layout_and_trace_observation','frozen_borrowed_transients_fit_existing_scratch']:
        jobs.append((lane,lane+'-'+n.replace('_','-'),'experimental::cache::tests::'+n,[]))
    jobs.append((lane,lane+'-profile-admission','experimental_swift_reactor::cache_tests::plan_reuse_profile_envelopes_without_guest_execution',[]))
for n in ['plan_reuse_collision_publish_boundaries','plan_reuse_cached_deadline_and_precedence']:
    jobs.append(('candidate','candidate-inherited-'+n.replace('_','-'),'experimental_swift_reactor::cache_tests::'+n,[]))
for n in common+candidate:jobs.append(('candidate','candidate-release-'+n.replace('_','-'),'experimental_swift_reactor::cache_tests::independent_review_'+n,['--release']))
results=[]
with (H/'batch.stdout').open('w') as out:
    for lane,label,name,extra in jobs:
        cmd=[sys.executable,'-B',str(H/'run.py'),lane,label,name,*extra]
        code=subprocess.run(cmd,stdout=out,stderr=subprocess.STDOUT).returncode
        results.append({'lane':lane,'label':label,'exitCode':code})
        print(json.dumps(results[-1]),flush=True)
(H/'batch-results.json').write_text(json.dumps(results,indent=2)+'\n')
