#!/usr/bin/env python3
"""Check the final host evidence bindings without declaring native qualification."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'binding-audit.json'
checked = {}
checks = 0


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def bind(path, expected):
    global checks
    path = ROOT / path
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    require(actual == expected, 'Digest differs: ' + str(path))
    checked[str(path.relative_to(ROOT))] = actual
    checks += 1


def read(relative):
    return json.loads((ROOT / relative).read_text())


seal_path = 'verification/android-binding-stage4/evidence.json'
bind(seal_path, 'b3e912c176710d23c4982efd400a78872e409e5c5a3f64da31716ca9898e16d3')
seal = read(seal_path)
for key in ['product_and_fixed_fixture_files', 'contracts_and_separate_amendments', 'tooling_files']:
    for path, expected in seal[key].items():
        bind(path, expected)
bind(seal['canonical_source_receipt'], seal['canonical_source_receipt_sha256'])
canonical = read(seal['canonical_source_receipt'])
require(canonical['source_tree_sha256'] == seal['canonical_source_manifest_sha256'], 'Canonical source identity differs')
for path, expected in canonical['source_files'].items():
    bind(Path(seal['source_export']) / path, expected)
for path, record in seal['receipts'].items():
    bind(path, record['sha256'])
    receipt = read(path)
    for command in receipt.get('commands', []):
        bind(command['log'], command.get('log_sha256', command.get('sha256')))
    for artifact, expected in receipt.get('artifacts', {}).items():
        bind(artifact, expected)
    if 'reference' in receipt:
        bind(receipt['reference'], receipt['reference_sha256'])
for record in seal['debugger_proofs'].values():
    bind(record['path'], record['sha256'])
    require(read(record['path'])['result'] == 'passed', 'Selected debugger proof did not pass')
for record in seal['mode_limitations'].values():
    bind(record['failed_attempt'], record['failed_attempt_sha256'])
    require(read(record['failed_attempt'])['result'] == 'failed', 'Historical failure incorrectly classified')
matrix_path = 'verification/android-binding-stage4/acceptance-results.json'
bind(matrix_path, seal['acceptance_results_sha256'])
matrix = read(matrix_path)
require([row['id'] for row in matrix['cases']] == ['S4-' + str(n).zfill(2) for n in range(1, 33)], 'Original case set differs')
require(not seal['full_original_dynamic_matrix_pass'] and not matrix['full_original_dynamic_matrix_pass'], 'Incomplete matrix labeled passed')
require(matrix['cases'][20]['dynamic_pending_stage5'], 'S4-21 missing native-delivery limit')
require(matrix['cases'][28]['mode_limitations']['release/lifetime-exhaustion'], 'S4-29 missing Release limit')
for key in ['normal_android_signed_ui_enabled', 'native_witness_authority', 'physical_devices_executed']:
    require(seal[key] is False, 'Unexpected qualification: ' + key)

ci = seal['root_fresh_source_CI']
bind(ci['path'], ci['sha256'])
fresh = read(ci['path'])
for key in ['inputs', 'artifacts']:
    for path, expected in fresh[key].items():
        bind(path, expected)
extra_path = 'verification/android-binding-ci/qualified-1/test-inputs.json'
extra = read(extra_path)
bind(ci['path'], extra['receipt_sha256'])
for path, expected in extra['files'].items():
    bind(path, expected)
bind(extra_path, hashlib.sha256((ROOT / extra_path).read_bytes()).hexdigest())
with tarfile.open(ROOT / 'verification/android-binding-ci/qualified-1/source.tar.gz', 'r:gz') as archive:
    fresh_source = read(fresh['receipts']['debug'])['source_files']
    require(sorted(archive.getnames()) == sorted(fresh_source), 'Fresh source archive member set differs')
    for path, expected in fresh_source.items():
        require(hashlib.sha256(archive.extractfile(path).read()).hexdigest() == expected, 'Fresh archived source changed: ' + path)
        checks += 1
receipt = {
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'status': 'bindings_passed_independent_final_host_review_pending',
    'checks': checks, 'unique_files': len(checked), 'files': checked,
    'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'scope': 'Root binding audit of producer seal, selected logs/binaries, canonical sources, explicit failed-mode evidence, and fresh-source CI archive/receipts. Independent final host review is separate.',
    'full_original_dynamic_matrix_pass': False,
    'pending': ['S4-21 dynamic native stale event/probe/attachment delivery',
                'S4-29 optimized Release lifetime-counter injection',
                'hosted pinned Swift 6.2.4 new CI step',
                'JNI/Looper/widgets/draw/signed core integration, physical devices, published consumers and GA'],
}
require(not OUT.exists(), 'Do not overwrite an existing evidence receipt')
OUT.write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'checks': checks, 'unique_files': len(checked), 'receipt': str(OUT.relative_to(ROOT))}))
