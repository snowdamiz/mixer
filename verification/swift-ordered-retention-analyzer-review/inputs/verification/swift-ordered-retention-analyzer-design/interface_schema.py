"""Fixed symbolic names for review, not a parser/analyzer implementation.

All unspecified slots are named reserved and must serialize zero.
"""
def words(prefix, count, names):
    names = names.split()
    assert len(names) <= count and len(set(names)) == len(names)
    return [prefix + '.' + name for name in names] + [
        f'{prefix}.reserved_{i}' for i in range(len(names), count)]

CONTROL = words('control', 64, '''step_limit replay_remaining replay_spent
    report_reserved io_reserved input_length physical_records accepted_records
    next_record last_work last_instructions last_operation current_phase
    observed_mask expected_mask writer_flags record_cap next_nonce acquisitions
    current_window recency_length resident_count resident_bytes held_pins
    selected_slots selected_pin_slots cache_base cache_capacity entry_capacity
    stop_reason invalid_record io_code inventory_initialized profile_verified
    binding_available tail_unknown context_version report_bytes input_bytes_read
    input_block_used input_block_cursor input_blocks_read counter_overflow''')
ACTIVE = words('active', 64, '''state operation function acquire_sequence
    acquire_work acquire_instructions lookup_hit lookup_slot scan_open
    scan_sequence scan_work scan_instructions plan_outcome plan_prior
    requested_bytes build_open build_sequence build_work build_instructions
    build_ready expected_destination failed failure_kind failure_code
    failure_stage failure_function failure_work failure_instructions
    plan_published temporary_owner_known temporary_owner_bytes''')
PLANNER = words('planner', 32, '''selected_mask emitted_mask taken_mask
    committed_mask initial_resident_bytes remaining_bytes destination
    first_empty next_emission pending_victim pending_bytes pending_stage
    all_pinned complete_selection pending_function pending_timestamp
    pending_generation''')
LIFECYCLE = words('lifecycle', 24, '''terminal_seen pin_failure_seen terminal_kind
    terminal_code terminal_stage terminal_function terminal_work
    terminal_instructions original_result_kind cleanup_invariant final_tickets
    final_phase final_mask terminal_matches_original final_ledger_matches
    final_ledger_zero pre_footer_attempts footer_stored footer_attempted
    footer_dropped footer_last_sequence footer_last_operation footer_valid''')
COUNTERS = words('counter', 128, '''acquire_attempts lookup_hits lookup_misses
    publications built_publications hit_publications release_success
    scans_started scans_completed plan_empty plan_conflicts plan_hits
    builds_started builds_completed evictions_begun evictions_taken
    evictions_committed eviction_bytes_taken eviction_bytes_committed
    evictions_open_before_take evictions_taken_uncommitted scan_credit_completed
    build_credit_completed scan_credit_partial build_credit_partial
    operation_credit_partial held_pins_current held_pins_peak held_pins_censored
    held_acquire_interval_total held_work_interval_total
    held_instruction_interval_total resident_count_current resident_count_peak
    resident_bytes_current resident_bytes_peak resident_headroom_min
    resident_headroom_max resident_headroom_known observations_headroom_unknown
    acquisition_gap_total work_gap_total instruction_gap_total first_functions
    distinct_functions_seen reuse_ge64 reuse_0_to_63 windows_opened
    completed_windows partial_window_acquisitions failure_pin failure_terminal
    open_acquisition open_scan open_build temporary_build_ready partial_eviction
    original_final_source original_final_metadata original_final_cache
    original_final_state original_final_wasi original_final_shared
    original_final_construction original_final_combined original_final_tickets
    original_final_entries original_final_pins original_final_frames
    original_final_values original_final_controls original_final_pages
    original_cleanup_invariant original_result_kind original_failure_kind
    original_failure_code original_failure_stage original_terminal_work
    original_terminal_instructions''')
SCALARS = CONTROL + ACTIVE + PLANNER + LIFECYCLE + COUNTERS + words('reserved', 200, '')
REPORT_HEADER = '''magic version report_bytes decision full_replay_accepted
    accepted_records physical_records footer_stored acquisitions steps_used
    stop_reason prefix_work prefix_instructions prefix_operation flags
    validity_mask guest_residents guest_pins taken_uncommitted completed_evictions
    original_kind original_code original_stage cleanup_invariant final_tickets
    phase observed_mask expected_mask counter_overflow io_code invalid_sequence
    reserved'''.split()
REPORT_REGIONS = [('header', 512), ('counters', 1024), ('histograms', 4096),
    ('windows', 16384), ('top', 4096), ('residents', 4096), ('pins', 3072),
    ('reserved', 15872)]
HOST_REGIONS = [('header', 512), ('custody', 1024), ('digests', 512),
    ('bindings_and_result', 2048), ('observations', 1024), ('reserved', 3072)]
DECISIONS = {'CompleteRecords': 1, 'TruncatedPrefix': 2, 'Invalid': 3,
             'AnalysisLimited': 4, 'Unavailable': 5}
STOP_REASONS = {'None': 0, 'Steps': 1, 'WindowCapacity': 2, 'ReportCapacity': 3,
                'Allocation': 4, 'Inventory': 5, 'Input': 6, 'Binding': 7,
                'Schema': 8, 'Replay': 9, 'Internal': 10, 'Output': 11}

def offsets(regions):
    cursor, result = 0, []
    for name, length in regions:
        result.append((name, cursor, length)); cursor += length
    return result
