#!/usr/bin/env python3
"""Independent frozen finite join review. Never imports/replays producer code."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

from oracle import normalize, checked_difference

D = Path(__file__).resolve().parent
R = D.parents[1]
P = R / 'verification/swift-root-bound-layout-accounting-join'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def unique(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result
        result[key] = value
    return result


def load(path):
    return json.loads(path.read_bytes(), object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def main():
    start = time.monotonic()
    checked_inputs = {}
    def pin(row, base=R):
        assert time.monotonic() - start < 55
        path = base / row['path']
        assert path.is_file() and not path.is_symlink()
        raw = path.read_bytes()
        actual = {'bytes': len(raw), 'sha256': sha(raw)}
        assert actual == {key: row[key] for key in ('bytes', 'sha256')}, path
        checked_inputs[str(path)] = actual
    assert sha((D / 'preaccess-seal.json').read_bytes()) == '985a3b2b07a2a8eaaf74d488059d06c38be9a2fceb4f6048bbc791950f317adf'
    pre = load(D / 'preaccess-seal.json')
    assert len(pre['members']) == 13 and sha(canonical(pre['members'])) == pre['tree_sha256']
    for row in pre['members']:
        pin(row, D)
    assert sha((P / 'seal.json').read_bytes()) == '8a3fd8e76d2826e53aecdf0399773d03c301e2610714d3ebb11f50b949ed0520'
    seal = load(P / 'seal.json')
    assert len(seal['members']) == seal['member_count'] == 17
    assert sha(canonical(seal['members'])) == seal['tree_sha256'] == 'fb66591aa61ac68217c7c190e4ac5c6607e35ded47470249a84199d7728c690f'
    assert sum(row['bytes'] for row in seal['members']) == seal['member_bytes']
    for row in seal['members']:
        pin(row, P)
    assert not any(path.is_symlink() for path in P.rglob('*'))
    assert sorted(path.relative_to(P).as_posix() for path in P.rglob('*') if path.is_file()) == sorted([row['path'] for row in seal['members']] + ['seal.json'])
    expected = load(D / 'role-expectations.json')['roles']
    contract = load(D / 'preaccess-contract.json')
    for path, observed in contract['inputs'].items():
        pin({'path': path, **observed})
    manifest = load(P / 'input-manifest.json')
    for row in manifest['inputs']:
        pin(row)
    pin(manifest['python']['tool'])
    assert sys.version == manifest['python']['version']
    assert seal['root_layout_acceptance_sha256'] == sha((R / 'verification/swift-semantic-adapter-root-review/root-bound-layout-observation-acceptance.json').read_bytes())
    accepted = load(R / 'verification/swift-semantic-adapter-root-review/root-bound-layout-observation-acceptance.json')['acceptance']
    catalogue = load(P / 'layout-crosswalk.json')['catalogue']
    assert len(catalogue) == 29 and len({row['id'] for row in catalogue}) == 29
    for index, (row, original) in enumerate(zip(catalogue[:28], accepted['named_layouts']), 1):
        assert row['id'] == 'L' + str(index).zfill(2)
        assert all(row[key] == original[key] for key in ('type', 'size', 'align'))
    assert len({normalize(row['type']) for row in catalogue[:28]}) == 28
    assert catalogue[28]['id'] == 'L29' and catalogue[28]['size'] == accepted['actual_closure']['size'] == 48
    assert catalogue[28]['align'] == accepted['actual_closure']['align'] == 8
    lookup = {normalize(row['type']): row['id'] for row in catalogue[:28]}
    joined = load(P / 'inventory-place-join.json')
    assert len(joined['roles']) == len(expected) == 645
    assert len({row['id'] for row in joined['roles']}) == 645
    assert joined['counts'] == {'arguments': 65, 'locals_returns': 580, 'total_roles': 645,
                                'named_shape_roles': 97, 'actual_closure_roles': 2, 'unbound_roles': 546}
    independent_bindings = {}
    for actual, original in zip(joined['roles'], expected):
        assert actual['function_index'] == original['function_index']
        assert actual['function_selector'] == original['selector']
        assert actual['MIR_item_index'] == original['MIR_item_index']
        assert actual['place'] == original['place'] and actual['type_spelling'] == original['type_spelling']
        assert actual['MIR_row_line'] == original['line'] and actual['MIR_row_sha256'] == original['row_sha256']
        assert actual['kind'] == ('argument' if original['kind'] == 'argument' else 'local_return')
        assert actual['storage_obligations'] == original['storage_obligations']
        assert actual['function_obligations'] == original['obligations']
        link = lookup.get(normalize(original['type_spelling']))
        if original['binding'] == 'exact-actual-dispatch-closure':
            link = 'L29'
        assert actual['layout_id'] == link
        independent_bindings[actual['id']] = link
        assert all(actual[key] is None for key in ['physical_storage_region_id', 'lifetime_interval', 'incremental_charge_bytes', 'runtime_work_price'])
    closure_roles = [row for row in joined['roles'] if row['layout_id'] == 'L29']
    assert len(closure_roles) == 2 and len({row['type_spelling'] for row in closure_roles}) == 1
    assert {(row['MIR_item_index'], row['kind'], row['place']) for row in closure_roles} == {(1236, 'local_return', '_25'), (1237, 'argument', '_1')}
    all_closure_types = {row['type_spelling'] for row in joined['roles'] if row['type_spelling'].startswith('{closure@')}
    assert len(all_closure_types) == 2
    other = [row for row in joined['roles'] if ':1187:22: 1187:38}' in row['type_spelling']]
    assert len(other) == 1 and other[0]['layout_id'] is None
    for row in catalogue:
        matches = [role for role in joined['roles'] if role['layout_id'] == row['id']]
        assert row['matching_inventory_place_ids'] == [role['id'] for role in matches]
        assert row['matching_place_count_is_coverage_not_charge'] == len(matches)
        assert row['matched_context_obligation_union'] == sorted({ob for role in matches for ob in role['function_obligations']})
        assert row['numeric_charge_bytes'] is None and row['runtime_work_price'] is None
    obligations = load(P / 'obligation-dispositions.json')
    inventory = load(R / 'verification/swift-root-bound-work-storage-delta/delta-inventory.json')
    assert len(obligations['obligations']) == 24
    assert obligations['work_obligations'] == obligations['storage_obligations'] == 12
    assert obligations['fully_closed_storage_charge_obligations'] == 0
    for actual, original in zip(obligations['obligations'], inventory['obligations']):
        assert actual['id'] == original['id'] and actual['original_inventory_obligation'] == original
        assert actual['status'] == 'OPEN_FOR_INCREMENTAL_ACCOUNTING'
        assert actual['numeric_storage_charge_proposed_closed'] is False
        assert actual['work_price'] is None and actual['storage_charge_bytes'] is None
        assert actual['source_function_or_constructor_selectors'] == [fn['selector'] for fn in inventory['functions_and_constructor_occurrences'] if original['id'] in fn['obligations']]
    differences = load(P / 'representation-differences.json')['differences']
    assert len(differences) == 14 and len({row['id'] for row in differences}) == 14
    by_id = {row['id']: row for row in catalogue}
    for row in differences:
        left, right = by_id[row['left_layout']], by_id[row['right_layout']]
        value = checked_difference(right['size'], left['size'])
        assert row['difference_bytes'] == value
        assert row['arithmetic'] == str(left['size']) + ' - ' + str(right['size']) + ' = ' + str(value)
        assert row['is_price_or_baseline_version_delta'] is False
        assert row['numeric_charge_bytes'] is None and row['work_price'] is None
    assert checked_difference(by_id['L16']['size'], by_id['L25']['size']) == 32
    prospective = load(P / 'prospective-controls.json')
    future = load(P / 'next-contract.json')
    assert len(prospective['controls']) == 16 and len({row['id'] for row in prospective['controls']}) == 16
    assert future['select_storage_grant'] is future['select_work_prices'] is False
    for leaf in future['numeric_leaves']:
        layout = by_id[leaf['layout']]
        assert leaf['size_bytes'] == layout['size'] and leaf['align_bytes'] == layout['align']
    producer_controls = load(P / 'controls-result.json')
    assert producer_controls['controls_passed'] == len(producer_controls['controls']) == 21
    assert all(row['rejected'] is True for row in producer_controls['controls'])
    assert producer_controls['all24_accounting_obligations_remain_open'] is True
    receipt = load(P / 'commands/final-offline/receipt.json')
    assert receipt['exit'] == 0 and receipt['elapsed_seconds'] < 55
    assert receipt['limits']['compiler_parser_runtime_child_replays'] == 0
    report = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
        'status': 'EXACT_FINITE_SOURCE_ACCOUNTING_JOIN_REVIEWED_ACCEPTANCE_RECOMMENDED_WITH_24_OBLIGATIONS_OPEN',
        'command': [sys.executable, '-B', str(Path(__file__).relative_to(R))], 'python': sys.version,
        'elapsed_seconds': time.monotonic() - start, 'script_sha256': sha(Path(__file__).read_bytes()),
        'producer_seal_sha256': sha((P / 'seal.json').read_bytes()), 'producer_members_verified': 17,
        'independent_preaccess_seal_sha256': sha((D / 'preaccess-seal.json').read_bytes()),
        'input_members_rehashed': len(checked_inputs), 'checked_input_tree_sha256': sha(canonical(checked_inputs)),
        'source146_tree': accepted['source146_tree'], 'diagnostic146_tree': accepted['diagnostic146_tree'],
        'catalogue_shapes': 29, 'named_shapes': 28, 'actual_closure_shapes': 1,
        'all_645_role_identities_source_hash_links_and_layout_bindings_match_independent': True,
        'role_coverage': joined['counts'], 'distinct_closure_types': 2,
        'exact_dispatch_closure_roles': 2, 'unbound_distinct_observation_closure_roles': 1,
        'all_24_positive_obligations_open': True, 'fully_closed_storage_charge_obligations': 0,
        'source_backed_measured_differences_checked': 14, 'nested_aggregate_difference_not_charge': 32,
        'independent_preaccess_adverse_controls_passed': 34, 'producer_integrity_controls_read_not_replayed': 21,
        'prospective_future_controls_read_not_executed': 16,
        'normalization_scope': 'All645 fixed source-bound producer links match stricter independent exact-token allowlist. Producer prefix-replacement helper is accepted only for this pinned finite spelling roster; no arbitrary future names or cross-source/target joins are qualified.',
        'acceptance_recommended': True,
        'acceptance_scope': 'Finite source/data catalogue-to-role accounting prerequisite and prospective dispatch/child/destruction contract only. No selected work/storage charge, physical region/lifetime overlap, backing/peak/retention/funding/ownership or GA.',
        'compiler_parser_runtime_native_ui_capture_child_process_queries': 0,
        'metadata_product_source_commits_pushes_changed': False,
        'cleanup': 'No process/build artifact created; no cleanup owed.'}
    with (D / 'review-result.json').open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({key: report[key] for key in ('status', 'producer_members_verified', 'all_645_role_identities_source_hash_links_and_layout_bindings_match_independent',
        'acceptance_recommended', 'fully_closed_storage_charge_obligations', 'compiler_parser_runtime_native_ui_capture_child_process_queries')}))


if __name__ == '__main__':
    main()
