"""Final independent input/custody review and immutable evidence seal."""
from pathlib import Path
import datetime,hashlib,json,os,sys
sys.dont_write_bytecode=True
import review
P=Path(__file__).resolve().parent
assert not (P/'seal.json').exists(),'already frozen'
assert not (P/'owned-scratch').exists(),'disposable scratch remains'
review.source_binding()
assert review.digest((P.parent/'swift-semantic-adapter-root-review/guarded-snapshot-phase-retention-independent-release.json').read_bytes())=='12627178051e0747ce835af0f22f44eab5d69e563f86dcf0a210b1cdf9f11f23'
assert review.digest((P.parent/'swift-semantic-adapter-root-review/guarded-snapshot-funding-host-acceptance.json').read_bytes())=='17789ef30bb818f91a928941162029a12c75ca7dddd33e8cfc073ec4950a615f'
producer=review.check_seal(review.PRODUCER,'623b5ec0b8ef7c2f68b344c191f9a6d2f5fd93b3085c7f0b4ae02c960c895001')
baseline=review.check_seal(review.BASE,'e006b90b8c9e351e0d4dd504c6de309e2c7970b628fe9fc4f788cb30e77bedf7')
known_drivers={review.digest(p.read_bytes()) for p in [P/'review.py',P/'drivers/review-before-exact-filter-correction.py']}
rows=[];expected_failures=[]
for p in sorted((P/'commands').glob('*/receipt.json')):
 r=json.loads(p.read_text());d=p.parent
 assert r['driver_sha256'] in known_drivers,p
 assert review.digest((d/'stdout').read_bytes())==r['stdout_sha256'],p
 assert review.digest((d/'stderr').read_bytes())==r['stderr_sha256'],p
 assert r['expectation_met'] and r['child_reaped'] and r['owned_group_absent'] and not r['timed_out'],p
 try:os.killpg(r['owned_process_group'],0);absent=False
 except ProcessLookupError:absent=True
 assert absent,('recorded owned group now present',r['owned_process_group'])
 rows.append(dict(command=d.name,process_group=r['owned_process_group'],reaped=r['child_reaped'],group_absent_at_postflight=absent,exit_code=r['exit_code'],expected_exit_code=r['expected_exit_code']))
 if r['exit_code']!=0:expected_failures.append(dict(command=d.name,exit_code=r['exit_code'],expected=True,reason='Exact baseline early-refund regression fails after actual completion; full output retained'))
 pre=d/'source-preimage.json'
 if pre.exists():
  x=json.loads(pre.read_text());vm=(review.BASE if d.name.startswith('baseline-') else review.PRODUCER)/'source/vm'
  assert x['exact_copied_members']==review.manifest(vm)
  assert r['environment']['MIXER_LOADER_MANIFEST_SHA256']==review.digest(review.canonical(x))
  assert x['compiler_sha256']==review.digest(review.RUSTC.read_bytes())
  if x['overlays']:
   instrumented={a['path']:dict(a) for a in x['exact_copied_members']}
   for a in x['overlays']:
    fragment=(P/a['fragment']).read_bytes()
    if a['baseline_field_spelling_only']:fragment=fragment.replace(b'control,retained:target,wasi',b'control,previous:target,wasi')
    assert review.digest(fragment)==a['sha256'] and len(fragment)==a['bytes']
    raw=(vm/a['target']).read_bytes()+b'\n'+fragment
    instrumented[a['target']]=dict(path=a['target'],bytes=len(raw),sha256=review.digest(raw))
   assert [instrumented[k] for k in sorted(instrumented)]==x['instrumented_members']
mir=json.loads((P/'mir-comparison.json').read_text())
assert len(mir['focused_functions'])==14 and mir['fresh_exact_compiles']==4
assert sum(len(x['declared_roles']) for x in mir['focused_functions'])==290
assert all(x['otherwise_identical'] and x['role_delta']==x['action_delta']==0 for x in mir['focused_functions'])
positive=(P/'commands/candidate-controls-run/stdout').read_text()
negative=(P/'commands/baseline-negative-controls-run/stdout').read_text()
assert '8 passed; 0 failed;' in positive and '468 filtered out' in positive
assert '0 passed; 1 failed;' in negative and '475 filtered out' in negative
assert '1467930' in (P/'commands/baseline-negative-controls-run/stderr').read_text()
assert '1898105' in (P/'commands/baseline-negative-controls-run/stderr').read_text()
for label in ['candidate-controls','baseline-negative-controls']:
 e=json.loads((P/'commands'/ (label+'-run')/'executable-binding.json').read_text())
 a=json.loads((P/'commands'/ (label+'-compile')/'removed-artifacts.json').read_text())
 assert e['sha256']==next(x['sha256'] for x in a if x['name']=='controls')
 assert e['source_preimage_sha256']==review.digest((P/'commands'/ (label+'-compile')/'source-preimage.json').read_bytes())
assert len(rows)==10 and len(expected_failures)==1,(len(rows),expected_failures)
review.write('cleanup.json',dict(schema=1,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),commands=rows,recorded_owned_groups_checked=len(rows),all_recorded_owned_groups_absent=True,all_child_processes_reaped=True,disposable_scratch_removed=True,binaries_metadata_full_MIR_removed=True,global_process_inventory=False,other_projects_processes_or_data_touched=False,native_UI_capture_started=False))
review.write('lifetime-assessment.json',dict(schema=1,verdict='conservative-phase-A-retention-amendment-passes-bounded-independent-review',source_binding=review.source_binding(),source_review={
 'sole_commit_caller':'begin_snapshot_access_v1: existing additional alias A -> checked commit -> existing result tuple -> Admitted.retained',
 'completion':'SnapshotAccessV1::complete forwards retained and existing WASI to unchanged normalizer; it drops storage before validations',
 'surviving_export':'construct_profile_core_v1 obtains attempt before branch.finish; finish completes storage before moving export into SnapshotOuterV1',
 'return_lifetime':'SnapshotOuterV1 survives in SnapshotRunV1, then export and phase_completion move into SnapshotPrimaryRetirementV1 and returned SnapshotScopeFinishV1',
 'finalizer':'finish_owned_cleanup remains conservative: enlarged Construction ticket cannot be refunded and records ConstructionBound',
 'exclusive_borrow':'Access retains exclusive actual control reference and lends only shared control to export/header/row operations',
 'zero_difference_limitation':'Same-target completion subtracts zero and does not newly diagnose counter corruption; existing underflow branches are separately tested with real shrink',
 'producer_vs_receiver':'No assumption that A producer return/move places have ended, transferred, or reused S receiving places; all original charges retained'},
 synthetic_executable_witness='Actual private SnapshotAttemptV1::Failed with io::Error owned backing is live at same address after real complete and dropped exactly once afterwards; actual checked finite control ledger retains same ticket/current/peaks',
 selected_ingress_witness=False,genuine_writer_result_witness=False,H_pre_ingress_ownership_qualified=False,external_harness_funding_qualified=False,healthy_cleanup_qualified=False,writer_release_authorized=False))
audit=json.loads((P/'audit.json').read_text())
review.write('summary.json',dict(schema=1,status='bounded-independent-phase-retention-review-passed',producer_seal=producer,baseline_seal=baseline,source_binding=review.source_binding(),immutable_source_evidence_checks=audit['checks_passed'],exact_replacements=7,changed_source_members=2,fresh_exact_metadata_MIR_compiles=4,focused_function_context_comparisons=14,declared_MIR_roles_compared=290,new_runtime_roles=0,new_runtime_fields_or_types=0,new_runtime_calls_arithmetic_or_actions=0,accepted_recipe=dict(C=78240,S=941467,A=430175,H=81327),all_existing_source_role_charges_retained=True,independent_actual_private_control_tests_passed=8,unrelated_tests_filtered=468,synthetic_owned_diagnostic_live_after_real_complete=True,expected_baseline_regression_rejected=True,control_test_compiles=2,recorded_owned_child_groups=10,all_owned_groups_absent_and_reaped=True,unexpected_independent_failed_commands=0,expected_failed_commands=expected_failures,producer_failed_first_source_MIR_assertion_preserved=True,producer_scalar_controls_reviewed_each_of_three_runs=174,producer_expected_E0080_reviewed=True,producer_ten_control_test_results_reviewed=True,normalizer_and_WASI_preserved=True,Original_refused_writer_final_ConstructionBound_preserved=True,WorkAuditPending_preserved=True,root_integration_accepted_by_this_review=False,canonical_product_or_Git_or_root_metadata_edited=False,complete_funding_or_writer_release_accepted=False,GA_gates_verified=0,native_checks='paused and pending; none started or inventoried',target='Pinned Rust1.99 aarch64-apple-darwin only',limitations=['Synthetic checked ledger/completion execution is not genuine selected ingress','H pre-ingress and external-harness ownership remain pending','No begin/adoption/source-loader/profile-loader/VM/writer dispatch','No healthy cleanup or complete writer storage/work funding qualification','No new global inventory, other-target/compiler, physical-stack/RSS or operational qualification','No OTA, FieldLog, native or GA acceptance']))
members=review.manifest(P)
review.write('seal.json',dict(schema=1,member_count=len(members),member_bytes=sum(x['bytes'] for x in members),tree_sha256=review.digest(review.canonical(members)),scope='Independent frozen exact two-file phase-retention review with targeted host controls only; no writer, full funding, healthy cleanup or GA grant',members=members))
print(json.dumps(dict(members=len(members),member_bytes=sum(x['bytes'] for x in members),seal_sha256=review.digest((P/'seal.json').read_bytes()),status='frozen-bounded-independent-review-passed')))
