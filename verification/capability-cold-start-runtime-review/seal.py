#!/usr/bin/env python3
"""Bind this bounded review without rewriting the owner's sealed evidence."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OWNER = ROOT / 'verification/capability-cold-start-runtime'
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
expected_seal = '32d31ae27e2665dd92ba6d4e0fcfed59a9402ff18bc2a64004518c7d5db69661'
assert sha(OWNER / 'final-receipt.json') == expected_seal
owner_seal = json.loads((OWNER / 'final-receipt.json').read_text())
candidate = json.loads((OWNER / '2026-10-23-candidate-1/receipt.json').read_text())
assert candidate['source_manifest_sha256'] == '68177f0a8488386138c8e9f2a92c7ea7d4c788caf74b7053c8f648179f95c078'
for path, digest in candidate['source_files'].items():
    assert sha(Path(candidate['export']) / path) == digest, 'frozen source drift: ' + path
for path, digest in owner_seal['new_production_files'].items():
    assert sha(ROOT / path) == digest, 'production drift: ' + path
owner_manifest = OWNER / 'file-manifest.sha256'
assert sha(owner_manifest) == owner_seal['file_manifest_sha256']
owner_evidence_files = 0
for line in owner_manifest.read_text().splitlines():
    digest, path = line.split('  ', 1)
    assert sha(OWNER / path) == digest, 'owner evidence drift: ' + path
    owner_evidence_files += 1
assert owner_evidence_files == owner_seal['evidence_files']
results = {}
for mode in ['debug', 'release', 'tsan']:
    directory = HERE / ('2026-10-23-' + mode)
    path = directory / 'receipt.json'
    r = json.loads(path.read_text())
    assert r['status'] == 'two original close race cases passed'
    assert r['frozen_inputs_unchanged']
    assert r['owner_final_seal_sha256'] == expected_seal
    assert sha(HERE / 'run.py') == r['driver_sha256']
    assert sha(HERE / 'ColdStartCommitCloseProbe.swift') == r['probe_sha256']
    assert sha(r['binary']['path']) == r['binary']['sha256']
    for command in r['commands']:
        assert command['exit_code'] == 0
        assert sha(directory / command['log']) == command['log_sha256']
    for name, digest in r['state_files'].items():
        assert sha(directory / name) == digest
    for entry in r['artifacts'].values():
        assert sha(entry['path']) == entry['sha256']
    results[mode] = {'path': str(path.relative_to(ROOT)), 'sha256': sha(path), 'original_cases': 2, 'close_calls': 48}
files = {str(p.relative_to(HERE)): sha(p) for p in sorted(HERE.rglob('*'))
         if p.is_file() and '.build' not in p.relative_to(HERE).parts
         and p.name not in ['receipt.json', 'file-manifest.sha256']}
for mode in ['debug', 'release', 'tsan']:
    path = HERE / ('2026-10-23-' + mode) / 'receipt.json'
    files[str(path.relative_to(HERE))] = sha(path)
manifest = ''.join(digest + '  ' + path + '\n' for path, digest in sorted(files.items()))
(HERE / 'file-manifest.sha256').write_text(manifest)
record = {
    'status': 'bounded independent review passed; no actionable defect found',
    'completed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'reviewer': 'gpt-6.1-sol xhigh; fresh bounded review lane',
    'source_manifest_sha256': candidate['source_manifest_sha256'],
    'candidate_baseline_revision': candidate['baseline_revision'],
    'workspace_revision_at_seal': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'owner_final_seal': {'path': str((OWNER / 'final-receipt.json').relative_to(ROOT)), 'sha256': expected_seal},
    'owner_candidate_receipt': {'path': str((OWNER / '2026-10-23-candidate-1/receipt.json').relative_to(ROOT)),
                                'sha256': sha(OWNER / '2026-10-23-candidate-1/receipt.json')},
    'owner_evidence_manifest': {'path': str(owner_manifest.relative_to(ROOT)), 'sha256': sha(owner_manifest),
                                'verified_files': owner_evidence_files},
    'frozen_source_files_verified': len(candidate['source_files']),
    'current_production_files_verified': owner_seal['new_production_files'],
    'design': {'path': 'docs/capability-durable-updater-api-design.md', 'sha256': sha(ROOT / 'docs/capability-durable-updater-api-design.md')},
    'original_executions': results,
    'actionable_findings': [],
    'file_manifest_sha256': sha(HERE / 'file-manifest.sha256'), 'evidence_files': len(files),
    'new_failed_experiments': 0, 'production_mutations': False, 'committed': False, 'pushed': False,
    'limitations': [
        'Independent source review plus six original executions of two held health-commit/close races; not an exhaustive concurrency proof.',
        'Existing owner full/derived/opacity/cross-platform matrices and separate root flow probes were not rerun by this reviewer.',
        'Synthetic milestone reports do not qualify real UI/FieldLog health or separately published package consumption.',
        'Swift TSan excludes uninstrumented Rust/system frameworks; no indefinitely hung native-I/O reproduction or allocator/RSS proof.',
        'No device tools or physical-device runs; phones remain disconnected and those gates pending.',
        'No publication, customer, store, operational or GA gate qualified.',
        'A later hosted Swift 6.2.4 test-only expression repair is outside this frozen candidate review.',
    ],
}
(HERE / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({'receipt_sha256': sha(HERE / 'receipt.json'), 'evidence_files': len(files),
                  'owner_evidence_files_verified': owner_evidence_files, 'original_cases_per_mode': 2}, indent=2))
