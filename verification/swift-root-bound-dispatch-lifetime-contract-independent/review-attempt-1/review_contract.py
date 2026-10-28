#!/usr/bin/env python3
"""Independent source/retained-evidence contract review; no model/checker replay."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

D = Path(__file__).resolve().parent
R = D.parents[1]
P = R / 'verification/swift-root-bound-dispatch-lifetime-contract'


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
    started = time.monotonic()
    inputs = {}
    def pin(row, base=R):
        assert time.monotonic() - started < 55
        path = base / row['path']
        assert path.is_file() and not path.is_symlink()
        raw = path.read_bytes()
        assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], path
        inputs[str(path.relative_to(R)) if path.is_relative_to(R) else str(path)] = {key: row[key] for key in ('bytes', 'sha256')}
        return raw
    assert sha((P / 'seal.json').read_bytes()) == '1ce05f8759b634e7a8c651a88ea4290b69ba8fde5bb100ed86802a0a5599a882'
    seal = load(P / 'seal.json')
    assert len(seal['members']) == seal['member_count'] == 12
    assert sha(canonical(seal['members'])) == seal['tree_sha256'] == 'c31307bddb4c3dcc9d8f87e1c86320300bec05bd1eab62df78729d5ff4c47175'
    for row in seal['members']:
        pin(row, P)
    assert sorted(path.relative_to(P).as_posix() for path in P.rglob('*') if path.is_file()) == sorted([row['path'] for row in seal['members']] + ['seal.json'])
    assert not any(path.is_symlink() for path in P.rglob('*'))
    manifest = load(P / 'input-manifest.json')
    for row in manifest['inputs']:
        pin(row)
    receipt = load(P / 'receipt.json')
    pin(receipt['python_tool'])
    assert sys.version == receipt['python'] and receipt['tests_executed'] == 0
    assert receipt['compiler_parser_runtime_child_checkers_version_commands'] == 0
    accepted = load(R / manifest['root_join_acceptance']['path'])['acceptance']
    assert accepted['status'] == 'accepted-finite-source-data-layout-accounting-prerequisite'
    assert manifest['source146_tree'] == seal['source146_tree'] == '91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f'
    inventory = load(R / 'verification/swift-root-bound-work-storage-delta/delta-inventory.json')
    frontier = load(P / 'source-frontier.json')
    retained = pin(frontier['MIR_file'])
    retained_lines = retained.splitlines(keepends=True)
    assert len(frontier['selected_methods']) == 17
    selected = []
    for row in frontier['selected_methods']:
        matches = [fn for fn in inventory['functions_and_constructor_occurrences'] if fn['selector'] == row['selector']]
        assert len(matches) == 1
        original = matches[0]
        assert row['source'] == original['source'] and row['accepted_MIR_item'] == original['MIR']
        source = row['source']
        lines = (R / source['path']).read_bytes().splitlines(keepends=True)
        body = b''.join(lines[source['first_line'] - 1:source['last_line']])
        assert len(body) == source['bytes'] and sha(body) == source['sha256']
        item = row['accepted_MIR_item']
        header = item['header'].encode()
        assert retained.count(header) == 1
        first = retained.index(header)
        mir_body = retained[first:first + item['bytes']]
        assert sha(mir_body) == item['sha256'], row['selector']
        selected.append({'selector': row['selector'], 'source_sha256': source['sha256'], 'MIR_item_index': item['index'], 'MIR_sha256': item['sha256']})
    assert len(frontier['source_blocks']) == 15
    for row in frontier['source_blocks']:
        raw = b''.join((R / row['path']).read_bytes().splitlines(keepends=True)[row['first_line'] - 1:row['last_line']])
        assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
    assert len(frontier['critical_MIR_rows']) == 19
    for row in frontier['critical_MIR_rows']:
        raw = retained_lines[row['retained_file_line'] - 1]
        assert sha(raw) == row['raw_line_sha256']
        assert raw.decode().split('//', 1)[0].strip() == row['code']
    source_root = R / 'verification/swift-guarded-snapshot-root-result-lifetime-implementation/source/vm/src/experimental_swift_reactor'
    loader = (source_root / 'retained_profile_loader_v1.rs').read_text()
    entry = (source_root / 'cache/initial_profile_v1.rs').read_text()
    host = (source_root / 'cache/initial_profile_v1/host_account_v1.rs').read_text()
    quote = host[host.index('pub(super) fn selected_whole_quote_v1()'):host.index('pub(super) fn selected_parent_account_v1()')]
    parent = host[host.index('pub(super) fn selected_parent_account_v1()'):host.index('pub(super) struct TrustedHostAccountV1')]
    assert 'Err(RefusalV1::WholeQuotePending)' in quote and 'Err(RefusalV1::RootPolicyPending)' in parent
    assert 'const COMPONENT_COUNT_V1: usize = 6;' in host
    assert 'if part.work == 0 || part.storage == 0' in host
    assert 'total.work.checked_add(part.work)' in host and 'total.storage.checked_add(part.storage)' in host
    reserve = host[host.index('pub(super) fn reserve_whole_v1'):host.index('// Neither Clone nor Copy')]
    assert reserve.index('checked_add(quote.total.work)') < reserve.index('self.usage.set(after)')
    assert reserve.index('checked_add(quote.total.storage)') < reserve.index('self.usage.set(after)')
    assert reserve.count('self.usage.set(after)') == 1
    scope = loader[loader.index("fn correlation_scope_core_v1<'owner>"):loader.index("fn correlation_scope_core_v1<'owner>") + 1000]
    assert scope.index('correlation_retirement_blocked.set(true)') < scope.index('attempt_taken.replace(true)')
    destroy = host[host.index('pub(super) fn destroy_owned_v1'):host.index('impl<T> Drop for PrepaidOwnedV1')]
    assert destroy.index('drop(owned)') < destroy.index('let reservation = self.reservation.take()') < destroy.index('drop(self)') < destroy.index('Some(DestroyedStorageV1')
    ordinary = host[host.index('impl<T> Drop for PrepaidOwnedV1'):host.index('pub(super) struct DestroyedStorageV1')]
    assert 'drop(owned)' in ordinary and 'release_destroyed_v1(' not in ordinary
    release = host[host.index("impl DestroyedStorageV1<'_>"):host.index('#[cfg(test)]')]
    assert 'checked_sub(self.reservation.storage)' in release and 'UsageV1 { storage, ..before }' in release
    retired = loader[loader.index('fn retire_acquired_owner_core_v1'):loader.index('fn retire_acquired_owner_core_v1') + 1600]
    assert retired.index('correlation_retirement_blocked.get()') < retired.index('cleanup_v1()')
    outer = entry[entry.index('fn consume_admitted_owner_once_v1'):entry.index('fn consume_admitted_owner_once_v1') + 3400]
    assert outer.index('correlation_scope_v1()') < outer.index('selected_parent_account_v1()') < outer.index('run_one_admitted_fixture_v1(') < outer.index('destroy_returned_admitted_fixture_v1(') < outer.index('release_after_retirement_v1(')
    events = load(P / 'events.json')
    regions = load(P / 'regions.json')
    quote_terms = load(P / 'quote-partitions.json')
    tests = load(P / 'prospective-tests.json')
    assert len(events['events']) == 22 and len({row['id'] for row in events['events']}) == 22
    assert events['current_production_dispatch_reachable'] is False
    assert len(regions['regions']) == 9 and len({row['id'] for row in regions['regions']}) == 9
    assert len(regions['backing_groups']) == 8
    assert regions['physical_region_map_complete'] is False and regions['numeric_grant'] is None
    terms = quote_terms['components']
    assert len(terms) == 10 and {row['id'] for row in terms} == {'A-operation', 'A-cleanup', 'A-storage', 'P0', 'C0', 'C1', 'C2', 'C3', 'C4', 'C5'}
    assert len(tests['tests']) == 20 and len({row['id'] for row in tests['tests']}) == 20
    assert tests['status'] == 'NOT_IMPLEMENTED_NOT_EXECUTED'
    implementation = (P / 'IMPLEMENTATION.md').read_text()
    assert 'model.rs' in implementation and 'tests.rs' in implementation and 'Every result remains model_only' in implementation
    assert 'IncompleteEvidence' in implementation and 'Synthetic' in implementation
    report = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
        'status': 'SOURCE_ONLY_DISPATCH_LIFETIME_CONTRACT_REVIEWED_MINIMAL_ISOLATED_MODEL_RECOMMENDED',
        'command': [sys.executable, '-B', str(Path(__file__).relative_to(R))], 'python': sys.version,
        'elapsed_seconds': time.monotonic() - started, 'script_sha256': sha(Path(__file__).read_bytes()),
        'producer_seal_sha256': sha((P / 'seal.json').read_bytes()), 'producer_members_verified': 12,
        'root_join_acceptance_sha256': sha((R / manifest['root_join_acceptance']['path']).read_bytes()),
        'source146_tree': manifest['source146_tree'], 'input_members_verified': len(inputs), 'input_tree_sha256': sha(canonical(inputs)),
        'source_MIR_methods_joined': selected, 'source_block_spans_verified': 15, 'retained_MIR_row_spans_verified': 19,
        'event_families': 22, 'semantic_ownership_regions': 9, 'backing_groups': 8, 'retained_quote_terms': 10, 'prospective_test_families': 20,
        'current_selectors_refuse': ['RootPolicyPending', 'WholeQuotePending'],
        'sticky_root_child_token_and_atomic_reserve_source_order_preserved': True,
        'no_leaf_doublecount_or_quote_partition_omission': True,
        'source_fact_physical_inference_boundary_preserved': True,
        'blocking_findings': [], 'minimal_model_implementation_recommended': True,
        'implementation_clarifications': [
            'Treat22events as finite families with explicit internal normal/unwind phases or outcomes; a payload-drop call is not an infallible atomic source operation. No token follows an interrupted payload/wrapper destruction.',
            'Keep work units distinct from byte capacities. The prepublication correlation call debits correlation work from A-operation and correlation_storage from A-storage; preserve the full existing acquisition quote and C0-C5 checked sums.',
            'PhysicalEvidenceMissing and backing/capacity gaps return IncompleteEvidence; semantic moves, containment, model IDs and observed type widths cannot manufacture physical witnesses.',
            'ModelFitsCapacity is always model_only even for reviewed-looking supplied data. Synthetic evidence cannot mint ReviewedWholeQuote, authority, reservation or production grant.',
            'Preserve explicit terminal unresolved/unreleased obligations for forget, unwind and missing final-owner destruction. Root lifetime ending never becomes durable funding evidence.'
        ],
        'minimal_next_files': ['verification/swift-root-bound-dispatch-region-model/source/model.rs', 'verification/swift-root-bound-dispatch-region-model/source/tests.rs'],
        'model_tests_implementation_or_product_code_executed': False,
        'compiler_parser_runtime_version_native_ui_capture_child_process_queries': 0,
        'numeric_grant_prices_backing_peaks_retention_funding_ownership_GA_accepted': False,
        'metadata_product_source_commits_pushes_changed': False,
        'cleanup': 'No process or build artifact created; no cleanup owed.'}
    with (D / 'review-result.json').open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({key: report[key] for key in ('status', 'producer_members_verified', 'event_families', 'semantic_ownership_regions',
        'source_block_spans_verified', 'minimal_model_implementation_recommended', 'compiler_parser_runtime_version_native_ui_capture_child_process_queries')}))


if __name__ == '__main__':
    main()
