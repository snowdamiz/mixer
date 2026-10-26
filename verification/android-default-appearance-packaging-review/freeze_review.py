#!/usr/bin/env python3
"""Freeze this review without executing product or producer code."""
import datetime
import hashlib
import json
import pathlib
import platform
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = pathlib.Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    checks = json.loads((BASE / 'frozen-proposal-checks.json').read_text())
    assert checks['status'] == 'source-and-retained-artifact-review-checks-passed'
    assert checks['producer_or_product_code_executed'] is False
    authored = [ROOT / 'docs/android-default-appearance-packaging-review.md',
                *sorted(path for path in BASE.rglob('*') if path.suffix in {'.py', '.md'})]
    for path in authored:
        text = path.read_text()
        assert text.endswith('\n'), str(path)
        assert all(line == line.rstrip() for line in text.splitlines()), str(path)
    receipt = {
        'schema_version': 1,
        'recorded_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'frozen-independent-source-contract-review-complete',
        'scope': 'Source contracts and retained artifacts only; no implementation acceptance',
        'source_revision': '99d6384306ea17643b70c472f93b57418c674f86',
        'selected_public_source_sha256': '0a399d1aaf3bcc9c24770a40a8093d8d62466f38b4244857a55ce716bd8e1d46',
        'preaccess_document_sha256': '0faed741bbac3a28c4f869eab6f6911981fdf5dbca32947468633b9b821907a5',
        'preaccess_seal_sha256': sha(BASE / 'preaccess-seal.sha256'),
        'frozen_producer_bindings': checks['frozen_proposal_bindings'],
        'review_checks': {
            'file': 'frozen-proposal-checks.json',
            'sha256': sha(BASE / 'frozen-proposal-checks.json'),
            'proposal_seal_entries': checks['proposal_seal_entries_verified'],
            'preaccess_seal_entries': checks['independent_preaccess_seal_entries_verified'],
            'retained_command_output_bindings': checks['retained_command_output_bindings_verified'],
            'authored_text_whitespace_check': 'passed',
            'authored_text_check_scope': 'Review Markdown and Python; immutable excerpts preserve original bytes.',
        },
        'review_document': {
            'path': 'verification/android-default-appearance-packaging-review/frozen-proposal-review.md',
            'sha256': sha(BASE / 'frozen-proposal-review.md'),
        },
        'root_selected_contract': 'CLI-linked canonical default generation once; locked internal asset; direct-driver lock/layout/size admission; final singleton asset inventory and byte equality; V1 unchanged',
        'root_selected_product_paths': [
            'cli/Package.swift', 'cli/Sources/MixerBuild/AndroidProject.swift',
            'cli/Sources/MixerBuild/Resources/android-build.py',
            'cli/Tests/MixerBuildTests/AndroidProjectTests.swift',
            'cli/build-tests/test_android_staging.py'],
        'root_selected_additional_test_surface': 'One new focused Python asset preflight/ZIP test file',
        'asset_preflight_order': 'Closed layout/type/size checks before general source_tree can open asset inputs and before output/tool work',
        'source_observation_scope': 'Local before/after mutation detection; not stable-input sandbox or attestation',
        'supplemental_source_manifest_sha256': sha(BASE / 'supplemental-source-manifest.json'),
        'unselected': ['ProjectGenerator edits', 'ProcessRunner edits', 'new emitter',
                       'Python supervisor', 'Swift watchdog', 'create-time copied-SDK compilation/equality policy'],
        'pending': ['Copied-SDK default/API/ABI compatibility before public V2',
                    'Native capture/lifecycle/public V2 integration',
                    'API28-35 versus private API36 runtime coverage', 'Resources/fonts/custom themes',
                    'Physical-phone/design-parity matrix', 'External immutable FieldLog packages',
                    'Signing/OTA/store/release/GA qualification'],
        'limitations': [
            'Python direct-driver layout/size/lock checks do not prove codec semantics after user rewrites an unauthenticated local lock',
            'Observed helper byte equality does not prove arbitrary copied-SDK behavior',
            'Synthetic AAPT2 archive is not an actual generated APK',
            'Optional nested process-group cancellation design and tests remain required if emitter is later selected'],
        'command': [sys.executable, str(pathlib.Path(__file__).resolve())],
        'freezer_sha256': sha(pathlib.Path(__file__).resolve()),
        'product_or_compiler_commands_run': [],
        'native_capture_ui_device_process_discovery_commands_run': [],
        'producer_packet_modified': False,
        'root_metadata_modified': False,
        'cleanup': 'No native/capture/disposable test processes started; only owned review files written',
        'python': platform.python_version(),
    }
    (BASE / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    files = [ROOT / 'docs/android-default-appearance-packaging-review.md',
             *sorted(path for path in BASE.rglob('*') if path.is_file() and path.name != 'seal.sha256')]
    seal = ''.join(sha(path) + '  ' + path.relative_to(ROOT).as_posix() + '\n' for path in sorted(files))
    (BASE / 'seal.sha256').write_text(seal)
    print(json.dumps({'review_complete': True, 'sealed_files': len(files),
                      'receipt_sha256': sha(BASE / 'receipt.json'),
                      'seal_sha256': sha(BASE / 'seal.sha256'),
                      'review_document_sha256': sha(BASE / 'frozen-proposal-review.md')}, sort_keys=True))


if __name__ == '__main__':
    main()
