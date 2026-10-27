"""Finite custody, source/action/storage and ordering checks; no runtime authority."""
from collections import Counter
import gzip
import json
import re
from prepare import HERE,BASE,CONTROL,TESTS,base_members,canonical,sha,write
from finalize_source import functions

def main():
    assert not (HERE/'seal.json').exists()
    groups=Counter()
    def check(value,group):
        assert value,group
        groups[group]+=1
    base=base_members();manifest=json.loads((HERE/'source-manifest.json').read_text())
    actual=[]
    for row in base:
        p=HERE/'overlay'/row['path'];p=p if p.exists() else BASE/'source/vm'/row['path']
        actual.append(dict(path=row['path'],bytes=p.stat().st_size,sha256=sha(p.read_bytes())))
    check(actual==manifest['members'],'candidate_custody')
    check(sha(canonical(actual))==manifest['source_tree_sha256'],'candidate_custody')
    check([a['path'] for a,b in zip(actual,base) if a!=b]==[CONTROL],'single_production_overlay')
    src=(HERE/'overlay'/CONTROL).read_text();old=(BASE/'source/vm'/CONTROL).read_text()
    start=src.index('    fn adopt_body_core_v1<');end=src.index('\n    fn check_budget(',start);core=src[start:end]
    order=['execution_work: 0,','control.check_budget(cursor)?;','control.deadline = started','control.check(cursor)?;',
        'if P::FIXED_EXECUTION_WORK_V1 != 0','if P::FIXED_EXECUTION_WORK_V1 > control.budget.execution_work',
        'control.execution_work = P::FIXED_EXECUTION_WORK_V1;','control.owner = NEXT_OWNER','source = Some(control.admit(',
        'metadata = Some(control.admit(','control.control_header =','control.cancellation_backing =','control.construction = Some(control.admit(']
    for a,b in zip(order,order[1:]):check(core.index(a)<core.index(b),'admission_order')
    check(src.count('control.execution_work = P::FIXED_EXECUTION_WORK_V1;')==1,'one_private_prepaid_store')
    check('const FIXED_EXECUTION_WORK_V1: u64 = 0;' in src,'original_zero_policy')
    check('const FIXED_EXECUTION_WORK_V1: u64 = SNAPSHOT_FIXED_EXECUTION_WORK_V1;' in src,'selected_sealed_price')
    check('trait ClosedAdoptionV1: adoption_state_seal_v1::Closed' in src,'selected_sealed_price')
    check('struct SnapshotAdoptionV1;' in src and 'pub struct SnapshotAdoptionV1' not in src,'selected_sealed_price')
    check('const SNAPSHOT_FIXED_EXECUTION_WORK_V1: u64 =\n    451_703_621 + 33_613 + 68_781 + 7_155 + 1_272;' in src,'exact_source_quote')
    check('const SNAPSHOT_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;' in src,'exact_source_storage')
    check('Some(selected) => selected.checked_add(SNAPSHOT_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1)' in src,'checked_selected_storage')
    # Preserve whole retirement/diagnostic tail byte for byte from the original
    # isolated source, independent of line movement from inserted constants.
    for marker in ['    pub(crate) fn finish_owned_cleanup','impl SnapshotRunV1 {','pub(crate) enum SnapshotAdmissionErrorV1',
                   '    pub(super) fn snapshot_debit_v1','    fn check_budget(']:
        extract=lambda text: text[text.index(marker):text.index('\n}',text.index(marker))+2]
        check(extract(src)==extract(old),'retirement_and_failure_preservation')
    unchanged=(BASE/'source/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs').read_text()
    check('WorkAuditPending' in unchanged,'writer_still_refused')
    check('snapshot_debit_v1(planning)' in unchanged and 'proposed_emission_work_v1(&shape)' in unchanged,'later_debits_separate')
    role=json.loads((HERE/'source-role-delta.json').read_text())
    check(role['added_role_count']==20 and role['added_bytes']==1436,'added_storage_roles')
    check(sum(r['bytes'] for r in role['added_roles'])==1436,'added_storage_roles')
    check(role['closure_captures_before']==role['closure_captures_after'] and role['closure_size_growth']==0,'unchanged_closure_layout')
    # Final compiler declarations independently agree with the provisional
    # injection inventory. Every old role is retained, with no negative credit.
    a=functions('metadata-base');b=functions('metadata-production');u=functions('metadata-unit')
    expected=Counter(r['type'] for r in role['added_roles'])
    for candidate,mode in [(b,'production'),(u,'unit')]:
        for name in a:
            before=Counter(r['type'] for r in a[name]['roles']);after=Counter(r['type'] for r in candidate[name]['roles'])
            check(not before-after,'final_mir_no_credits')
            check(after-before==(expected if name=='::{closure#0}' else Counter()),'final_mir_inventory')
    # New source callsite branch upper-sum. Existing callee totals are accepted
    # frozen logical rows, not measured CPU/time or inferred native costs.
    ingress=json.loads((HERE.parent/'swift-guarded-snapshot-ingress-work/ledger.json').read_text())
    own={'selected_const_fetch_compare_decision':3,'limit_const_budget_fetch_compare_decision':4,
        'failure_limit_const_budget_fetch':2,'failure_None_and_Err':2,'success_const_fetch_store':2}
    calls={k:ingress['rows'][k]['expanded_actions'] for k in ['fault','fault_limit','fail']}
    check(own=={'selected_const_fetch_compare_decision':3,'limit_const_budget_fetch_compare_decision':4,
        'failure_limit_const_budget_fetch':2,'failure_None_and_Err':2,'success_const_fetch_store':2},'exact_action_parts')
    check(calls=={'fault':10,'fault_limit':6,'fail':1243},'accepted_callee_prices')
    check(sum(own.values())+sum(calls.values())==1272,'dispatch_delta')
    fixed=451703621+33613+68781+7155+1272
    check(fixed==451814442,'dispatch_delta')
    write('work-delta.json',dict(schema=1,own_actions=own,callee_expanded_actions=calls,delta=1272,
        original_prefix=451703621,ingress=33613,optional_setup=68781,optional_wasi_finish=7155,fixed=fixed,
        planning=16384,emission_expression='19537+299377B+32E',optional_credits=False,
        source_shell_sha256=sha(core[core.index('            // Private selected admission shell.'):core.index('            control.owner = NEXT_OWNER')].encode()),
        convention='Accepted logical source-callsite plus requested IO, each closed std callback once; branch upper-sum retained; private std/retries/kernel/CPU/time excluded',
        bootstrap_interval='Selected consuming carrier through budget/deadline/check and admission comparison; commit is prepaid interval boundary. No host grant is provided or qualified.',
        complete_source_interval_funded=False,H_pre_ingress_funded=False,writer_runtime_selected=False))
    for label in ['metadata-base','metadata-probe','metadata-probe-minimal','metadata-production','metadata-unit',
                  'host-control-debug','host-control-release','scalar-checked']:
        folder=HERE/'commands'/label
        r=json.loads((folder/'receipt.json').read_text())
        check(r['exit_code']==0 and not r['timed_out'] and r['owned_group_absent'] and r['child_reaped'],'compiler_command_custody')
        check(sha(gzip.decompress((folder/'stdout.gz').read_bytes()))==r['stdout_sha256'],'command_output_custody')
        check(sha((folder/'stderr').read_bytes())==r['stderr_sha256'],'command_output_custody')
        check(json.loads((folder/'cleanup.json').read_text())['removed'],'owned_scratch_cleanup')
        if (folder/'test-receipt.json').exists():
            r=json.loads((folder/'test-receipt.json').read_text())
            check(r['exit_code']==0 and not r['timed_out'] and r['owned_group_absent'] and r['child_reaped'],'host_execution_custody')
            check(sha((folder/'test-stdout').read_bytes())==r['stdout_sha256'],'host_execution_custody')
            if label.startswith('host-control-'):check('7 passed; 0 failed' in (folder/'test-stdout').read_text(),'seven_actual_host_tests')
    write('control-results.json',dict(schema=1,checks_passed=sum(groups.values()),groups=groups,
        status='finite candidate source/custody/ordering checks only',source_tree_sha256=manifest['source_tree_sha256']))
    print(json.dumps(dict(checks_passed=sum(groups.values()),groups=groups),sort_keys=True))

if __name__=='__main__':main()
