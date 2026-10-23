#!/usr/bin/env python3
"""Combine source-bound prerequisite and contract reviews for root acceptance."""
import hashlib
import json
import platform
import runpy
import tarfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
owned = runpy.run_path(str(HERE / 'audit_owned.py'))
count = owned['count']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
def bind(path, digest):
    global count
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    assert sha(path) == digest, str(path)
    count += 1

review_dir = ROOT / 'verification/swift-cache-prerequisites-review'
review = read(review_dir / 'receipt.json')
assert review['passed'] and review['final_overlay_stable']
for item in review['producer_audit']:
    bind(item['path'], item['sha256'])
    assert item['overlay_match'] and item['producer_passed']
for command in review['commands']:
    assert command['exit'] == command['expected_exit']
    if 'source_stable' in command:
        assert command['source_stable']
    for stream in ('stdout', 'stderr'):
        bind(review_dir / command[stream]['path'], command[stream]['sha256'])
    if 'source_input' in command:
        item = command['source_input']
        bind(review_dir / item['path'], item['sha256'])
for name, key in [('frozen-source-manifest.json', 'frozen_source_manifest_sha256'), ('probe-source-manifest.json', 'probe_source_manifest_sha256'), ('probe-source.tar.gz', 'probe_source_archive_sha256'), ('run.py', 'collector_sha256'), ('source-audit.json', 'source_audit_sha256'), ('audit.py', 'audit_collector_sha256')]:
    bind(review_dir / name, review[key])
freeze = read(review_dir / 'freeze.json')
manifest = read(review_dir / 'frozen-source-manifest.json')
combined = read(HERE / 'combined-1/receipt.json')
assert freeze['baseline'] == owned['descriptor']['baseline']
reconstructed = dict(owned['baseline'])
reconstructed.update(freeze['overlay_sha256'])
assert manifest == reconstructed
count += len(manifest)
for name, digest in combined['source_files'].items():
    assert manifest[name] == digest
    bind(Path(combined['source']) / name, digest)
for name, digest in freeze['overlay_sha256'].items():
    bind(name, digest)
with tarfile.open(review_dir / 'probe-source.tar.gz') as archive:
    contents = {m.name: archive.extractfile(m).read()
                for m in archive.getmembers() if m.isfile()}
files = {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()}
assert files == read(review_dir / 'probe-source-manifest.json')
count += len(files)
differences = sorted(name for name in files.keys() | manifest.keys()
                     if files.get(name) != manifest.get(name))
assert differences == sorted(review['probe_only_differences'])
for directory, probe in [('experimental_swift_reactor', 'reviewer_control_probes.rs'),
                         ('experimental_wasi', 'reviewer_wasi_probes.rs')]:
    test = 'control_tests.rs' if directory == 'experimental_swift_reactor' else 'accounted_tests.rs'
    name = f'vm/src/{directory}/{test}'
    original = (Path(combined['source']) / name).read_bytes()
    assert contents[name] == original + f'\ninclude!("{probe}");\n'.encode()
    assert f'vm/src/{directory}/{probe}' not in manifest
    count += 2
for name, digest in files.items():
    bind(Path(freeze['source']) / name, digest)

contract_dir = ROOT / 'verification/swift-cache-contract-review/v2'
contract = read(contract_dir / 'receipt.json')
assert contract['artifact_checks_passed'] and contract['reviewed_sources_stable']
assert contract['remaining_concrete_contract_blockers'] == []
assert contract['cache_engine_acceptance_tests_executed'] == 0
for name, digest in contract['source_before'].items():
    bind(name, digest)
for command in contract['commands']:
    assert command['exit_code'] == 0
for name, digest in combined['source_files'].items():
    assert manifest[name] == digest
    count += 1
paths = [HERE / 'owner-audit.json', HERE / 'combined-1/receipt.json', review_dir / 'receipt.json', contract_dir / 'receipt.json', ROOT / 'docs/swift-cache-stage-contract.md']
receipt = {
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'command': 'python3 verification/swift-cache-prerequisites-root-review/audit.py',
    'python': platform.python_version(), 'auditor_sha256': sha(Path(__file__)),
    'accepted': True, 'verified_bindings': count,
    'accepted_source_tree_sha256': combined['source_tree_sha256'],
    'source_overlays': freeze['overlay_sha256'],
    'receipts': {str(p.relative_to(ROOT)): sha(p) for p in paths},
    'scope': 'Accept the nine private borrowed-descriptor and observed-control prerequisite paths plus the independently refined cache contract. Root combined318+9 checks per Debug/Release pass; independent7 probes per mode,103 original lib tests per mode,37 old-route regressions, privacy and literal-layout/dispatch checks pass. Authorize bounded private cache implementation only after this checkpoint, with actual layout/18-test acceptance still required.',
    'pending': ['Private cache/decoder implementation and exact concrete cleanup/construction/operation envelopes', 'All18 named cache synthetic functions and independent review', 'Executor and separately accepted bounded full-target runner', 'Physical phones, immutable published separate-repository consumers, delivery/performance and GA gates']
}
(HERE / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'accepted': True, 'verified_bindings': count}))
