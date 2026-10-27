"""Surface exact source delta for future cost/descriptor rebinding, no grants."""
import json
import sys
sys.dont_write_bytecode=True
from prepare import HERE,COMBINED,ACCOUNT_PACKET,BOOT,PROFILE,ACCOUNT,LOADER,sha,canonical,roster,row,write,checked_candidate

def main():
    source,hosts=checked_candidate()
    previous=json.loads((COMBINED/'source-manifest.json').read_bytes())
    old={item['path']:item for item in previous['members']}
    current=roster(source)
    changed=[]
    for item in current['members']:
        prior=old.get(item['path'])
        if item!=prior:
            changed.append(dict(path=item['path'],before=prior,after=item,
                bytes_delta=item['bytes']-(prior['bytes'] if prior else 0)))
    assert {r['path'] for r in changed}=={PROFILE,ACCOUNT,LOADER}
    entry=(ACCOUNT_PACKET/'entry.inc.rs').read_bytes()
    leaf=(BOOT/'driver.inc.rs').read_bytes()
    assert next(r for r in changed if r['path']==PROFILE)['bytes_delta']==len(entry)+len(leaf)+4
    required=[
      'Rebind exact source146 roster/count and every freshly generated build identity; source145 loader quote does not bind source146.',
      'Reprice count-dependent loader source-manifest validation, source bytes and all dynamic backing using the unchanged original validation-budget contract.',
      'Bind genuine selected source/build/session/executable/process geometry and trusted outer-parent invocation before any grant.',
      'Price all pre-existing P0 account, quote, closure, call, return, destroy/token/release and error places/work before constructing the account.',
      'Bind P1 setup and real-loader/original-validation work, P2 argument backing, P3 final composed pre-store/failure shell, P4 composed leaf/callee, and P5 retained diagnostics/output backing/destruction.',
      'Review child boundary and work quote against composed146; prior partial role/source sums are not complete storage/work or host authority.',
    ]
    write('cost-rebinding-required.json',dict(schema=1,
      command=['python3','verification/swift-guarded-snapshot-host-composition/rebinding.py'],
      python_version=sys.version,tool_sha256=sha((HERE/'rebinding.py').read_bytes()),
      previous_source145=dict(tree_sha256=previous['tree_sha256'],member_count=previous['member_count'],bytes=sum(r['bytes'] for r in previous['members'])),
      composed_source146=dict(tree_sha256=current['tree_sha256'],member_count=current['member_count'],bytes=sum(r['bytes'] for r in current['members'])),
      delta=changed,total_source_bytes_delta=sum(r['bytes_delta'] for r in changed),
      appended_leaf=dict(bytes=len(leaf),sha256=sha(leaf)),appended_entry=dict(bytes=len(entry),sha256=sha(entry)),
      append_separator_bytes=4,source_count_derived_from_exact_union=True,
      host_support=roster(hosts),fixed_host_count_changed=False,
      source145_loader_quote_applies_to_source146=False,source145_quote_rejected_or_recomputed_here=False,
      selected_policy='RootPolicyPending',selected_whole_quote='WholeQuotePending',emission='WorkAuditPending',
      retained_selected_execution_work=451814442,selected_product_store_does_not_fund_host=True,
      retained_inventory=dict(functions=19,roles=396,logical_source_object_bytes=311071,
          P0_functions=15,P0_roles=208,P0_logical_source_object_bytes=234375,discounted_roles=0),
      requirements=required,complete_work_or_storage_quote=None,
      source_objects_are_dynamic_backing_RSS_stack_allocator_or_CPU=False,
      root_policy_whole_quote_healthy_cleanup_operational_authority=False))
    print(json.dumps(dict(delta=changed,total_source_bytes_delta=sum(r['bytes_delta'] for r in changed))))

if __name__=='__main__':main()
