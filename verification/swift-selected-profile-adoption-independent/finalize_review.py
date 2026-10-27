"""Finalize only this independent review; never changes a selected input."""
from pathlib import Path
from datetime import datetime, timezone
import collections
import difflib
import hashlib
import json
import re
import shutil
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CANDIDATE=ROOT/'verification/swift-selected-profile-adoption'
BASE=ROOT/'verification/swift-real-profile-loader-binding'


def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_bytes())
def write(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def ident(p):
    b=p.read_bytes();return {'path':str(p.relative_to(HERE)),'bytes':len(b),'sha256':sha(b)}


def closed_packet(path, expected):
    seal=path/'seal.json';assert sha(seal.read_bytes())==expected
    data=load(seal);rows=data['members']
    actual=set()
    for p in path.rglob('*'):
        assert not p.is_symlink(),str(p)
        if p.is_file():actual.add(str(p.relative_to(path)))
    assert actual=={m['path']for m in rows}|{'seal.json'}
    for m in rows:
        b=(path/m['path']).read_bytes();assert len(b)==m['bytes']and sha(b)==m['sha256'],m['path']
    return {'path':str(path.relative_to(ROOT)),'seal_sha256':expected,'members':len(rows),'member_bytes':sum(m['bytes']for m in rows),'exact_closed_file_set_and_member_bytes_verified':True}


def source_manifest(path):
    rows=[]
    for p in sorted(path.rglob('*')):
        assert not p.is_symlink(),str(p)
        if p.is_file():
            b=p.read_bytes();rows.append({'path':str(p.relative_to(path)),'bytes':len(b),'sha256':sha(b)})
    return {'schema':1,'member_count':len(rows),'members':rows,'tree_sha256':sha(json.dumps(rows,sort_keys=True,separators=(',',':')).encode())}


def command_records(path):
    rows=[]
    for p in sorted((path/'commands').glob('*/receipt.json')):
        d=load(p);assert d['terminally_waited'];assert d['supervisor_killed_for']is None
        for key,filename in [('stdout','stdout'),('stderr','stderr')]:
            b=(p.parent/filename).read_bytes();assert len(b)==d[key]['bytes']and sha(b)==d[key]['sha256']
        rows.append({'receipt':str(p.relative_to(HERE)),**{k:d[k]for k in ['label','exit_code','expectation_met','source_tree_sha256','elapsed_seconds']}})
    return rows


assert not (HERE/'seal.json').exists(),'never rewrite a sealed review'
for name,expected in [('preaccess-plan.json','a7f57a8130602be0a4d7f9e09e389979acdee20b69b0b445c9948959894b83ae'),('preaccess-receipt.json','d635a9ebd524c818f151f607afde9c8e79aa1cdf447627c2d4114014f95190d3')]:
    assert sha((HERE/name).read_bytes())==expected

custody=closed_packet(CANDIDATE,'83a7c57bc5f208b06a42384f14b4056040604ef01685a9dfbe8bbe32b832a7ad')
privacy=closed_packet(HERE/'compiler-privacy','a8b1d415ee82796e7adaa393a739f2b192db53cfb6c7c46b241829b8ceb2fa22')
candidate=load(CANDIDATE/'source-manifest.json')
assert source_manifest(CANDIDATE/'source/vm')==candidate
assert source_manifest(HERE/'replay/source/vm')==candidate
extra=source_manifest(HERE/'independent-controls/source/vm')
write(HERE/'independent-source-manifest.json',extra)
write(HERE/'candidate-post-review-custody.json',custody)

baseline=load(BASE/'source-manifest.json');old={m['path']:m for m in baseline['members']}
changed=[m['path']for m in candidate['members']if old[m['path']]!=m]
selection=load(CANDIDATE/'selection.json')
allowed=set(selection['allowed_existing_distribution_changes'])|set(selection['conditional_test_expectation_changes']['paths'])|{'src/experimental_swift_reactor/mod.rs'}
assert set(changed)<=allowed and len(changed)==12
for name in changed:
    before=(BASE/'source/vm'/name).read_text();after=(CANDIDATE/'source/vm'/name).read_text()
    out=HERE/'source-diffs'/Path(name).with_suffix('.diff')
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='accepted-loader/'+name,tofile='selected-adoption/'+name)))
src='src/experimental_swift_reactor/'
old_control=(BASE/'source/vm'/src/'control.rs').read_text()
new_control=(CANDIDATE/'source/vm'/src/'control.rs').read_text()
assert re.search(r'pub\(crate\) fn adopt\(.*?\) -> Result<\(Self, AdoptedProof\), SwiftRunFailure>',old_control,re.S).group()==re.search(r'pub\(crate\) fn adopt\(.*?\) -> Result<\(Self, AdoptedProof\), SwiftRunFailure>',new_control,re.S).group()
assert old_control[old_control.index('impl Default for SwiftRunBudget'):old_control.index('#[derive(Clone, Copy, Debug, PartialEq, Eq)]\npub enum SwiftReservationCategory')]==new_control[new_control.index('impl Default for SwiftRunBudget'):new_control.index('#[derive(Clone, Copy, Debug, PartialEq, Eq)]\npub enum SwiftReservationCategory')]
before=(BASE/'source/vm'/src/'mod.rs').read_text();after=(CANDIDATE/'source/vm'/src/'mod.rs').read_text()
assert before.replace('Selected-host retained source correlation only; no runtime adoption or public route.','Selected-host retained source correlation and private adoption; no public route.')==after

old_local=(BASE/'source/vm'/src/'cache/initial_profile_v1/local_structure.rs').read_text()
new_local=(CANDIDATE/'source/vm'/src/'cache/initial_profile_v1/local_structure.rs').read_text()
assert re.findall(r'compare!\((\d+),(.+)\);',old_local)==re.findall(r'compare!\((\d+),(.+)\);',new_local)
new_initial=(CANDIDATE/'source/vm'/src/'cache/initial_profile_v1.rs').read_text()
old_initial=(BASE/'source/vm'/src/'cache/initial_profile_v1.rs').read_text()
start=old_initial.index('fn construct_with_initial_profile_v1(');end=old_initial.index('fn write_initial_profile_rows_v1(')
ns=new_initial.index('fn construct_with_initial_profile_v1(');ne=new_initial.index('fn write_initial_profile_rows_v1(')
assert old_initial[start:end]==new_initial[ns:ne]
layout_matches=[]
for mode in ['debug','optimized']:
    for kind in ['unit','production']:
        measured=load(HERE/'replay/layouts'/f'{kind}-{mode}.json')
        claimed=load(CANDIDATE/'layouts'/f'{kind}-{mode}.json')
        assert measured==claimed
        assert len(measured['rows'])==201
        layout_matches.append({'configuration':kind,'mode':mode,'entries':201,'values':measured['values'],'all_names_sizes_alignments_and_envelopes_match':True})

records=command_records(HERE/'replay')+command_records(HERE/'independent-controls')
failed=[r for r in records if not r['expectation_met']]
assert len(records)==209 and len(failed)==1
assert failed[0]['label']=='debug-suite-experimental_swift_reactor::control::tests::'
assert failed[0]['source_tree_sha256']==candidate['tree_sha256']
write(HERE/'command-summary.json',{'schema':1,'commands':records,'count':len(records),'passed_expectations':208,'failed_expectations':1})

artifacts=[]
for dirname in ['replay','independent-controls']:
    scratch=HERE/dirname/'owned-work'
    assert scratch.is_relative_to(HERE)
    if scratch.exists():
        for p in sorted(scratch.rglob('*')):
            assert not p.is_symlink(),str(p)
            if p.is_file():artifacts.append(ident(p))
        shutil.rmtree(scratch)
write(HERE/'artifacts-measured-before-owned-removal.json',artifacts)
cleanup={'schema':1,'main_direct_children_terminally_waited':209,'compiler_privacy_direct_children_terminally_waited':120,'total_direct_children_terminally_waited':329,'timeouts_or_output_kills':0,'owned_scratch_removed':True,'candidate_or_baseline_mutated':False,'preaccess_plan_and_receipt_unchanged':True,'native_simulator_emulator_device_UI_capture_process_inventory_used':False,'File_drop_or_process_exit_is_close_success':False,'descendant_process_group_cleanup_claimed':False,'other_projects_files_or_processes_touched':False}
write(HERE/'cleanup.json',cleanup)
result={
    'schema':1,'at':datetime.now(timezone.utc).isoformat(),
    'status':'independent-original-candidate-review-complete-blocked-by-stale-original-control-test-and-missing-suite',
    'scope':'Isolated private full-provenance selected adoption and source-object accounting under trusted launcher/compiler and quiescent macOS host',
    'candidate':custody,'source_tree_sha256':candidate['tree_sha256'],'source_members':144,
    'changed_existing_source_files':changed,'baseline_unchanged_source_files':132,'unchanged_host_support_members':11,
    'preaccess_plan_receipt_unchanged':True,
    'main_commands':209,'main_passed_expectations':208,'main_failed_expectations':1,
    'compiler_privacy':{'packet':privacy,'controls_passed':117,'negative':112,'positive':5,'additional_tool_and_library_commands_passed':3,'optimized_test_context_controls_run':False,'actionable_findings':[]},
    'all_recorded_host_commands':329,'total_passed_expectations':328,'total_failed_expectations':1,
    'blocking_findings':[{
        'id':'I1','priority':2,'classification':'stale original test-accounting expectation and missing required original suite; no observed production admission defect',
        'file':'verification/swift-selected-profile-adoption/source/vm/src/experimental_swift_reactor/control_tests.rs','line':1196,
        'test':'experimental_swift_reactor::control::tests::optional_observation_chain_is_reserved_before_runtime_work',
        'observed':'Original full Debug control suite:36 passed,1 failed; expected Some(277176),actual Some(366896)',
        'omitted_floors':{'ADOPTION_ENTRY_BYTES_V1':7584,'ADOPTION_MOVE_BYTES_V1':21768,'ADOPTION_CLEANUP_BYTES_V1':12600,'INITIAL_PROFILE_WRAPPER_SOURCE_PLACES_V1_unit':47768,'omitted_unit_total':89720,'wrapper_production':47720},
        'receipt':failed[0]['receipt'],
        'required_correction':'Select separate immutable corrected candidate with explicit control_tests.rs expectation amendment. Add the four named source constants to non_observation_shapes, preserve original observation/historical-floor/headroom cases and unchanged budgets, and include full original37-method control suite in final Debug and optimized matrices. Preserve this original candidate and failure.',
        'why_not_accepted':'The original observation-admission boundary assertion fails before its headroom controls; candidate266 required matrix omitted the entire original control suite.'
    }],
    'source_review':{
        'ordinary_adopt_signature_unchanged':True,'one_original_adopt_body_ledger':True,
        'actual_selected_carrier_consumed_into_full_inline_optional_provenance':True,
        'body_private_proof_and_private_optional_provenance':True,
        'adopted_owner_has_body_and_original_two_tickets':True,
        'body_destroyed_before_both_independent_refunds':True,
        'original_refund_return_behavior_and_first_failure_preserved':True,
        'actual_initial_constructor_function_byte_unchanged':True,'sole_original_guard_and_all8_outcome_owner_paths_preserved':True,
        'all_original165_identity_records_preserved':True,'new_loader23_plus_adoption13_measurements_appended':True,
        'cache_header_subtracts_only_original_proof_leaving_full_inline_sidecar_charged':True,
        'explicit_entry_move_cleanup_wrapper_floors_composed_before_prepare':True,
        'original_validation_and_runtime_caps_unchanged':True,
        'R1_allfour_role_correction_actual_safe_File_mismatches_and_synthetic_helper_IO_pass':True,
        'new_production_behavior_defects_found':[]
    },
    'exact_source_replay':{'control_Debug':{'passed':36,'failed':1},'control_optimized':'not rerun because known deterministic stale formula already reproduced; required after correction','cache_methods_each_mode':38,'execution_methods_each_mode':22,'initial_profile_methods_each_mode':17,'selected_genuine_cases_each_mode':15,'loader_genuine_cases_each_mode':37,'loader_behavior_helpers_each_mode':16,'loader_helper_filter_includes_noop_emitter_method':True,'genuine_fixture_emission_separately_passed_each_mode':True,'production_host_methods_each_mode':8,'ordinary_production_metadata_layout_assertions_each_mode':201,'original_nested_Cargo_wrapper':'UNRUN; candidate separately maps13 original sources, independent compiler review tests production/public/privacy contexts; not original wrapper pass'},
    'independent_new_genuine_selected_controls':{'passed_each_mode':13,'modes':['debug','optimized'],'direct_full_original_failure_payload_parity_except_elapsed_each_mode':6,'synthetic_private_ticket_fault_quarantine_and_both_refunds_each_mode':3,'actual_selected_foundation_floor_below_equal_above_each_mode':3,'allfive_narrowed_validation_limits_through_actual_cache_each_mode':1,'source_variant_tree_sha256':extra['tree_sha256'],'only_source_changes':'append test-only control helper; route independent genuine loader test scenarios and append independent assertions; no product implementation changes'},
    'layout_matches':layout_matches,
    'cleanup':cleanup,
    'retained_limits':['Optimized compiler test-context controls unrun','Original nested-Cargo external_surface_and_borrow_privacy wrapper unrun','Known original stale control test blocks whole-candidate acceptance','Raw APFS cwd/executable path and actual raw nonUTF8 argv0 harness cases unrun','No loader operational admission,File close-success,authenticated package/hostile launcher guarantees','Native/device/simulator/emulator/UI/capture/process inventories paused-unused','No exporter/context/canonical integration,FieldLog immutable package release,OTA/store/customer/operations or GA acceptance'],
    'recommendation':'Do not accept original candidate as fully validated. Select narrowly amended corrected immutable candidate and verify full control suite/final byte coverage; all other observed scopes remain finite host evidence.',
    'runtime_slice_accepted':False,'canonical_or_native_or_operational_or_GA_accepted':False,
}
write(HERE/'review-result.json',result)
members=[]
for p in sorted(HERE.rglob('*')):
    assert not p.is_symlink(),str(p)
    if p.is_file()and p!=HERE/'seal.json':
        b=p.read_bytes();members.append({'path':str(p.relative_to(HERE)),'bytes':len(b),'sha256':sha(b)})
write(HERE/'seal.json',{'schema':1,'scope':'Independent original selected-adoption candidate review; one blocking original-control validation finding retained','member_count':len(members),'member_bytes':sum(m['bytes']for m in members),'members':members})
print(json.dumps({'status':result['status'],'seal_sha256':sha((HERE/'seal.json').read_bytes()),'members':len(members),'member_bytes':sum(m['bytes']for m in members),'host_commands':329,'failed_expectations':1},sort_keys=True))
