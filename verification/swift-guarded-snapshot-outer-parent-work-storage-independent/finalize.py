#!/usr/bin/env python3
"""Freeze only this review output after a final read-only custody check."""
import datetime, hashlib, json, sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
C=ROOT/'verification/swift-guarded-snapshot-outer-parent-work-storage'
def sha(b):return hashlib.sha256(b).hexdigest()
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def write(name,value):(HERE/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
def main():
    if (HERE/'seal.json').exists():raise ValueError('review already frozen')
    sealed=json.loads((C/'seal.json').read_bytes())
    if sha((C/'seal.json').read_bytes())!='7d7c6be167de0a7e20dbde2a50a5ea900a954a8e5e32262cf185411f1dc041b0':raise ValueError('candidate seal changed')
    for row in sealed['members']:
        b=(C/row['path']).read_bytes()
        if len(b)!=row['bytes'] or sha(b)!=row['sha256']:raise ValueError('candidate member changed: '+row['path'])
    reconstruction=json.loads((HERE/'reconstruction.json').read_bytes())
    arithmetic=json.loads((HERE/'arithmetic-review.json').read_bytes())
    controls=json.loads((HERE/'adversarial-controls.json').read_bytes())
    assertions=json.loads((HERE/'assertions.json').read_bytes())
    if not controls['passed'] or controls['cases']!=673 or assertions['count']!=1450:raise ValueError('missing successful independent checks')
    receipts=[]
    for p in sorted((HERE/'commands').glob('*/receipt.json')):
        value=json.loads(p.read_bytes());receipts.append(dict(path=p.relative_to(HERE).as_posix(),sha256=sha(p.read_bytes()),exit_code=value['exit_code'],elapsed_seconds=value['elapsed_seconds']))
    for mode in ['review','controls','replay','producer-tests']:
        latest=next(x for x in reversed(receipts) if '/'+mode+'-' in x['path'])
        if latest['exit_code']!=0:raise ValueError('latest mode failed: '+mode)
    failures=dict(schema=1,candidate_failures_retained_unchanged=['attempts/derive-001/failure.json','preliminary-failures.json'],
      reviewer_command_failures=[
       dict(path='commands/review-001',exit_code=1,reason='Reviewer manifest ordering used lexicographic strings instead of path components.',correction='Reviewer independently sorts source member path components, matching the frozen canonical manifest order.'),
       dict(path='commands/controls-001',exit_code=1,reason='Reviewer caught only new model Refused, while inherited storage overflow correctly raises its own ValueError subclass.',correction='Catch ValueError rejection family, without catching unrelated exceptions.'),
       dict(path='commands/controls-002',exit_code=1,reason='Reviewer view marker incorrectly survived a completed unwind of the callee that consumes the view.',correction='Materialize returned view only on return edge; consuming observer return or completed unwind ends its shared references before caller cleanup.')],
      reviewer_read_only_lookup_failure=dict(exit_code=2,missing_path='verification/swift-guarded-snapshot-outer-parent-source/query-outer-layout.inc.rs',effect='No write or execution; actual frozen independent query-layout.inc.rs read next.'),
      unresolved_product_failures=[],candidate_changed=False)
    write('failures.json',failures)
    cleanup=dict(schema=1,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
      all_python_children_completed=True,compiler_children_started=0,native_runtime_UI_capture_started=False,
      global_process_inventory=False,processes_signaled=False,other_projects_preserved=True,
      scratch_created=False,bytecode_created=bool(list(HERE.rglob('__pycache__'))),
      candidate_seal_and_all44_members_rehashed_unchanged=True,
      outside_owned_writes=False,Git_or_root_metadata_mutations=False,active_lanes_read=False,
      physical_device_or_native_runtime_checks='pending under user pause',
      source_tree='27deefde4b492bab2e2d5a28da9ae749cc4ae51094e0fca30154d044097988a3')
    if cleanup['bytecode_created']:raise ValueError('unexpected owned bytecode')
    write('cleanup.json',cleanup)
    review=dict(schema=1,status='independent-bounded-source-work-storage-review-pass',
      candidate_path=C.relative_to(ROOT).as_posix(),candidate_seal_sha256=sha((C/'seal.json').read_bytes()),
      candidate_members=44,candidate_member_bytes=693873,
      root_release_sha256='0a28f10bee285dc3c150eea771013001a9ad90d0a70f03cb362badf1b35a36ab',
      source_tree='27deefde4b492bab2e2d5a28da9ae749cc4ae51094e0fca30154d044097988a3',
      inherited_source_tree='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',
      source_revision_from_retained_receipt='a32d056355ec2f417e9ef7a73788b420176377b6',live_Git_read=False,
      independently_reconstructed=reconstruction,independent_arithmetic=arithmetic,
      independent_assertions=1450,independent_adversarial_cases=673,random_storage_oracle_cases=64,
      producer_exact_replay=True,producer_test_methods_passed=32,commands=receipts,
      all_new130_roles_P0_before_binding_policy_quote_account_entry=True,
      all_new_roles_retained_through_external_final_result_consumption=True,
      all_original_payload_diagnostic_File_error_proof_and_destructor_owners_and_allowances_preserved=True,
      shared_view_ends_before_actual_payload_destruction=True,
      payload_destroyed_at_most_once_across_explicit_and_cleanup_routes=True,
      normal_release_only_after_Some_token_from_payload_and_carrier_destruction_return=True,
      none_refusal_unwind_refund=False,alias_move_or_sharing_credit=False,
      required_actual_identity_preimages=12,required_native_Path_pointees=5,required_separate_retained_byte_bodies=5,
      original_unverified_claims=8,product_budget_fields=17,required_positive_residual_work_terms=10,
      L_str5080_selected=False,all_selectors_pending=True,actual_I_U_entry_release=dict(I=0,U=0,entry=0,release=0),
      current_static_provider_requirement_proven=False,self_embedded_executable_assumed=False,
      arithmetic_evaluator_authenticates_receipts=False,source_rebind_is_binary_correspondence=False,
      prior_independent_production_compiler_pass='retained previous scope only;44 observations/22 types',
      missing_Result_layout_query=dict(retained_only=True,observations=[8,8],expected_exit=1,E0308_errors=2,elapsed_seconds=3.3535296670161188,cleanup_recorded=True,production_compiler_pass=False),
      producer_original_terminal_facts='unknown retained as unknown',
      limitations=[
       'Logical source/typed aggregate/destructor-interface occurrences plus native typed-byte allowances; no private std/compiler/panic/CPU/physical allocation unit.',
       'All full immutable actual identities/path correspondence/backing/provenance and eight claims require independent root review; labels and hashes alone are not proof.',
       'Future complete upstream provider/launcher work, inline and owned backing plus original immutable diagnostic and Error backing remain mandatory; no fresh finite or static provider is established.',
       'Ten residual work inputs, complete native/backing/error-owner/destructor interfaces and actual whole root policy/quote/funding remain unselected.',
       'Whole compiled standard-library/caller/binary correspondence, genuine loader/writer/destructor route and healthy cleanup remain pending.',
       'Native simulator/emulator/device/UI/capture checks remain paused and pending; FieldLog must use immutable separately published packages; OTA and GA remain separate.'
      ],
      unread_active_lanes=['swift-guarded-snapshot-scoped-binding-source','native open','string correction'],
      root_policy_work_storage_or_operational_grant_selected=False,actual_fixture_runtime=False,healthy_cleanup=False,
      native_FieldLog_OTA_GA=False,cleanup=cleanup,
      reviewer_corrections_retained='failures.json',root_selection_required=True)
    write('review.json',review)
    members=[]
    for p in sorted(HERE.rglob('*')):
        if p.is_file() and p.name!='seal.json':
            b=p.read_bytes();members.append(dict(path=p.relative_to(HERE).as_posix(),bytes=len(b),sha256=sha(b)))
    frozen=dict(schema=1,status='frozen-independent-bounded-review',members=members,member_count=len(members),member_bytes=sum(x['bytes'] for x in members),
                manifest_sha256=sha(canon(members)),review_sha256=sha((HERE/'review.json').read_bytes()),
                candidate_seal_sha256=review['candidate_seal_sha256'],source_tree=review['source_tree'],
                independent_review_passed=True,root_selection_or_operational_grant=False,compiler_or_native_processes_started=0,
                actual_binding_funding_provider_or_GA_selected=False)
    write('seal.json',frozen)
    print(json.dumps(dict(path=str(HERE),seal_sha256=sha((HERE/'seal.json').read_bytes()),members=len(members),bytes=frozen['member_bytes'],review_sha256=frozen['review_sha256'])))
if __name__=='__main__':main()
