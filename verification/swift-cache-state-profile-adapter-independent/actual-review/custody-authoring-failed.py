#!/usr/bin/env python3
"""Copy only the released frozen candidate into this independent owned lane."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

P = Path(__file__).absolute().parent
ROOT = P.parents[2]
PRODUCER = ROOT / 'verification/swift-cache-state-profile-adapter'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    seal = PRODUCER / 'seal.json'
    assert sha(seal) == '472dc4fcffbca9718c9b7c47ced3586170ffd9ab1dbf7185b07e3b4cd2ff87a3'
    packet = json.loads(seal.read_bytes())
    for row in packet['members']:
        source = PRODUCER / row['path']
        assert not source.is_symlink()
        assert source.stat().st_size == row['bytes'] and sha(source) == row['sha256'], row['path']
    prior = json.loads((P.parent / 'seal.json').read_bytes())
    assert sha(P.parent / 'seal.json') == 'e55e941159b42477e6cae3c615c3f86faf8d7cd397dc90f84934e9a33373b30e'
    for row in prior['members']:
        source = P.parent / row['path']
        assert source.stat().st_size == row['bytes'] and sha(source) == row['sha256']
    selected = [x for x in packet['members'] if x['path'].startswith(('source/', 'closed-fixture-source/'))]
    names = ['README.md', 'decision.json', 'ACCOUNTING.md', 'accounting.json', 'accounting.py',
        'source-freeze.json', 'candidate-source-manifest.json', 'required-tests.json', 'required-bridge.json',
        'bridge.rs', 'qualify_bridge.py', 'qualify_units.py', 'run_command.py', 'tools.json',
        'unit-qualification-debug.json', 'unit-qualification-optimized.json',
        'bridge-qualification-debug.json', 'bridge-qualification-optimized.json',
        'actual-source-row-comparison.json', 'inherited-warning-inventory.json']
    selected += [x for x in packet['members'] if x['path'] in names]
    for row in selected:
        out = P / 'candidate' / row['path']
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PRODUCER / row['path'], out)
    shutil.copy2(seal, P / 'producer-seal.json')
    manifest = json.loads((P / 'candidate/candidate-source-manifest.json').read_bytes())
    assert manifest['tree_sha256'] == 'd65ea46493da772cdbf15c3f00da366feb43113c52104079147449c0aa9789cf'
    for row in manifest['members']:
        f = P / 'candidate/source/vm' / row['path']
        assert f.stat().st_size == row['bytes'] and sha(f) == row['sha256']
    frozen = json.loads((P / 'candidate/source-freeze.json').read_bytes())
    original_mismatches = []
    for row in frozen['members']:
        f = P / 'candidate/source' / row['path']
        if sha(f) != row['sha256']:
            original_mismatches.append(row['path'])
            assert row['path'] == 'vm/src/experimental_swift_reactor/mod.rs'
            b = f.read_bytes().split(b'\n// Isolated diagnostic prerequisite; no public export.')[0] + b'\n'
            assert hashlib.sha256(b).hexdigest() == row['sha256']
    assert original_mismatches == ['vm/src/experimental_swift_reactor/mod.rs']
    for src, ref in [('src/experimental/swift.rs','swift.rs'), ('src/experimental/metadata.rs','metadata.rs'),
                     ('src/experimental/policy.rs','policy.rs'), ('src/experimental/descriptors.rs','descriptors.rs'),
                     ('src/experimental_wasi/descriptor.rs','wasi-descriptor.rs')]:
        assert sha(P/'candidate/source/vm'/src) == sha(P.parent/'inputs/validator'/ref)
    for name in ['analyzer.rs', 'envelope.rs', 'cache_state.rs']:
        assert sha(P/'candidate/closed-fixture-source'/name) == sha(P.parent/'inputs/closed-fixture/source/library'/name)
    (P/'custody.json').write_text(json.dumps({'at':datetime.now(timezone.utc).isoformat(), 'argv':sys.argv,
        'producer_seal_sha256':sha(seal), 'producer_members_verified':len(packet['members']),
        'producer_bytes_verified':sum(x['bytes'] for x in packet['members']),
        'preaccess_members_unchanged':len(prior['members']),
        'original_vm_members_checked':len(frozen['members']), 'only_original_change':original_mismatches,
        'candidate_vm_tree':manifest['tree_sha256'], 'copied_selected_members':selected,
        'selected_validator_and_fixture_source_exact':True, 'no_Git_native_or_process_inventory':True},sort_keys=True,indent=2)+'\n')
    print(f'PASS custody: {len(packet["members"])} producer members; {len(prior["members"])} immutable preaccess members; {len(selected)} selected copies')


if __name__ == '__main__':
    main()
