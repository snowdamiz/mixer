#!/usr/bin/env python3
"""Read-only root verification of the final WASI source and retained evidence."""
import hashlib
import json
import platform
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
REVIEW = ROOT / 'verification/swift-accounted-wasi-review'
count = 0
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def bind(path, digest, size=None):
    global count
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    assert sha(path) == digest, str(path)
    if size is not None:
        assert path.stat().st_size == size, str(path)
    count += 1

def descriptor(d):
    bind(d['path'], d['sha256'], d.get('bytes'))

def json_file(path):
    return json.loads(path.read_text())

def evidence(path):
    d = json_file(path)
    for command in d['commands']:
        for stream in ('stdout', 'stderr'):
            descriptor(command[stream])
    for tool in d.get('toolchain_files', []):
        descriptor(tool)
    for key in ('snapshot_manifest', 'overlay_manifest', 'probe', 'source', 'source_manifests'):
        if isinstance(d.get(key), dict):
            descriptor(d[key])
    return d

review = json_file(REVIEW / 'receipt.json')
assert review['accepted']
descriptor(review['final_source_manifest'])
descriptor(review['binding_audit'])
audit = json_file(ROOT / review['binding_audit']['path'])
assert audit['passed'] and audit['total_checks'] == 953
assert all(c['success'] for c in audit['checks'])
for stage, desc in review['independent_receipts'].items():
    descriptor(desc)
    data = evidence(ROOT / desc['path'])
    assert data['expectations_met'] and data['source_stable']
descriptor(review['standalone_parity'])
parity = evidence(ROOT / review['standalone_parity']['path'])
assert parity['success'] and parity['all_observations_equal']

owner_path = ROOT / 'verification/swift-accounted-wasi/final-v2/receipt.json'
bind(owner_path, 'd08ecf98930baa2981a76fcf931691a047a3351c123be455cbc6a022b885ae34')
owner = evidence(owner_path)
assert owner['success'] and owner['source_stable']
descriptor(owner['source_manifest'])
owner_manifest = json_file(ROOT / owner['source_manifest']['path'])
assert hashlib.sha256(json.dumps(owner_manifest['files'], sort_keys=True, separators=(',', ':')).encode()).hexdigest() == owner['source_tree_sha256']
for item in owner_manifest['files']:
    historical = REVIEW / '.build/original' / item['path']
    bind(historical if historical.is_file() else ROOT / item['path'], item['sha256'], item.get('bytes'))

for desc in review['support_receipts']:
    descriptor(desc)
    receipt_path = ROOT / desc['path']
    d = json_file(receipt_path)
    assert d['passed']
    bind(receipt_path.parent.parent / 'collect.py', d['collector_sha256'])
    bind(d['source_archive'], d['source_archive_sha256'])
    for name, digest in d['source_files'].items():
        bind(Path(d['source']) / name, digest)
    with tarfile.open(ROOT / d['source_archive']) as archive:
        actual = {m.name: hashlib.sha256(archive.extractfile(m).read()).hexdigest()
                  for m in archive.getmembers() if m.isfile()}
    assert actual == d['source_files']
    count += len(actual)
    for command in d['commands']:
        assert command['exit'] == 0 and command['source_stable']
        bind(command['log'], command['sha256'])

combined = json_file(HERE / 'combined-3/receipt.json')
manifest = json_file(ROOT / review['final_source_manifest']['path'])
assert len(manifest['files']) == 58
for item in manifest['files']:
    descriptor(item)
    assert combined['source_files'][item['path']] == item['sha256']
    count += 1
for name, digest in combined['source_files'].items():
    bind(name, digest)
wiring = b'#[cfg(feature = "experimental-swift-reactor")]\npub(crate) mod accounted;\n'
for name in ('mod.rs', 'tests.rs', 'descriptor.rs', 'platform.rs'):
    relative = 'vm/src/experimental_wasi/' + name
    old = subprocess.check_output(['git', 'show', review['baseline_revision'] + ':' + relative], cwd=ROOT)
    current = (ROOT / relative).read_bytes()
    if name == 'mod.rs':
        assert current.count(wiring) == 1
        current = current.replace(wiring, b'')
    assert current == old, relative
    count += 1

result = {
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'command': 'python3 verification/swift-accounted-wasi-root-review/audit.py',
    'python': platform.python_version(), 'auditor_sha256': sha(Path(__file__)),
    'passed': True, 'verified_bindings': count,
    'reviewer_binding_checks': audit['total_checks'],
    'accepted_source_tree_sha256': combined['source_tree_sha256'],
    'review_manifest_tree_sha256': review['final_tree_sha256'],
    'receipts': {str(p.relative_to(ROOT)): sha(p) for p in [owner_path, REVIEW / 'receipt.json', HERE / 'combined-3/receipt.json']},
    'root_review': 'Root read accounted owner/control/allocation-helper changes and repaired cleanup-first loss of actual WASI diagnostics. Four buffer and header storage drops precede observed refunds; six diagnostic copies are reserved. Original standalone context stays byte-identical except private module wiring. Final combined Debug/Release each pass308 tests plus9 reference checks, focused Clippy and formatting. Independent descriptor/cancellation/fault/privacy/legacy parity evidence is bound above.',
    'limits': [
        'Historical owner final-v2 and isolated-2 predate the final cleanup fix; final acceptance binds independent final source and combined-3 only.',
        'Original/repaired finding evidence and failed root attempts remain retained, not relabeled.',
        'Requested logical storage and conservative named objects exclude allocator overhead, RSS and compiler stack measurements.',
        'Private prerequisite only: no cache/executor owner, full53MB target execution, physical devices, immutable published consumer or GA qualification.'
    ]
}
(HERE / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'passed': True, 'verified_bindings': count}))
