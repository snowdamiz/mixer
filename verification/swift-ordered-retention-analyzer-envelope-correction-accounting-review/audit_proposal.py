#!/usr/bin/env python3
"""Independent proposal arithmetic, source-path ledger and range checks; no replay."""
import hashlib
import json
from math import ceil
from pathlib import Path
from datetime import datetime, timezone
import sys
from admit_proposal import verify_proposal
from prepare_baseline import verify_old_seals

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
INPUT = OWN/'commands/proposal-admission-1/inputs'
def sha(data): return hashlib.sha256(data).hexdigest()
def write_json(path, value): path.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
def main():
    name = sys.argv[1]
    assert name.startswith('source-audit-') and '/' not in name and '..' not in name
    run = OWN/'commands'/name; run.mkdir(parents=True, exist_ok=False)
    before = verify_proposal(); old_before = verify_old_seals()
    ledger = json.loads((INPUT/'operation-ledger.json').read_bytes())
    numeric = json.loads((INPUT/'numeric-proposal.json').read_bytes())
    ranges = json.loads((INPUT/'ranges-and-lifetimes.json').read_bytes())
    source = (INPUT/'source-envelope.rs').read_bytes(); lines = source.decode().splitlines()
    assert sha(source) == 'e86ef43a99f99245c78308666f91f5147981859ca03fa3f97e62d46993667535'
    rows = {row['id']: row for row in ledger['rows']}; assert len(rows) == len(ledger['rows']) == 115
    row_checks = []
    for row in ledger['rows']:
        scalar = sum(atom['count'] for atom in row['scalar_atoms'])
        copies = sum(ceil(edge['bytes']/128)*edge['count'] for edge in row['copies'])
        assert scalar == row['scalar_operations']
        assert ceil(scalar/16) == row['scalar_groups']
        assert copies == row['copy_groups']
        assert all(0 < edge['bytes'] <= 128 for edge in row['copies'])
        total = (ceil(scalar/16)+copies)*row['repeat'] + row.get('helper_groups', 0) + row.get('linked_groups', 0)
        assert total == row['groups'], row['id']
        row_checks.append({'id': row['id'], 'scalar_operations': scalar, 'scalar_groups': ceil(scalar/16), 'copy_groups': copies, 'repeat': row['repeat'], 'total': total})
    composition = ledger['charge_composition']
    checked_totals = {}
    for names, total_name in [('leaf_rows','leaf_total'), ('guard_shared_rows','guard_total'), ('wrapper_record_rows','wrapper_record_total'), ('setup_rows','setup_actual_bound'), ('wrapper_setup_rows','wrapper_setup_total'), ('finish_rows','finish_total'), ('wrapper_final_rows','wrapper_final_total')]:
        total = sum(rows[name]['groups'] for name in composition[names]); assert total == composition[total_name]
        checked_totals[total_name] = total
    assert rows['L07']['linked_groups'] == sum(rows[f'H{i:02d}']['groups'] for i in range(1,8)) + max(rows[f'HA{i:02d}']['groups'] for i in range(1,15))
    assert rows['L11']['linked_groups'] == sum(row['groups'] for name,row in rows.items() if name.startswith(('TP','TS','TC')))
    assert rows['L14']['helper_groups'] == max(rows['RH01']['groups'],rows['RH02']['groups'])
    assert rows['W08']['linked_groups'] == rows['DV01']['groups'] + rows['DV02']['groups']
    assert composition['budget_helper_setup_total'] == rows['BS01']['groups'] + rows['BR01']['groups']
    assert rows['S01']['helper_groups'] == rows['BS01']['groups']+rows['BR01']['groups']+2*rows['BP01']['groups']
    assert rows['T01']['helper_groups'] == rows['BS01']['groups']+rows['BR01']['groups']+rows['BP01']['groups']
    p = numeric['proposed']
    assert p['leaf'] == checked_totals['leaf_total'] == 425
    assert p['W'] == checked_totals['wrapper_record_total'] == 24
    assert p['B'] == 22+p['leaf']+p['W'] == 471 <= 8192
    assert p['G'] == checked_totals['guard_total'] == 112
    assert p['T'] == checked_totals['wrapper_setup_total'] == 42
    assert p['finish'] == checked_totals['finish_total'] == 47
    assert p['F'] == checked_totals['wrapper_final_total'] == 29
    assert p['setup_actual_bound'] == checked_totals['setup_actual_bound'] == 329 <= 534
    assert p['T']+534 == 576 <= 65536
    assert p['finish']+p['G']+p['F'] == 188 <= 3000000
    assert 534+p['finish'] == 581
    assert (268435456-numeric['feasibility']['steps_before_records_lower_bound'])//p['B'] == numeric['feasibility']['arithmetic_record_upper_ignoring_other_existing_costs'] == 566339
    cells = [7,9,10,11,12,13,14,64,65,66,160,161]
    assert [r['cell'] for r in ranges['ranges']] == cells
    for i,r in enumerate(ranges['ranges']):
        assert (r['start'],r['end'],r['candidate_start'],r['candidate_end']) == (7729760+8*cells[i],7729760+8*cells[i]+8,888+8*i,896+8*i)
        assert r['end'] <= 7731056 <= 8388608 and r['candidate_end'] <= 984 <= 2048
        read = f'word.copy_from_slice(&arena[{r["start"]:_}..{r["end"]:_}]); prior[{i}] = u64::from_le_bytes(word);'
        stage = f'candidate[{r["candidate_start"]}..{r["candidate_end"]}].copy_from_slice(&next[{i}].to_le_bytes());'
        commit = f'arena[{r["start"]:_}..{r["end"]:_}].copy_from_slice(&candidate[{r["candidate_start"]}..{r["candidate_end"]}]);'
        assert read in source.decode() and stage in source.decode() and commit in source.decode()
    assert 'if arena.len() < 7_731_056' in source.decode()
    assert lines[299].strip() == 'budget.report(FINISH_ENVELOPE)?; p.debit += FINISH_ENVELOPE;'
    assert lines[347].strip().startswith('let before_s = initial(stream, budget)?;')
    assert lines[352].strip().startswith('walk_fixture_envelope_v1(')
    assert lines[374].strip() == 'let envelope = finalize(&p, &s, &result, &arena);'
    findings = [
        {'id': 'C1', 'priority': 'P1', 'title': 'Early-error finalization has no named prepaid coverage under proposed finish split',
         'source': 'source-envelope.rs', 'source_sha256': sha(source), 'source_lines': [300,348,353,375],
         'path': ['wrapper T42 and F29 admission succeeds', 'initial(stream), context, profile, header or setup fails before finish reservation', 'observe_inputs returns Err', 'core still calls finalize unconditionally', 'Err branch calls project and returns observation'],
         'executed_finish_rows_for_early_input_error': ['E01','E09','E10'],
         'declared_early_finish_path_upper': sum(rows[name]['groups'] for name in ['E01','E09','E10']),
         'finish_reservation_succeeded': False,
         'prepaid_wrapper_rows': composition['wrapper_final_rows'],
         'coverage_gap': 'F01-F04 cover aggregates/changed inherited calls/outer errors, not E01/E09/E10. Globally withheld reporting capacity is not a recorded authored debit. Inactive success/error row credits cannot be reassigned.',
         'requested_change': 'Explicitly fund every early finalize/project path before it can execute, reconcile source call order and finish/public-counter semantics, and reissue a frozen operation/numeric proposal. No particular amended amount is selected.'},
        {'id': 'C2', 'priority': 'P2', 'title': 'Complete unit Result transfer sizes are labeled32 instead of actual40',
         'rows': ['BR01','BS01','BP01','S01','S03','F03'],
         'actual_type': 'Result<(),AnalyzerError>', 'actual_bytes': 40, 'listed_bytes': 32,
         'fresh_probe': 'commands/proposal-layout-1/receipt.json',
         'numeric_effect': 'Each complete transfer still fits one<=128byte copy group. Correct the complete-type labels; do not infer a group-count change from this annotation alone.',
         'requested_change': 'Replace all affected unit/walk Result32 transfer annotations with actual complete40byte types and carry them consistently into the memory/edge inventory.'},
    ]
    write_json(OWN/'findings.json', {'schema':1,'status':'proposal-revision-required-before-numeric-selection','proposal_manifest_sha256': before['manifest_sha256'],'findings':findings,'numeric_values_selected':False})
    write_json(run/'row-arithmetic.json', {'schema':1,'rows':row_checks,'totals':checked_totals,'all_115_row_arithmetic_checks_pass':True})
    early = {'schema':1,'source_sha256':sha(source),'branch':'input Err before walk setup/finish','finish_flag':0,'candidate_initialized':False,'source_still_finalizes':True,'finish_rows_executed':['E01','E09','E10'],'declared_path_upper':13,'named_prepaid_finish_groups':0,'wrapper_F29_covers_these_rows':False,'sufficiency_check':False,'runtime_replay':False}
    write_json(run/'early-finalization-path.json', early)
    after = verify_proposal(); old_after = verify_old_seals(); assert before == after and old_before == old_after
    receipt = {'schema':1,'at':datetime.now(timezone.utc).isoformat(),'invocation':sys.orig_argv,
               'status':'115row-arithmetic-pass-two-source-proposal-findings-numeric-selection-withheld',
               'proposal_before':before,'proposal_after':after,'old_before':old_before,'old_after':old_after,
               'source_sha256':sha(source),'ledger_sha256':sha((INPUT/'operation-ledger.json').read_bytes()),
               'review_script_sha256':sha(Path(__file__).read_bytes()),'totals':checked_totals,
               'all_115_row_arithmetic_checks_pass':True,'twelve_exact_read_stage_commit_ranges_match':True,
               'proposed_B471_within_preflight8192':True,'proposed_fixed_charge_arithmetic_within_caps':True,
               'source_upper425_is_not_a_minimum_lower_bound':True,'leaf425_source_bound_accepted':False,
               'early_finalization_prepaid_coverage_sufficient':False,'complete_unit_result_annotations_correct':False,
               'cost_dependent_runtime_replay':False,'numeric_values_selected':False,'product_acceptance':False,
               'native_capture_process_or_device_discovery':False,
               'cleanup':'No executable/child/scratch created. Immutable inputs, explicit failed coverage check, row arithmetic and source-path findings retained.'}
    write_json(run/'receipt.json', receipt)
    output=json.dumps({'status':receipt['status'],'arithmetic_rows':115,'findings':2,'early_finalize_declared_groups':13,'early_finish_reservation':0,'numeric_selection':False},sort_keys=True)+'\n'
    (run/'stdout.txt').write_text(output);(run/'stderr.txt').write_text('');print(output,end='')
if __name__ == '__main__': main()
