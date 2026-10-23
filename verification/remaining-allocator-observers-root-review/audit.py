#!/usr/bin/env python3
"""Read-only root audit of source, executable evidence and CI command binding."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import tarfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
count = 0

def bind(path, digest):
    global count
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    assert sha(p) == digest, str(p)
    count += 1

owner = ROOT / 'verification/remaining-allocator-observers'
review = ROOT / 'verification/remaining-allocator-observers-review'
addon = review / 'combined-ci-noise'
receipts = [json.loads((p / 'receipt.json').read_text()) for p in [owner, review, addon]]
seals = [json.loads((p / 'seal.json').read_text()) for p in [review, addon]]
for p in [owner, review, addon]:
    manifest = json.loads((p / 'evidence-manifest.json').read_text())
    for name, digest in manifest['files'].items():
        bind(p / name, digest)
bind(owner / 'evidence-manifest.json', seals[0]['owner_evidence_manifest_sha256'])
bind(review / 'evidence-manifest.json', seals[0]['evidence_manifest_sha256'])
bind(review / 'receipt.json', seals[0]['independent_receipt_sha256'])
bind(review / 'findings.json', seals[0]['findings_sha256'])
bind(review / 'seal.json', seals[1]['base_review_seal_sha256'])
bind(addon / 'receipt.json', seals[1]['receipt_sha256'])
bind(addon / 'evidence-manifest.json', seals[1]['evidence_manifest_sha256'])
assert receipts[0]['source_before']['sha256'] == receipts[1]['repaired_tree_sha256'] == receipts[2]['source_tree_sha256']
for path, digest in receipts[0]['overlay'].items():
    bind(path, digest)
bind('vm/tests/common/allocation_observer.rs', receipts[0]['unchanged_pointer_ledger_sha256'])
with tarfile.open(ROOT / receipts[0]['full_snapshot']) as archive:
    source = {m.name: hashlib.sha256(archive.extractfile(m).read()).hexdigest()
              for m in archive.getmembers() if m.isfile()}
assert source == receipts[0]['source_before']['files']
count += len(source)
assert all(c['passed'] for c in json.loads((owner / 'audit-receipt.json').read_text())['checks'])
assert all(c['passed'] for c in receipts[1]['checks'])
for receipt, key in [(receipts[0], 'checks'), (receipts[1], 'commands'), (receipts[2], 'checks')]:
    for command in receipt[key]:
        assert command['exit'] == 0
        bind(command['log'], command['log_sha256'])
for receipt in receipts[1:]:
    for path, artifact in receipt['artifacts'].items():
        bind(path, artifact['sha256'])
        assert Path(path).stat().st_size == artifact['bytes']
workflow = (ROOT / '.github/workflows/verify.yml').read_text()
for command in receipts[2]['checks']:
    assert ' '.join(command['command']) in workflow
    assert command['environment']['MIXER_ALLOCATOR_NOISE'] == '1'
    assert command['passed_test_processes'] == 5
assert sum(receipts[1]['assertion_counts'].values()) == 69
assert all(len(lines) == 17 for lines in receipts[1]['measurement_runs'].values())
assert sum(r['checks'] for r in receipts[1]['derived_runs'].values()) == 172
result = {
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'command': 'python3 verification/remaining-allocator-observers-root-review/audit.py',
    'python': platform.python_version(), 'auditor_sha256': sha(Path(__file__)),
    'verified_bindings': count, 'status': 'passed',
    'source_tree_sha256': receipts[0]['source_before']['sha256'],
    'workflow_sha256': sha(ROOT / '.github/workflows/verify.yml'),
    'receipts': {str((p / 'receipt.json').relative_to(ROOT)): sha(p / 'receipt.json') for p in [owner, review, addon]},
    'seals': {str((p / 'seal.json').relative_to(ROOT)): sha(p / 'seal.json') for p in [review, addon]},
    'review': 'Root read the TLS adapter and all three test diffs. Single synchronous owner, pointer lifetime ledger and fault/gate scope remain explicit; no product engine changes. All69 original assertions and17 measurements are unchanged. Independent43 derived checks pass in four modes; combined five-test noise commands match CI and pass D/R.',
    'limitations': ['Root audited retained executable evidence; did not claim another root executable rerun.', 'The synthetic exact900byte/fourcall replay does not identify the hosted allocation origin.', 'Earlier harness failures remain retained and excluded from acceptance.', 'Single synchronous test lane and requested bytes only; no RSS, physical device, published consumer or GA qualification.']
}
(HERE / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'verified_bindings': count, 'status': result['status']}))
