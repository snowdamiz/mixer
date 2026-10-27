"""Verify this completed owned packet and seal it once; no runtime dispatch."""
from pathlib import Path
import json
import os
import shutil
import sys

sys.dont_write_bytecode=True
from prepare import HERE,sha,canonical,members,write
from verify import custody

def member(path):
    return dict(path=path.relative_to(HERE).as_posix(),bytes=path.stat().st_size,sha256=sha(path.read_bytes()))

def main():
    if len(sys.argv)==2 and sys.argv[1]=='--check':
        seal=json.loads((HERE/'seal.json').read_text())
        for row in seal['members']:
            assert member(HERE/row['path'])==row,row['path']
        assert sha(canonical(seal['members']))==seal['tree_sha256']
        print(json.dumps(dict(verified_members=len(seal['members']),seal_sha256=sha((HERE/'seal.json').read_bytes()))))
        return
    assert len(sys.argv)==1 and not (HERE/'seal.json').exists()
    binding=custody()
    receipts=sorted((HERE/'commands').glob('*/receipt.json'))
    assert len(receipts)==8
    groups=[]
    compiler=0
    standalone=0
    for path in receipts:
        receipt=json.loads(path.read_text())
        assert receipt['child_reaped'] and receipt['owned_group_absent'] and not receipt['timed_out']
        expected_overflow=receipt.get('expected_result')=='checked-overflow E0080'
        assert receipt['exit_code']!=0 if expected_overflow else receipt['exit_code']==0
        if 'expectation_met' in receipt:
            assert receipt['expectation_met']
            compiler+=1
        assert sha((path.parent/'stdout').read_bytes())==receipt['stdout_sha256']
        assert sha((path.parent/'stderr').read_bytes())==receipt['stderr_sha256']
        owned=[('command',receipt)]
        if 'compiler_version_command' in receipt:
            owned.append(('compiler-version',receipt['compiler_version_command']))
        scalar=path.parent/'scalar-receipt.json'
        if scalar.exists():
            value=json.loads(scalar.read_text())
            assert value['exit_code']==0 and value['child_reaped'] and value['owned_group_absent'] and not value['timed_out']
            assert sha((path.parent/'scalar-stdout').read_bytes())==value['stdout_sha256']
            assert sha((path.parent/'scalar-stderr').read_bytes())==value['stderr_sha256']
            owned.append(('standalone-scalar',value))
            standalone+=1
        for kind,value in owned:
            try:
                os.killpg(value['owned_process_group'],0)
                absent=False
            except ProcessLookupError:
                absent=True
            assert absent,value['owned_process_group']
            groups.append(dict(receipt=path.relative_to(HERE).as_posix(),kind=kind,
                owned_process_group=value['owned_process_group'],child_reaped=True,owned_group_absent_at_final_recheck=True))
    assert compiler==6 and standalone==3
    work=HERE/'owned-work'
    assert not list(work.iterdir())
    work.rmdir()
    for cache in HERE.rglob('__pycache__'):
        shutil.rmtree(cache)
    cleanup=dict(schema=1,owned_groups=groups,all_recorded_groups_absent_and_reaped=True,
        owned_scratch_removed=not work.exists(),packet_bytecode_removed=True,
        native_or_capture_processes_started=0,process_inventory_performed=False,
        scope='Only this packet recorded owned groups were checked; no other project process or data was inspected/changed.')
    write('cleanup.json',cleanup)
    summary=dict(schema=1,source_binding=binding,changed_files=2,source_members=144,
        exact_metadata_MIR_contexts=['production','cfg(test)'],scalar_compilations=4,
        scalar_executions=3,synthetic_phase_controls_per_execution=174,
        expected_overflow_E0080=True,source_ordering_accounting_controls=34,
        added_runtime_roles=0,added_runtime_storage_bytes=0,retained_old_selected_floor_charge=200,
        optional_or_removed_role_credits_selected=False,
        accepted_recipe=dict(C=78240,S=941467,A=430175,H=81327),
        integration_source_implemented=True,source_integration_independently_accepted=False,
        admitted_A_narrowing_lifetime_review_pending=True,H_pre_ingress_ownership_review_pending=True,
        WorkAuditPending_preserved=True,helper_delegation_added=False,
        original_300000_400000_fixtures_preserved=True,fixed_policy_limits_changed=False,
        all_recorded_owned_groups_absent_and_reaped=True,owned_scratch_removed=True,
        engine_VM_writer_dispatched=False,native_checks='paused and pending',
        canonical_product_changed=False,healthy_cleanup_accepted=False,GA_gates_verified=0)
    write('summary.json',summary)
    rows=[member(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    seal=dict(schema=1,members=rows,member_count=len(rows),member_bytes=sum(r['bytes'] for r in rows),
        tree_sha256=sha(canonical(rows)),scope='Constants-only isolated funding source implementation and compiler/pure scalar evidence; no writer admission or operational acceptance')
    write('seal.json',seal)
    print(json.dumps(dict(members=len(rows),bytes=seal['member_bytes'],tree_sha256=seal['tree_sha256'],
        seal_sha256=sha((HERE/'seal.json').read_bytes()),owned_groups=len(groups)),sort_keys=True))

if __name__=='__main__':
    main()
