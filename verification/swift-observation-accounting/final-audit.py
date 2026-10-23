#!/usr/bin/env python3
"""Accept only the independently reviewed optional-observation correction."""
import hashlib
import json
import platform
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / 'verification/swift-observation-accounting'
REVIEW = ROOT / 'verification/swift-observation-accounting-review'
sha = lambda data: hashlib.sha256(data).hexdigest()
read = lambda path: json.loads(path.read_text())
r = read(REVIEW / 'receipt.json')
owned = read(HERE / 'root-audit.json')
assert r['decision'] == 'accept-six-optional-control-accounting-correction-and-cache-contract-v3-only'
assert r['producer_and_prior_review_bytes_unchanged']
assert r['source_tree_sha256'] == owned['source_tree_sha256']
assert r['audited_root_bindings'] == owned['verified_bindings'] == 859
assert r['artifact_tests_passed'] == 3 and r['mutants_rejected'] == 36
assert not any(r[k] for k in ['cache_implementation_accepted', 'executor_accepted',
                             'target_execution_authorized', 'physical_device_runs', 'ga_gate_changes'])
count = 0
for name, digest in r['preserved_artifacts'].items():
    assert sha((ROOT / name).read_bytes()) == digest, name
    count += 1
assert sha((REVIEW / 'review-inputs.tar').read_bytes()) == r['review_archive_sha256']
with tarfile.open(REVIEW / 'review-inputs.tar') as tar:
    archived = {m.name: sha(tar.extractfile(m).read()) for m in tar.getmembers() if m.isfile()}
assert archived == r['preserved_artifacts']
count += len(archived)
producer = read(HERE / 'isolated-1/receipt.json')
with tarfile.open(ROOT / producer['source_archive']) as tar:
    source = {m.name: tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
manifest = {p: sha(data) for p, data in source.items()}
assert manifest == producer['source_files'] == read(REVIEW / 'source-manifest.json')
count += len(manifest)
assert sha((REVIEW / 'deep_probes.rs').read_bytes()) == r['probe_sha256']
assert sha((REVIEW / 'review.py').read_bytes()) == r['script_sha256']
probe = dict(manifest)
path = 'vm/src/experimental_swift_reactor/control_tests.rs'
probe[path] = sha(source[path] + (REVIEW / 'deep_probes.rs').read_bytes())
assert sha(json.dumps(probe, sort_keys=True).encode()) == r['probe_tree_sha256']
count += 3
for c in r['commands']:
    assert c['exit'] == 0
    data = (ROOT / c['log']).read_bytes()
    assert sha(data) == c['sha256']
    if c['label'].endswith('deep-and-cleanup'):
        assert c['passed_tests'] == 30
        assert b'review_six_optional_floor_covers_standalone_deep_fault_paths ... ok' in data
    count += 1
result = {
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'command': 'python3 verification/swift-observation-accounting/final-audit.py',
    'python': platform.python_version(), 'auditor_sha256': sha(Path(__file__).read_bytes()),
    'accepted': True, 'base_revision': r['base_revision'],
    'source_tree_sha256': r['source_tree_sha256'], 'source_overlays': r['source_overlays'],
    'independent_bindings': count, 'producer_bindings': 859,
    'independent_receipt_sha256': sha((REVIEW / 'receipt.json').read_bytes()),
    'scope': 'Private shared foundation observation accounting and cache contract v3 only. Six optional shapes cover five nested control parameters plus one caller copy. Host16504-byte foundation (+464), same ticket/layout/behavior. Root320+9/73 tests per mode; independent admission plus30 control tests per mode and36 contract mutants.',
    'pending': ['Actual cache implementation and composed executor layouts/implementation',
                'Hosted CI for this source correction', 'Separately accepted bounded full-target runner',
                'Physical devices, immutable published consumer and all specified GA gates'],
}
(HERE / 'acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'accepted': True, 'independent_bindings': count, 'producer_bindings': 859}))
