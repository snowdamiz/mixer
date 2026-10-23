#!/usr/bin/env python3
"""Accept only the independently reviewed immutable instruction-observation delta."""
import hashlib
import json
import platform
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / 'verification/swift-instruction-observation'
REVIEW = ROOT / 'verification/swift-instruction-observation-review'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
r = read(REVIEW / 'receipt.json')
owned = read(HERE / 'root-audit.json')
assert r['passed'] and r['producer_artifacts_unchanged']
assert r['decision'] == 'accepted-private-instruction-observation-prerequisite'
assert r['source_tree_sha256'] == owned['source_tree_sha256']
assert r['audited_bindings'] == owned['verified_bindings'] == 853
count = 0
for name, digest in r['preserved_artifacts'].items():
    assert sha(ROOT / name) == digest, name
    count += 1
for name, digest in r['changed_sources'].items():
    original = subprocess.check_output(['git', 'show', r['revision'] + ':' + name], cwd=ROOT)
    assert hashlib.sha256(original).hexdigest() == digest
    count += 1
assert sha(ROOT / r['source_archive']) == r['source_archive_sha256']
with tarfile.open(ROOT / r['source_archive']) as archive:
    files = {m.name: hashlib.sha256(archive.extractfile(m).read()).hexdigest() for m in archive.getmembers() if m.isfile()}
assert len(files) == r['source_files']
assert files == read(REVIEW / 'source-manifest.json')
assert files == read(HERE / 'isolated-1/receipt.json')['source_files']
count += len(files)
assert sha(REVIEW / 'boundary_probes.rs') == r['probe_sha256']
assert sha(REVIEW / 'review.py') == r['script_sha256']
count += 3
for c in r['commands']:
    assert c['exit'] == 0
    assert sha(ROOT / c['log']) == c['sha256']
    count += 1
result = {
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'command': 'python3 verification/swift-instruction-observation/final-audit.py',
    'python': platform.python_version(), 'auditor_sha256': sha(Path(__file__)),
    'accepted': True, 'revision': r['revision'], 'source_tree_sha256': r['source_tree_sha256'],
    'source_overlays': r['changed_sources'], 'independent_bindings': count,
    'producer_bindings': 853, 'independent_receipt_sha256': sha(REVIEW / 'receipt.json'),
    'scope': 'Private observed instruction/fuel delta only. Root319+9 tests per mode and72 minimal-Swift library per mode; independent actual eleven cases and3 additional probes per mode. Unchanged stored layouts, None wrappers, arithmetic/order, first-cause observations and no-effect repetition.',
    'pending': ['Separate reviewed shared-foundation observation shape/count accounting amendment discovered by cache layout measurement', 'Private cache implementation acceptance and executor contract/implementation', 'Separately accepted bounded target runner, physical devices, immutable published consumer and GA qualification']
}
(HERE / 'acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'accepted': True, 'independent_bindings': count, 'producer_bindings': 853}))
