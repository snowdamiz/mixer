"""Finalize scoped findings only after the fresh bounded tests and custody pass."""
import json
from review_custody import HERE, ROOT, PRODUCER, TREE, SEAL, load, need, row, snapshot

def main():
    result = load(HERE / 'test-results.json')
    need((result['methods'], result['failures'], result['errors'], result['adverse_cases_rejected'], result['independent_equalities']) == (7, 0, 0, 1473, 532), 'exact passing independent result')
    commands = {}
    for label in ('fresh-independent-01', 'fresh-independent-02', 'fresh-independent-03'):
        receipt = load(HERE / 'commands' / label / 'receipt.json')
        need(receipt['waited_and_reaped'] and receipt['owned_group_absent'] and receipt['exact_frozen_inputs_before_after_unchanged'] and not receipt['timed_out'], 'closed independent command')
        need(receipt['exit_code'] == (0 if label.endswith('03') else 1), 'retain actual exit')
        commands[label] = {'receipt': row(HERE / 'commands' / label / 'receipt.json'), 'exit_code': receipt['exit_code'],
                           'PID': receipt['owned_PID'], 'PGID': receipt['owned_PGID'], 'reaped': True, 'group_absent': True}
    custody = snapshot()
    review = {
        'schema': 1, 'status': 'recommend-bounded-partial-interface-acceptance',
        'producer_seal_sha256': SEAL, 'source146_tree_sha256': TREE,
        'task_configuration': {'model': 'gpt-6.1-sol', 'reasoning_effort': 'xhigh', 'context': 'fresh bounded independent review'},
        'scope': 'Independent offline R1-R3 source correction and inherited-condition preservation only',
        'recommendation': 'Accept this isolated partial-interface correction under the existing logical source/typed-aggregate/finite-end accounting unit. Ten interfaces remain conditionally closed; range_next and the three inherited frontiers remain partial. All exact residual work and bytes remain mandatory. Root selection is separate.',
        'findings': [
            {'id': 'R1', 'disposition': 'satisfied-by-permitted-positive-partial-frontier',
             'evidence': 'Exact revision num/mod.rs:1450-1454 selects Self=usize and ActualT=u64. uint_macros.rs:2989-2992 writes usize->u64, usize->u64, u64->usize. The full helper entry, cast/intrinsic/destructure/final tuple result/return and every finite end remain mandatory in the range work AND storage frontier.',
             'unknown_layout': 'Full (u64,bool) remains unpriced; no i64 inference, field sum or (usize,bool) substitution. Observed outer (usize,bool) and production closure remain full16/alignment8.'},
            {'id': 'R2', 'disposition': 'satisfied-by-permitted-positive-partial-frontier-and-consumed-known-shell',
             'evidence': 'Exact empty capture retains unit (), both exact function items, intrinsic argument/result/return and finite endings. The selected source runtime()->bool entry, cfg!(miri), unary-not, bool result/return and finite ends remain inside the mandatory range frontier. Compiletime body only is unselected; its function-item argument stays retained. Private compiler implementation remains outside the inherited unit.',
             'known_shell': 'ConstEvalSelectResidual bool is consumed by switchInt; both ub_checks result and false arm are retained. No unused synthetic result or complete runtime-helper closure is claimed.',
             'unknown_layout': 'Both exact callable item layouts remain unpriced; no zero/one or fn-pointer price is substituted.'},
            {'id': 'R3', 'disposition': 'satisfied-by-expanded-existing-five-positive-contains-composites',
             'evidence': 'All five composites explicitly require &Option<usize> receiver auto-borrow, Option::<usize>::is_some(&self), dereference and exact matches expansion match *self { Some(_) => true, _ => false }, all typed operands/results/returns and finite ends. Existing transmute_copy/from_raw_parts preconditions/helpers/slots, source tuple, assert_unchecked and installed memchr_aligned obligations remain mandatory.',
             'actual_lengths': 'Synthetic unequal-length native byte paths exercise per-context actual lengths, including invalid UTF-8 bytes; no decoded string length or selected maximum is substituted.'}
        ],
        'residuals': {'count_per_unit': 30, 'work_and_storage_individually_positive': True,
                      'decomposition': {'digest': 1, 'path': 5, 'contains': 5, 'range': 19},
                      'range_contexts': 'identity headers0..12 (13) plus path headers0..5 (6), with exact source/type/compiler/target/digest and immutable invocation context',
                      'final_None_headers': [['identity', 12, 12], ['path', 5, 5]],
                      'zero_default_alias_move_inactive_helper_None_refusal_unwind_credit': False},
        'known_shell_only': {'fixed': 187034, 'B': 6867, 'B2': 160, 'source_place_bytes': 19029,
                             'native_ABI_field_bytes': 9882, 'all15_phase_addition': 28911,
                             'provisional_P0_excluding_mandatory_positive_residual_storage': 330644,
                             'per_range_shell': 2246, 'range_cap': 19, 'range_request_shell': 42674,
                             'range_source_places': 3819, 'range_native_ABI_fields': 1824,
                             'complete_price_decrease_or_refund_claim': False},
        'preservation': {'provider': '276580+1324B;9696slots', 'callback': '7675+120B full body;cap5',
                         'inherited_work': 'all10 including unselected67424*L_str', 'upstream_work_terms': 2,
                         'backing': 'all12 full preimages+5 native Path+5 separate retained bodies; B=max of22 actual bodies',
                         'original_binding': 1168, 'child_components': 6, 'phases': 15,
                         'diagnostics_root_backing_Error_native_destructor_obligations': 'mandatory',
                         'normal_release': 'actual original payload/carrier destruction returning existing Some token remains required; never observed or qualified by this review'},
        'fresh_checks': result, 'command_receipts': commands,
        'custody': {'producer_members': 219, 'producer_bytes': 13305313,
                    'producer_files_0444': 220, 'producer_directories_0555': 22,
                    'inherited_priced_inputs': 1245, 'inherited_frozen_packets': 15, 'complete_frozen_packets_checked': 18,
                    'full_before_after_rehash_each_command': True, 'excluded_cache': custody['excluded_cache_metadata_only'],
                    'query_named_or_cache_imported_executed_mutated': False, 'mutable_PLAN_or_HEAD_priced': False},
        'history': {'producer_tuple_vs_JSON_array_audit_failure': 'preserved failed, not replayed or relabelled',
                    'root_read_only_mode_preflight_failure': 'preserved failed; initial byte loop did not complete and no release was written',
                    'root_after_mode_hardening_release': 'separate receipt verifies complete bytes and read-only modes',
                    'own_setup_failures': 'two retained with source preimages/output/receipt and reaped absent groups; final seven methods pass'},
        'root_price_or_funding_or_implementation_selected': False, 'compiler_authorized_or_invoked': False,
        'actual_acquisition_authenticated_owner_backing_and_L_str_selection': 'pending',
        'linked_executable_build_session_caller_proof': 'pending', 'native_destructor_runtime_qualification': 'pending',
        'native_UI_capture_simulator_emulator_phones': 'not run under current pause',
        'published_package_FieldLog_store_customer_operational_OTA_GA': 'pending',
        'canonical_product_or_other_lane_edits_Git_or_delivery': False
    }
    (HERE / 'review.json').write_text(json.dumps(review, sort_keys=True, indent=2) + '\n')
    (HERE / 'cleanup.json').write_text(json.dumps({'schema': 1, 'commands': commands, 'all_started_children_reaped_and_own_groups_absent': True,
        'timeout_kills_needed': 0, 'scratch_or_native_runtime_or_capture_processes_started': False, 'global_process_inventory_performed': False,
        'other_projects_processes_or_data_touched': False, 'finalization_child_cleanup_record': 'commands/finalization-01/receipt.json, completed by outer runner before seal'}, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'status': review['status'], 'review': row(HERE / 'review.json'), 'fresh_methods': 7, 'adverse_cases': 1473, 'independent_equalities': 532}))

if __name__ == '__main__':
    main()
