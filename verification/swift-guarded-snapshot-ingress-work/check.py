#!/usr/bin/env python3
"""Finite logical-source ledger only. Does not compile, invoke VM or authorize OTA."""
from pathlib import Path
import copy
import hashlib
import json
import platform
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
FROZEN = HERE.parent / 'swift-guarded-snapshot-scope-authority-correction'
VM = FROZEN / 'source/vm'
EXPECTED_TREE = '575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896'
EXPECTED_SEAL = '351caf4860621989119d16b474dbb53c496a688c4efb0cbb3abb918825b79e6c'
C = 'src/experimental_swift_reactor/control.rs'
L = 'src/experimental_swift_reactor/retained_profile_loader_v1.rs'
A = 'src/experimental_wasi/accounted.rs'
W = 'src/experimental_wasi/mod.rs'
S = 'src/experimental/swift.rs'
E = 'src/execute.rs'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def emit(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def record(path):
    data = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(data), 'sha256': sha(data)}

def extract(path, marker, occurrence=0):
    """Bind an exact source definition, ignoring comment/string braces; no authority inference."""
    data = (VM / path).read_bytes()
    starts = []; offset = 0
    while True:
        offset = data.find(marker.encode(), offset)
        if offset < 0:
            break
        starts.append(offset); offset += len(marker)
    start = starts[occurrence]
    opening = data.index(b'{', start)
    depth = 0; state = 'code'; block = 0; index = opening
    while index < len(data):
        char = data[index:index+1]; pair = data[index:index+2]
        if state == 'line':
            if char == b'\n': state = 'code'
        elif state == 'string':
            if char == b'\\': index += 1
            elif char == b'"': state = 'code'
        elif state == 'block':
            if pair == b'/*': block += 1; index += 1
            elif pair == b'*/':
                block -= 1; index += 1
                if block == 0: state = 'code'
        elif pair == b'//': state = 'line'; index += 1
        elif pair == b'/*': state = 'block'; block = 1; index += 1
        elif char == b'"': state = 'string'
        elif char == b'{': depth += 1
        elif char == b'}':
            depth -= 1
            if depth == 0:
                body = data[start:index+1]
                return {'path': path, 'marker': marker, 'occurrence': occurrence,
                        'line': data[:start].count(b'\n')+1, 'bytes': len(body),
                        'sha256': sha(body), 'source': body.decode()}
        index += 1
    raise AssertionError(('unclosed definition', path, marker))

def calculate():
    manifest = json.loads((FROZEN / 'source-manifest.json').read_text())
    members = [{'path': p.relative_to(VM).as_posix(), 'bytes': p.stat().st_size,
                'sha256': sha(p.read_bytes())}
               for p in sorted(VM.rglob('*')) if p.is_file()]
    assert members == manifest['members'] and len(members) == 144
    assert sha(json.dumps(members, sort_keys=True, separators=(',', ':')).encode()) == EXPECTED_TREE
    assert sha((FROZEN / 'seal.json').read_bytes()) == EXPECTED_SEAL
    old = json.loads((HERE.parent/'swift-guarded-snapshot-writer-work-correction/corrected-ledger.json').read_text())
    inherited = {r['name']: r for r in old['rows']}
    rows = {}; bindings = {}; inherited_rows = {}

    def bind(path, marker, occurrence=0):
        key = path+'::'+marker+'#'+str(occurrence)
        if key not in bindings:
            bindings[key] = extract(path, marker, occurrence)
        return key

    def row(name, path, marker, parts, calls=None, occurrence=0, note='', loops=None):
        assert name not in rows
        rows[name] = {'binding': bind(path, marker, occurrence), 'parts': parts,
                      'calls': calls or {}, 'note': note, 'loops': loops or []}

    def reuse(name, old_name, path, marker, occurrence=0):
        original = inherited[old_name]
        assert sum(original['parts'].values()) == original['credits']
        inherited_rows[name] = copy.deepcopy(original)
        row(name, path, marker, copy.deepcopy(original['parts']), occurrence=occurrence,
            note='Exact previously priced row rebound to this frozen body; dependencies, when any, are explicit below.')

    # Existing convention and exact small rows. Their old markers can include a
    # trailing newline; the separately bound body here intentionally omits it.
    reuse('proof', 'AdoptionBody.proof', L, 'pub(super) fn proof(&self)')
    reuse('validation_usage', 'SwiftValidationUsage_getter', S, 'pub fn usage(&self) -> SwiftValidationUsage')
    reuse('cancelled', 'Cancellation.is_cancelled', E, 'pub fn is_cancelled(&self)')
    reuse('backing_layout', 'Cancellation.requested_backing_layout', E, 'pub(crate) fn requested_backing_layout()')
    reuse('category', 'SwiftReservations.category', C, 'fn category(&self,')
    # category_mut has the same constant seven-arm reference selection.
    row('category_mut', C, 'fn category_mut(&mut self,',
        {'enter_return': 2, 'enum_match': 1, 'selected_reference': 1})
    row('foundation', C, 'pub(crate) fn foundation_construction_bytes()',
        {'enter_return': 2, 'precomputed_Option_fetch': 1},
        note='The 13-term FOUNDATION_CONSTRUCTION_BYTES initializer is const evaluation, not runtime work.')
    reuse('snapshot_foundation_callback', 'SnapshotAdoption.foundation_added_bookkeeping',
          C, 'fn foundation()->Option<usize>{snapshot_scope_candidate_foundation_v1()')
    # Expand this inherited19 into its actual two bodies so the replacement
    # interface can name the changed helper without repricing the callback.
    rows['snapshot_foundation_callback']['parts'] = {'callback_enter_return': 2}
    rows['snapshot_foundation_callback']['calls'] = {'snapshot_foundation': 1}
    row('snapshot_foundation', C, 'fn snapshot_scope_candidate_foundation_v1()',
        {'enter_return': 2, 'original_question': 2, 'three_checked_add': 3,
         'two_propagating_questions': 4, 'two_sizeof_events': 2, 'cache_constant_fetch': 1},
        {'foundation': 1})
    reuse('snapshot_adoption_wrapper', 'RuntimeControl.adopt_snapshot_body_v1_added_bookkeeping',
          C, 'pub(super) fn adopt_snapshot_body_v1(')
    rows['snapshot_adoption_wrapper']['parts'].pop('selected_body_forward_helper')
    rows['snapshot_adoption_wrapper']['calls'] = {'selected_body_unwrap': 1, 'adopt_core': 1}
    reuse('snapshot_retire', 'SnapshotAdoption.retire_tickets_added_bookkeeping',
          C, 'fn retire_tickets(control:&mut RuntimeControl,source:Option<ReservationTicket>,metadata:Option<ReservationTicket>)->Self::Retirement')
    rows['snapshot_retire']['calls'] = {'refund': 2}
    reuse('snapshot_failure', 'SnapshotAdoption.failure_added_bookkeeping',
          C, 'fn failure(primary:SwiftRunFailure,retirement:Self::Retirement)->Self::Failure')

    # Source-only scalar helpers and explicit aggregate Copy widths. Named
    # constructor stores are retained in addition to Copy transfers: deliberate
    # upper sums, never optimizer discounts. Bound local arguments are free.
    row('cursor', C, 'pub(crate) const fn adoption()',
        {'enter_return': 2, 'three_output_fields': 3})
    row('fault', C, 'pub(crate) fn new(kind: SwiftRunFailureKind,',
        {'enter_return': 2, 'eight_output_fields': 8})
    row('fault_limit', C, 'fn limit(mut self,',
        {'enter_return': 2, 'Some_resource_carrier': 1, 'three_field_stores': 3})
    row('micros', C, 'fn micros(duration:',
        {'enter_return': 2, 'Duration_as_micros_event': 1, 'try_from_event': 1, 'unwrap_or_event': 1})
    row('budget_default', C, 'fn default() -> Self',
        {'enter_return': 2, 'seventeen_output_fields': 17, 'six_literal_MIB_multiplications_upper': 6},
        note='Each explicit output slot and each written MIB multiplication is retained, without optimizer discounts.')
    row('reservations_default', C, 'pub struct SwiftReservations',
        {'derive_enter_return': 2, 'eighteen_default_leaf_stores': 18,
         'eight_nested_reservation_usage_derive_boundaries': 16})
    row('live_default', C, 'pub struct SwiftLiveUsage',
        {'derive_enter_return': 2, 'twelve_default_leaf_stores': 12,
         'six_nested_reservation_usage_derive_boundaries': 12})
    row('usage', C, 'pub(crate) fn usage(&self, wasi:',
        {'enter_return': 2, 'clock_event_and_binding': 2,
         'forty_nine_borrowed_leaf_fetch_store_pairs': 98,
         'sixty_five_output_slots_upper': 65,
         'two_clock_duration_events_and_receiver_fetches': 4},
        {'micros': 2},
        note='49 borrowed leaves=18 reservations+12 live+5 counters+2 cleanup+1 deadline_ms+1 origin+10 validation. The additional65 output slots deliberately upper-sum output construction with copies; no WASI payload scan.')
    row('fail', C, 'pub(crate) fn fail(',
        {'enter_return': 2, 'first_failure_fetch_inspect': 2,
         'Existing_borrowed_Copy_151_leaves': 302,
         'diagnostic_fields_twenty_leaf_fetch_store_pairs_upper': 40,
         'usage_binding': 1, 'after_cleanup_None': 1, 'fourteen_output_fields': 14,
         'failure_binding': 1, 'latch_Copy_151_leaves_upper': 302,
         'latch_Some': 1, 'return_Copy_151_leaves_upper': 302}, {'usage': 1},
        note='Existing and fresh branches are upper-summed. Two local Copy allowances are conservative even though bound local operands/owned moves need no deep copy under the inherited convention.')
    row('check_with_wasi', C, 'pub(crate) fn check_with_wasi(',
        {'enter_return': 2, 'first_failure_fetch_inspect': 2,
         'Existing_Copy_151_leaves': 302, 'cancellation_receiver': 1,
         'cancellation_decision': 1, 'clock_event': 1,
         'deadline_fetch_compare_decision': 3, 'two_error_carriers': 2, 'healthy_Ok': 1},
        {'cancelled': 1, 'fault': 1, 'fail': 1},
        note='At most one Cancelled/Deadline fault invokes fail; take the branch maximum1. The separate Existing Copy is an upper sum over the early existing arm.')
    row('check', C, 'pub(crate) fn check(&mut self, cursor:',
        {'enter_return': 2, 'None_argument': 1}, {'check_with_wasi': 1})
    row('check_budget', C, 'fn check_budget(',
        {'enter_return': 2, 'default_binding': 1,
         'seventeen_array_tuple_slots': 17,
         'thirty_four_budget_field_fetches': 34,
         'fifty_one_tuple_field_stores': 51,
         'seventeen_resources_and_four_reservation_payloads': 21,
         'loop_setup_termination': 2,
         'seventeen_iterations_tuple_advance_bind_compare_decide': 17*5,
         'failure_and_success_carriers': 2},
        {'budget_default': 1, 'fault': 1, 'fault_limit': 1, 'fail': 1},
        loops=[{'source': 'for (resource, attempted, limit) in fields', 'max_iterations': 17,
                'per_iteration': {'advance_and_tuple_bind': 3, 'comparison': 1, 'decision': 1},
                'terminal_fail_calls_max': 1}])
    row('category_limit', C, 'fn category_limit(',
        {'enter_return': 2, 'enum_match': 1, 'selected_budget_field_fetch': 1})
    row('preflight', C, 'fn preflight_bytes(',
        {'enter_return': 2,
         'category_current_fetch_checked_add_binding': 3,
         'limit_binding': 1,
         'two_Option_predicate_calls_inspects_comparisons_branches_upper': 16,
         'retained_kind_match_and_output_binding': 3,
         'combined_current_fetch_checked_add_binding': 3,
         'budget_combined_two_fetches': 2,
         'map_or_event_callback_enter_return_cast_upper': 5,
         'failure_and_success_carriers_tuple_slots': 5,
         'two_unwrap_events': 2},
        {'category': 1, 'category_limit': 1, 'fault': 1, 'fault_limit': 1, 'fail': 1},
        note='Two terminal error alternatives select at most one fault+limit+fail. is_none_or closed predicates are priced once each; std internals excluded.')
    rows['preflight']['parts']['reservations_category_receiver_fetch'] = 1
    row('commit', C, 'fn commit_bytes(',
        {'enter_return': 2, 'usage_binding': 1, 'current_stores': 2,
         'two_peak_fetches_two_max_events_two_stores': 6}, {'category_mut': 1})
    rows['commit']['parts']['reservations_category_mut_receiver_fetch'] = 1
    row('admit_with_wasi', C, 'pub(crate) fn admit_with_wasi(',
        {'enter_return': 2, 'two_question_inspect_propagations': 4,
         'live_ticket_fetch_compare_decision': 3,
         'attempted_fetch_cast_add_and_inventory_cast': 4,
         'two_tuple_bindings': 2,
         'live_increment_fetch_add_store': 3,
         'peak_fetch_current_fetch_max_store': 4,
         'ticket_owner_fetch_three_slots_and_Ok': 5, 'error_carrier': 1},
        {'check_with_wasi': 1, 'fault': 1, 'fault_limit': 1, 'fail': 1, 'preflight': 1, 'commit': 1})
    row('admit', C, 'pub(crate) fn admit(',
        {'enter_return': 2, 'None_argument': 1}, {'admit_with_wasi': 1})
    row('cleanup_fault', C, 'fn cleanup_fault_with_wasi(',
        {'enter_return': 2, 'invariant_receiver_fetch_get_or_insert_event': 2,
         'three_cursor_fields': 3}, {'fault': 1, 'fail': 1})
    row('refund_with_wasi', C, 'fn refund_with_wasi(',
        {'enter_return': 2, 'owner_fields_comparisons_or_decision': 7,
         'category_current_ticket_bytes_fetch_checked_sub_binding': 4,
         'combined_current_ticket_bytes_fetch_checked_sub_binding': 4,
         'live_count_fetch_checked_sub_binding': 3,
         'three_Option_pattern_inspections_bindings_and_tuple_slot_upper': 10,
         'two_ticket_category_fetches': 2, 'two_reservations_receivers': 2,
         'three_current_stores': 3,
         'two_error_and_one_success_carriers': 3},
        {'category': 1, 'category_mut': 1, 'cleanup_fault': 1},
        note='Owner and underflow branches select at most one cleanup_fault. No retry, admission, work debit or ledger repair.')
    row('refund', C, 'fn refund(&mut self,',
        {'enter_return': 2, 'None_argument': 1}, {'refund_with_wasi': 1})
    row('finish_owned_cleanup', C, 'pub(crate) fn finish_owned_cleanup(',
        {'enter_return': 2, 'started_deadline_fetch_bindings': 4, 'usage_binding': 1,
         'three_Option_take_receiver_events_array_stores': 9,
         'iterator_flatten_logical_events': 2, 'loop_setup_termination': 2,
         'three_iterations_advance_bind': 6,
         'three_owner_guard_fetch_compare_or_decisions': 21,
         'three_owner_invariant_insert_and_continue_upper': 9,
         'three_construction_category_tag_fetch_compare': 9,
         'three_construction_bytes_fetch_Some_compare_and_decisions_upper': 12,
         'three_construction_invariant_insert_and_continue_upper': 9,
         'three_category_current_ticket_bytes_checked_sub_bindings': 12,
         'three_combined_current_ticket_bytes_checked_sub_bindings': 12,
         'three_live_count_fetch_checked_sub_bindings': 9,
         'three_Option_tuple_inspect_bind_decision_upper': 30,
         'six_ticket_category_fetches': 6, 'six_reservations_receiver_fetches': 6,
         'nine_success_current_stores': 9,
         'three_underflow_insert_upper': 6,
         'control_drop_event': 1, 'clock_event_binding': 2,
         'two_duration_events_two_stores': 4},
        {'usage': 1, 'foundation': 3, 'category': 3, 'category_mut': 3, 'micros': 2},
        loops=[{'source': 'for ticket in [control_header.take(),cancellation_backing.take(),construction.take()].into_iter().flatten()',
                'max_iterations': 3, 'reason': 'exact three-element inline array; flatten cannot add elements',
                'foundation_calls_max': 3}],
        note='Three foundation checks deliberately upper-bound the single Construction ticket. Owner, bound and underflow branches are upper-summed; control/private std destruction is one logical drop event.')

    # Selected ingress. No loader file reads, validation/metadata construction,
    # row writing or constructor/cache cleanup are charged a second time.
    row('selected_into_body', L, 'fn into_adoption_body_v1(self)->AdoptionBodyV1',
        {'enter_return': 2, 'proof_provenance_pattern_bindings': 2,
         'proof_selected_fields': 2, 'Some_provenance': 1}, occurrence=1)
    row('selected_body_unwrap', L, 'pub(super) fn into_adoption_body_v1(self)->AdoptionBodyV1',
        {'enter_return': 2, 'tuple_projection': 1})
    row('selected_into_scope', L, 'pub(super) fn into_snapshot_scope_v1(',
        {'enter_return': 2, 'selected_tuple_slot': 1, 'selected_body_binding': 1},
        {'selected_into_body': 1, 'snapshot_adoption_wrapper': 1})
    row('adopt_core', C, 'fn adopt_body_core_v1<',
        {'enter_return': 2, 'validation_binding': 1,
         'twenty_runtime_control_field_stores': 20,
         'cursor_binding': 1, 'two_None_ticket_initializers_and_bindings': 4,
         'closed_closure_enter_return_result_binding': 3,
         'ten_propagating_questions_upper': 20,
         'deadline_budget_fetch_duration_checked_add_Option_inspect_output_store': 6,
         'owner_atomic_try_update_logical_event': 1,
         'closed_owner_callback_enter_return_checked_add': 3,
         'owner_map_err_inspect_carrier_and_store': 4,
         'two_validation_field_fetches': 2,
         'five_Some_ticket_stores_upper': 10,
         'control_sizeof_backing_size_events': 2,
         'foundation_Option_inspect_output_and_binding': 3,
         'three_error_closure_enter_return_error_None_slots_upper': 9,
         'result_failure_match_pattern': 2,
         'body_drop_event': 1, 'retirement_binding': 1,
         'cleanup_None_Some_after_cleanup_store': 3,
         'failure_and_success_Result_tuple_fields_upper': 5,
         'two_ticket_expect_inspect_extract': 4, 'adopted_three_fields': 3},
        {'proof': 1, 'validation_usage': 1, 'reservations_default': 1, 'live_default': 1,
         'cursor': 1, 'check_budget': 1, 'check': 2, 'admit': 5,
         'backing_layout': 1, 'snapshot_foundation_callback': 1,
         'fault': 3, 'fault_limit': 1, 'fail': 3,
         'snapshot_retire': 1, 'finish_owned_cleanup': 1, 'snapshot_failure': 1},
        note='Branch upper sum includes five admissions, two independent checks, all three written local failure callbacks, and one failure cleanup even though healthy and failed arms are exclusive. Atomic try_update and its pure checked_add callback are each priced once by the selected logical convention; std retry reevaluations are excluded.')

    # Optional WASI setup. Four construction iterations; one attempt per scope.
    row('wasi_budget_default', W, 'fn default() -> Self',
        {'enter_return': 2, 'seven_output_stores': 7, 'two_written_literal_multiplications': 2})
    row('wasi_budget_check', W, 'pub fn check(self)',
        {'enter_return': 2, 'default_binding': 1, 'fourteen_field_fetches': 14,
         'seven_compares': 7, 'six_short_circuit_decisions_and_final_decision': 7,
         'two_Result_carriers_and_error_tag_upper': 3}, {'wasi_budget_default': 1})
    row('carry_wasi_deadline', C, 'pub(crate) fn carry_wasi_deadline(',
        {'enter_return': 2, 'three_propagating_questions': 6,
         'budget_error_match_pattern': 2, 'fault_binding_and_wasi_error_Some_store': 3,
         'deadline_ms_fetch_duration_event_checked_add_Option_inspect_output_binding': 6,
         'overflow_closure_enter_return_and_None': 3,
         'earliest_deadline_fetch_compare_decision_two_stores': 5,
         'returned_deadline_fetch_and_Ok': 2, 'error_carrier': 1},
        {'check': 2, 'wasi_budget_check': 1, 'fault': 2, 'fail': 2})
    row('accounted_construction_bytes', A, 'pub(crate) fn accounted_construction_bytes()',
        {'enter_return': 2, 'thirteen_tuple_slots_and_twenty_six_fields': 39,
         'thirteen_sizeof_events': 13, 'into_iter_and_try_fold_events': 2,
         'initial_accumulator': 1, 'loop_setup_termination': 2,
         'thirteen_tuple_advance_bind': 39, 'thirteen_closure_enter_return': 26,
         'thirteen_checked_multiply': 13, 'thirteen_question_inspect_propagations': 26,
         'thirteen_checked_add': 13},
        loops=[{'source': 'thirteen-term array.into_iter().try_fold', 'max_iterations': 13,
                'per_iteration': {'tuple_advance_bind': 3, 'closure_enter_return': 2,
                                  'checked_mul': 1, 'question': 2, 'checked_add': 1}}])
    row('accounted_header_bytes', A, 'pub(crate) fn accounted_header_bytes()',
        {'enter_return': 2, 'four_sizeof_events': 4, 'three_checked_multiply': 3,
         'three_checked_add': 3, 'five_question_inspect_propagations': 10})
    row('layout_failure', A, 'fn layout_failure(',
        {'enter_return': 2, 'None_argument': 1}, {'fault': 1, 'fail': 1})
    row('enlarge_with_wasi', C, 'pub(crate) fn enlarge_construction_with_wasi(',
        {'enter_return': 2, 'two_question_inspect_propagations': 4,
         'construction_fetch_as_ref_map_event_and_callback_fetch_upper': 6,
         'missing_closure_enter_return': 2, 'old_Option_inspection_output_binding': 3,
         'shrink_compare_decision': 2, 'bytes_subtraction': 1,
         'two_tuple_bindings': 2, 'construction_as_mut_unwrap_bytes_store': 4,
         'two_error_and_one_success_carriers': 3},
        {'check_with_wasi': 1, 'fault': 1, 'fail': 1, 'preflight': 1, 'commit': 1},
        note='Missing-construction/shrink alternatives select at most one local fault+fail.')
    row('enlarge', C, 'pub(crate) fn enlarge_construction(',
        {'enter_return': 2, 'None_argument': 1}, {'enlarge_with_wasi': 1})
    row('prepare', A, 'pub(crate) fn prepare(',
        {'enter_return': 2, 'None_usage_argument': 1,
         'previous_construction_projection_binding': 2,
         'and_then_event_callback_enter_return_checked_add': 4,
         'ok_or_else_inspect_carrier_closure_enter_return': 4,
         'two_question_inspect_propagations': 4, 'bound_binding': 1,
         'three_phase_fields_and_Ok': 4},
        {'usage': 1, 'accounted_construction_bytes': 1, 'layout_failure': 1, 'enlarge': 1})
    row('partial_empty', A, 'fn empty() -> Self',
        {'enter_return': 2, 'two_array_from_fn_events': 2,
         'two_loop_setup_termination_upper': 4,
         'eight_callback_enter_return': 16, 'four_Vec_new_events': 4,
         'four_None_slots': 4, 'eight_array_output_stores_upper': 8,
         'three_Partial_fields': 3},
        loops=[{'source': 'two array::from_fn calls for four slots each', 'max_iterations': 8}])
    row('drop_reserved_with_wasi', C, 'pub(crate) fn drop_reserved_with_wasi<T>',
        {'enter_return': 2, 'storage_drop_event': 1}, {'refund_with_wasi': 1})
    row('drop_reserved', C, 'pub(crate) fn drop_reserved<T>',
        {'enter_return': 2, 'None_argument': 1}, {'drop_reserved_with_wasi': 1})
    row('partial_cleanup', A, 'fn cleanup(mut self, control:',
        {'enter_return': 2, 'loop_setup_termination': 2,
         'four_iterations_advance_bind': 8,
         'four_storage_index_bounds_take_borrow_binding': 16,
         'four_buffer_index_bounds_take_inspect_bind_decide': 24,
         'four_else_drop_events_upper': 4, 'header_take_inspect_bind_decide': 5},
        {'drop_reserved': 5},
        loops=[{'source': 'for index in 0..4', 'max_iterations': 4,
                'buffer_drop_refunds_max': 4}, {'source': 'header Option', 'max_iterations': 1}])
    row('exact_capacity_with_wasi', C, 'pub(crate) fn exact_capacity_with_wasi(',
        {'enter_return': 2, 'question_inspect_propagation': 2,
         'requested_observed_compare_decision': 2,
         'fault_binding_observed_Some_store': 3, 'two_Result_carriers': 2},
        {'check_with_wasi': 1, 'fault': 1, 'fault_limit': 1, 'fail': 1})
    row('exact_capacity', C, 'pub(crate) fn exact_capacity(',
        {'enter_return': 2, 'None_argument': 1}, {'exact_capacity_with_wasi': 1})
    row('control_cancellation', C, 'pub(crate) fn cancellation(&self)',
        {'enter_return': 2, 'cancellation_field_fetch': 1,
         'derive_clone_boundary_and_output': 3, 'Arc_clone_logical_event': 1},
        note='One public Arc clone logical event; reference-count implementation/atomic retry/allocator internals excluded.')
    row('span_default', W, 'struct Span', {'derive_enter_return': 2, 'two_leaf_stores': 2})
    row('wasi_usage_default', W, 'pub struct WasiUsage',
        {'derive_enter_return': 2, 'thirteen_default_leaf_stores': 13,
         'nested_WasiReservations_derive_boundary': 2})
    row('wasi_construct', A, 'pub(crate) fn construct(',
        {'enter_return': 2, 'constructed_fetch_decision_and_store': 3,
         'repeat_attempt_error_and_None_carriers': 2,
         'deadline_question_binding': 3,
         'header_Option_inspect_carrier_closure_boundary_question_binding': 7,
         'partial_binding': 1, 'closure_enter_return_result_binding': 3,
         'header_Some_and_field_store_question': 4,
         'four_budget_fetch_cast_array_stores': 12,
         'array_into_iter_enumerate_events_loop_setup_termination': 4,
         'four_loop_tuple_advance_bind': 12,
         'four_buffer_index_bounds_Some_store_and_admit_question': 20,
         'four_check_questions': 8,
         'four_storage_index_bounds_borrow_and_try_reserve_events': 12,
         'four_map_err_inspect_output_closure_boundaries_question_upper': 28,
         'four_error_fault_bindings_wasi_Some_attempted_cast_stores_upper': 24,
         'four_capacity_fetch_events_index_bounds_and_exact_question': 16,
         'result_error_match_bindings_and_error_carrier': 3,
         'current_iter_try_fold_events_loop_setup_termination': 4,
         'capacity_fold_initial_sizeof_event': 1,
         'four_capacity_fold_advance_bind_callback_boundary_capacity_checked_add': 28,
         'current_Option_pattern_decision_binding_error_carrier': 4,
         'storage_take_and_four_pattern_bindings': 5,
         'WasiReservations_seven_output_slots_four_capacity_and_eight_sizeof_cast_events': 19,
         'AccountedWasi_three_context_sixteen_fields_usage_two_fields_upper': 21,
         'two_grant_fetches_two_output_stores': 4,
         'iovec_array_sixty_four_Span_fetch_store_pair_upper': 256,
         'buffers_take_header_take_two_receivers_Ok': 5,
         'twenty_one_self_control_receiver_fetches_upper': 21},
        {'fault': 2, 'fail': 2, 'carry_wasi_deadline': 1,
         'accounted_header_bytes': 1, 'layout_failure': 2, 'partial_empty': 1,
         'admit': 5, 'check': 5, 'exact_capacity': 4,
         'partial_cleanup': 1, 'control_cancellation': 1,
         'wasi_usage_default': 1, 'span_default': 1},
        loops=[{'source': 'enumerated four buffer sizes', 'max_iterations': 4,
                'admit_calls': 4, 'check_calls': 4, 'exact_capacity_calls': 4,
                'try_reserve_exact_logical_events': 4,
                'allocation_error_callback_evaluations_max': 1},
               {'source': 'partial.storage.iter().try_fold', 'max_iterations': 4},
               {'source': '[Span::default();64]', 'max_iterations': 64,
                'span_default_calls': 1, 'copy_leaf_slots_per_output': 2}],
        note='At most one allocation callback and one of the two partial-cleanup branches is selected; cleanup body priced once. Allocation callback scalar bookkeeping is conservatively upper-summed four times, but fail/Fault is once for allocation plus once for repeat-attempt branch. Four Vec reserve calls are logical events, not requested-byte copying or allocator/kernel CPU bounds.')
    row('end_phase_with_wasi', C, 'pub(crate) fn end_construction_phase_with_wasi<T>',
        {'enter_return': 2, 'storage_drop_event': 1,
         'ticket_fetch_as_ref_inspect_pattern': 4,
         'owner_category_fetch_compare_or_decision': 7,
         'floor_unwrap_or_binding': 2,
         'lower_upper_bound_fetch_compare_or_decision': 5,
         'ticket_bytes_fetch_subtract_difference_binding': 3,
         'category_current_checked_sub_binding': 3,
         'combined_current_checked_sub_binding': 3,
         'Option_tuple_inspect_pattern_bind_decision_upper': 7,
         'two_current_stores': 2, 'construction_as_mut_unwrap_bytes_store': 4,
         'four_error_carriers_and_Ok_upper': 5},
        {'foundation': 1, 'cleanup_fault': 1},
        note='Missing ticket, foreign ticket, invalid floor and underflow branches are terminal alternatives; cleanup_fault branch maximum1.')
    row('end_phase', C, 'pub(crate) fn end_construction_phase<T>',
        {'enter_return': 2, 'None_argument': 1}, {'end_phase_with_wasi': 1})
    row('wasi_complete', A, 'pub(crate) fn complete(self)',
        {'enter_return': 2, 'two_pattern_bindings': 2, 'unit_storage_argument': 1}, {'end_phase': 1})
    # The accepted original writer proposal prices the attachment wrappers at
    #16+45. No new wrapper charge may also be added by the outer composition lane.
    reuse('attach', 'SnapshotScope.attach_wasi_v1_outer_per_call', C, 'pub(super) fn attach_wasi_v1(')
    rows['attach']['calls'] = {'attach_inner': 1}
    reuse('attach_inner', 'SnapshotScope.attach_wasi_inner_v1_added_bookkeeping', C, 'fn attach_wasi_inner_v1(')
    rows['attach_inner']['calls'] = {'fault': 1, 'fail': 1, 'prepare': 1, 'wasi_construct': 1, 'wasi_complete': 1}

    # WASI final cleanup is outside the old521088's named constructor+cache
    # scopes. Expose it independently; outer finish owns only its match/binding.
    reuse('wasi_usage', 'AccountedWasi.usage', A, 'pub(crate) fn usage(&self)')
    reuse('wasi_context_usage', 'WasiContext.usage', W, 'pub fn usage(&self) -> WasiUsage')
    rows['wasi_usage']['parts'].pop('context_usage')
    rows['wasi_usage']['calls'] = {'wasi_context_usage': 1}
    row('wasi_cleanup', A, 'pub(crate) fn cleanup(mut self, control:',
        {'enter_return': 2, 'wasi_Some_and_binding': 2,
         'initial_Ok_and_binding': 2, 'loop_setup_termination': 2,
         'four_loop_advance_bind': 8,
         'four_index_match_context_borrow_take_binding': 20,
         'four_buffer_index_bounds_receiver_take_pattern_decision': 24,
         'four_released_bindings_and_Result_and_inspect_output_stores': 16,
         'four_else_drop_events_upper': 4,
         'header_take_inspect_pattern_decision': 5,
         'last_release_binding_Result_and_inspect_output_store': 4},
        {'wasi_usage': 1, 'drop_reserved_with_wasi': 5},
        loops=[{'source': 'for index in 0..4', 'max_iterations': 4,
                'drop_reserved_with_wasi_calls_max': 4},
               {'source': 'header Option', 'max_iterations': 1,
                'drop_reserved_with_wasi_calls_max': 1}],
        note='Every refund can observe the already terminal first failure; the full helper upper is retained for all five calls. No new cancellation/deadline checks, admission, allocation or host dispatch.')

    # These explicit signature transfer allowances are conservative even where
    # bound local arguments could be free. They protect reusable Copy inputs
    # (especially cursor and optional observation) without inventing deep owned
    # payload moves. Named borrowed-source Copies above remain separately priced.
    transfer_slots = {
        'usage': 14, 'fail': 5+14+14, 'check_with_wasi': 5+14,
        'check': 5, 'check_budget': 5, 'preflight': 5+14,
        'admit_with_wasi': 5+14, 'admit': 5, 'cleanup_fault': 14,
        'refund_with_wasi': 3+14, 'refund': 3, 'finish_owned_cleanup': 14,
        'adopt_core': 17, 'wasi_budget_check': 7,
        'carry_wasi_deadline': 7+5, 'layout_failure': 5,
        'enlarge_with_wasi': 5+14, 'enlarge': 5, 'prepare': 5,
        'drop_reserved_with_wasi': 3+14, 'drop_reserved': 3,
        'exact_capacity_with_wasi': 5+14, 'exact_capacity': 5,
        'wasi_construct': 5+7+5, 'end_phase_with_wasi': 14,
    }
    for name, slots in transfer_slots.items():
        rows[name]['parts']['explicit_Copy_argument_fetch_store_upper'] = 2*slots
        rows[name]['Copy_argument_leaf_slots_upper'] = slots

    # Every fixed loop has an independent source fragment fingerprint in
    # addition to its complete containing body. Expression repeats and implicit
    # from_fn loops bind the exact expression, not fabricated Rust source.
    loop_sources = [
        ('budget17', C, 'for (resource, attempted, limit) in fields', 0, 17),
        ('finish3', C, 'for ticket in [', 0, 3),
        ('construction13', A, '.try_fold(0usize, |sum, (count, bytes)|', 0, 13),
        ('partial4', A, 'for index in 0..4', 0, 4),
        ('construct4', A, 'for (index, bytes) in [', 0, 4),
        ('capacity4', A, '.try_fold(size_of::<WasiContext>(), |sum, bytes|', 0, 4),
        ('cleanup4', A, 'for index in 0..4', 1, 4),
        ('cleanup_header1', A, 'if let Some(ticket) = self.header.take()', 0, 1),
    ]
    loop_bindings = {}
    for name, path, marker, occurrence, maximum in loop_sources:
        fragment = extract(path, marker, occurrence)
        fragment['max_iterations'] = maximum
        loop_bindings[name] = fragment
    for name, expression, maximum in [
        ('partial_vec4', 'std::array::from_fn(|_| Vec::new())', 4),
        ('partial_option4', 'std::array::from_fn(|_| None)', 4),
        ('iovec64', '[Span::default(); 64]', 64),
    ]:
        data = (VM/A).read_text(); assert data.count(expression) == 1
        loop_bindings[name] = {'path': A, 'source': expression,
                              'line': data[:data.index(expression)].count('\n')+1,
                              'bytes': len(expression.encode()), 'sha256': sha(expression.encode()),
                              'max_iterations': maximum}

    totals = {}
    def total(name, visiting=()):
        assert name not in visiting, ('recursive work row', visiting, name)
        if name not in totals:
            r = rows[name]
            assert all(type(v) is int and v >= 0 for v in r['parts'].values())
            assert all(type(v) is int and v >= 0 for v in r['calls'].values())
            totals[name] = sum(r['parts'].values()) + sum(count*total(child, visiting+(name,)) for child, count in r['calls'].items())
        return totals[name]
    for name in rows:
        total(name)
    for name, r in rows.items():
        r['own_actions'] = sum(r['parts'].values())
        r['expanded_actions'] = totals[name]
    exported = {'W_ingress': totals['selected_into_scope'], 'W_setup': totals['attach'],
                'W_wasi_finish': totals['wasi_cleanup']}
    controls = []
    def check(name, okay):
        assert okay, name
        controls.append({'name': name, 'passed': True})
    check('exact_144_member_source_tree', len(members) == 144)
    check('exact_source_and_seal_digest', manifest['source_tree_sha256'] == EXPECTED_TREE)
    check('all_rows_source_bound_and_nonrecursive', len(rows) > 50 and all(r['binding'] in bindings for r in rows.values()))
    check('reused_adoption_wrapper_27', sum(inherited_rows['snapshot_adoption_wrapper']['parts'].values()) == 27)
    check('reused_callback_bookkeeping_35', totals['snapshot_foundation_callback'] + rows['snapshot_retire']['own_actions'] + rows['snapshot_failure']['own_actions'] == 35)
    check('reused_attach_bookkeeping_61', rows['attach']['own_actions'] + rows['attach_inner']['own_actions'] == 61)
    check('five_adoption_admissions', rows['adopt_core']['calls']['admit'] == 5)
    check('both_refunds_even_first_fails', rows['snapshot_retire']['calls']['refund'] == 2)
    check('adoption_failure_finalizer_once', rows['adopt_core']['calls']['finish_owned_cleanup'] == 1)
    check('four_WASI_payloads_plus_one_header', rows['wasi_construct']['calls']['admit'] == 5)
    check('partial_cleanup_terminal_branch_max_one', rows['wasi_construct']['calls']['partial_cleanup'] == 1)
    check('one_attachment_prepare_construct_complete', all(rows['attach_inner']['calls'][key] == 1 for key in ['prepare','wasi_construct','wasi_complete']))
    check('five_final_WASI_drops', rows['wasi_cleanup']['calls']['drop_reserved_with_wasi'] == 5)
    check('runtime_const_foundation_only_three', totals['foundation'] == 3)
    check('snapshot_foundation_19_reused_exact', totals['snapshot_foundation_callback'] == inherited_rows['snapshot_foundation_callback']['credits'] == 19)
    check('snapshot_foundation_constcopy_delta_fourteen', totals['snapshot_foundation']-3 == 14)
    check('selected_consuming_carrier_body_not_tuple_accessor',
          'AdoptionBodyV1 { proof,selected:Some(provenance) }' in bindings[rows['selected_into_body']['binding']]['source'])
    check('selected_tuple_accessor_is_separate',
          bindings[rows['selected_body_unwrap']['binding']]['source'].endswith('{self.0}'))
    for root in ['selected_into_scope', 'attach', 'wasi_cleanup']:
        def visit(name, multiplier=1, counts=None):
            counts = {} if counts is None else counts
            counts[name] = counts.get(name, 0) + multiplier
            for child, count in rows[name]['calls'].items():
                visit(child, multiplier*count, counts)
            return counts
        counts = visit(root)
        check('expanded_call_graph_reconciles_'+root,
              sum(rows[name]['own_actions']*count for name, count in counts.items()) == totals[root])
    # Mutations exercise actual rejection: independently re-expand changed rows
    # against the recorded export, rather than treating a positive coefficient
    # as a successful negative control.
    def recompute(candidate_rows, name):
        return sum(candidate_rows[name]['parts'].values()) + sum(
            count*recompute(candidate_rows, child)
            for child, count in candidate_rows[name]['calls'].items())
    for target, part in [('usage','forty_nine_borrowed_leaf_fetch_store_pairs'),
                         ('fail','Existing_borrowed_Copy_151_leaves'),
                         ('wasi_construct','four_loop_tuple_advance_bind'),
                         ('accounted_construction_bytes','thirteen_question_inspect_propagations'),
                         ('wasi_cleanup','four_buffer_index_bounds_receiver_take_pattern_decision')]:
        changed = copy.deepcopy(rows); changed[target]['parts'].pop(part)
        check('reject_missing_'+target+'_'+part,
              any(recompute(changed, root) != totals[root]
                  for root in ['selected_into_scope','attach','wasi_cleanup']))
    for target, callee in [('adopt_core','admit'), ('snapshot_retire','refund'),
                           ('wasi_construct','partial_cleanup'), ('wasi_cleanup','drop_reserved_with_wasi')]:
        changed = copy.deepcopy(rows); changed[target]['calls'][callee] -= 1
        check('reject_missing_call_'+target+'_'+callee,
              any(recompute(changed, root) != totals[root]
                  for root in ['selected_into_scope','attach','wasi_cleanup']))
    check('snapshot_work_admission_still_pending', 'Err(AError::WorkAuditPending)' in (VM/'src/experimental_swift_reactor/cache/initial_profile_v1.rs').read_text())
    delta = {'status': 'interface-only-not-applied',
             'replacement_body': 'entry2+precomputed Option/constant fetch1=3; requires new exact body/source binding before selection',
             'snapshot_foundation': {'frozen': totals['snapshot_foundation'], 'replacement': 3,
                                     'W_ingress_delta': -(totals['snapshot_foundation']-3)},
             'accounted_construction_bytes': {'frozen': totals['accounted_construction_bytes'], 'replacement': 3,
                                              'W_setup_delta_if_replaced': -(totals['accounted_construction_bytes']-3)},
             'accounted_header_bytes': {'frozen': totals['accounted_header_bytes'], 'replacement': 3,
                                       'W_setup_delta_if_replaced': -(totals['accounted_header_bytes']-3)}}
    return {'schema': 1, 'status': 'finite-source-work-candidate-independent-review-pending',
            'source_members': 144, 'source_tree_sha256': EXPECTED_TREE, 'source_seal_sha256': EXPECTED_SEAL,
            'inputs': [record(HERE.parent/'swift-guarded-snapshot-writer-work-audit/cost-convention.md'),
                       record(HERE.parent/'swift-guarded-snapshot-writer-work-correction/corrected-ledger.json'),
                       record(HERE.parent/'swift-semantic-adapter-root-review/guarded-snapshot-writer-work-host-acceptance.json'),
                       record(HERE.parent/'swift-semantic-adapter-root-review/initial-profile-source-action-scope-selection.json')],
            'exports': exported, 'source_bindings': bindings, 'loop_bindings': loop_bindings, 'rows': rows,
            'reused_rows': inherited_rows, 'constcopy_replacement_interface': delta,
            'controls': controls,
            'source_unit': 'one named fetch/store/scalar/decision or logical primitive invocation; entry+return2; aggregate Copy fetch+store per leaf; bound operands free',
            'branch_rule': 'Upper sums of written branch work are retained; terminal callbacks/helpers use stated branch maximum when named. No elapsed/CPU/native work inference.',
            'composition': 'W_ingress once per selected ingress; z*W_setup for z in {0,1}; z*W_wasi_finish separately at final scope retirement. Setup already includes one partial-failure cleanup and completion. Other scope construct/outer/finish wrappers belong to the sibling complete-work-plan lane.',
            'historical_521088': 'No automatic adoption/WASI debit. Historical constructor+row/cache cleanup envelope is separate; these three exports are newly priced missing source bodies. No subtraction of broad remaining_fixed_nonrecursive_source_paths is justified.',
            'excluded': ['std atomic retry reevaluations and private std implementation', 'kernel/allocator/native-call implementation and CPU/wall time',
                         'loader file validation and source construction before selected carrier consumption', 'constructor/row/encoder/writer bodies and outer finish wrappers owned by sibling lane',
                         'physical native device/simulator/emulator/UI/capture work', 'operational admission, OTA publication and GA acceptance'],
            'WorkAuditPending_preserved': True, 'actual_writer_executed': False,
            'runtime_or_native_executed': False, 'operational_work_selected': False, 'GA_gates_verified': 0}

def main():
    result = calculate()
    target = HERE/'ledger.json'
    if '--write' in sys.argv:
        assert not target.exists()
        emit(target, result)
    else:
        assert json.loads(target.read_text()) == result
    print(json.dumps({'source_members': result['source_members'], 'source_tree_sha256': EXPECTED_TREE,
                      'rows': len(result['rows']), 'source_bindings': len(result['source_bindings']),
                      'controls_passed': len(result['controls']), **result['exports'],
                      'runtime_or_native_executed': False, 'operational_work_selected': False}, sort_keys=True))

if __name__ == '__main__':
    main()
