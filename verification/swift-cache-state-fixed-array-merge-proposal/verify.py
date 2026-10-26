#!/usr/bin/env python3
"""Independent source/custody/arithmetic verifier; imports no producer code."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(name):
    return json.loads((HERE / name).read_text())


def main():
    bindings = read('input-bindings.json')
    for item in bindings['inputs']:
        data = (ROOT / item['path']).read_bytes()
        assert len(data) == item['bytes'] and sha(data) == item['sha256']
    assert sha(json.dumps(bindings['inputs'], sort_keys=True, separators=(',', ':')).encode()) == bindings['input_tree_digest']
    frozen = json.loads((ROOT / 'verification/swift-cache-state-cached-head-proposal/seal.json').read_text())
    assert frozen['member_count'] == 22 and frozen['member_bytes'] == 787075
    for item in frozen['members']:
        data = (ROOT / item['path']).read_bytes()
        assert len(data) == item['bytes'] and sha(data) == item['sha256']

    source = (HERE / 'source/merge.rs.txt').read_text()
    expansion = read('expansion.json')
    assert sha(source.encode()) == expansion['merge_sha256']
    assert "indices: &'a [u8; 64]" in source and "timestamps: &'a [[u8; 8]; 64]" in source
    assert source.count('let take_left = if s.ri >= 255 {') == 384
    assert source.count('let out = s.li as u8;') == 384 and source.count('let out = s.ri as u8;') == 384
    assert source.count('s.lp += 1;') == 384 and source.count('s.rp += 1;') == 384
    assert source.count('if s.lp < s.le {') == 384 and source.count('if s.rp < s.re {') == 384
    assert source.count('let index = s.indices[') == 894
    assert source.count('s.lt = u64::from_le_bytes(s.timestamps[index as usize]);') == 447
    assert source.count('s.rt = u64::from_le_bytes(s.timestamps[index as usize]);') == 447
    assert source.count('.first_chunk::<64>()') == 7
    assert source.count('            [\n') == 6 and source.count('.copy_from_slice(&output);') == 6
    assert 'fn cached_' not in source and 'macro_rules!' not in source
    assert 'unsafe' not in source and 'cached_emit(' not in source and 'cached_load_heads(' not in source
    assert len(expansion['emit_places']) == 384

    # A second mathematical derivation uses stable left/right sorted lists,
    # independently of the producer's cached-cursor state machine. Each run
    # interleaves until the left side is exhausted, then emits the final right.
    stamps = [int(format(i, '06b')[::-1], 2) for i in range(64)]
    values = list(range(64))
    comparisons = 0
    for width in [1, 2, 4, 8, 16, 32]:
        nxt = []
        pass_comparisons = 0
        for base in range(0, 64, width * 2):
            left = values[base:base + width]
            right = values[base + width:base + width * 2]
            assert all(stamps[left[i]] < stamps[right[i]] for i in range(width))
            assert all(stamps[right[i]] < stamps[left[i + 1]] for i in range(width - 1))
            while left and right:
                comparisons += 1
                pass_comparisons += 1
                if (stamps[left[0]], left[0]) <= (stamps[right[0]], right[0]):
                    nxt.append(left.pop(0))
                else:
                    nxt.append(right.pop(0))
            assert left == [] and len(right) == 1
            nxt += right
        assert pass_comparisons == (64 // (2 * width)) * (2 * width - 1)
        values = nxt
    assert comparisons == sum(64 - 64 // (2 * width) for width in [1, 2, 4, 8, 16, 32]) == 321
    assert values == sorted(range(64), key=lambda slot: (stamps[slot], slot))
    w = read('witness.json')
    assert w['output'] == values and w['timestamps'] == stamps
    assert [p['comparisons'] for p in w['passes']] == [32, 48, 56, 60, 62, 63]
    assert all(p['head_loads'] == p['outputs'] == 64 for p in w['passes'])
    assert sum(p['exhaustion_guard_false'] for p in w['passes']) == 126
    assert sum(p['exhaustion_guard_true'] for p in w['passes']) == 258

    templates = read('component-templates.json')['templates']
    def scalars(ops):
        return sum(op['kind'] == 'scalar' for op in ops)
    assert scalars(templates['eligible_head']) == 68
    assert [op['bytes'] for op in templates['eligible_head'] if op['kind'] == 'copy'] == [8]
    assert scalars(templates['pair_choice']) == 26
    assert scalars(templates['right_tail_choice']) == 17
    assert scalars(templates['left_exhausted_choice']) == 19
    assert scalars(templates['inline_emit_body']) == 23
    assert scalars(templates['inline_block_result']) == 1
    necessary = read('necessary-bound.json')
    assert sum(necessary['eligible_head_breakdown_scalars'].values()) == 68
    n_scalar = 384 * 68 + 321 * 26 + 63 * 17
    assert n_scalar == necessary['necessary_scalars'] == 35529
    assert (n_scalar + 15) // 16 + 384 == necessary['necessary_groups'] == 2605
    assert necessary['over_cap'] == 37 and necessary['cap'] == 2568

    raw = gzip.decompress((HERE / 'finite-subtrace-ledger.json.gz').read_bytes())
    summary = read('subtrace-summary.json')
    assert sha(raw) == summary['decompressed_sha256'] and len(raw) == summary['decompressed_bytes']
    ledger = json.loads(raw)
    events = ledger['events']
    assert len(events) == summary['event_count']
    event_map = {event['id']: event for event in events}
    assert len(event_map) == len(events)
    used = []
    for group in ledger['groups']:
        used += group['events']
        members = [event_map[name] for name in group['events']]
        assert all(e['owner'] == group['owner'] and e['kind'] == group['kind'] for e in members)
        if group['kind'] == 'scalar':
            assert 1 <= len(members) <= 16
        else:
            assert len(members) == 1 and members[0]['bytes'] == group['bytes'] <= 128
    assert sorted(used) == sorted(event_map) and len(used) == len(set(used))
    expected_scalar = {'G3': 384 * 68 + 321 * 26 + 63 * 19 + 126 * 3,
                       'G4': 384 * 24 + 57 * 12 + 6 * 28 + 6 * 44}
    expected_copy = {'G3': 384, 'G4': 12}
    for owner in ['G3', 'G4']:
        s = sum(e['owner'] == owner and e['kind'] == 'scalar' for e in events)
        c = sum(e['owner'] == owner and e['kind'] == 'copy' for e in events)
        assert s == expected_scalar[owner] and c == expected_copy[owner]
        assert summary['totals'][owner]['scalars'] == s
        assert summary['totals'][owner]['groups'] == (s + 15) // 16 + c
    assert summary['totals']['G3']['groups'] == 2637 > 2568
    assert summary['totals']['G4']['groups'] == 658

    source_binding = read('source-assembly.json')
    original = (ROOT / 'verification/swift-cache-state-implementation/correction-3/source/library/cache_state.rs').read_text()
    candidate = (HERE / 'source/cache_state.rs.txt').read_text()
    assert sha(original.encode()) == source_binding['base_sha256']
    assert sha(candidate.encode()) == source_binding['proposed_sha256']
    assert source in candidate
    assert original[original.index('fn cleanup('):] == candidate[candidate.index('fn cleanup('):]
    marker = '            sq(c, 10, mask);'
    assert original[original.index(marker):] == candidate[candidate.index(marker):]
    marker, call = '    let body = w[6] as usize;', '            merge(c);'
    assert original[original.index(marker):original.index(call)] == candidate[candidate.index(marker):candidate.index(call)]
    assert original[original.index(call):original.index('            // The preceding checked base+request guard')] == candidate[candidate.index(call):candidate.index('            // G5.')]
    print(json.dumps({'verified': 'source/custody and two finite mathematical witness derivations only',
                      'command': [sys.executable, '-B', str(HERE / 'verify.py')],
                      'source_revision': source_binding['base_sha256'],
                      'input_tree_digest': bindings['input_tree_digest'],
                      'G3_floor': 2605, 'G3_cap': 2568, 'G3_over_cap': 37,
                      'all_counted_events_grouped_once': True, 'whole_source_accepted': False,
                      'compiler_or_runtime_executed': False, 'python': sys.version}, indent=2))


if __name__ == '__main__':
    main()
