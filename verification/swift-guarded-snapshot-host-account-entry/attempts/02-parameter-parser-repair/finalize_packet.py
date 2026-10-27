#!/usr/bin/env python3
"""Reconcile finite compiler/test evidence, losslessly compact and seal packet."""
from collections import defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent
def sha(data):return hashlib.sha256(data).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def write(name,value):(HERE/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def read(name):return json.loads((HERE/name).read_text())

def snapshot_tools():
    current=(HERE/'run_inventory.py').read_text()
    # Reconstruct the exact metadata driver version from the retained source
    # transformations, then compare its bytes to the recorded at-start hash.
    before=current
    start=before.index('    printed=(HERE/')
    end=before.index('    query_types={}',start)
    before=before[:start]+before[end:]
    before=before.replace('    concrete_anonymous={}\n','')
    start=before.index("        if ty=='impl FnOnce() -> T':")
    end=before.index("        if 'impl FnOnce' in ty",start)
    before=before[:start]+before[end:]
    before=before.replace('use crate::{experimental,experimental_wasi};\\n','')
    start=before.index('            elif ty in concrete_anonymous:')
    end=before.index('            else:',start)
    before=before[:start]+before[end:]
    before=before.replace('          actual_compiler_anonymous_types=concrete_anonymous,\n','')
    folder=HERE/'compiler-commands/production-metadata-mir'
    receipt=json.loads((folder/'receipt.json').read_text())
    assert sha(before.encode())==receipt['tool_sha256'],(sha(before.encode()),receipt['tool_sha256'])
    (folder/'driver-at-start.py').write_text(before)
    folder=HERE/'compiler-commands/actual-type-layout-queries'
    receipt=json.loads((folder/'receipt.json').read_text())
    assert sha(current.encode())==receipt['tool_sha256']
    (folder/'driver-at-start.py').write_text(current)

def compress_outputs():
    for receipt_path in sorted(HERE.rglob('receipt.json')):
        receipt=json.loads(receipt_path.read_text())
        if 'output' not in receipt:continue
        changed=False
        for name,record in receipt['output'].items():
            path=receipt_path.parent/name
            if not path.exists():
                assert record.get('storage_encoding')=='gzip'
                data=gzip.decompress((receipt_path.parent/record['stored_path']).read_bytes())
            else:data=path.read_bytes()
            assert len(data)==record['bytes'] and sha(data)==record['sha256'],str(path)
            if len(data)>1000000 and path.exists():
                packed=gzip.compress(data,compresslevel=9,mtime=0)
                target=path.with_name(path.name+'.gz')
                target.write_bytes(packed)
                record.update(storage_encoding='gzip',stored_path=target.name,
                              stored_bytes=len(packed),stored_sha256=sha(packed))
                path.unlink();changed=True
        if changed:receipt_path.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

def main():
    assert not (HERE/'seal.json').exists()
    for name in ['owned-account-work','owned-mir-work','owned-layouts-work']:assert not (HERE/name).exists()
    source=read('source-manifest.json')
    assert len(source['members'])==145 and sha(canonical(source['members']))==source['source_tree_sha256']
    inputs=read('input-bindings.json')
    for member in inputs['authored']:
        data=(HERE/member['path']).read_bytes()
        assert len(data)==member['bytes'] and sha(data)==member['sha256']
    tests=read('account-test-results.json')
    assert tests['actual_tests_per_mode']==11 and tests['negative_compile_controls']==3 and tests['all_expected']
    assert tests['source_bindings'][0]['sha256']==sha((HERE/'host_account.rs').read_bytes())
    inv=read('caller-inventory.json')
    assert inv['role_count']==394 and inv['measured_logical_bytes']==311047 and inv['unmeasured_roles']==0
    assert inv['source_tree_sha256']==source['source_tree_sha256']
    diagnostics=(HERE/'compiler-commands/actual-type-layout-queries/stderr').read_text()
    assert diagnostics.count('error[E0308]')==90
    assert not re.findall(r'error\[E(?!0308)\d+\]',diagnostics)
    # Correct the distinction between diagnostics and unique resolved types.
    inv['actual_type_queries']=90
    inv['distinct_nonunit_actual_type_sizes']=89
    write('caller-inventory.json',inv)
    raw=(HERE/'entry-and-account.mir').read_text()
    functions=[]
    for match in re.finditer(r'^fn .+ \{$',raw,re.M):
        end=raw.index('\n}\n',match.start())+3
        functions.append(raw[match.start():end])
    assert len(functions)==19
    by_phase=defaultdict(lambda:dict(functions=0,roles=0,logical_bytes=0,parameters=0,return_places=0))
    work=[]
    for fn,record in zip(functions,inv['functions'],strict=True):
        assert sha(fn.encode())==record['sha256']
        group=by_phase[record['phase']]
        group['functions']+=1;group['roles']+=record['role_count'];group['logical_bytes']+=record['measured_logical_bytes']
        group['parameters']+=sum(r['kind']=='parameter' for r in record['roles'])
        group['return_places']+=sum(r['kind']=='return-place' for r in record['roles'])
        calls=[line.strip() for line in fn.splitlines() if ' -> [' in line and '=' in line]
        work.append(dict(header=record['header'],phase=record['phase'],
                         MIR_basic_blocks=len(re.findall(r'^    bb\d+',fn,re.M)),
                         MIR_call_terminators=len(calls),calls=calls,
                         MIR_assert_terminators=len(re.findall(r'^\s+assert\(',fn,re.M)),
                         exact_logical_work_price=None,price_status='pending-source-operation-unit-and-all-callee-prices'))
    write('phase-inventory.json',dict(schema=1,source_tree_sha256=source['source_tree_sha256'],
          by_phase=dict(by_phase),functions=work,source_role_union_bytes=311047,
          whole_quote_complete=False,authority_root='pre-existing trusted local parent; no selected root constructor',
          bounded_authored_loops={'checked_components_v1':6,'setup_files_once_v1':5},
          account_or_release_callback_is_guest_controlled=False,
          P0_call_return_token_release_places_preexisting_and_not_child_funded=True,
          P0_exact_logical_work_price=None,P0_price_status='pending-before-account-construction',
          P0_measured_account_header_bytes=104,P0_measured_root_policy_header_bytes=64,
          P0_measured_destroyed_token_header_bytes=16,
          missing_external_intervals={
            'P0':'exact outer parent binding/invocation; source operations, immutable binding/backing, construction/quote/account/call/drop/retirement/release/error root allocation',
            'P1':'exact selected paths/source/build/session/executable/process geometry; setup backing and real loader/original validator work',
            'P2':'actual original validation/product budgets, claims, cancellation shared backing and all argument production',
            'P3':'finally composed common shell before fixed product-store and every refusal/retirement alternative',
            'P4':'finally composed callee/leaf places, requested dynamic storage and exact selected work',
            'P5':'retained original/refusal/output/diagnostic backing, output observations and destruction'},
          MIR_counts_are_work_price_or_OTA_authorization=False))
    snapshot_tools()
    write('attempts/tool-failure.json',dict(schema=1,
          first_layout_attempt='Retained parser wrongly ended array types at their internal semicolon and selected suffix-matching diagnostic functions; compiler refused malformed query source before any layout query.',
          first_layout_compiler_exit=1,source_or_runtime_bypass=False,
          closure_filter_attempt='Assertion selected every base-profile closure, not only the new caller closure; failed before any compiler invocation.',
          closure_filter_compiler_invocations=0,
          repairs='Full-line declarations and exact function-name boundaries; bind only closure types in the selected19-function role set.',
          final_production_compile_pass=True,final_layout_diagnostics=90,final_roles=394,final_unmeasured_roles=0))
    layout=read('layout-source-manifest.json')
    write('compiler-receipt-amendments.json',dict(schema=1,
          actual_layout_query_source_tree_sha256=layout['source_tree_sha256'],
          actual_layout_query_manifest_sha256=sha((HERE/'layout-source-manifest.json').read_bytes()),
          production_source_tree_sha256=source['source_tree_sha256'],
          command_receipt_source_tree_field_is_production_base_for_layout_query=True,
          tool_snapshots_verified_against_at_start_hashes=True,
          metadata_or_layout_source_dispatched=False))
    compress_outputs()
    checks=0
    for path in HERE.rglob('receipt.json'):
        receipt=json.loads(path.read_text())
        if 'output' not in receipt:continue
        for name,record in receipt['output'].items():
            if record.get('storage_encoding')=='gzip':
                packed=(path.parent/record['stored_path']).read_bytes()
                assert len(packed)==record['stored_bytes'] and sha(packed)==record['stored_sha256']
                data=gzip.decompress(packed)
            else:data=(path.parent/name).read_bytes()
            assert len(data)==record['bytes'] and sha(data)==record['sha256'];checks+=1
    write('boundary.json',dict(schema=1,at=datetime.now(timezone.utc).isoformat(),
          status='private-atomic-account-and-real-typed-entry-source-implemented; complete-quote-and-root-policy-pending',
          source_tree_sha256=source['source_tree_sha256'],source_members=145,
          source_is_active_combined145=False,authentic_carrier_required=True,
          new_functions=19,new_roles=394,new_logical_source_object_bytes=311047,
          actual_layout_diagnostics=90,distinct_nonunit_layouts=89,unmeasured_roles=0,
          standalone_account_tests_per_mode=11,test_modes=['debug','optimized'],negative_compile_controls=3,
          account_atomic_both_dimensions=True,work_refunded=False,automatic_Drop_storage_refund=False,
          destroyed_token_uses_actual_account_borrow=True,
          release_only_after_explicit_destroy_returned_to_preexisting_P0=True,
          P0_root_policy_and_complete_quote_reviewed=False,
          selected_parent_account_constructed=False,selected_quote_can_succeed=False,
          fixture_binding_selected=False,genuine_fixture_or_loader_dispatched=False,
          product_limits={'execution_work':1000000000,'combined_bytes':268435456},
          product_limits_changed=False,product_counter_or_leaf_return_refunds_host=False,
          fixed451814442_or_final_composed_source_qualified=False,
          native_UI_capture_device_simulator_emulator_global_process_inventory=False,
          operational_OTA_FieldLog_customer_GA_qualified=False,
          source_independent_acceptance=False,owned_scratch_removed=True,
          logical_source_counts_are_complete_work_or_RSS_bound=False))
    write('audit-results.json',dict(schema=1,producer_checks_passed=True,
          python_version=sys.version,command_output_hashes_reverified=checks,
          current_authored_source_hashes_reverified=True,compiler_tool_snapshots_reverified=True,
          all394_roles_have_actual_measurements=True,superseded_failure_outputs_retained=True,
          account_tests_are_synthetic_only=True,independent_acceptance=False,
          current_native_and_real_entry_checks='pending; paused native scope respected'))
    listing=[dict(path=p.relative_to(HERE).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes()))
             for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='seal.json']
    seal=dict(schema=1,status='frozen-private-source-and-host-only-controls; no-operational-grant',
              member_count=len(listing),member_bytes=sum(m['bytes'] for m in listing),members=listing,
              source_tree_sha256=source['source_tree_sha256'],source_members=145,
              complete_quote_or_root_policy_accepted=False)
    write('seal.json',seal)
    print(json.dumps(dict(seal_sha256=sha((HERE/'seal.json').read_bytes()),
                          members=seal['member_count'],bytes=seal['member_bytes'],
                          source_tree_sha256=source['source_tree_sha256'])))

if __name__=='__main__':main()
