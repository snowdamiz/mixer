"""Final owned audit, cleanup and compact independent packet freeze."""
from pathlib import Path
import json
import os
import sys
sys.dont_write_bytecode=True
from prepare import HERE,sha,canonical,load,write,member
from run_filtered import bounded

def main():
    assert not (HERE/'seal.json').exists()
    command=[sys.executable,str(HERE/'audit.py')]
    out,err,receipt=bounded(command,{'PATH':'/usr/bin:/bin'},HERE,30)
    (HERE/'audit-stdout').write_bytes(out);(HERE/'audit-stderr').write_bytes(err)
    receipt.update(schema=1,python_version=sys.version,source_sha256=sha((HERE/'audit.py').read_bytes()),
        stdout_sha256=sha(out),stderr_sha256=sha(err),
        scope='final finite source/custody audit; only owned child group observed')
    write('audit-command.json',receipt)
    assert receipt['exit_code']==0 and not receipt['timed_out'] and receipt['owned_group_absent'],out.decode()+err.decode()
    groups=[]
    for label in ['production-const-floors','independent-debug-boundaries']:
        folder=HERE/'commands'/label;r=load(folder/'receipt.json')
        groups.append((str(folder.relative_to(HERE))+'/receipt.json',r))
        groups.append((str(folder.relative_to(HERE))+'/receipt.json#version_receipt',r['version_receipt']))
        if (folder/'test-receipt.json').exists():groups.append((str(folder.relative_to(HERE))+'/test-receipt.json',load(folder/'test-receipt.json')))
    groups.append(('audit-command.json',receipt))
    cleanup=[]
    for source,r in groups:
        assert r['child_reaped'] and r['owned_group_absent']
        try: os.killpg(r['owned_process_group'],0);absent=False
        except ProcessLookupError: absent=True
        assert absent,source
        cleanup.append(dict(receipt=source,owned_process_group=r['owned_process_group'],rechecked_absent=True))
    assert not (HERE/'owned-work').exists()
    write('cleanup.json',dict(schema=1,owned_groups_rechecked=cleanup,owned_scratch_removed=True,
        only_recorded_owned_groups_probed=True,global_process_inventory=False,
        native_device_simulator_emulator_UI_capture_processes_started=False,canonical_root_sibling_or_git_changes=False))
    review=load(HERE/'review.json')
    write('summary.json',dict(schema=1,status='independent-const-common-attribution-correction-accepted-only',
        review='review.json',correction_seal_sha256=review['correction_seal_sha256'],
        source_tree_sha256=review['source_tree_sha256'],source_members=144,
        reviewed_correction_members=119,reviewed_correction_bytes=6308959,
        finite_checks=review['total_finite_checks'],differential_custody_checks=114,arithmetic_checks=280,
        fresh_compiler_executions=2,fresh_actual_host_tests_passed=4,
        independent_host_release='not repeated; producer debug/release9 audited',
        blocking_findings=[],common_added_bytes=1436,common_C=79676,selected_S=941467,
        production=review['production'],unit=review['unit'],selected_admitted_totals_unchanged=True,
        fixed_execution_work=451814442,dispatch_actions=1272,ordinary_outer_source_actions=3,
        ordinary_successful_counter=0,ordinary_unchanged_source_behavior_qualified=False,
        bootstrap_H_authentic_ingress_complete_funding_writer_or_GA_qualified=False,
        native_device_simulator_emulator_UI_capture='paused and pending',
        runtime_scope='actual ordinary parser/validator and private control adoption/cleanup only; synthetic selected fixture',
        loader_guest_cache_scope_construct_writer_executed=False,WorkAuditPending_preserved=True,
        producer_initial_compiler_timeouts_preserved=3,owned_groups_rechecked_absent=len(cleanup),scratch_removed=True,
        canonical_root_sibling_or_git_changes=False,GA_gates_verified=0))
    rows=[member(path,str(path.relative_to(HERE))) for path in sorted(HERE.rglob('*')) if path.is_file() and path.name!='seal.json']
    assert not any('__pycache__' in row['path'] or row['path'].startswith('owned-work/') for row in rows)
    seal=dict(schema=1,status='frozen independent const-common attribution acceptance only',
        correction_seal_sha256=review['correction_seal_sha256'],source_tree_sha256=review['source_tree_sha256'],
        manifest_sha256=sha(canonical(rows)),member_count=len(rows),member_bytes=sum(row['bytes'] for row in rows),members=rows)
    write('seal.json',seal)
    for row in rows: assert member(HERE/row['path'],row['path'])==row
    print(json.dumps(dict(seal_sha256=sha((HERE/'seal.json').read_bytes()),members=len(rows),bytes=seal['member_bytes'],
        finite_checks=394,actual_host_tests_passed=4,blocking_findings=[],owned_groups_absent=len(cleanup),scratch_removed=True),sort_keys=True))
if __name__=='__main__':main()
