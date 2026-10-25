from pathlib import Path
import subprocess,sys,json
H=Path(__file__).resolve().parent
names=['decoder_opcode_and_count_build_parity','review_every_decoded_instruction_matches_independent_owned_ir','pins_hits_lru_and_eviction','foreign_stale_nonce_and_control_ownership','borrowed_owner_preflight_preserves_storage_and_ignores_ordinary_checks','entry_and_combined_admission_precedes_allocation','parameters_and_function_inclusive_depth','deadline_inside_decode_and_reset','component_cleanup_and_first_cleanup_invariant','sticky_failure_has_no_new_effects','resident_index_all_pinned_exact_capacity_and_empty_links','resident_index_inclusive_64_node_chain_and_cycle_bound','review_exact_phase_and_header_admission_boundaries','frozen_layout_allocation_work_error_snapshots']
results=[]
with (H/'control-dispatch.stdout').open('w') as out:
 for i,name in enumerate(names):
  label=f'inherited-{i+1:02}'
  cmd=[sys.executable,'-B',str(H/'record.py'),'source',label,'test','--offline','--lib','--all-features','experimental_swift_reactor::cache_tests::'+name,'--','--exact','--nocapture','--test-threads=1']
  p=subprocess.run(cmd,stdout=out,stderr=subprocess.STDOUT)
  results.append({'name':name,'command':label,'exitCode':p.returncode})
(H/'inherited-controls.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
