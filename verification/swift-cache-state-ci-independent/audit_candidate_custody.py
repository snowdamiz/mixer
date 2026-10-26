#!/usr/bin/env python3
"""Read-only independent custody/source-inventory audit, then exact owned copy."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys

HERE = Path(__file__).absolute().parent
ROOT = HERE.parent.parent
CANDIDATE = ROOT / 'verification/swift-cache-state-ci-preparation'
CUSTODY = ROOT / 'verification/swift-semantic-adapter-root-review/scalar-cursor-ci-review-custody.json'
SEAL = 'b22b11db7ce9dda9910117d730eed385793426fb220981fa15de71b9253b39f8'
RUNNER = '92bf2c0ca453ad9cae8ad6274d2248870af1cad4f4044039afde28f806d4392d'
MANIFEST = '6c52eb0ed737530d92011ce63e1eda593159c670b262a5f7bcf8b54b5338d857'
CUSTODY_SHA = '0ffc8cf911fef06179532f90109875e64583f414c82a53f82c716d1c870b9eeb'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def canonical(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def inventory(base):
    rows = []
    for p in sorted(base.rglob('*')):
        mode = p.lstat().st_mode
        assert stat.S_ISDIR(mode) or stat.S_ISREG(mode)
        if stat.S_ISREG(mode):
            rows.append({'path': p.relative_to(base).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)})
    return rows

def verify(base, rows):
    for r in rows:
        name = PurePosixPath(r['path'])
        assert not name.is_absolute() and '..' not in name.parts and '.git' not in name.parts
        p = base / name
        assert stat.S_ISREG(p.lstat().st_mode) and p.stat().st_size == r['bytes'] and sha(p) == r['sha256']

def main():
    assert sha(CUSTODY) == CUSTODY_SHA and sha(CANDIDATE / 'seal.json') == SEAL
    seal = json.loads((CANDIDATE / 'seal.json').read_bytes())
    rows = seal['members']
    assert len(rows) == 2434 and sum(r['bytes'] for r in rows) == 156179074
    verify(CANDIDATE, rows)
    assert [r for r in inventory(CANDIDATE) if r['path'] != 'seal.json'] == rows
    assert canonical(rows) == seal['tree_sha256']
    assert sha(CANDIDATE / 'check_cache_state.py') == RUNNER
    assert sha(CANDIDATE / 'pack/manifest.json') == MANIFEST
    manifest = json.loads((CANDIDATE / 'pack/manifest.json').read_bytes())
    assert len(manifest['members']) == 86 and sum(r['bytes'] for r in manifest['members']) == 8836866
    verify(CANDIDATE / 'pack', manifest['members'])
    assert [r for r in inventory(CANDIDATE / 'pack') if r['path'] != 'manifest.json'] == manifest['members']
    assert canonical(manifest['members']) == manifest['tree_sha256']
    accepted = ROOT / 'verification/swift-cache-state-scalar-cursor-implementation'
    old = json.loads((accepted / 'seal.json').read_bytes())
    old_rows = {r['path']: r for r in old['members']}
    source_rows = [r for r in manifest['members'] if r['path'].startswith('source/')]
    api_rows = [r for r in manifest['members'] if r['path'].startswith('api/')]
    assert len(source_rows) == 17 and len(api_rows) == 25
    for row in [*source_rows, *api_rows]:
        assert row == old_rows[row['path']]
    independent = json.loads((HERE / 'independent-expected-inventory.json').read_bytes())
    pack = CANDIDATE / 'pack/inventories'
    methods = json.loads((pack / 'methods.json').read_bytes())
    for n in ('host', 'producer', 'independent'):
        key = 'base' if n == 'host' else n
        assert sorted(methods[n]) == independent['methods'][key]
    assert methods['normalized_union'] == independent['methods']['normalized_base_union']
    assert methods['normalized_union_count'] == 122 and len(methods['controls']) == 94
    assert len(methods['extra_producer']) == 3 and len(methods['extra_independent']) == 7
    partition = methods['producer_debug_partition']
    assert len(partition) == 18 and sorted(n for g in partition for n in g['methods']) == sorted(methods['producer'])
    assert len({n for g in partition for n in g['methods']}) == 108
    assert sorted(len(g['methods']) for g in partition) == [1] * 17 + [91]
    for group in partition:
        if len(group['methods']) == 1:
            assert group['args'] == [group['methods'][0], '--exact']
        else:
            assert group['args'] == ['product::'] and all(n.startswith('product::') for n in group['methods'])
    layouts = json.loads((pack / 'layouts.json').read_bytes())
    assert layouts['layouts'] == independent['complete_producer_layouts']
    cases = json.loads((pack / 'file-cases.json').read_bytes())
    assert len(cases['cases']) == 31
    for packed, expected in zip(sorted(cases['cases'], key=lambda c: c['case']), sorted(independent['actual_File_case_inventory'], key=lambda c: c['case'])):
        assert {k: packed[k] for k in expected} == expected
        scope = 'private-fault-cases' if packed['scope'].startswith('private') else 'public-cases'
        name = 'evidence/' + scope + '/debug/' + packed['case'] + '/result.txt'
        assert packed['result_first_line'] == (accepted / name).read_text().splitlines()[0]
    api = json.loads((pack / 'api-contract.json').read_bytes())
    own_api = json.loads((HERE / 'independent-api-contract.json').read_bytes())
    assert api['probes'] == own_api['probes']
    copy = HERE / 'candidate-copy'
    copy.mkdir(exist_ok=False)
    shutil.copy2(CANDIDATE / 'check_cache_state.py', copy / 'check_cache_state.py')
    shutil.copytree(CANDIDATE / 'pack', copy / 'pack')
    (copy / 'runs').mkdir()
    assert sha(copy / 'check_cache_state.py') == RUNNER
    assert inventory(copy / 'pack') == inventory(CANDIDATE / 'pack')
    receipt = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv,
        'python': sys.version, 'script_sha256': sha(Path(__file__)), 'custody_sha256': CUSTODY_SHA,
        'candidate_seal_sha256': SEAL, 'candidate_members_verified': len(rows),
        'candidate_bytes_verified': sum(r['bytes'] for r in rows), 'runner_sha256': RUNNER,
        'pack_manifest_sha256': MANIFEST, 'pack_tree_sha256': manifest['tree_sha256'],
        'exact_source_roster_count': len(source_rows), 'exact_API_roster_count': len(api_rows),
        'independent_API_contract_equal': True, 'independent_method_inventory_equal': True,
        'independent_File_cases_and_results_equal': True, 'independent_layouts_equal': True,
        'owned_copy': str(copy), 'passed_custody_and_expected_inventory_only': True,
        'fresh_normal_runner_execution_pending': True}
    (HERE / 'candidate-custody.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    print('PASS custody2434members/156179074bytes; exact3-file/API25/source17; independent inventories agree; owned copy ready')

if __name__ == '__main__':
    main()
