#!/usr/bin/env python3
"""Independent fixed source ledger; no producer execution or release authority."""
import hashlib
import json
from pathlib import Path
import sys
from datetime import datetime, timezone
from admit_frozen import verify_seal, SOURCE_SHA

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
INPUT = OWN / 'commands/frozen-admission-1/inputs'
def sha(data): return hashlib.sha256(data).hexdigest()
def write_json(path, value): path.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')

def main():
    run = OWN/'commands/source-ledger-1'
    run.mkdir(parents=True, exist_ok=False)
    before = verify_seal()
    source_bytes = (INPUT/'src/envelope.rs').read_bytes()
    assert sha(source_bytes) == SOURCE_SHA['src/envelope.rs']
    lines = source_bytes.decode().splitlines()
    assert lines[135] == '    for i in 0..12 {'
    assert lines[136] == '        let pair = word_at(arena, SCALAR.base + 8 * CELLS[i]);'
    assert lines[137] == '        if pair.status != 1 { return poisoned(if underfunded { 0 } else { RECORD_ENVELOPE }); }'
    assert lines[138] == '        prior[i] = pair.value;'
    ledger = [
        {'id': 'caller01', 'line': 137, 'operation': 'CELLS[i] indexed scalar read', 'minimum_scalar_operations': 1},
        {'id': 'caller02', 'line': 137, 'operation': '8 * selected cell', 'minimum_scalar_operations': 1},
        {'id': 'caller03', 'line': 137, 'operation': 'SCALAR.base + computed offset', 'minimum_scalar_operations': 1},
        {'id': 'caller04', 'line': 138, 'operation': 'pair.status scalar load', 'minimum_scalar_operations': 1},
        {'id': 'caller05', 'line': 138, 'operation': 'status != 1 comparison', 'minimum_scalar_operations': 1},
        {'id': 'caller06', 'line': 138, 'operation': 'if status discriminator branch', 'minimum_scalar_operations': 1},
        {'id': 'caller07', 'line': 139, 'operation': 'pair.value scalar load', 'minimum_scalar_operations': 1},
        {'id': 'caller08', 'line': 139, 'operation': 'prior[i] destination index', 'minimum_scalar_operations': 1},
        {'id': 'caller09', 'line': 139, 'operation': 'scalar store to prior destination', 'minimum_scalar_operations': 1},
    ]
    minimum = 12 * sum(item['minimum_scalar_operations'] for item in ledger)
    assigned = 3 * 16
    assert minimum == 108 and assigned == 48 and minimum > assigned
    step = json.loads((INPUT/'step-inventory.json').read_bytes())
    logical = json.loads((INPUT/'logical-inventory.json').read_bytes())
    baseline = json.loads((OWN/'commands/accounting-1/accepted-inventory.json').read_bytes())
    assert sum(x['groups'] for x in step['record']['wrapper_groups']) == 42
    assert sum(x['groups'] for x in step['record']['leaf_groups']) == 111
    assert sum(x['groups'] for x in step['fixed']['guard_groups']) == 36
    assert sum(x['groups'] for x in step['fixed']['wrapper_setup_groups']) == 20
    assert sum(x['groups'] for x in step['fixed']['wrapper_final_groups']) == 44
    recomputed = {}
    for group, roles in logical['extra_roles'].items():
        if group == 'candidate': recomputed[group] = sum(x['bytes'] for x in roles)
        else: recomputed[group] = baseline['named_role_upper_by_group'][group] + sum(x['bytes'] for x in roles)
    for name, phase in logical['phases'].items():
        actual = baseline['phases'][phase['accepted_phase']]['control_upper'] + sum(logical['additional_helper_leases'][helper]['bytes'] for helper in phase['additional_helpers'])
        assert actual == phase['control_upper'], name
    recomputed['control'] = max(baseline['named_role_upper_by_group']['control'], *(phase['control_upper'] for phase in logical['phases'].values()))
    assert recomputed == logical['named_role_upper_by_group']
    assert sum(recomputed.values()) == logical['named_role_upper_total'] == 24656
    assert sum(logical['reservations'].values()) == 41984
    for group, total in recomputed.items(): assert total <= logical['reservations'][group]
    original = (OWN/'commands/preaccess-1/inputs/verification__swift-ordered-retention-analyzer-library__src__analyzer.rs').read_bytes()
    frozen = (INPUT/'src/analyzer.rs').read_bytes()
    assert frozen.startswith(original)
    finding = {
        'id': 'A1', 'priority': 'P1',
        'title': 'Prior-read caller work exceeds its named scalar allowance',
        'source': 'verification/swift-ordered-retention-analyzer-envelope/src/envelope.rs',
        'source_sha256': SOURCE_SHA['src/envelope.rs'], 'start_line': 136, 'end_line': 139,
        'rule': 'At most16 bounded scalar source operations OR one fixed copy <=128 bytes per group; no inactive-group credit borrowing',
        'source_ledger': ledger, 'iterations': 12,
        'minimum_scalar_operations_per_iteration': 9, 'minimum_scalar_operations_total': minimum,
        'assigned_caller_groups': 3, 'assigned_scalar_capacity': assigned,
        'minimum_caller_groups_excluding_loop_arguments_and_bounds': (minimum+15)//16,
        'excluded_from_lower_bound': ['loop creation/next/condition/increment', 'separate bounds checks', 'borrow and argument handoff', 'Pair source/return/caller handling', 'word_at internal work', 'fixed error arm'],
        'conservatism': 'CELLS[i] indexing plus load is counted as only one operation here; counting them separately strengthens the finding.',
        'affected_claims': ['leaf prior-read subtotal27', 'leaf authored upper111', 'guard G36', 'combined debit/preflight proof'],
        'not_established': ['128 suffices for actual complete source', 'B192 suffices', 'a particular amended G or wrapper amount', 'CPU or native cost'],
        'requested_correction': 'Provide a complete operation-level worst-path source ledger, reconcile old/new word accesses and every caller/helper/copy/move/branch, and revise separately prepaid G before mutation. Independently review the amended proof; do not consume the stated17 unused credits by inference.',
    }
    write_json(OWN/'findings.json', {'schema': 1, 'status': 'source-accounting-proof-rejected-revision-required', 'findings': [finding], 'product_acceptance': False, 'combined_debit_preflight_qualified': False})
    after = verify_seal()
    receipt = {
        'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'invocation': sys.orig_argv,
        'before': before, 'after': after, 'source_sha256': sha(source_bytes),
        'reviewer_script_sha256': sha(Path(__file__).read_bytes()),
        'status': 'actionable-accounting-finding-reproduced',
        'checks': {'prior_read_allocation_sufficient': False, 'declared_arithmetic_reconciles': True, 'all_declared_group_sums_within_existing_reservations': True, 'accepted_framing_prefix_exact': True},
        'logical_group_arithmetic': recomputed, 'logical_total': 24656, 'logical_reservation': 41984, 'logical_ceiling': 65536,
        'layout_or_arithmetic_implies_complete_source_proof': False,
        'product_acceptance': False, 'combined_lifetime_qualified': False, 'combined_debit_preflight_qualified': False,
        'producer_code_executed': False, 'native_capture_process_or_device_discovery': False,
        'cleanup': 'No child process or disposable binary is created by this ledger check. All bounded input bytes and review outputs retained.'
    }
    write_json(run/'receipt.json', receipt)
    output = json.dumps({'status': receipt['status'], 'minimum_caller_scalar_ops': minimum, 'assigned_caller_scalar_capacity': assigned, 'findings': 1, 'declared_logical_total': 24656, 'numeric_proof_accepted': False}, sort_keys=True)+'\n'
    (run/'stdout.txt').write_text(output); (run/'stderr.txt').write_text(''); print(output, end='')

if __name__ == '__main__': main()
