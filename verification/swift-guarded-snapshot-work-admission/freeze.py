"""Freeze only this compact overlay candidate and owned bounded evidence."""
import gzip
import json
import os
from prepare import HERE,BASE,BASE_TREE,BASE_SEAL,CONTROL,WORK_RECEIPT_SHA,base_members,canonical,sha,write

def main():
    assert not (HERE/'seal.json').exists()
    base_members()
    manifest=json.loads((HERE/'source-manifest.json').read_text())
    controls=json.loads((HERE/'control-results.json').read_text())
    assert controls['checks_passed']==101
    assert not any((HERE/'owned-work').iterdir())
    commands=[]
    for p in sorted((HERE/'commands').glob('*/receipt.json')):
        r=json.loads(p.read_text());assert r['exit_code']==0 and r['owned_group_absent'] and r['child_reaped'] and not r['timed_out']
        assert sha(gzip.decompress((p.parent/'stdout.gz').read_bytes()))==r['stdout_sha256']
        assert sha((p.parent/'stderr').read_bytes())==r['stderr_sha256']
        try:os.killpg(r['owned_process_group'],0);absent=False
        except ProcessLookupError:absent=True
        assert absent
        commands.append(dict(path=str(p.relative_to(HERE)),owned_process_group=r['owned_process_group'],rechecked_absent=absent))
        for name in ['test-receipt.json']:
            q=p.parent/name
            if q.exists():
                t=json.loads(q.read_text());assert t['exit_code']==0 and t['owned_group_absent'] and not t['timed_out']
                try:os.killpg(t['owned_process_group'],0);absent=False
                except ProcessLookupError:absent=True
                assert absent
                commands.append(dict(path=str(q.relative_to(HERE)),owned_process_group=t['owned_process_group'],rechecked_absent=absent))
    write('cleanup.json',dict(schema=1,owned_scratch_removed=True,owned_groups_rechecked=commands,
        global_process_inventory=False,native_or_capture_processes_started=False,other_projects_touched=False))
    write('summary.json',dict(schema=1,status='frozen-private-source-candidate-awaiting-independent-review',
        source_members=144,source_tree_sha256=manifest['source_tree_sha256'],base_tree_sha256=BASE_TREE,base_seal_sha256=BASE_SEAL,
        accepted_full_work_interface_sha256=WORK_RECEIPT_SHA,independent_work_seal_sha256='1a0dfc2f649f9e7196fd64f8a1cf066240c8cdb4acb5fe67cfc5937fd3f9b701',
        fixed_work=451814442,new_action_delta=1272,new_source_roles=20,new_selected_source_bytes=1436,
        production_floor=dict(common=444552,selected=1387455,admitted=1817630),
        unit_floor=dict(common=445136,selected_with_H=1469366,admitted_with_H=1899541),
        compiler='rustc1.99.0 aarch64-apple-darwin',metadata_compiles=2,host_control_tests=dict(debug=7,release=7),scalar_arithmetic_controls=393,
        finite_source_custody_controls=101,original_policy_zero_work=True,failed_admission_usage_zero=True,
        work_limit=1000000000,memory_limit=268435456,planning_work=16384,emission_expression='19537+299377B+32E',
        bootstrap_pregrant_qualified=False,H_pre_ingress_qualified=False,complete_source_interval_funded=False,
        authentic_loader_ingress_executed=False,guest_executed=False,cache_construction_executed=False,snapshot_scope_construct_executed=False,
        WorkAuditPending_preserved=True,writer_runtime_selected=False,phase_A_retention_changed=False,
        source145_descriptor_changed=False,operational_or_full_funding_accepted=False,canonical_changes=False,
        native_checks='paused/pending; no device/simulator/emulator/UI/capture',GA_gates_verified=0))
    rows=[dict(path=p.relative_to(HERE).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='seal.json']
    write('seal.json',dict(schema=1,member_count=len(rows),members=rows,manifest_sha256=sha(canonical(rows)),
        status='frozen candidate; no independent or operational acceptance'))
    print(json.dumps(dict(members=len(rows),bytes=sum(r['bytes'] for r in rows),seal_sha256=sha((HERE/'seal.json').read_bytes()),source_tree_sha256=manifest['source_tree_sha256'])))

if __name__=='__main__':main()
