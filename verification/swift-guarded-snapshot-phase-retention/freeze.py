"""Seal only after bounded evidence passes; inputs and packet then immutable."""
from pathlib import Path
import json,os,shutil,sys
sys.dont_write_bytecode=True
from prepare import HERE,BASE,BASE_SEAL,ACCEPT,ACCEPT_SHA,sha,canonical,members,write,custody,seal

def member(p):return dict(path=p.relative_to(HERE).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes()))
def main():
 if len(sys.argv)==2 and sys.argv[1]=='--check':
  s=json.loads((HERE/'seal.json').read_text())
  for r in s['members']:assert member(HERE/r['path'])==r,r['path']
  assert sha(canonical(s['members']))==s['tree_sha256']
  print(json.dumps(dict(verified_members=len(s['members']),seal_sha256=sha((HERE/'seal.json').read_bytes()))));return
 assert len(sys.argv)==1 and not (HERE/'seal.json').exists();binding=custody();seal(BASE,BASE_SEAL);assert sha(ACCEPT.read_bytes())==ACCEPT_SHA
 labels=['baseline-production','baseline-unit','candidate-production','candidate-unit','scalar-production','scalar-unit','scalar-overflow','scalar-overflow-negative','control-tests','source-ordering-accounting-controls','source-ordering-accounting-controls-attempt-1']
 receipts=sorted((HERE/'commands').glob('*/receipt.json'));assert {p.parent.name for p in receipts}==set(labels)
 groups=[];failures=[]
 for p in receipts:
  x=json.loads(p.read_text());negative=p.parent.name=='scalar-overflow-negative'
  failed_control=p.parent.name=='source-ordering-accounting-controls-attempt-1'
  assert x['exit_code']!=0 if negative or failed_control else x['exit_code']==0,p
  if x['exit_code']!=0:failures.append(dict(label=p.parent.name,exit_code=x['exit_code'],expected=negative,diagnostic='E0080 checked const overflow' if negative else 'Control driver assumed direct Ok(copy local); actual unchanged MIR copies into existing operand temporary then Ok(move temp). Driver corrected; exact first source and outputs retained.'))
  assert x.get('expectation_met',True)
  assert sha((p.parent/'stdout').read_bytes())==x['stdout_sha256'];assert sha((p.parent/'stderr').read_bytes())==x['stderr_sha256']
  owners=[('command',x)]
  if 'compiler_version_command' in x:owners.append(('compiler-version',x['compiler_version_command']))
  rp=p.parent/'run-receipt.json'
  if rp.exists():
   r=json.loads(rp.read_text());assert r['exit_code']==0
   assert sha((p.parent/'run-stdout').read_bytes())==r['stdout_sha256'];assert sha((p.parent/'run-stderr').read_bytes())==r['stderr_sha256'];owners.append(('finite-execution',r))
  for kind,r in owners:
   assert r['child_reaped'] and r['owned_group_absent'] and not r['timed_out']
   try:os.killpg(r['owned_process_group'],0);absent=False
   except ProcessLookupError:absent=True
   assert absent,(p,kind,r['owned_process_group'])
   groups.append(dict(receipt=p.relative_to(HERE).as_posix(),kind=kind,owned_process_group=r['owned_process_group'],child_reaped=True,owned_group_absent_at_final_recheck=True))
 work=HERE/'owned-work';assert not list(work.iterdir());work.rmdir()
 for cache in HERE.rglob('__pycache__'):shutil.rmtree(cache)
 write('cleanup.json',dict(schema=1,owned_groups=groups,all_recorded_groups_absent_and_reaped=True,owned_scratch_removed=True,compiler_artifacts_removed=True,process_inventory_performed=False,native_or_capture_processes_started=0,other_project_processes_or_data_changed=False))
 accounting=json.loads((HERE/'source-delta-accounting.json').read_text());ordering=json.loads((HERE/'ordering-controls.json').read_text());test=(HERE/'commands/control-tests/run-stdout').read_text()
 assert '10 passed; 0 failed;' in test
 write('summary.json',dict(schema=1,source_binding=binding,source_members=144,changed_product_files=2,declared_source_replacements=7,focused_mir_functions_per_context=7,exact_metadata_mir_compiles=4,contexts=['production','cfg(test)'],target='Rust1.99 aarch64-apple-darwin only',scalar_compiles=4,scalar_executions=3,scalar_controls_per_execution=174,recorded_nonzero_commands=failures,actual_private_control_tests_passed=10,test_overlay_files=3,exact_source144_executions=0,source_ordering_accounting_controls=ordering['passed'],added_runtime_roles=0,added_runtime_storage_bytes=0,added_work_actions=0,all_old_source_role_charges_retained=True,retained_old_selected_floor_charge_bytes=200,accepted_recipe=dict(C=78240,S=941467,A=430175,H=81327),A_retained_through_completion=True,normalizer_owner_missing_bounds_underflow_errors_preserved=True,WASI_observation_preserved=True,paired_storage_destruction_preserved=True,original_path_preserved=True,final_ConstructionBound_retention_preserved=True,WorkAuditPending_preserved=True,helper_delegation_added=False,fixed_policy_changed=False,fixture_300000_400000_grants_preserved=True,pre_ingress_H_external_harness_ownership_pending=True,all_recorded_owned_groups_absent_and_reaped=True,owned_scratch_removed=True,VM_writer_loader_adoption_dispatched=False,native_checks='paused and pending',canonical_product_changed=False,independent_phase_retention_review='pending',complete_writer_funding_accepted=False,healthy_cleanup_accepted=False,GA_gates_verified=0))
 rows=[member(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
 s=dict(schema=1,members=rows,member_count=len(rows),member_bytes=sum(r['bytes'] for r in rows),tree_sha256=sha(canonical(rows)),scope='Conservative isolated snapshot phase A retention amendment; exact metadata/MIR, pure constants and separate private control overlay only. No writer/full-funding/healthy-cleanup/GA acceptance.')
 write('seal.json',s);print(json.dumps(dict(members=len(rows),bytes=s['member_bytes'],tree_sha256=s['tree_sha256'],seal_sha256=sha((HERE/'seal.json').read_bytes()),owned_groups=len(groups)),sort_keys=True))
if __name__=='__main__':main()
