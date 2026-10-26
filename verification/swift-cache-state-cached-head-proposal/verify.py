#!/usr/bin/env python3
"""Verify only this finite source-accounting rejection packet."""
import collections
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def read(name):
    return json.loads((HERE / name).read_text())


def digest(b):
    return hashlib.sha256(b).hexdigest()


def main():
    for row in read('input-bindings.json')['inputs']:
        data = (ROOT / row['path']).read_bytes()
        assert len(data) == row['bytes'] and digest(data) == row['sha256'], row['path']
    base = (ROOT / 'verification/swift-cache-state-implementation/correction-3/source/library/cache_state.rs').read_text()
    proposed = (HERE / 'source/cache_state.rs.txt').read_text()
    assembly = read('source-assembly.json')
    assert digest(base.encode()) == assembly['base_sha256']
    assert digest(proposed.encode()) == assembly['proposed_sha256']
    assert base[base.index('fn cleanup('):] == proposed[proposed.index('fn cleanup('):]
    merge = (HERE / 'source/merge.rs.txt').read_text()
    assert merge.count('cached_emit(&mut s)') == 384
    assert merge.count('cached_load_heads(&mut s)') == 63
    assert merge.count('copy_from_slice(&output)') == 6
    assert 'unsafe' not in merge and 'macro_rules!' not in merge
    assert proposed.count('SORT_COMPARISONS.fetch_add') == 1
    assert proposed.count('SORT_MOVES.fetch_add') == 1

    # Independently query the selected SOURCE-ACCOUNTING class, never any Rust
    # compiler/runtime/native or product code. This is just a template unit test.
    selected = ROOT / 'verification/swift-cache-state-g6-complete/ledger.py'
    spec = importlib.util.spec_from_file_location('selected_grammar', selected)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    trace = module.Trace('fixed-index')
    trace.e(module.I('plain', module.V('i')), 'target')
    assert sum(x['kind'] == 'scalar' for x in trace.ops) == 21  # Index20 + value1
    trace = module.Trace('range')
    trace.rangeview('indices', module.K(0), module.K(64))
    assert sum(x['kind'] == 'scalar' for x in trace.ops) == 28
    trace = module.Trace('copytail')
    trace.copytail(64)
    assert sum(x['kind'] == 'scalar' for x in trace.ops) == 7
    assert sum(x['kind'] == 'copy' for x in trace.ops) == 1

    ledger_raw = gzip.decompress((HERE / 'finite-kernel-ledger.json.gz').read_bytes())
    summary = read('kernel-ledger-summary.json')
    assert digest(ledger_raw) == summary['decompressed_sha256']
    ledger = json.loads(ledger_raw)
    ids = [x['id'] for x in ledger['events']]
    assert len(ids) == len(set(ids)) == summary['events']
    groups = collections.defaultdict(list)
    totals = {owner: {'scalars': 0, 'copies': 0} for owner in ['G3', 'G4']}
    for event in ledger['events']:
        groups[event['group']].append(event)
        totals[event['owner']]['scalars' if event['kind'] == 'scalar' else 'copies'] += 1
    for group, events in groups.items():
        assert len({e['owner'] for e in events}) == 1
        if events[0]['kind'] == 'scalar':
            assert all(e['kind'] == 'scalar' for e in events) and len(events) <= 16
        else:
            assert len(events) == 1 and 0 < events[0]['bytes'] <= 128
    assert max(e['bytes'] for e in ledger['events']) == summary['copy_max_bytes'] == 64
    for owner, total in totals.items():
        assert total['scalars'] == summary['totals'][owner]['scalars']
        assert total['copies'] == summary['totals'][owner]['copies']
        assert (total['scalars'] + 15) // 16 + total['copies'] == summary['totals'][owner]['groups']

    bound = read('necessary-bound.json')
    assert bound['head_load_scalars'] == 70
    assert bound['necessary_scalars'] == 384 * 70 + 321 * 26 + 63 * 17 == 36297
    assert bound['necessary_groups'] == (36297 + 15) // 16 + 384 == 2653 > 2568
    assert bound['even_omitting_two_slice_length_edges_per_head']['groups'] == 2605 > 2568
    g4 = read('G4-necessary-bound.json')
    assert g4['necessary_scalars'] == 384 * 29 + 57 * 12 + 6 * 28 + 6 * 44 == 12252
    assert g4['necessary_groups'] == (12252 + 15) // 16 + 12 == 778 > 768
    assert summary['totals']['G4']['groups'] == 778
    assert summary['totals']['G3']['groups'] == 2708
    witness = read('witness.json')['result']
    assert witness['comparisons'] == 321 and witness['outputs'] == witness['head_loads'] == 384
    assert [x['comparisons'] for x in witness['passes']] == [32, 48, 56, 60, 62, 63]
    model = read('model-results.json')
    assert model['cases'] == 2066 and model['all_passed']
    result = {'schema': 1, 'python': sys.version, 'command': [sys.executable, '-B', str(HERE / 'verify.py')],
              'checks_passed': True, 'candidate_accepted': False, 'G3_necessary_groups': 2653,
              'G4_necessary_groups': 778, 'G3_helper_kernel_groups': 2708,
              'G2_G5_complete_recount': 'not built after initial finite obstacle',
              'no_compiler_runtime_native_UI_capture_process_inventory': True}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
