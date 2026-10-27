"""Independent finite differential/custody review, never runs frozen scripts."""
from collections import Counter
import difflib
import gzip
from pathlib import Path
import re
import sys
sys.dont_write_bytecode=True
from prepare import HERE,VERIFICATION,ORIGINAL,INDEPENDENT,BASE,CONTROL,TESTS,sha,canonical,load,write,custody,arithmetic,member
from run_filtered import PRODUCTION_ASSERTIONS,verify_correction

CORRECTION=VERIFICATION/'swift-guarded-snapshot-work-common-correction'
EXPECTED_SEAL='c679b12e5a82c5cd6746f87d8615cb19c6cba00f1d72625cad334bb11adc1422'
EXPECTED_TREE='3d7c4e7d557da60e7e111e59f7178d7db300e1018aa781d941b7cd90369cc43b'
def normal_mir(text):
    text=re.sub(r'//[^\n]*','',text)
    text=re.sub(r'\{closure@[^}]+\}','{closure}',text)
    text=re.sub(r'<impl at [^>]+>','<impl>',text)
    return '\n'.join(line.rstrip() for line in text.splitlines() if line.strip())+'\n'
def main():
    assert not (HERE/'seal.json').exists()
    groups=Counter()
    def check(value,label):
        assert value,label
        groups[label]+=1
    inputs=custody();model=arithmetic()
    release=load(HERE/'release.json');rootrelease=VERIFICATION.parent/release['root_release']
    check(sha(rootrelease.read_bytes())==release['root_release_sha256'],'root_release_exact')
    rootrelease=load(rootrelease)
    check(rootrelease['producer_seal_sha256']==EXPECTED_SEAL and rootrelease['source_tree_sha256']==EXPECTED_TREE,'root_release_frozen_input')
    seal=load(CORRECTION/'seal.json')
    manifest=verify_correction(CORRECTION,EXPECTED_SEAL)
    check(len(seal['members'])==119 and sum(row['bytes'] for row in seal['members'])==6308959,'correction_packet_count_bytes')
    check(manifest['source_tree_sha256']==EXPECTED_TREE,'correction_tree')
    oldmanifest=load(ORIGINAL/'source-manifest.json')
    check([a['path'] for a,b in zip(manifest['members'],oldmanifest['members']) if a!=b]==[CONTROL],'one_changed_source_member')
    check([a['path'] for a in manifest['members']]==[a['path'] for a in oldmanifest['members']],'source_manifest_paths_unchanged')
    check(manifest['base_seal_sha256']==oldmanifest['base_seal_sha256'] and manifest['base_tree_sha256']==oldmanifest['base_tree_sha256'],'funding_base_unchanged')
    old=(ORIGINAL/'overlay'/CONTROL).read_text();new=(CORRECTION/'overlay'/CONTROL).read_text()
    replacements=[
        ('// Twenty new unoptimized compiler source roles total1436 logical bytes.\n// No old role is credited; core and all existing closure captures are unchanged.\nconst SNAPSHOT_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;',
         '// Twenty new shared, non-P-dependent unoptimized source roles total1436\n// logical bytes. Charge every role to common C; no old role is credited.\nconst COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;'),
        ('        Some(original) => original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1),',
         '        Some(original) => match original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1) {\n            Some(common) => common.checked_add(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1),\n            None => None,\n        },'),
        ('        Some(common) => match common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1) {\n            Some(selected) => selected.checked_add(SNAPSHOT_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1),\n            None => None,\n        },',
         '        Some(common) => common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1),')]
    expected=old
    for before,after in replacements:
        check(expected.count(before)==1,'exact_unique_const_replacement')
        expected=expected.replace(before,after)
    check(expected==new,'entire_source_exact_const_only_relocation')
    oldstart=old.index('// Twenty new ');newstart=new.index('// Twenty new ')
    oldend=old.index('#[cfg(not(test))]\nconst SNAPSHOT_SCOPE_FOUNDATION',oldstart)
    newend=new.index('#[cfg(not(test))]\nconst SNAPSHOT_SCOPE_FOUNDATION',newstart)
    check(old[:oldstart]==new[:newstart],'all_pre_const_bytes_unchanged_including_F0_fixed_quote')
    check(old[oldend:]==new[newend:],'all_runtime_helper_closure_capture_retirement_bytes_unchanged')
    check(not any(token in new[newstart:newend] for token in ['fn ','impl ','trait ','unsafe','static ']),'relocation_only_const_recipe')
    patch=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='original-work-admission-source144/'+CONTROL,tofile='corrected-source144/'+CONTROL))
    check(patch==(CORRECTION/'correction-delta.patch').read_text(),'exact_original_correction_patch')
    base=(BASE/'source/vm'/CONTROL).read_text()
    patch=''.join(difflib.unified_diff(base.splitlines(True),new.splitlines(True),fromfile='accepted-funding-source144/'+CONTROL,tofile='corrected-source144/'+CONTROL))
    check(patch==(CORRECTION/'source-delta.patch').read_text(),'exact_complete_base_correction_patch')
    runtime_binding=dict(pre_const_sha256=sha(new[:newstart].encode()),post_const_sha256=sha(new[newend:].encode()),
        post_const_bytes=len(new[newend:].encode()),original_control_sha256=sha(old.encode()),corrected_control_sha256=sha(new.encode()))
    roles=load(ORIGINAL/'source-role-delta.json');storage=load(INDEPENDENT/'storage-review.json')
    check((CORRECTION/'inherited-source-role-delta.json').read_bytes()==(ORIGINAL/'source-role-delta.json').read_bytes(),'inherited_role_ledger_exact')
    check(roles['added_bytes']==1436 and roles['added_role_count']==20 and len(roles['added_roles'])==20,'twenty_roles_1436_reused')
    check(sum(row['bytes'] for row in roles['added_roles'])==1436,'inherited_role_bytes')
    check(roles['closure_captures_before']==roles['closure_captures_after'] and len(storage['closure_captures'])==8,'eight_captures_reused')
    check((CORRECTION/'inherited-work-delta.json').read_bytes()==(ORIGINAL/'work-delta.json').read_bytes(),'inherited_work_ledger_exact')
    work=load(CORRECTION/'inherited-work-delta.json');actions=load(INDEPENDENT/'action-review.json')
    check(work['delta']==1272 and work['fixed']==451814442 and actions['dispatch_delta']==1272 and actions['fixed']==451814442,'fixed_451814442_dispatch_1272_unchanged')
    check(actions['outer_predicate_added_to_original_source_actions']==3,'ordinary_three_source_actions_retained')
    mir=[]
    for mode,label in [('production','metadata-production'),('unit','metadata-unit-retry')]:
        oldmir=(ORIGINAL/'commands'/('metadata-'+mode)/'adoption-functions.mir').read_text()
        newmir=(CORRECTION/'commands'/label/'adoption-functions.mir').read_text()
        check(normal_mir(oldmir)==normal_mir(newmir),'producer_fresh_mir_normalized_exact')
        mir.append(dict(mode=mode,original_sha256=sha(oldmir.encode()),corrected_sha256=sha(newmir.encode()),normalized_sha256=sha(normal_mir(newmir).encode())))
    overlay=load(CORRECTION/'overlay-bindings.json')
    check((CORRECTION/'compiler-overlay'/CONTROL).read_bytes()==new.encode()+(CORRECTION/'floor-assertions.inc.rs').read_bytes(),'producer_compiler_overlay_separate')
    check((CORRECTION/'test-overlay'/TESTS).read_bytes()==(BASE/'source/vm'/TESTS).read_bytes()+(ORIGINAL/'host-controls.inc.rs').read_bytes()+(CORRECTION/'floor-controls.inc.rs').read_bytes(),'producer_test_overlay_separate')
    for label in ['metadata-production','metadata-unit-retry','metadata-production-assertions','host-control-debug-retry','host-control-release-retry','scalar-production','scalar-unit','metadata-unit','host-control-debug','host-control-release']:
        folder=CORRECTION/'commands'/label;r=load(folder/'receipt.json')
        failed=label in ['metadata-unit','host-control-debug','host-control-release']
        check((r['timed_out'] and r['exit_code']!=0) if failed else (not r['timed_out'] and r['exit_code']==0),'producer_honest_command_outcomes')
        check(r['child_reaped'] and r['owned_group_absent'],'producer_recorded_owned_child_cleanup')
        check(sha(gzip.decompress((folder/'stdout.gz').read_bytes()))==r['stdout_sha256'],'producer_stdout_custody')
        check(sha((folder/'stderr').read_bytes())==r['stderr_sha256'],'producer_stderr_custody')
        check(load(folder/'cleanup.json')['removed'],'producer_recorded_owned_scratch_removed')
        if 'source_binding' in r:
            binding=r['source_binding'];check(sha(canonical(binding['members']))==binding['source_tree_sha256'],'producer_compiler_binding_digest')
        if label in ['metadata-production','metadata-unit-retry']:
            actual={row['path']:row for row in r['source_binding']['members']}
            check(all(actual[row['path']]==(overlay['test_overlay'] if label=='metadata-unit-retry' and row['path']==TESTS else row) for row in manifest['members']),'producer_exact_compiler_source_binding')
        if label in ['host-control-debug-retry','host-control-release-retry']:
            for prefix,count in [('test',7),('floor-test',2)]:
                tr=load(folder/(prefix+'-receipt.json'))
                out=(folder/(prefix+'-stdout')).read_bytes()
                check(tr['exit_code']==0 and not tr['timed_out'] and tr['owned_group_absent'],'producer_host_tests_success')
                check(sha(out)==tr['stdout_sha256'] and (str(count)+' passed; 0 failed').encode() in out,'producer_host_tests_count_custody')
    actual_runs=[]
    for label,unit in [('production-const-floors',False),('independent-debug-boundaries',True)]:
        folder=HERE/'commands'/label;r=load(folder/'receipt.json');binding=r['source_binding']
        check(r['exit_code']==0 and not r['timed_out'] and r['owned_group_absent'] and r['child_reaped'],'independent_fresh_compile_success_cleanup')
        check(sha(gzip.decompress((folder/'stdout.gz').read_bytes()))==r['stdout_sha256'] and sha((folder/'stderr').read_bytes())==r['stderr_sha256'],'independent_output_custody')
        check(sha((folder/'compiler-version-stdout').read_bytes())==sha(r['compiler_version'].encode()),'independent_compiler_version_custody')
        check(sha(canonical(binding['members']))==binding['source_tree_sha256'] and binding['frozen_source_tree_sha256']==EXPECTED_TREE,'independent_overlay_binding_digest')
        append=(HERE/'independent-tests.inc.rs').read_bytes() if unit else PRODUCTION_ASSERTIONS
        expectedrows=[]
        for row in manifest['members']:
            if row['path']==(TESTS if unit else CONTROL):
                data=(BASE/'source/vm'/TESTS).read_bytes() if unit else new.encode()
                expectedrows.append(dict(path=row['path'],bytes=len(data+append),sha256=sha(data+append)))
            else: expectedrows.append(row)
        check(expectedrows==binding['members'] and sha(append)==binding['overlay_sha256'],'independent_overlay_exact_separate')
        check(load(folder/'cleanup.json')['removed'],'independent_scratch_removed')
        actual_runs.append(dict(label=label,compile_seconds=r['elapsed_seconds'],source_tree_sha256=binding['source_tree_sha256'],overlay_sha256=binding['overlay_sha256']))
        if unit:
            tr=load(folder/'test-receipt.json');out=(folder/'test-stdout').read_bytes()
            check(tr['exit_code']==0 and not tr['timed_out'] and tr['owned_group_absent'] and tr['child_reaped'],'independent_four_host_tests_success_cleanup')
            check(sha(out)==tr['stdout_sha256'] and b'4 passed; 0 failed' in out,'independent_four_host_tests_output_custody')
    check('WorkAuditPending' in (BASE/'source/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs').read_text(),'WorkAuditPending_preserved')
    summary=load(CORRECTION/'summary.json');account=load(CORRECTION/'correction-accounting.json')
    check(summary['production']==dict(F0=366312,common=445988,selected=1387455,admitted=1817630),'producer_production_floors')
    check(summary['unit']==dict(F0=366896,common=446572,selected_before_H=1388039,selected_with_H=1469366,admitted_with_H=1899541),'producer_unit_floors')
    check(account['common_new_bytes']==1436 and account['selected_only_new_bytes']==0 and account['C_corrected']==79676 and account['S']==941467,'common_relocation_accounting')
    check(all(summary[k] is False for k in ['bootstrap_grants_qualified','H_pre_ingress_qualified','complete_or_operational_source_funding','genuine_selected_loader_ingress_qualified','original_source_or_timing_overhead_newly_funded_by_selected_counter']),'producer_scope_limitations_honest')
    write('review.json',dict(schema=1,status='accept-const-common-attribution-correction-only',blocking_findings=[],
        finite_differential_custody_checks=sum(groups.values()),groups=dict(groups),independent_arithmetic=model,
        total_finite_checks=sum(groups.values())+model['checks_passed'],inputs=inputs,
        correction_seal_sha256=EXPECTED_SEAL,correction_members=119,correction_bytes=6308959,source_tree_sha256=EXPECTED_TREE,
        runtime_binding=runtime_binding,reused_fresh_MIR=mir,original_accepted_role_review_reused=True,role_recatalog_repeated=False,
        new_roles_common=20,new_common_bytes=1436,common_C=79676,selected_S=941467,
        production=summary['production'],unit=summary['unit'],selected_admitted_totals_unchanged=True,
        fixed_work=451814442,dispatch_actions=1272,actual_independent_host_tests=4,actual_runs=actual_runs,
        producer_initial_timeout_history_preserved=3,ordinary_outer_predicate_source_actions=3,ordinary_successful_counter=0,
        ordinary_source_behavior_unchanged_relative_to_funding_qualified=False,
        bootstrap_H_complete_funding_authentic_ingress_writer_GA_qualified=False,
        runtime_operations_executed=['ordinary in-memory parser/validator proof','private control adoption/cleanup only'],
        loader_guest_cache_scope_construct_writer_executed=False,native_checks='paused/pending',GA_gates_verified=0))
    print(__import__('json').dumps(dict(status='accept const attribution correction only',finite_differential_custody_checks=sum(groups.values()),independent_arithmetic_checks=model['checks_passed'],total_finite_checks=sum(groups.values())+model['checks_passed'],actual_independent_host_tests=4,blocking_findings=[]),sort_keys=True))
if __name__=='__main__':main()
