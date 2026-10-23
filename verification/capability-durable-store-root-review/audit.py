#!/usr/bin/env python3
"""Read-only source/evidence audit of the frozen private store foundation."""
from pathlib import Path
import hashlib, json, re, subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text())
owner_path = ROOT / 'verification/capability-durable-store/final-receipt.json'
review_path = ROOT / 'verification/capability-durable-store-review/final-receipt.json'
assert sha(owner_path) == '1c668160091a5fa5cc27e027c64d71a48a057d67a3886f0dfe37122a651b0bca'
assert sha(review_path) == 'a3642344f8c3dde11ab33c4040e863b6632a2c5b0001ab4b495ce5cf84d1047b'
owner, review = load(owner_path), load(review_path)
qualification_path = ROOT / review['ownerReceipt']['path']
assert sha(qualification_path) == owner['qualification_receipt_sha256'] == review['ownerReceipt']['sha256']
q = load(qualification_path)
for name, digest in q['source_files'].items(): assert sha(Path(q['export']) / name) == digest, name
for name, digest in q['owned_files'].items(): assert sha(ROOT / name) == digest, name
for name, digest in q['baseline_files'].items():
    assert hashlib.sha256(subprocess.check_output(['git', 'show', q['dependency_revision'] + ':' + name], cwd=ROOT)).hexdigest() == digest
for row in q['commands']:
    path = ROOT / row['log']
    assert sha(path) == row['sha256'] and row['exit_code'] == row['expected_exit']
    if 'expected_tests' in row:
        actual = [int(n) for n in re.findall(rb'Executed (\d+) tests?, with 0 failures', path.read_bytes())]
        assert row['expected_tests'] in actual and row['observed_tests'] == [row['expected_tests']]
for group in q['retained_products'].values():
    for name, digest in group['files'].items(): assert sha(Path(group['directory']) / name) == digest
for outputs in q['artifacts'].values():
    for item in outputs: assert sha(Path(item['path'])) == item['sha256']
for name, digest in q['native_files'].items(): assert sha(Path(q['native_copy']) / name) == digest
for path, base, expected in [
    (owner_path.parent / 'evidence-manifest.sha256', owner_path.parent, owner['evidence_manifest_sha256']),
    (review_path.parent / 'evidence-manifest.sha256', ROOT, review['evidenceManifestSHA256'])]:
    assert sha(path) == expected
    for line in path.read_text().splitlines():
        digest, name = line.split('  ', 1)
        assert sha(base / name) == digest, name
assert not review['openActionableFindings'] and review['probeExecutions'] == 24
rpath = ROOT / review['reviewReceipt']['path']
assert sha(rpath) == review['reviewReceipt']['sha256']
r = load(rpath)
for row in r['commands']:
    assert row['exitCode'] == 0 and row['fragmentPresent']
    assert sha(rpath.parent / row['log']) == row['logSHA256']
for products in r['products'].values():
    for name, digest in products.items(): assert sha(Path(name)) == digest
for item in r['binaries'].values(): assert sha(Path(item['path'])) == item['sha256']
receipt = {
    'status': 'root source and evidence audit passed; scoped independent approval verified',
    'owner_final_sha256': sha(owner_path), 'independent_final_sha256': sha(review_path),
    'source_manifest_sha256': q['source_manifest_sha256'], 'frozen_inputs': len(q['source_files']),
    'live_owned_inputs': len(q['owned_files']), 'owner_commands': len(q['commands']),
    'host_tests': {'debug': 41, 'release': 41, 'tsan_new_tests': 18}, 'independent_probes': 24,
    'root_audit_sha256': sha(Path(__file__)),
    'reviewed_invariants': [
        'Admission before copied input, actor construction or filesystem work.',
        'One store and one active adapter obligation; concurrent owner destruction joins before capacity release.',
        'Actual I/O close, validator return and logical ingress tails gate store retirement.',
        'Closed bounded state and exact raw signed candidate identity retain sequence high-water.',
        'Real native validation and original verifier context are rechecked before payload publication.',
        'Uncertain commits poison the live owner; close clears unique metadata after diagnostics.'
    ],
    'limitations': [
        'Root audited source and preserved artifacts; did not repeat the execution matrix.',
        'Foundation qualification exports dependencies from 3bdf5cd; later policy/lifecycle composition is not tested here.',
        'No startup selection, health/effects transition, coordinator or execution-authority API exists in this slice.',
        'Logical lifetime bounds do not establish Task destruction, recoverable OOM or hard wall-time guarantees.',
        'Cross compilation is not device execution; phones remain disconnected and all product gates remain open.'
    ]
}
(HERE / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(receipt['status'])
