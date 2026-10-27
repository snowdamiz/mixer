#!/usr/bin/env python3
"""Freeze the compact source/host boundary packet; no compiler/runtime work."""
import datetime
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def write(name,data):
    (HERE/name).write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')


def members():
    return [dict(path=p.relative_to(HERE).as_posix(),bytes=p.stat().st_size,
                 sha256=sha(p.read_bytes())) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='seal.json']


def main():
    assert not (HERE/'seal.json').exists()
    assert not (HERE/'owned-work').exists()
    inv=json.loads((HERE/'driver-inventory.json').read_text())
    model=json.loads((HERE/'ordering-results.json').read_text())
    audit=json.loads((HERE/'audit-results.json').read_text())
    pure=json.loads((HERE/'pure-command-receipts.json').read_text())
    assert len(pure['commands'])==4 and all(c['exit_code']==0 for c in pure['commands'])
    boundary=dict(schema=1,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status='frozen compile-only leaf inventory and concrete trusted-local host recipe; operational authority absent',
        selected_scope='one fixture; private production-library custom cfg; no WASI attachment; no runtime dispatch',
        entry_boundary='Pre-existing controlling trusted host account must reserve both complete storage/work bundle dimensions before File setup/loading, argument creation, carrier conversion/control initialization and every failed admission.',
        compiled_base_tree_sha256='7e3e861ca65d8c6359623443d6a7810b878c1029494a0ae557307d35ed43484b',
        compiled_leaf_source_tree_sha256=inv['source_tree_sha256'],
        compiled_leaf_source_sha256=inv['scaffold_sha256'],
        compiler_role_count=inv['role_count'],logical_leaf_source_bytes=inv['logical_source_object_union_bytes'],
        compiler_parameter_count=7,logical_parameter_bytes=inv['parameter_source_object_bytes'],
        actual_type_layout_queries=len(inv['actual_type_sizes']),
        old_H_or_163_harness_roles_transferred=False,
        cfg_test_specific_H_and_instrumentation_excluded_from_this_build=True,
        new_tool_or_driver_added_to_historical_host11=False,
        loader_and_leaf_partial_logical_union=152_533_634,
        partial_union_is_grant_or_complete_inventory=False,
        ingress_plus_provisional_dispatch_subenvelope=34_885,
        provisional_fixed_work_counter=451_814_442,
        provisional_work_implementation_in_compiled_leaf_base=False,
        fixed_counter_store_pays_earlier_shell=False,
        host_work_refund_or_product_counter_transfer_selected=False,
        product_limits=dict(execution_work=1_000_000_000,combined_bytes=268_435_456),
        pure_protocol_controls=model['controls_passed'],packet_audit_controls=audit['controls_passed'],
        input_bindings_sha256=sha((HERE/'input-bindings.json').read_bytes()),
        source_manifest_sha256=sha((HERE/'source-manifest.json').read_bytes()),
        source145_or_final_composed_layout_rebinding_qualified=False,
        work_admission_common_role_review_settled=False,
        trusted_host_account_or_enforcing_launcher_implemented=False,
        complete_external_host_work_or_storage_quote_qualified=False,
        whole_source_or_operational_funding_qualified=False,
        future_caller_access_runtime_selected=False,
        actual_loaded_carrier_runtime_dispatched=False,
        loader_guest_VM_cache_scope_construct_writer_executed=False,
        production_native_UI_capture_simulator_emulator_GA_qualified=False,
        owned_scratch_removed=True,global_process_inventory=False,
        required_next=[
          'Author/freeze exact one-fixture enforcing trusted host account and caller entry, separate from historical host11.',
          'Price exact whole launcher/setup/arguments/return/custody/reservation bookkeeping plus loader work and all P0..P5 storage/failure lifetimes before host reservation.',
          'Rebind actual final composition/source member count/descriptor/compiler/privacy/consume/borrow and leaf/callee layouts, retaining fixed product limits.',
          'Independently review real grant-before-setup/load/shell and every terminal failure before selecting any actual loaded-carrier runtime.' ])
    write('boundary.json',boundary)
    authored=['driver.inc.rs','run_inventory.py','finalize_inventory.py','ordering_model.py','verify_inputs.py','audit_packet.py','run_pure_checks.py','freeze.py']
    write('tool-test-manifest.json',dict(schema=1,scope='New authored include/utilities; separate from historical host11; not loader authority',
        members=[dict(path=n,bytes=(HERE/n).stat().st_size,sha256=sha((HERE/n).read_bytes())) for n in authored],
        actual_compiler_driver_snapshot='commands/compiler-driver-at-start.py',
        no_product_runtime_tests=True))
    listing=members()
    write('seal.json',dict(schema=1,status=boundary['status'],
        source_tree_sha256=inv['source_tree_sha256'],member_count=len(listing),
        member_bytes=sum(m['bytes'] for m in listing),members_tree_sha256=sha(canonical(listing)),members=listing))
    print(json.dumps(dict(member_count=len(listing),member_bytes=sum(m['bytes'] for m in listing),
        seal_sha256=sha((HERE/'seal.json').read_bytes()),boundary_sha256=sha((HERE/'boundary.json').read_bytes()))))


if __name__=='__main__':
    main()
