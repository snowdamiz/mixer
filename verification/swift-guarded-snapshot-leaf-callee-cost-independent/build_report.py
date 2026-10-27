#!/usr/bin/env python3
"""Pure report materialization from the reviewed immutable inputs."""
import copy, json, sys
from pathlib import Path
sys.dont_write_bytecode=True
import audit
H=Path(__file__).resolve().parent;R=H.parents[1];V=R/'verification';P=audit.PRODUCER
def encoded(value):return json.dumps(value,sort_keys=True,indent=2).encode()+b'\n'

def render():
    l=audit.load(P/'callee-ledger.json');c=audit.load(P/'cost-interface.json')
    roster=audit.load(P/'native-query-roster/roster.json');mir=audit.bodies((P/'selected.mir').read_text())
    inputs=audit.rehash_packet(P,audit.SEAL)
    native=audit.native_observations(roster)
    capture=audit.actual_core_capture_binding(l,mir)
    callaudit=audit.check_call_edges(l,mir);operation_count=audit.check_operation_coverage(l,mir)
    compiler_inputs=[dict(path=p,sha256=audit.sha((R/p).read_bytes())) for p in [
        'verification/swift-guarded-snapshot-source146-callee-storage-layouts/compiler-receipt.json',
        'verification/swift-guarded-snapshot-source146-closure-layouts/compiler-receipt.json']]
    compiler_input_bytes=audit.canon(compiler_inputs)
    capture_correction=dict(schema=1,source_tree_sha256=audit.TREE,
        finding='F1-frozen-native-query-index8-pretty-field-list-is-incomplete-and-mislabelled',
        frozen_roster_sha256=audit.sha((P/'native-query-roster/roster.json').read_bytes()),
        frozen_index=8,frozen_creation_capture_count=7,actual_capture_count=8,
        missing_local='_36',wrong_labels={'_33':dict(frozen='validation',actual='source'),
            '_34':dict(frozen='source',actual='validation__source_bytes'),
            '_35':dict(frozen='metadata',actual='validation__metadata_reserved')},
        actual=capture,
        disposition='frozen candidate preserved; this exact binding supersedes capture metadata for native substitution only',
        original_closure_size_observed=64,original_closure_alignment_observed=8,
        layout_authority='released exact original monomorphized compiler diagnostic, not a capture proxy',
        original_conditional_cost_graph_changed=False,operational_grant=False)
    native_receipt=dict(schema=1,source_tree_sha256=audit.TREE,
        native_query_roster_sha256=c['native_query_roster_sha256'],
        capture_roster_correction_sha256=audit.sha(encoded(capture_correction)),
        target='aarch64-apple-darwin',scope='compiler-observed-source146-size-and-alignment',
        product_executed=False,compiler_receipt_sha256=audit.sha(compiler_input_bytes),
        compiler_receipt_kind='canonical compiler-inputs.json containing both root-released compiler receipts',
        observations=native,operational_grant=False)
    native_receipt_bytes=encoded(native_receipt);sizes={r['key']:r['size'] for r in native}
    bound=copy.deepcopy(c)
    bound.update(status='independent-native-complete-conditional-callee-interface',
        native_binding_receipt_sha256=audit.sha(native_receipt_bytes),
        frozen_conditional_interface_sha256=audit.sha((P/'cost-interface.json').read_bytes()),
        capture_roster_correction_sha256=audit.sha(encoded(capture_correction)),
        remaining_native_terms=0,complete_host_quote=False,operational_grant=False)
    for row in bound['exports'].values():
        row['fixed']+=sum(n*sizes[k] for k,n in row['native'].items());row['native']={}
    leaf=audit.load(V/'swift-guarded-snapshot-leaf-shell-cost/cost-interface.json')
    leafcuts=leaf['required_nonzero_callee_drop_and_backing_cuts']
    composition={}
    for key,count in leafcuts.items():
        composition[key]=dict(leaf_occurrences=count,
            disposition='conditional-callee-expression' if key in bound['exports'] else 'preserved-required-leaf-payload-or-backing-import')
        if key in bound['exports']:composition[key]['per_one']=bound['exports'][key]
    sourceaudit=dict(schema=1,source_tree_sha256=audit.TREE,source_members=146,
        authored_MIR_bodies=38,actual_written_operations=operation_count,
        actual_callsite_count=callaudit['callsites'],callback_callsite_count=callaudit['callback_callsites'],
        nodes=85,exports=21,accepted_source144_rows=32,
        all_actual_MIR_operations_and_authored_standard_callback_policy_drop_edges_covered=True,
        core_store=dict(block='bb25',precheck='budget/deadline/check/fixed-policy comparison/refusal',
            after='counter store; owner update; five reservations; final check',
            prepaid='whole outer core frame and shared return/failure/unwind scaffolding conservatively paid before',
            shared_callback_exit_blocks=['bb3','bb69'],ordinary_zero_policy_allowed=False),
        loops=dict(cache=dict(disjoint_source_loops=2,iterations=64,block_visits_upper=65,
                route='fresh closed selected construction; complete budget and ceiling comparison; no intervening mutation/execution/pin/observation'),
            wasi=dict(disjoint_source_loops=2,iterations=4,block_visits_upper=5,
                route='actual four buffer ticket array and four capacity array')),
        selected_policy='actual SnapshotAdoptionV1 impl at control.rs1909, not stale trait/OriginalAdoption capture',
        source144_transfer='32 individual exact body/own-part/child multiplicity bindings; one3unit newly derived foundation getter; one named constructor region only at actual consuming call',
        constructor=dict(original_header_rows_reachable=True,
            snapshot_emission='unconditional WorkAuditPending refuses before writer/encoder/transfer-array initialization or changed commit-storage call',
            phase_return_carriers='preparation and original_return taken before complete; semantic None tuples have no owning resource',
            actual_internal_payload_imports=l['constructor_applicability']['typed_internal_destructor_cuts']),
        drop_order='actual AdoptionBody payload drop precedes both refund calls; logical drop events never pay actual destructor bodies',
        private_standard_boundary='closed primitive and callback source event once; private implementation, atomic retries and callback reevaluation, unwind/lowering/backing remain required external allowances',
        product451814442_reused_as_aggregate=False,product_work_discount=0,
        operational_grant=False,actual_product_execution=False)
    latest=audit.load(H/'attempts/04/receipt.json')
    findings=[dict(id='F1',severity='required-capture-binding-amendment',
        description='Index8 printed capture plan has seven fields but original compiler environment has eight; source/validation roles mislabelled and metadata ticket omitted.',
        correction_file='capture-roster-correction.json',
        original_frozen_evidence_preserved=True,
        disposition='Corrected through independent original projection/local binding and direct64/8 compiler observation. Do not use original seven-capture roster as role evidence.'),
        dict(id='F2',severity='observed-zero-size-handling-verified',
        description='Original719atomic callback has actual0/1 layout. Qualified receipt substitution permits zero and removes only that native occurrence term; synthetic/missing zeros fail closed.',
        disposition='No producer code correction needed; independently exercised both synthetic receipt-format and actual compiler-bound paths.')]
    report=dict(schema=1,status='independent-reviewed-bounded-callee-interface-with-native-and-capture-amendment',
        reviewed_at=latest['finished_at'],source_tree_sha256=audit.TREE,producer=inputs,
        producer_root_release_sha256=audit.RELEASE,
        reviewed_dimensions=dict(authored_MIR_bodies=38,written_operations=operation_count,
            actual_callsite_count=callaudit['callsites'],closed_callback_callsites=callaudit['callback_callsites'],
            graph_nodes=85,exports=21,leaf_cuts=33,accepted_specific_source144_rows=32,
            retained_full_type_size_records=3072,initial_native_missing=100,earlier_exact_resolved=87,
            newly_bound_named=8,newly_bound_original_closures=5,remaining_native_terms=0,
            typed_payload_interfaces=19,unsized_interfaces=['str','[Option<ReservationTicket>]'],private_export_allowances=21),
        tests=dict(independent_methods=17,required_input_negative_cases=616,failures=0,errors=0,
            final_attempt='attempts/04',producer_replay_methods=20,producer_replay_exit_code=0,
            negative_controls=['operation/callback/payload omission','recursive graph','reduced loop caps',
                'wrong/missing capture metadata','wrong exact span/qualified layout expression',
                'wrong receipt selection and omitted ZST key','all required native/payload/unsized/private inputs',
                'checked independent export flattening and actual native zero substitution']),
        findings=findings,
        independent_conclusion='Accept the source-specific conditional callee cost graph and actual13native substitutions only together with capture-roster-correction.json. All resource payload, finite str/array backing, and private primitive/native/retry/unwind allowances remain mandatory. No whole-host price or permission is derived.',
        root_selection_required_for_consumption=True,whole_host_quote_accepted=False,
        P0_and_six_child_host_funding_accepted=False,product451814442_changed=False,
        physical_native_simulator_emulator_UI_capture_checks='paused and pending; no new instance or capture started',
        native_or_GA_qualified=False,operational_grant=False,
        reviewer_compiler_invoked=False,reviewer_product_runtime=False,
        failures_preserved=dict(attempts=['01','02','03'],
            cause='review harness assumptions corrected: duplicate unqualified whole-MIR headers, impl generic name/forwarding parsing, selected associated-type drop mapping, and target read from explicit compiler argv when no binding.target exists',
            final_failed_checks=0,earlier_output_and_script_hashes_preserved=True,
            complete_reviewer_source_snapshots_from_attempt='03'),
        cleanup=dict(owned_native_or_capture_processes_started=0,owned_product_or_compiler_processes_started=0,
            pure_python_children_waited=True,global_process_inventory=False,
            other_projects_processes_or_data_modified=False,canonical_source_or_root_metadata_or_git_modified=False))
    cleanup=dict(schema=1,completed=True,owned_persistent_processes_started=0,
        product_or_compiler_or_native_or_capture_processes_started=0,
        pure_python_children_waited=True,owned_compiler_or_native_scratch_created=False,
        global_process_inventory=False,other_projects_processes_preserved=True)
    return {'compiler-inputs.json':compiler_input_bytes,'capture-roster-correction.json':encoded(capture_correction),
        'native-binding-receipt.json':native_receipt_bytes,'bound-cost-interface.json':encoded(bound),
        'call-edge-audit.json':encoded(callaudit),'source-audit.json':encoded(sourceaudit),
        'leaf-cut-composition.json':encoded(dict(schema=1,source_tree_sha256=audit.TREE,cuts=composition,
            complete_host_quote=False,operational_grant=False)),
        'review.json':encoded(report),'cleanup.json':encoded(cleanup)}

if __name__=='__main__':
    if (H/'seal.json').exists():raise SystemExit('frozen reviewer packet: use verify.py')
    for name,raw in render().items():(H/name).write_bytes(raw)
    print(json.dumps(dict(status='independent-callee-review-materialized',native_terms_remaining=0,
        payload_terms_remaining=19,findings_preserved=2,operational_grant=False)))
