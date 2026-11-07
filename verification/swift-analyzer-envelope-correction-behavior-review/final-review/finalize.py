#!/usr/bin/env python3
"""Freeze observed failure, scoped coverage and owned cleanup; no analyzer run."""
from pathlib import Path
import hashlib,json,tarfile,shutil,datetime,sys,importlib.util,re
OWN=Path(__file__).resolve().parent;BASE=OWN.parent;ROOT=BASE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def dump(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
def load(p):s=importlib.util.spec_from_file_location('acquisition',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
if __name__=='__main__':
 assert not (OWN/'seal.json').exists()
 a=load(OWN/'acquire.py');a.protected();a.verify_producer()
 run=OWN/'runs/run-2';out=(run/'independent-tests/stdout.bin').read_bytes();err=(run/'independent-tests/stderr.bin').read_bytes()
 assert b'18 passed; 1 failed' in out and b'Accepted absent-state priority' in err
 candidate=(OWN/'archive-source/src/envelope.rs').read_text().splitlines()
 lines=[{'line':i+1,'text':line}for i,line in enumerate(candidate)if 'if !underfunded { steps.remaining -=' in line or 'if arena.len() < 7_731_056' in line]
 dump(OWN/'finding-R2.json',{'schema':1,'id':'R2','status':'reproduced-candidate-mismatch-acceptance-withheld','scope':'private unreadable prior-state boundary; public initialized safe-File path is separate','source_sha256':sha((OWN/'archive-source/src/envelope.rs').read_bytes()),'contract':'accepted absent state -> InternalPoisoned/debit0; numeric selection changes threshold only','expected':'length0/32 cannot read any required prior state: status3/reason15, private debit0/spent0, prior budget and arena/candidate bytes unchanged','actual':'credits425/426 -> status3/reason15, debit425/spent425; credits0/1/424 -> debit0/spent0; no arena/candidate mutation','inputs':{'arena_lengths':[0,32],'credits':[0,1,424,425,426]},'actual_debit_vector':[0,0,0,425,425,0,0,0,425,425],'expected_debit_vector':[0]*10,'source_lines':lines,'method':'fixture_envelope::independent_final::independent_absent_prior_state_precedes_normal_debit','stdout_sha256':sha(out),'stderr_sha256':sha(err),'stdout':'runs/run-2/independent-tests/stdout.bin','stderr':'runs/run-2/independent-tests/stderr.bin','candidate_changed':False,'public_paid_counter_change_authorized':False})
 baseline=json.loads((BASE/'baseline.json').read_text());rows=[]
 mappings={
 'R1-exact-original':['selected_review_exact_r1_poison_stops_scheduling_before_stale_state'],
 'poison-cross-product':['selected_review_poison_cross_product_keeps_zero_extent_and_paid_debit'],
 'poison-later-wire-error':['independent_paid_latched_skip_and_poison_call_counter','independent_late_input_errors_and_paid_decode'],
 'absent-backing':['selected_review_absent_backing_never_projects_candidate_initialization'],
 'zero-actual-leaf-calls':['independent_preflight_zero_and_partial_then_bad_footer'],
 'reply-valid-only-after-return':['selected_review_absent_backing_never_projects_candidate_initialization','selected_review_all_underfunded_values_preserve_first_and_later_state'],
 'absent-prior-state-before-underfunding':['independent_absent_prior_state_precedes_normal_debit'],
 'underfunded-first-and-later':['selected_review_all_underfunded_values_preserve_first_and_later_state'],
 'exact-leaf-funding':['selected_review_exact_and_one_above_private_funding'],
 'ordinary-refusal-atomic':['independent_paid_latched_skip_and_poison_call_counter'],
 'last-cell-boundary':['selected_review_final_checked_cell_precedes_all_writes'],
 'partial-commit-fault':['selected_review_poison_cross_product_keeps_zero_extent_and_paid_debit'],
 'complete-sole-cap-eleven-states':['independent_complete_cap_all_eleven_states'],
 'complete-noncap-finality':['independent_actual_files_and_fixed_report','independent_finite_phase_failure_and_atomicity'],
 'successful-limited-table':['independent_preflight_zero_and_partial_then_bad_footer','selected_review_poison_cross_product_keeps_zero_extent_and_paid_debit'],
 'failed-limited-drain':['independent_failed_limited_drain'],
 'invalid-private-values':['independent_finalization_errors_unsupported_and_closed'],
 'unknown-context':['independent_actual_files_and_fixed_report','independent_early_context_profile_header_debit'],
 'context-profile-header-errors':['independent_actual_files_and_fixed_report','independent_early_context_profile_header_debit'],
 'setup-finish-admission':['independent_exact_setup_finish_guard_admission'],
 'next-record-preflight':['independent_preflight_zero_and_partial_then_bad_footer'],
 'paid-decode-failure':['independent_late_input_errors_and_paid_decode'],
 'paid-latched-skip':['independent_paid_latched_skip_and_poison_call_counter'],
 'late-record-footer-EOF-metadata':['independent_late_input_errors_and_paid_decode'],
 'outer-safety-and-allocation':['independent_output_errors_no_aggregate','independent_bounded_io_and_allocation'],
 'bounded-IO-and-report-errors':['independent_output_errors_no_aggregate','independent_bounded_io_and_allocation'],
 'finite-stage-and-failure-sequences':['independent_finite_phase_failure_and_atomicity'],
 'candidate-and-arena-footprint':['independent_finite_phase_failure_and_atomicity','selected_review_all_underfunded_values_preserve_first_and_later_state'],
 'public-API-positive':['api-positive'], 'public-API-negative':['api-private-record','api-private-leaf','api-private-field','api-no-copy','api-no-clone','api-no-word-trust-constructor','api-no-serializer','api-no-descriptor-authority-entry'],
 'old-framing-and-fixed-report':['independent_actual_files_and_fixed_report'],
 'complete-memory-and-lifetime-handoff':[]}
 limitations={
 'reply-valid-only-after-return':'Actual complete reply installation and source ordering observed; no artificial callback between indivisible statements.',
 'ordinary-refusal-atomic':'Framing/latch/debit behavior executed; complete pre/post snapshots executed for underfunding and final-cell refusal. Full ordinary refusal matrix not independently rerun.',
 'partial-commit-fault':'No fallible callback exists after first unrolled safe write; no artificial partial-write source change. Retained poison fault controls executed; arbitrary partial-memory-failure execution unqualified.',
 'complete-sole-cap-eleven-states':'Eleven build-prefix cuts cover ten unique states (Ready6 repeats); independent Hit2 CAP cut pending. Passing method name does not prove eleven distinct states.',
 'successful-limited-table':'Absent, Observed and poisoned limited paths executed; exhaustive latched-refused limited table remains scoped source review, not a full independent matrix.',
 'invalid-private-values':'Unsupported status/reason/state/phase/mask/latch controls executed; not every inconsistent framing flag combination separately rerun.',
 'outer-safety-and-allocation':'Private identity alias, Budget and allocator refusal executed. Every actual File hardlink/clone alias variant remains producer/accepted-framing evidence.',
 'finite-stage-and-failure-sequences':'Hit/build/eviction, Failure cursors/Release and terminal-phase refusal exercised; producer21714 model cases not independently rerun.',
 'complete-memory-and-lifetime-handoff':'Separate final accountant owns complete source-operation/type/lifetime and F05 funding proof. No acceptance inferred from behavioral results.'}
 for case in baseline['cases']:
  ident=case['id'];status='scoped-executable-evidence'
  if ident=='absent-prior-state-before-underfunding':status='failed-R2'
  elif ident in limitations:status='partial-or-source-scoped-see-limitation'
  rows.append({'id':ident,'status':status,'methods':mappings[ident],'limitation':limitations.get(ident),'no_claim_of_full_product_qualification':True})
 assert len(rows)==32 and len(mappings)==32
 dump(OWN/'coverage.json',{'schema':1,'baseline_cases':32,'rows':rows,'suite_methods':19,'passed':18,'failed':1,'API_positive':1,'API_expected_negative':8,'actual_File_paired_cases':7,'all32_passed':False,'producer_model_comparisons_independently_rerun':0,'full70_or_original64_replayed':False})
 # Before touching owned scratch/binaries, require every command's cleanup proof.
 receipts=[]
 for r in sorted((OWN/'runs').glob('run-*/*/receipt.json')):
  value=json.loads(r.read_text())
  if 'cleanup'in value:assert value['cleanup']['cleanup_verified'],str(r);receipts.append(str(r.relative_to(ROOT)))
 archived=[];targets=[]
 for r in sorted((OWN/'runs').glob('run-*')):
  targets.extend([r/'scratch',r/'test-source'])
 targets.append(OWN/'archive-source')
 targets.append(OWN/'runs/run-1/independent-tests/stderr.bin')
 archive=OWN/'owned-source-scratch-and-first-failure.tar.gz'
 with tarfile.open(archive,'w:gz')as t:
  for target in targets:
   assert target.is_relative_to(OWN) and target.exists()
   members=[target]if target.is_file()else sorted(p for p in target.rglob('*')if p.is_file())
   for p in members:
    b=p.read_bytes();name=str(p.relative_to(OWN));archived.append({'original_path':str(p.relative_to(ROOT)),'archive_member':name,'bytes':len(b),'sha256':sha(b)});t.add(p,arcname=name,recursive=False)
 with tarfile.open(archive,'r:gz')as t:
  for row in archived:assert sha(t.extractfile(row['archive_member']).read())==row['sha256']
 for target in targets:
  if target.is_dir():shutil.rmtree(target)
  else:target.unlink()
 removed=[]
 for r in sorted((OWN/'runs').glob('run-*')):
  for p in [r/'review-tests',r/'libreviewed.rlib',r/'api/positive']:
   if p.exists():b=p.read_bytes();removed.append({'path':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':sha(b)});p.unlink()
 a.protected();a.verify_producer()
 dump(OWN/'cleanup.json',{'schema':1,'command_cleanup_receipts_verified':receipts,'all_known_direct_children_reaped_and_owned_groups_gone':True,'unrelated_process_discovery':False,'archive':str(archive.relative_to(ROOT)),'archive_sha256':sha(archive.read_bytes()),'archived_members':archived,'owned_binaries_hashed_and_removed':removed,'owned_scratch_and_source_copies_removed_after_archive_verification':True,'protected52_and_producer306_unchanged':True})
 dump(OWN/'command-correction.json',{'run1_invocation':[sys.executable,'-B',str((OWN/'run_review.py').relative_to(ROOT)),'run-1'],'run2_invocation':[sys.executable,'-B',str((OWN/'run_review.py').relative_to(ROOT)),'run-2','101'],'note':'Run2 collector receipt command field omitted the trailing101 argument. Exact tool invocation includes101 solely to continue API checks after the known candidate-failing test; suite remains18pass/1fail.'})
 dump(OWN/'final-receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(Path(__file__).relative_to(ROOT))],'python':sys.version,'status':'withhold-acceptance-R2-absent-prior-state-debit','source_sha256':'7b8237abbaec492e595508eb7456dab38fbb0d92d8d3cd5a88184f7c1082b9d1','producer_seal_sha256':'4ddff8237bd49cab9f6191be89e4764966e1af5dfa686bb931ac1372d1e98df1','source_binding':'runs/run-2/source-binding.json','test_methods':19,'methods_passed':18,'methods_failed':1,'API_positive':1,'API_expected_negative':8,'actual_File_paired_cases':7,'preaccess_control_ids_accounted':32,'all32_passed':False,'finding':'finding-R2.json','coverage':'coverage.json','first_reviewer_failure_preserved':True,'R1_passed_in_this_scope':True,'protected_baseline_members':39,'protected_supplement_members':13,'admitted_producer_members_unchanged':306,'cleanup':'cleanup.json','compiler_version_output':'runs/run-2/rust-version/stdout.bin','native_capture_or_device_execution':False,'hosted_engine_CLI_execution':False,'producer_collector_executed':False,'original64_timeout_retried':False,'implementation_accepted':False,'combined_final_accounting_accepted_by_this_lane':False,'storedPrefixValidated':False,'fullReplayAccepted':False,'semanticMetricsValid':False,'ga_gate_promotions':0})
 members=[]
 for p in [BASE/'final-review.md']+sorted(p for p in OWN.rglob('*')if p.is_file()and p.name not in('seal.json','seal.sha256')):
  b=p.read_bytes();members.append({'path':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':sha(b)})
 dump(OWN/'seal.json',{'schema':1,'scope':'independent rejected selected-source behavior review; no acceptance','members':members,'excluded':[str((OWN/'seal.json').relative_to(ROOT)),str((OWN/'seal.sha256').relative_to(ROOT))]})
 digest=sha((OWN/'seal.json').read_bytes());(OWN/'seal.sha256').write_text(digest+'  '+str((OWN/'seal.json').relative_to(ROOT))+'\n')
 print(json.dumps({'status':'withhold-acceptance-R2','seal_sha256':digest,'members':len(members),'bytes':sum(m['bytes']for m in members),'methods_passed':18,'methods_failed':1,'api_positive':1,'api_negative':8,'protected_members_unchanged':52,'cleanup_complete':True},sort_keys=True))
