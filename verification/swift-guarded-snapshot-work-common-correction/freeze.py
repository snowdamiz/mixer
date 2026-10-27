"""Freeze only the correction packet; preserve every timed-out attempt."""
import gzip
import json
import os
import sys
sys.dont_write_bytecode=True
from prepare import HERE,BASE_TREE,BASE_SEAL,ORIGINAL_TREE,ORIGINAL_SEAL,RELEASE_SHA,base_members,canonical,sha,write

def main():
    assert not (HERE/'seal.json').exists()
    base_members()
    assert not any((HERE/'owned-work').iterdir())
    controls=json.loads((HERE/'control-results.json').read_text())
    groups=[];outcomes=[]
    for p in sorted((HERE/'commands').glob('*/receipt.json')):
        r=json.loads(p.read_text())
        assert r['child_reaped'] and r['owned_group_absent']
        assert sha(gzip.decompress((p.parent/'stdout.gz').read_bytes()))==r['stdout_sha256']
        assert sha((p.parent/'stderr').read_bytes())==r['stderr_sha256']
        outcomes.append(dict(label=p.parent.name,exit_code=r['exit_code'],timed_out=r['timed_out'],seconds=r['elapsed_seconds']))
        records=[(str(p.relative_to(HERE)),r)]
        if 'compiler_version_command' in r:records.append((str(p.relative_to(HERE))+'#compiler_version_command',r['compiler_version_command']))
        for q in sorted(p.parent.glob('*-receipt.json')):
            t=json.loads(q.read_text());assert t['exit_code']==0 and t['owned_group_absent'] and not t['timed_out']
            prefix=q.name.removesuffix('-receipt.json')
            assert sha((q.parent/(prefix+'-stdout')).read_bytes())==t['stdout_sha256']
            assert sha((q.parent/(prefix+'-stderr')).read_bytes())==t['stderr_sha256']
            records.append((str(q.relative_to(HERE)),t))
        for name,r in records:
            try:os.killpg(r['owned_process_group'],0);absent=False
            except ProcessLookupError:absent=True
            assert absent,name
            groups.append(dict(receipt=name,owned_process_group=r['owned_process_group'],rechecked_absent=absent))
    write('cleanup.json',dict(schema=1,owned_scratch_removed=True,owned_groups_rechecked=groups,
        global_process_inventory=False,only_owned_groups_rechecked=True,other_projects_touched=False,
        native_device_simulator_emulator_UI_capture_processes_started=False))
    manifest=json.loads((HERE/'source-manifest.json').read_text())
    write('summary.json',dict(schema=1,status='frozen-common-attribution-correction-awaiting-independent-review',
        source_members=144,source_tree_sha256=manifest['source_tree_sha256'],base_tree_sha256=BASE_TREE,base_seal_sha256=BASE_SEAL,
        original_work_admission_source_tree_sha256=ORIGINAL_TREE,original_work_admission_seal_sha256=ORIGINAL_SEAL,root_release_sha256=RELEASE_SHA,
        common_new_roles=20,common_new_bytes=1436,selected_only_new_bytes=0,S_unchanged=941467,
        production=dict(F0=366312,common=445988,selected=1387455,admitted=1817630),
        unit=dict(F0=366896,common=446572,selected_before_H=1388039,selected_with_H=1469366,admitted_with_H=1899541),
        selected_admitted_totals_unchanged=True,ordinary_common_floor_increased=1436,
        ordinary_shared_source_predicate_actions=3,ordinary_shared_source_predicate_bool_bytes=1,
        ordinary_successful_execution_work=0,const_relocation_runtime_source_delta=0,
        fixed_work=451814442,dispatch_upper_sum=1272,fresh_exact_metadata_modes=['production','unit'],
        compile_only_assertion_overlay_verifies_actual_floors=True,
        actual_host_tests=dict(debug=dict(existing=7,changed_floor=2),release=dict(existing=7,changed_floor=2),other_tests_undispatched=468),
        standalone_checked_integer_controls=dict(production=237,unit=237),finite_source_custody_controls=controls['checks_passed'],
        compiler_attempts=outcomes,initial_timeouts_preserved=3,python_version=sys.version,
        source_convention='shared unoptimized declarations; no specialization or constant-folding credit',
        original_source_or_timing_overhead_newly_funded_by_selected_counter=False,
        bootstrap_grants_qualified=False,H_pre_ingress_qualified=False,genuine_selected_loader_ingress_qualified=False,
        complete_or_operational_source_funding=False,WorkAuditPending_preserved=True,
        loader_guest_cache_scope_construct_writer_executed=False,
        phase_retention_or_descriptor_changes_included=False,canonical_root_or_git_mutations=False,
        native_checks='paused and pending; no device/simulator/emulator/UI/capture runtime',GA_gates_verified=0))
    rows=[dict(path=p.relative_to(HERE).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes()))
          for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='seal.json']
    write('seal.json',dict(schema=1,member_count=len(rows),members=rows,manifest_sha256=sha(canonical(rows)),
        status='frozen correction; no independent or operational acceptance'))
    print(json.dumps(dict(member_count=len(rows),bytes=sum(r['bytes'] for r in rows),source_members=144,
        seal_sha256=sha((HERE/'seal.json').read_bytes()),source_tree_sha256=manifest['source_tree_sha256'])))

if __name__=='__main__':main()
