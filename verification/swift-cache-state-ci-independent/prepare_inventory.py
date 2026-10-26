#!/usr/bin/env python3
"""Independently extract the accepted complete inventories, without fresh credit."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from prepare_contract import PRODUCER, INDEPENDENT, SEAL_SHA, INDEPENDENT_SEAL_SHA, accepted

HERE = Path(__file__).absolute().parent

def extract(base, seal, path):
    data, row = accepted(base, seal, path)
    return data.decode(), {'packet': base.name, **row}

def methods(text):
    found = re.findall(r'^test (\S+) \.\.\. ', text, re.M)
    assert len(found) == len(set(found))
    return sorted(found)

def main():
    provenance = []
    raw, row = extract(PRODUCER, SEAL_SHA, 'proofs/fresh-qualification.json')
    provenance.append(row)
    proof = json.loads(raw)
    raw, row = extract(PRODUCER, SEAL_SHA, 'evidence/selected-regression-summary.json')
    provenance.append(row)
    regression = json.loads(raw)
    mode_methods = {}
    for mode in ('debug', 'optimized'):
        host = proof['actual_host_method_ids'][mode]
        assert len(host) == len(set(host)) == 84
        producer = next(r for r in regression['runs'] if r['mode'] == mode and r['label'] == 'producer')['inventory']
        independent = next(r for r in regression['runs'] if r['mode'] == mode and r['label'] == 'independent')['inventory']
        normalize = lambda names: sorted(name.removeprefix('product::') for name in names)
        assert len(producer) == 108 and len(independent) == 98
        assert set(host) == set(normalize(producer)) & set(independent)
        assert len(set(normalize(producer)) | set(independent)) == 122
        raw, row = extract(PRODUCER, SEAL_SHA, 'evidence/changed-controls-' + mode + '-tests.stdout')
        provenance.append(row)
        private = methods(raw)
        assert len(private) == 3
        raw, row = extract(INDEPENDENT, INDEPENDENT_SEAL_SHA, 'evidence/tests-' + mode + '.stdout')
        provenance.append(row)
        additional = methods(raw)
        assert len(additional) == 7
        mode_methods[mode] = {'base': sorted(host), 'producer': sorted(producer),
            'independent': sorted(independent), 'normalized_base_union': sorted(set(normalize(producer)) | set(independent)),
            'private_three': private, 'independent_seven': additional,
            'base_overlap_all_three': 84, 'base_union_count': 122,
            'private_control_count': 10, 'combined_unique_count': 132}
    assert mode_methods['debug'] == mode_methods['optimized']
    layouts = proof['fresh_layouts']['debug']
    assert layouts == proof['fresh_layouts']['optimized'] and len(layouts) == 23
    cases = {}
    for mode in ('debug', 'optimized'):
        rows = proof['modes'][mode]['cases']
        cases[mode] = [{k: row[k] for k in ('case', 'scope', 'raw', 'actual_complete32', 'aggregate_present')} for row in rows]
        assert len(rows) == 31 and sum(r['aggregate_present'] for r in rows) == 29
        assert sum(r['scope'].startswith('public') for r in rows) == 29
        assert sum(r['scope'].startswith('private') for r in rows) == 2
    assert cases['debug'] == cases['optimized']
    result = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv,
        'python': sys.version, 'builder_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'basis': 'Only accepted exact frozen output; expected inventory, zero fresh execution credit',
        'candidate_files_read': False, 'provenance': provenance, 'methods': mode_methods['debug'],
        'complete_producer_layouts': layouts, 'actual_File_case_inventory': cases['debug'],
        'scope_counts': {'public': 29, 'public_complete32': 27, 'public_outer_error': 2,
                         'private_injected_poison': 2, 'private_complete32': 2},
        'finite_control_counts': {'base_merge_oracle': 1300, 'independent_merge': 16456,
            'independent_G2_admitted_G5': 2056, 'independent_malformed_refusals': 27,
            'producer_private_G5_capacity': 83, 'producer_private_admitted_malformed': 6,
            'producer_private_preG5_refusal': 5},
        'full_producer_Debug_single60s_timeout_remains_failed': True,
        'fresh_runner_or_other_compiler_target_qualified': False}
    (HERE / 'independent-expected-inventory.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print('Expected:84 common;108 producer;98 independent;122 union;10 extra;132 combined;31 File cases;23 layouts')

if __name__ == '__main__':
    main()
