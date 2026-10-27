"""Read-only inputs; writes this lane's independently reconstructed review."""
import sys
sys.dont_write_bytecode=True
from collections import Counter, defaultdict
from pathlib import Path
import difflib
import gzip
import json
import os
import re
from review import HERE, ROOT, PRODUCER, BASE, CONTROL, TESTS, RELEASE, RUSTC, EXPECTED_TREE, custody, sha, canonical, write, load, functions

def main():
    assert not (HERE/'seal.json').exists()
    custody()
    passed=Counter()
    def check(ok,group):
        assert ok,group
        passed[group]+=1
    old=(BASE/'source/vm'/CONTROL).read_text()
    new=(PRODUCER/'overlay'/CONTROL).read_text()
    patch=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='accepted-source144/'+CONTROL,tofile='candidate-source144/'+CONTROL))
    check(patch==(PRODUCER/'source-delta.patch').read_text(),'exact_single_file_diff')
    start=new.index('    fn adopt_body_core_v1<');end=new.index('\n    fn check_budget(',start)
    core=new[start:end]
    shell=core[core.index('            // Private selected admission shell.'):core.index('            control.owner = NEXT_OWNER')]
    check(sha(shell.encode())==load(PRODUCER/'work-delta.json')['source_shell_sha256'],'exact_shell')
    tokens=['execution_work: 0,','control.check_budget(cursor)?;','control.deadline = started','control.check(cursor)?;',
        'if P::FIXED_EXECUTION_WORK_V1 != 0','if P::FIXED_EXECUTION_WORK_V1 > control.budget.execution_work',
        'control.execution_work = P::FIXED_EXECUTION_WORK_V1;','control.owner = NEXT_OWNER','source = Some(control.admit(',
        'metadata = Some(control.admit(','control.control_header =','control.cancellation_backing =','control.construction = Some(control.admit(']
    for a,b in zip(tokens,tokens[1:]):check(core.index(a)<core.index(b),'ordered_admission')
    check(core.count('control.execution_work = P::FIXED_EXECUTION_WORK_V1;')==1,'one_counter_store')
    check(core[core.index('        if let Err(mut failure) = result {'):]==old[old.index('        if let Err(mut failure) = result {'):old.index('\n    fn check_budget(')],'unchanged_failure_retirement')
    tail='    fn check_budget('
    newtail=new[new.index(tail):].replace('    const FIXED_EXECUTION_WORK_V1: u64;\n','').replace('    const FIXED_EXECUTION_WORK_V1: u64 = 0;\n','').replace('    const FIXED_EXECUTION_WORK_V1: u64 = SNAPSHOT_FIXED_EXECUTION_WORK_V1;\n','')
    check(newtail==old[old.index(tail):],'unchanged_all_post_core_helpers')
    check('trait ClosedAdoptionV1: adoption_state_seal_v1::Closed' in new and 'struct SnapshotAdoptionV1;' in new,'private_closed_price')
    check('const FIXED_EXECUTION_WORK_V1: u64 = 0;' in new and 'const FIXED_EXECUTION_WORK_V1: u64 = SNAPSHOT_FIXED_EXECUTION_WORK_V1;' in new,'sealed_associated_prices')
    check('control.budget.execution_work' in shell and 'budget.execution_work' not in shell.replace('control.budget.execution_work',''),'no_new_budget_capture')

    ledger_path=HERE.parent/'swift-guarded-snapshot-ingress-work/ledger.json'
    ledger=load(ledger_path)
    accepted_seal=load(ledger_path.parent/'seal.json')
    for member in accepted_seal['members']:
        data=(ledger_path.parent/member['path']).read_bytes()
        check((len(data),sha(data))==(member['bytes'],member['sha256']),'accepted_action_input_custody')
    expanded={}
    def expand(name):
        if name in expanded:return expanded[name]
        row=ledger['rows'][name]
        check(not row['loops'],'callee_no_new_loop_multiplicity')
        binding=ledger['source_bindings'][row['binding']]
        check(sha(binding['source'].encode())==binding['sha256'] and binding['source'] in new,'exact_accepted_callee_body')
        check(sum(row['parts'].values())==row['own_actions'],'accepted_action_parts')
        value=row['own_actions']+sum(mult*expand(callee) for callee,mult in row['calls'].items())
        check(value==row['expanded_actions'],'callee_expansion')
        expanded[name]=value
        return value
    calls={name:expand(name) for name in ['fault','fault_limit','fail']}
    check(calls==dict(fault=10,fault_limit=6,fail=1243),'new_callee_prices')
    own=dict(outer_associated_const_fetch_compare_decision=3,inner_const_budget_fetch_compare_decision=4,
        refusal_const_budget_fetch=2,refusal_none_and_err_carriers=2,success_const_fetch_store=2)
    check(sum(own.values())==13 and sum(own.values())+sum(calls.values())==1272,'exact_new_branch_upper_sum')
    check(shell.count('Fault::new(')==1 and shell.count('.limit(')==1 and shell.count('control.fail(')==1,'new_callsite_multiplicity')
    check(all(t not in shell for t in ['for ','while ','loop {','checked_add','work_with_wasi']),'new_shell_no_loop_or_repeated_debit')
    accepted=load(ROOT/'verification/swift-semantic-adapter-root-review/guarded-snapshot-full-work-host-acceptance.json')
    check(sha((ROOT/'verification/swift-semantic-adapter-root-review/guarded-snapshot-full-work-host-acceptance.json').read_bytes())==load(PRODUCER/'source-manifest.json')['work_receipt_sha256'],'accepted_full_work_custody')
    fixed=accepted['prefix_with_optional_setup_and_cleanup_prepaid']+1272
    check(fixed==451814442,'accepted_full_work_plus_delta')
    write('action-review.json',dict(schema=1,source_tree_sha256=EXPECTED_TREE,new_own_actions=own,new_callees=calls,
        inherited_expanded=expanded,dispatch_delta=1272,accepted_prefix=451813170,fixed=fixed,
        outer_predicate_added_to_original_source_actions=3,
        interpretation='Exact accepted abstract source-callsite/requested-IO branch upper-sum; no CPU/retry/private-std/kernel/time claim.',
        bootstrap_external_grant_qualified=False,H_pre_ingress_qualified=False,complete_source_funding=False))

    a=functions((HERE/'commands/fresh-base/adoption-functions.mir').read_text())
    b=functions((HERE/'commands/fresh-production/adoption-functions.mir').read_text())
    u=functions((HERE/'commands/host-debug-corrected/adoption-functions.mir').read_text())
    # Map unchanged source occurrences by exact diff matching blocks. New spans
    # are named explicitly; remaining declaration aliases are exact span+type,
    # one to one with occurrence multiplicity, not just pooled same-size types.
    line_map={}
    for block in difflib.SequenceMatcher(None,old.splitlines(),new.splitlines(),autojunk=False).get_matching_blocks():
        for offset in range(block.size):line_map[block.b+offset+1]=block.a+offset+1
    def span(role):
        m=re.search(r'control.rs:(\d+):(\d+): (\d+):(\d+)',role['span'])
        assert m,role
        return tuple(map(int,m.groups()))
    def injected(line):
        m=re.search(r'control.rs:(\d+):\d+: (\d+):\d+',line)
        return m is not None and 704<=int(m[1])<=717
    body=b['::{closure#0}']['body']
    direct=[r for r in b['::{closure#0}']['roles'] if injected(r['span'])]
    referenced=set()
    for line in body.splitlines():
        if injected(line) and 'let ' not in line:referenced.update(re.findall(r'\b_\d+\b',line))
    selected_ids={r['local'] for r in direct}
    aliases=[r for r in b['::{closure#0}']['roles'] if r['local'] in referenced and r['local'] not in selected_ids and r['type'].startswith('&')]
    added=direct+aliases
    check(len(direct)==15 and len(aliases)==5,'new_roles_direct_and_reborrow_provenance')
    expected=Counter(r['type'] for r in added)
    sizes={name:int(size) for name,size in re.findall(r'print-type-size type: `([^`]+)`: (\d+) bytes',gzip.decompress((HERE/'commands/fresh-production/stdout.gz').read_bytes()).decode())}
    sizes.update({'()':0,'!':0,'u64':8,'bool':1})
    added_rows=[]
    for r in added:
        size=8 if r['type'].startswith('&') else sizes[r['type']]
        added_rows.append(dict(**r,bytes=size))
    check(len(added_rows)==20 and sum(r['bytes'] for r in added_rows)==1436,'exact_new_roles_and_bytes')
    alias_counts=[]
    for name in a:
        before=Counter(r['type'] for r in a[name]['roles'])
        for candidate in [b,u]:
            after=Counter(r['type'] for r in candidate[name]['roles'])
            check(not before-after,'no_removed_role_credit')
            check(after-before==(expected if name=='::{closure#0}' else Counter()),'fresh_final_inventory')
        def key(r,convert=False):
            first,col,last,endcol=span(r)
            if convert:first,last=line_map[first],line_map[last]
            return r['type'],first,col,last,endcol
        old_keys=Counter(key(r) for r in a[name]['roles'])
        new_keys=Counter(key(r,True) for r in b[name]['roles'] if not (name=='::{closure#0}' and r['local'] in {x['local'] for x in added}))
        check(old_keys==new_keys,'exact_old_role_span_type_aliases')
        alias_counts.append(dict(function=name,old_roles=sum(old_keys.values()),exact_preserved_aliases=sum(new_keys.values())))
    capture=lambda text:re.findall(r'^\s+debug [^\n]+=> \(\*\(\(\*_1\)\.(\d+): ([^)]+)\)\);',text,re.M)
    check(capture(a['::{closure#0}']['body'])==capture(body) and len(capture(body))==8,'eight_unchanged_closure_captures')
    # The established accepted template recipe funds non-inherited shared core
    # roles as common-extra. The new roles have no P-dependent representation;
    # optimizing an Original monomorph is not that raw-source inventory rule.
    correction=HERE.parent/'swift-guarded-snapshot-owner-storage-alias-correction'
    correction_seal=load(correction/'seal.json')
    funding_row=next(r for r in correction_seal['members'] if r['path']=='funding.json')
    check(sha((correction/'funding.json').read_bytes())==funding_row['sha256'],'accepted_template_rule_custody')
    funding=load(correction/'funding.json')
    common=[r for r in funding['roles'] if 'adopt_body_core_v1::{closure#0}::' in r['id'] and r['funding']['common-extra']>0]
    check(len(common)>0 and any(r['funding']['common-extra']==1096 for r in common),'shared_template_common_precedent')
    check(all('<P ' not in r['type'] and ' as ' not in r['type'] for r in added_rows),'all_new_roles_representation_identical')
    predicate=next(r for r in added_rows if r['local']=='_38')
    check(predicate['type']=='bool' and predicate['bytes']==1 and span(predicate)==(704,16,704,47),'original_outer_predicate_role')
    write('storage-review.json',dict(schema=1,new_roles=added_rows,role_count=20,bytes=1436,
        exact_old_role_aliases=alias_counts,closure_captures=capture(body),no_removed_role_credit=True,
        accepted_rule_input=dict(path=str(correction/'funding.json'),sha256=sha((correction/'funding.json').read_bytes())),
        common_template_precedent=common,status='selected total confirmed; selected-only classification requires correction',
        smallest_conservative_template_correction=dict(common_increment=1436,selected_delta_remainder=0,selected_total_delta=1436,
            production_common=445988,unit_common=446572,production_selected=1387455,unit_selected_with_H=1469366),
        minimum_unavoidable_common_source_role=dict(local='_38',type='bool',bytes=1),
        optimization_exclusion='No accepted credit for const folding, LLVM elimination, private-library behavior or physical stack.') )

    receipts=[]
    for folder in sorted((HERE/'commands').iterdir()):
        r=load(folder/'receipt.json')
        check(r['exit_code']==0 and not r['timed_out'] and r['owned_group_absent'] and r['child_reaped'],'fresh_compile_receipt')
        check(sha(gzip.decompress((folder/'stdout.gz').read_bytes()))==r['stdout_sha256'],'compiler_stdout_custody')
        check(sha((folder/'stderr').read_bytes())==r['stderr_sha256'],'compiler_stderr_custody')
        check(load(folder/'cleanup.json')['removed'],'owned_scratch_cleanup')
        receipts.append(dict(path=(folder/'receipt.json').relative_to(HERE).as_posix(),**{k:r[k] for k in ['owned_process_group','exit_code']}))
        v=r['version_receipt']
        check(v['exit_code']==0 and v['owned_group_absent'] and v['child_reaped'],'compiler_version_receipt')
        receipts.append(dict(path=(folder/'receipt.json').relative_to(HERE).as_posix()+'#version_receipt',**{k:v[k] for k in ['owned_process_group','exit_code']}))
        if (folder/'test-receipt.json').exists():
            t=load(folder/'test-receipt.json')
            check(t['owned_group_absent'] and t['child_reaped'] and not t['timed_out'],'host_child_cleanup')
            check(sha((folder/'test-stdout').read_bytes())==t['stdout_sha256'] and sha((folder/'test-stderr').read_bytes())==t['stderr_sha256'],'host_output_custody')
            if folder.name=='host-debug':check(t['exit_code']!=0 and '7 passed; 1 failed' in (folder/'test-stdout').read_text(),'initial_expectation_failure_preserved')
            else:check(t['exit_code']==0 and '8 passed; 0 failed' in (folder/'test-stdout').read_text(),'eight_independent_host_tests')
            receipts.append(dict(path=(folder/'test-receipt.json').relative_to(HERE).as_posix(),**{k:t[k] for k in ['owned_process_group','exit_code']}))
    cleanup=[]
    for r in receipts:
        try:os.killpg(r['owned_process_group'],0);absent=False
        except ProcessLookupError:absent=True
        check(absent,'recorded_owned_group_absent')
        cleanup.append(dict(**r,rechecked_absent=absent))
    write('cleanup.json',dict(schema=1,owned_commands=cleanup,owned_scratch_removed=not any((HERE/'owned-work').iterdir()),
        global_process_inventory=False,native_or_capture_processes_started=False,other_projects_touched=False))
    write('review.json',dict(schema=1,status='request-correction-shared-common-template-accounting',source_tree_sha256=EXPECTED_TREE,
        producer_seal_sha256=sha((PRODUCER/'seal.json').read_bytes()),release_sha256=sha(RELEASE.read_bytes()),
        checks_passed=sum(passed.values()),groups=dict(passed),fixed=451814442,delta_actions=1272,new_roles=20,new_bytes=1436,
        independent_host_tests=dict(debug=8,release='not repeated; frozen producer release7 audited by custody'),initial_host_test_outcome='7 passed / 1 failed: independent assertion wrongly expected healthy selected final cleanup; corrected to preserved conservative ConstructionBound.',
        finding='All new shared generic template roles were charged S only. Established source-template rule requires common funding; at minimum outer Original predicate adds one bool byte and three logical source actions.',
        requested_correction='Move1436 from selected-only increment to common increment; selected total unchanged. Disclose Original/common source overhead; do not claim zero ordinary overhead from zero work counter or optimizer folding.',
        pending=['bootstrap external grant','H pre-ingress ownership/funding','authentic selected ingress','complete source funding','phase-retention/descriptor composition','writer','healthy cleanup','native runtime','GA'],
        loader_guest_cache_scope_construct_writer_executed=False,GA_gates_verified=0))
    print(json.dumps(dict(checks_passed=sum(passed.values()),status='request correction',groups=dict(passed)),sort_keys=True))

if __name__=='__main__':main()
