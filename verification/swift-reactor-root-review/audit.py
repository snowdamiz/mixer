#!/usr/bin/env python3
"""Join exact target, independent proof review and root regression evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
owner_path = ROOT / 'verification/swift-reactor-validation/2026-10-23-final-v2/receipt.json'
review_path = ROOT / 'verification/swift-reactor-validation-review/receipt.json'
combined_path = HERE / 'combined-1/receipt.json'
matrix_path = HERE / 'feature-matrix-1/receipt.json'
owner, review, combined, matrix = [json.loads(p.read_text()) for p in [owner_path, review_path, combined_path, matrix_path]]
bindings = 0

def bound(path, expected):
    global bindings
    assert sha(path) == expected, str(path)
    bindings += 1

for source in owner['sources']: bound(ROOT / source['path'], source['sha256'])
artifact = owner['artifact']
bound(Path(artifact['path']), artifact['sha256'])
assert Path(artifact['path']).stat().st_size == artifact['bytes'] == 53777114
assert owner['valid'] and not owner['executed'] and owner['focusedChecksPassed']
for command in owner['commands']:
    assert command['exitCode'] == 0
    for stream in ['stdout', 'stderr']:
        bound(owner_path.parent / command[stream]['path'], command[stream]['sha256'])
assert review['passed'] and review['owner_source_unchanged'] and review['reviewed_source_unchanged']
for name, digest in review['reviewed_source'].items(): bound(ROOT / 'vm' / name, digest)
for archive_name, key, prefix in [('reviewed-source.tar.gz', 'reviewed_source', 'vm/'), ('baseline-source.tar.gz', 'baseline_source', 'vm/'), ('probes-source.tar.gz', 'probe_source', '')]:
    with tarfile.open(review_path.parent / archive_name) as archive:
        manifest = {entry.name.removeprefix(prefix): hashlib.sha256(archive.extractfile(entry).read()).hexdigest() for entry in archive if entry.isfile()}
    assert manifest == review[key], archive_name
    bindings += len(manifest)
for command in review['commands']:
    assert command['exit'] == command['expected'], command['name']
    for stream in ['stdout', 'stderr']: bound(ROOT / command[stream], command[stream + '_sha256'])
golden = review['legacy_observations']['baseline-stream']
assert len(review['legacy_observations']) == 5 and len(review['legacy_boundaries']) == 16
assert all(observations == golden for observations in review['legacy_observations'].values())
for name, digest in combined['source_files'].items(): bound(ROOT / name, digest)
bound(ROOT / combined['source_archive'], combined['source_archive_sha256'])
bound(ROOT / matrix['source_receipt'], matrix['source_receipt_sha256'])
assert combined['passed'] and matrix['passed'] and combined['source_tree_sha256'] == matrix['source_tree_sha256']
counts = {}
for receipt in [combined, matrix]:
    for command in receipt['commands']:
        assert command['exit'] == 0 and command['source_stable']
        log = ROOT / command['log']
        bound(log, command['sha256'])
        counts[command.get('label', command.get('name'))] = sum(int(n) for n in re.findall(r'test result: ok\. (\d+) passed;', log.read_text()))
assert counts['debug'] == counts['release'] == 263
assert counts['debug-oracles'] == counts['release-oracles'] == 9
v = owner['validation']
assert v['validated_bodies'] == v['defined_functions'] == 79832
assert v['instructions'] == 6505659 and v['work_used'] == 188428924
assert v['input_length'] == v['input_capacity'] == artifact['bytes']
assert v['runner_input_internal_reservation_peak_overlap'] == v['input_capacity'] + v['internal_total_peak_reserved']
result = {
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'command': 'python3 verification/swift-reactor-root-review/audit.py', 'python': platform.python_version(),
    'auditor_sha256': sha(Path(__file__)),
    'receipt_bindings': {str(p.relative_to(ROOT)): sha(p) for p in [owner_path, review_path, combined_path, matrix_path]},
    'verified_bindings': bindings, 'source_tree_sha256': combined['source_tree_sha256'],
    'target': artifact, 'complete_validation': v, 'test_counts': counts,
    'review': 'No open actionable independent-review defects. Zero-sized specialization preserves frozen layouts and all five legacy observation sets plus sixteen exact/minus-one budget boundaries. Root inspected source/policy/ABI/ownership/accounting changes and audited all retained command/source bindings.',
    'scope': 'Complete fixed-policy host type validation only, with bounded source/metadata/scratch reservations and same-policy adversarial fixtures. Frozen routes retain their policy. No target execution, runtime/WASI composition, native ABI/signing route, physical-device, immutable published consumer or GA acceptance. Full artifact still exceeds the 3MiB compressed delivery gate.',
}
(HERE / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'verified_bindings': bindings, 'counts': counts, 'result': 'passed'}))
