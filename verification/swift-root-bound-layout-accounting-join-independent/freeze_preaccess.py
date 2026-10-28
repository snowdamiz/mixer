#!/usr/bin/env python3
"""Independent accepted-inventory/layout join expectations before producer read."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

from oracle import normalize, observed_map, checked_difference, OWNER, ENTRY, CHILD

D = Path(__file__).resolve().parent
R = D.parents[1]
INVENTORY = R / 'verification/swift-root-bound-work-storage-delta'
REVIEW = R / 'verification/swift-root-bound-work-storage-delta-independent'
ACCEPT = R / 'verification/swift-semantic-adapter-root-review/root-bound-layout-observation-acceptance.json'


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


def put(name, value):
    with (D / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def main():
    start = time.monotonic()
    inputs = {}
    def pin(path, expected=None):
        assert time.monotonic() - start < 55 and path.is_file() and not path.is_symlink()
        raw = path.read_bytes()
        row = {'bytes': len(raw), 'sha256': sha(raw)}
        if expected:
            assert row == {key: expected[key] for key in ('bytes', 'sha256')}
        inputs[path.relative_to(R).as_posix()] = row
        return raw
    for base, digest, count in [(INVENTORY, '1b077039023f424fb72f9e32902f329e3257edb50a4ab99aa42192149271cb29', 25),
                                (REVIEW, 'addd2beb80ae25174c210563bffc9122cbe655f69420170ad16305eaeef544ec', 41)]:
        assert sha(pin(base / 'seal.json')) == digest
        seal = load(base / 'seal.json')
        assert len(seal['members']) == count
        for row in seal['members']:
            pin(base / row['path'], row)
        assert sha(canonical(seal['members'])) == seal['tree_sha256']
    inventory = load(INVENTORY / 'delta-inventory.json')
    pin(ACCEPT)
    acceptance = load(ACCEPT)['acceptance']
    assert acceptance['status'] == 'accepted-retrospective-source-tool-target-bound-diagnostic-layout-observations'
    assert acceptance['source146_tree'] == inventory['candidate_source146_tree'] == '91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f'
    assert len(acceptance['named_layouts']) == 28 and acceptance['actual_closure'] == {'size': 48, 'align': 8, 'source_bits': 384, 'wrapper_bits': 448}
    for key in ['historical_query_plan', 'historical_query_receipt', 'candidate', 'offline_receipt', 'independent_observation',
                'independent_terminal_seal', 'independent_terminal_review', 'amendment_plan', 'amendment_seal', 'root_release', 'warning_provenance_seal']:
        row = acceptance[key]
        pin(R / row['path'], row)
    historical = load(R / acceptance['historical_query_plan']['path'])
    assert historical['argv'][historical['argv'].index('--target') + 1] == 'aarch64-apple-darwin'
    shapes = observed_map(acceptance['named_layouts'])
    assert len(shapes) == 28
    source_paths = set()
    for item in inventory['types'] + inventory['functions_and_constructor_occurrences']:
        source = item.get('source')
        if source:
            path = R / source['path']
            if path not in source_paths:
                pin(path, inventory['inputs'][source['path']])
                source_paths.add(path)
            lines = path.read_bytes().splitlines(keepends=True)
            span = b''.join(lines[source['first_line'] - 1:source['last_line']])
            assert len(span) == source['bytes'] and sha(span) == source['sha256']
    # These are nominal structs/enums. Equal observations do not turn them into
    # aliases, imply free construction, or authorize adding both representations.
    loader = R / 'verification/swift-guarded-snapshot-root-result-lifetime-implementation/source/vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs'
    cache = R / 'verification/swift-guarded-snapshot-root-result-lifetime-implementation/source/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs'
    child = R / 'verification/swift-guarded-snapshot-root-result-lifetime-implementation/source/vm/src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs'
    owner_text, entry_text, child_text = loader.read_text(), cache.read_text(), child.read_text()
    for needle in ["struct RootBoundV1<'root, T>", "struct CorrelatedSelectedProfileV1<'root>",
                   "struct RootBoundSelectedProfileV1<'root>", "struct OwnedCorrelationOutcomeV1<'root>",
                   "struct RootBoundFixtureOutcomeV1<'root>"]:
        assert needle in owner_text
    assert "struct AdmittedFixtureOutcomeV1<'root>" in entry_text and "enum AdmittedFixturePayloadV1<'root>" in entry_text
    assert "struct PrepaidOwnedV1<'a, T>" in child_text and 'owned: Option<T>' in child_text and "reservation: Option<ReservationV1<'a>>" in child_text
    closure_type = '{closure@' + str(cache) + ':861:36: 861:38}'
    assert cache.read_text().splitlines()[860][35:37] == '||'
    roles = []
    for fn_index, fn in enumerate(inventory['functions_and_constructor_occurrences']):
        places = [('argument', row) for row in fn['argument_places']]
        places += [('local-or-return', row) for row in fn['rows'] if 'storage_role' in row]
        for kind, place in places:
            spelling = place['storage_role']['type_spelling']
            key = normalize(spelling)
            direct = shapes.get(key)
            closure = spelling == closure_type
            if closure:
                assert (fn['MIR']['index'], kind, place['place']) in [(1236, 'local-or-return', '_25'), (1237, 'argument', '_1')]
            role_id = str(fn['MIR']['index']) + ':' + kind + ':' + place['place'] + ':' + str(place.get('line', 'header'))
            roles.append({'role_id': role_id, 'function_index': fn_index, 'selector': fn['selector'], 'MIR_item_index': fn['MIR']['index'],
                'kind': kind, 'place': place['place'], 'line': place.get('line'), 'row_sha256': place.get('sha256'),
                'type_spelling': spelling, 'normalized_type': key, 'obligations': fn['obligations'],
                'storage_obligations': place['storage_role']['obligations'],
                'binding': 'exact-named-shape' if direct else 'exact-actual-dispatch-closure' if closure else 'unobserved-exact-shape',
                'observed_layout': {'size': direct['size'], 'align': direct['align']} if direct else acceptance['actual_closure'] if closure else None,
                'not_additive_charge_or_peak': True})
    assert len(roles) == 645 and sum(row['kind'] == 'argument' for row in roles) == 65
    assert len({row['role_id'] for row in roles}) == 645
    counts = {key: sum(row['binding'] == key for row in roles) for key in ['exact-named-shape', 'exact-actual-dispatch-closure', 'unobserved-exact-shape']}
    assert counts['exact-actual-dispatch-closure'] == 2
    pairs = [
        ('RawSelectedBundleV1', "RootBoundV1<'static, RawSelectedBundleV1>"),
        ("RootBoundV1<'static, RawSelectedBundleV1>", "CorrelatedSelectedProfileV1<'static>"),
        ("RootBoundV1<'static, RawSelectedBundleV1>", "RootBoundSelectedProfileV1<'static>"),
        ('RawCorrelationOutcomeV1', "RootBoundV1<'static, RawCorrelationOutcomeV1>"),
        ("RootBoundV1<'static, RawCorrelationOutcomeV1>", "OwnedCorrelationOutcomeV1<'static>"),
        ('RawFixtureResultV1', "RootBoundV1<'static, RawFixtureResultV1>"),
        ("RootBoundV1<'static, RawFixtureResultV1>", "RootBoundFixtureOutcomeV1<'static>"),
        ("RootBoundFixtureOutcomeV1<'static>", "AdmittedFixturePayloadV1<'static>"),
        ("AdmittedFixturePayloadV1<'static>", "AdmittedFixtureOutcomeV1<'static>"),
        ("AdmittedFixtureOutcomeV1<'static>", "Option<AdmittedFixtureOutcomeV1<'static>>"),
        ("Option<AdmittedFixtureOutcomeV1<'static>>", "PrepaidOwnedV1<'static, AdmittedFixtureOutcomeV1<'static>>"),
        ("PrepaidOwnedV1<'static, AdmittedFixtureOutcomeV1<'static>>", "Result<PrepaidOwnedV1<'static, AdmittedFixtureOutcomeV1<'static>>, RefusalV1>"),
        ("RootBoundV1<'static, Result<LoaderCarrierCoreV1<File>, (OriginalCorrelationRefusalV1, LoaderCarrierCoreV1<File>)>>",
         "Result<RootBoundV1<'static, LoaderCarrierCoreV1<File>>, RootBoundV1<'static, (OriginalCorrelationRefusalV1, LoaderCarrierCoreV1<File>)>>"),
        ("(AdmittedLoaderCorrespondenceV1<'static, 'static>, PrepaidCorrelationAttemptV1<'static, 'static>)",
         "Result<(AdmittedLoaderCorrespondenceV1<'static, 'static>, PrepaidCorrelationAttemptV1<'static, 'static>), BootstrapFailureV1>")]
    differences = [{'source': a, 'destination': b, 'source_size': shapes[normalize(a)]['size'], 'destination_size': shapes[normalize(b)]['size'],
                    'observed_aggregate_difference': checked_difference(shapes[normalize(a)]['size'], shapes[normalize(b)]['size']),
                    'not_work_price_or_storage_charge_or_peak': True} for a, b in pairs]
    assert len(differences) == 14
    obligations = []
    for obligation in inventory['obligations']:
        linked = [row for row in roles if obligation['id'] in row['obligations']]
        obligations.append({**obligation, 'status': 'OPEN_POSITIVE_OBLIGATION',
            'role_links': len(linked), 'representation_witness_role_links': sum(row['observed_layout'] is not None for row in linked),
            'layout_frontier_only': 'Some exact representations now observed; all work prices/backing/lifetime overlap/funding/drop completeness remain separate unresolved evidence.',
            'price': 'UNRESOLVED', 'complete_storage_charge': 'UNRESOLVED'})
    assert len(obligations) == 24 and sum(row['id'].startswith('W') for row in obligations) == 12
    put('role-expectations.json', {'schema': 1, 'roles': roles, 'counts': counts, 'total_roles': len(roles),
                                  'aggregation': 'Links are overlapping place coverage; do not sum role sizes as charge or simultaneous peak.'})
    put('shape-differences.json', {'schema': 1, 'differences': differences,
        'nested_fixture_to_child_difference': checked_difference(shapes[normalize('RawFixtureResultV1')]['size'], shapes[normalize("PrepaidOwnedV1<'static, AdmittedFixtureOutcomeV1<'static>>")]['size']),
        'nested_difference_scope': 'Observed complete-size difference32 across source-bound nesting; not standalone reservation/root width, extra allocation, charge or simultaneous peak.'})
    put('obligation-frontier.json', {'schema': 1, 'obligations': obligations, 'all_24_positive_obligations_remain_open': True})
    put('preaccess-contract.json', {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
        'status': 'FROZEN_INDEPENDENT_ACCOUNTING_JOIN_EXPECTATIONS_BEFORE_PRODUCER_ACCESS',
        'command': [sys.executable, '-B', str(Path(__file__).relative_to(R))], 'python': sys.version,
        'elapsed_seconds': time.monotonic() - start, 'inputs': inputs,
        'source146_tree': acceptance['source146_tree'], 'diagnostic146_tree': acceptance['diagnostic146_tree'],
        'target': 'aarch64-apple-darwin', 'compiler': historical['compiler'], 'named_shapes': 28, 'actual_closure': acceptance['actual_closure'],
        'role_counts': counts, 'argument_roles': 65, 'local_return_roles': 580, 'distinct_type_spellings': len({row['type_spelling'] for row in roles}),
        'normalization': 'Only enumerated source-qualified names and std Result/Option/File aliases; preserve nominal newtypes, all type payload parameters, lifetime generic arity, references/mutability and unknowns. Lifetime abstraction is representation-only.',
        'forbidden_inferences': ['additive645-role charge or peak', 'generic R/T/A/B/E substituted with concrete File/fixture', 'arbitrary module suffix match',
            'newtype unwrapped as alias', 'closure capture-proxy sum', 'reference layout funding pointee', 'zero measured delta means zero work',
            'layout closes work/backing/peak/lifetime/retention/funding/ownership obligations'],
        'all_24_obligations_open': True, 'prospective_queries_authorized': False,
        'producer_join_accessed': False, 'compiler_runtime_native_ui_capture_process_queries': 0,
        'cleanup': 'No process or build artifact created; no cleanup owed.'})
    print(json.dumps({'status': 'INDEPENDENT_JOIN_PREACCESS_FROZEN', 'roles': len(roles), 'counts': counts, 'obligations': 24,
                      'differences': len(differences), 'producer_join_accessed': False, 'compiler_runtime_invocations': 0}))


if __name__ == '__main__':
    main()
