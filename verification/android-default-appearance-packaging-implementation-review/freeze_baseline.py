#!/usr/bin/env python3
"""Seal preaccess vectors and accepted sources without implementation access."""
import datetime
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = pathlib.Path(__file__).resolve().parent
DOCUMENT = ROOT / 'docs/android-default-appearance-packaging-implementation-review.md'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((BASE / 'accepted-source-manifest.json').read_text())
    for row in manifest['files']:
        path = BASE / 'accepted-sources' / row['path']
        assert sha(path) == row['sha256'] and path.stat().st_size == row['bytes'], row['path']
    previous = ROOT / 'verification/android-default-appearance-packaging-review/seal.sha256'
    assert sha(previous) == 'ed37dd21de797fa520a7bd2a8db369768c329551ab5a9e0d35552e3334370dee'
    for line in previous.read_text().splitlines():
        expected, name = line.split('  ', 1)
        assert sha(ROOT / name) == expected, name
    vectors = json.loads((BASE / 'vectors.json').read_text())
    assert len(vectors['vectors']) == 50
    assert all(row['execution_status'] == 'pending-frozen-handoff' for row in vectors['vectors'])
    for path in [DOCUMENT, *BASE.glob('*.py')]:
        text = path.read_text()
        assert text.endswith('\n') and all(line == line.rstrip() for line in text.splitlines()), str(path)
    result = {
        'schema_version': 1, 'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'preaccess-independent-assertions-frozen-awaiting-root-handoff',
        'command': [sys.executable, str(pathlib.Path(__file__).resolve())],
        'freezer_sha256': sha(pathlib.Path(__file__).resolve()),
        'accepted_source_revision': manifest['revision'],
        'accepted_selected_source_sha256': manifest['selected_source_sha256'],
        'accepted_source_files': len(manifest['files']),
        'vector_count': len(vectors['vectors']),
        'vectors_sha256': sha(BASE / 'vectors.json'),
        'document_sha256': sha(DOCUMENT),
        'selection_sha256': sha(BASE / 'implementation-selection.json'),
        'previous_15_file_review_preserved_and_verified': True,
        'product_working_tree_or_mutable_implementation_packet_access': False,
        'producer_or_product_code_executed': False,
        'compiler_native_capture_ui_device_process_discovery_commands': [],
        'next_action': 'Await root frozen implementation source/evidence handoff before source access or execution',
        'qualification': 'Assertions and execution plan only; all implementation checks pending',
    }
    (BASE / 'baseline-freeze.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    files = [DOCUMENT, *sorted(path for path in BASE.rglob('*') if path.is_file() and path.name != 'baseline-seal.sha256')]
    seal = ''.join(sha(path) + '  ' + path.relative_to(ROOT).as_posix() + '\n' for path in sorted(files))
    (BASE / 'baseline-seal.sha256').write_text(seal)
    print(json.dumps({'baseline_frozen': True, 'vectors': len(vectors['vectors']),
                      'files': len(files), 'baseline_seal_sha256': sha(BASE / 'baseline-seal.sha256'),
                      'baseline_freeze_receipt_sha256': sha(BASE / 'baseline-freeze.json'),
                      'document_sha256': sha(DOCUMENT)}, sort_keys=True))


if __name__ == '__main__':
    main()
