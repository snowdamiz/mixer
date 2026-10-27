"""Finite source/custody proof; never grants operational or OTA authority."""
from collections import Counter
import difflib
import gzip
import json
import re
import sys
sys.dont_write_bytecode=True
from prepare import HERE,ORIGINAL,BASE,OWNER,CONTROL,TESTS,base_members,canonical,row,sha,write

def normalized_mir(text):
    text=re.sub(r'//[^\n]*','',text)
    text=re.sub(r'\{closure@[^}]+\}','{closure}',text)
    text=re.sub(r'<impl at [^>]+>','<impl>',text)
    return '\n'.join(line.rstrip() for line in text.splitlines() if line.strip())+'\n'

def main():
    assert not (HERE/'seal.json').exists()
    groups=Counter()
    def check(value,group):
        assert value,group
        groups[group]+=1
    base=base_members();manifest=json.loads((HERE/'source-manifest.json').read_text())
    actual=[row(r['path'],(HERE/'overlay'/r['path']).read_bytes()) if (HERE/'overlay'/r['path']).exists() else r for r in base]
    check(actual==manifest['members'],'source_custody')
    check(len(actual)==144 and sha(canonical(actual))==manifest['source_tree_sha256'],'source_custody')
    check([a['path'] for a,b in zip(actual,base) if a!=b]==[CONTROL],'single_production_overlay')
    src=(HERE/'overlay'/CONTROL).read_text();old=(ORIGINAL/'overlay'/CONTROL).read_text()
    # The entire change is inside a const-only block. All functions, runtime
    # policy constants, failure/retirement bodies and work shell remain exact.
    begin='// Twenty new '
    end='/// Common named-source foundation:'
    check(src[:src.index(begin)]==old[:old.index(begin)],'const_only_source_delta')
    check(src[src.index(end):]==old[old.index(end):],'const_only_source_delta')
    check('const COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;' in src,'common_attribution')
    check('SNAPSHOT_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1' not in src,'common_attribution')
    common=src[src.index('const COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1:'):src.index('const SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1:')]
    check('original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1)' in common,'checked_common_recipe')
    check('Some(common) => common.checked_add(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1)' in common,'checked_common_recipe')
    selected=src[src.index('const SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1:'):src.index('#[cfg(not(test))]')]
    check('Some(common) => common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1)' in selected,'selected_only_extra_removed')
    check('COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1' not in selected,'selected_only_extra_removed')
    for declaration in ['const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1: usize = 78_240;',
                        'const SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1: usize = 941_467;',
                        'const SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1: usize = 430_175;',
                        'const SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1: usize = 81_327;']:
        check(declaration in src,'unchanged_accepted_constants')
    funding=json.loads((OWNER/'funding.json').read_text())
    check(funding['formulas']=={'common-extra':78240,'selected-unconditional':941467,'admitted-only':430175},'accepted_owner_attribution')
    inherited=json.loads((HERE/'inherited-source-role-delta.json').read_text())
    check((HERE/'inherited-source-role-delta.json').read_bytes()==(ORIGINAL/'source-role-delta.json').read_bytes(),'inherited_role_custody')
    check(inherited['added_role_count']==20 and sum(r['bytes'] for r in inherited['added_roles'])==1436,'all_added_roles_common')
    check(all(r['function']=='::{closure#0}' and 'P::' not in r['type'] for r in inherited['added_roles']),'all_added_roles_common')
    check((HERE/'inherited-work-delta.json').read_bytes()==(ORIGINAL/'work-delta.json').read_bytes(),'unchanged_work_custody')
    work=json.loads((HERE/'inherited-work-delta.json').read_text())
    check(work['delta']==1272 and work['fixed']==451814442,'unchanged_work_price')
    check(work['own_actions']['selected_const_fetch_compare_decision']==3,'ordinary_outer_predicate_disclosure')
    check((HERE/'host-controls.inc.rs').read_bytes()==(ORIGINAL/'host-controls.inc.rs').read_bytes(),'unchanged_seven_test_append')
    overlay=json.loads((HERE/'overlay-bindings.json').read_text())
    for label,key in [('test-overlay','test_overlay'),('compiler-overlay','compiler_assertion_overlay')]:
        r=overlay[key];check(row(r['path'],(HERE/label/r['path']).read_bytes())==r,'separate_overlay_custody')
    mir=[]
    for mode,label in [('production','metadata-production'),('unit','metadata-unit-retry')]:
        a=(ORIGINAL/'commands'/('metadata-'+mode)/'adoption-functions.mir').read_text()
        b=(HERE/'commands'/label/'adoption-functions.mir').read_text()
        check(normalized_mir(a)==normalized_mir(b),'fresh_mir_runtime_unchanged')
        mir.append(dict(mode=mode,original_sha256=sha(a.encode()),corrected_sha256=sha(b.encode()),
            normalized_sha256=sha(normalized_mir(b).encode()),equal=True))
    good=['metadata-production','metadata-unit-retry','metadata-production-assertions','host-control-debug-retry',
          'host-control-release-retry','scalar-production','scalar-unit']
    failed=['metadata-unit','host-control-debug','host-control-release']
    for label in good+failed:
        folder=HERE/'commands'/label;r=json.loads((folder/'receipt.json').read_text())
        check(r['owned_group_absent'] and r['child_reaped'],'command_custody')
        check((r['exit_code']==0 and not r['timed_out']) if label in good else (r['timed_out'] and r['exit_code']!=0),'honest_command_outcome')
        check(sha(gzip.decompress((folder/'stdout.gz').read_bytes()))==r['stdout_sha256'],'command_output_custody')
        check(sha((folder/'stderr').read_bytes())==r['stderr_sha256'],'command_output_custody')
        check(json.loads((folder/'cleanup.json').read_text())['removed'],'owned_scratch_cleanup')
        if 'source_binding' in r:
            binding=r['source_binding'];check(sha(canonical(binding['members']))==binding['source_tree_sha256'],'compiler_source_binding')
        for prefix,count in [('test',7),('floor-test',2)] if label.startswith('host-control-') and label in good else []:
            r=json.loads((folder/(prefix+'-receipt.json')).read_text())
            check(r['exit_code']==0 and not r['timed_out'] and r['owned_group_absent'],'host_test_outcome')
            check(sha((folder/(prefix+'-stdout')).read_bytes())==r['stdout_sha256'],'host_test_output')
            check((str(count)+' passed; 0 failed') in (folder/(prefix+'-stdout')).read_text(),'host_test_count')
    for mode in ['production','unit']:
        check('237 checked common/selected/admitted floor and overflow controls passed' in (HERE/'commands'/('scalar-'+mode)/'test-stdout').read_text(),'integer_controls')
    check('WorkAuditPending' in (BASE/'source/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs').read_text(),'writer_still_refused')
    write('correction-accounting.json',dict(schema=1,source_tree_sha256=manifest['source_tree_sha256'],
        original_role_ledger_sha256=sha((HERE/'inherited-source-role-delta.json').read_bytes()),
        common_new_role_count=20,common_new_bytes=1436,selected_only_new_bytes=0,
        C_previous=78240,C_corrected=79676,S=941467,A=430175,H=81327,
        production=dict(F0=366312,common=445988,selected=1387455,admitted=1817630),
        unit=dict(F0=366896,common=446572,selected_before_H=1388039,selected_with_H=1469366,admitted_with_H=1899541),
        original_production_common=444552,original_unit_common=445136,
        selected_admitted_totals_unchanged=True,F0_unchanged=True,all_runtime_source_after_const_block_unchanged=True,
        const_relocation_runtime_local_or_action_delta=0,fresh_mir=mir,
        source_convention='unoptimized shared source declarations; no policy specialization or constant-folding credit',
        ordinary_source_predicate_actions=3,ordinary_source_predicate_bool_bytes=1,
        ordinary_successful_work_counter=0,ordinary_common_floor_increased=1436,
        fixed_selected_work=451814442,selected_branch_upper_sum=1272,
        selected_counter_funds_ordinary_source_overhead=False,bootstrap_grants_qualified=False,H_pre_ingress_qualified=False,
        original_source_timing_overhead_newly_funded_by_selected_counter=False,complete_source_funding=False,
        WorkAuditPending_preserved=True))
    write('control-results.json',dict(schema=1,checks_passed=sum(groups.values()),groups=groups,
        status='finite source/custody controls; no operational qualification',source_tree_sha256=manifest['source_tree_sha256'],
        failed_compiler_attempts_preserved=failed))
    print(json.dumps(dict(checks_passed=sum(groups.values()),groups=groups),sort_keys=True))

if __name__=='__main__':main()
