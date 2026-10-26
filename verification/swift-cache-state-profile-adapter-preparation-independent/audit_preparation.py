#!/usr/bin/env python3
"""Independent read-only custody, source-alignment and wire arithmetic review."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import stat
import struct
import sys

HERE = Path(__file__).absolute().parent
ROOT = HERE.parent.parent
SOURCE = ROOT / 'verification/swift-cache-state-next-integration-preparation'
SEAL_SHA = '02f16c13fcea823444a5b775b45e778209f877259fd7222fbfbc7936c19ac412'
CUSTODY = ROOT / 'verification/swift-semantic-adapter-root-review/profile-adapter-preparation-custody.json'
CUSTODY_SHA = '4c3053701eac44d9321266bd0f110e296e4d6af8b88478c14481982d28ed1f4d'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rows(base):
    found = []
    for p in sorted(base.rglob('*')):
        mode = p.lstat().st_mode
        assert stat.S_ISDIR(mode) or stat.S_ISREG(mode)
        if stat.S_ISREG(mode):
            found.append({'path': p.relative_to(base).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)})
    return found

def main():
    assert sha(CUSTODY) == CUSTODY_SHA and sha(SOURCE / 'seal.json') == SEAL_SHA
    seal = json.loads((SOURCE / 'seal.json').read_bytes())
    actual = [r for r in rows(SOURCE) if r['path'] not in ['seal.json', 'seal.sha256']]
    assert actual == seal['members'] and len(actual) == 67 and sum(r['bytes'] for r in actual) == 1660679
    assert hashlib.sha256(''.join(r['path']+'\t'+str(r['bytes'])+'\t'+r['sha256']+'\n' for r in actual).encode()).hexdigest() == seal['tree_sha256']
    assert (SOURCE / 'seal.sha256').read_text().split()[0] == SEAL_SHA
    snapshot = HERE / 'preparation'
    snapshot.mkdir(exist_ok=False)
    for row in [*actual, {'path': 'seal.json'}, {'path': 'seal.sha256'}]:
        p = snapshot / row['path']
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE / row['path'], p)
    manifest = json.loads((snapshot / 'input-manifest.json').read_bytes())
    for row in manifest['members']:
        p = snapshot / row['snapshot']
        assert p.stat().st_size == row['bytes'] and sha(p) == row['sha256']
    canonical = ''.join(str(r['path']) + '\t' + str(r['bytes']) + '\t' + r['sha256'] + '\n' for r in sorted(manifest['members'], key=lambda r: r['path']))
    assert hashlib.sha256(canonical.encode()).hexdigest() == manifest['consulted_tree_sha256']
    seams = json.loads((snapshot / 'source-seams.json').read_bytes())
    for row in seams['members']:
        data = (snapshot / 'inputs' / row['path']).read_bytes().splitlines(keepends=True)
        selected = b''.join(data[row['first_line']-1:row['last_line']])
        excerpt = snapshot / row['excerpt']
        assert selected == excerpt.read_bytes() and len(selected) == row['bytes'] and sha(excerpt) == row['sha256']
    completion = json.loads((snapshot / 'inputs/verification/swift-ordered-retention-diagnostic-completion/candidate-manifest.json').read_bytes())
    names = ['src/experimental/swift.rs', 'src/experimental/policy.rs', 'src/experimental/metadata.rs',
        'src/experimental/descriptors.rs', 'src/experimental/reader.rs', 'src/experimental/validate.rs',
        'src/experimental/account.rs', 'src/experimental/mod.rs', 'src/experimental_wasi/mod.rs']
    additional = []
    for name in names:
        live = ROOT / 'vm' / name
        data = live.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        assert digest == completion[name]
        target = HERE / 'additional-validator-inputs' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        additional.append({'path': 'vm/' + name, 'snapshot': str(target.relative_to(HERE)),
            'bytes': len(data), 'sha256': digest, 'selected_completion_equal': True})
    wire = struct.calcsize('<IIQQQ')
    assert wire == 32 and 80000 * wire == 2560000 and 512 + 80000 * wire == 2560512
    sentinel = struct.pack('<IIQQQ', 0, 2**32-1, 2**64-1, 0, 0)
    assert struct.unpack('<4Q', sentinel) == (0xffffffff00000000, 2**64-1, 0, 0)
    variants = []
    for block in [32, 4096, 32768, 65536]:
        count = (2560000 + block - 1) // block
        variants.append({'block_bytes': block, 'rows_per_block': block // 32,
                         'blocks': count, 'max_write_calls_at32_per_block': count * 32})
    assert variants[1] == {'block_bytes': 4096, 'rows_per_block': 128, 'blocks': 625, 'max_write_calls_at32_per_block': 20000}
    source_alignment = []
    for name in ['src/experimental/cache/borrowed.rs', 'src/experimental_swift_reactor/cache.rs', 'src/experimental_swift_reactor/control.rs']:
        p = snapshot / 'inputs/vm' / name
        source_alignment.append({'path': 'vm/' + name, 'snapshot_sha256': sha(p),
            'accepted_completion_sha256': completion[name], 'equal': sha(p) == completion[name]})
    assert all(not r['equal'] for r in source_alignment)
    report = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv,
        'python': sys.version, 'script_sha256': sha(Path(__file__)),
        'preparation_seal_sha256': SEAL_SHA, 'root_custody_sha256': CUSTODY_SHA,
        'preparation_members_verified': 67, 'preparation_bytes_verified': 1660679,
        'input_snapshots_verified': len(manifest['members']), 'excerpts_verified': len(seams['members']),
        'prepared_source_revision': manifest['source_revision'], 'prepared_source_tree': manifest['source_commit_tree'],
        'additional_validator_core': additional, 'known_cache_control_differences': source_alignment,
        'wire_arithmetic_only': {'row_bytes': wire, 'body_bytes': 2560000, 'profile_bytes': 2560512,
            'first_defined_absolute': 34, 'minimum_defined_for_export62': 29,
            'maximum_defined_at_total80000_and34imports': 79966, 'last_absolute': 79999,
            'undefined_wire_hex': sentinel.hex(), 'block_bound_examples': variants},
        'root_proposed4096_625_20000_arithmetic_consistent': True,
        'no_product_source_import_compile_or_execution': True,
        'no_model_or_syntax_result_treated_as_runtime_qualification': True,
        'no_native_capture_UI_process_inventory_Git_or_canonical_edits': True,
        'scope': 'Contract/preaccess custody, exact source alignment, fixed wire arithmetic only',
        'passed_offline_preaccess_checks_only': True}
    (HERE / 'offline-audit.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    print('PASS preaccess only:67frozen members;30input snapshots;22excerpts;9validator core identities;4096/625/20000 arithmetic')

if __name__ == '__main__':
    main()
