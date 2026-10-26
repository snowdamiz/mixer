#!/usr/bin/env python3
"""Offline final evidence audit and seal; executes no product code."""
import datetime
import hashlib
import json
import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = pathlib.Path(__file__).resolve().parent
PRODUCER = ROOT / 'verification/android-default-appearance-packaging'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    for line in (BASE / 'baseline-seal.sha256').read_text().splitlines():
        expected, name = line.split('  ', 1)
        assert sha(ROOT / name) == expected, name
    expected_handoff = 'ddbaabec45eaac4fc8862bec0011f518167919a8032842cb19769e9cd5e76f1d'
    expected_seal = 'e7b005b12e6534db0c32ce213e52b2a20c5313ef744bae0411b6344b6a80941f'
    assert sha(PRODUCER / 'handoff.json') == expected_handoff
    assert sha(PRODUCER / 'seal.json') == expected_seal
    producer_seal = json.loads((PRODUCER / 'seal.json').read_text())
    for name, row in producer_seal['files'].items():
        path = PRODUCER / name
        assert sha(path) == row['sha256'] and path.stat().st_size == row['bytes'], name
    for name, row in producer_seal['external_owned_files'].items():
        path = ROOT / name
        assert sha(path) == row['sha256'] and path.stat().st_size == row['bytes'], name
    inspection = json.loads((BASE / 'handoff-inspection.json').read_text())
    for name, row in inspection['source_files'].items():
        path = BASE / 'frozen-source' / name
        assert sha(path) == row['sha256'] and path.stat().st_size == row['bytes'], name
    run = BASE / 'independent-run-3'
    receipt = json.loads((run / 'receipt.json').read_text())
    vectors = json.loads((BASE / 'vectors.json').read_text())
    assert receipt['status'] == 'independent-selected-development-contract-checks-passed'
    assert set(receipt['vectors']) == {row['id'] for row in vectors['vectors']}
    assert all(row['status'] == 'passed' for row in receipt['vectors'].values())
    assert receipt['source_inputs_unchanged'] is True
    assert receipt['cleanup']['owned_scratch_removed'] is True
    assert receipt['cleanup']['all_collector_owned_command_groups_absent'] is True
    commands = 0
    for attempt in ['independent-run-1', 'independent-run-2', 'independent-run-3']:
        folder = BASE / attempt
        attempt_receipt = json.loads((folder / 'receipt.json').read_text())
        assert attempt_receipt['cleanup']['owned_scratch_removed'] is True
        for row in attempt_receipt['commands']:
            for stream in ['stdout', 'stderr']:
                assert sha(folder / row[stream]) == row[stream + '_sha256'], (attempt, row['label'], stream)
            assert row['owned_group_absent_on_completion'] is True
            commands += 1
    for identifier in ['L01-edit', 'L02-edit', 'L03-remove', 'L03-rename', 'L04-edit']:
        value = json.loads((run / ('cli-lock-' + identifier + '.stdout')).read_text())
        assert value['status'] == 'error'
        assert value['code'] == ('lock.sdk-drift' if identifier.startswith('L04') else 'lock.android-drift')
    descriptor = run / 'extracted-descriptor.json'
    assert descriptor.read_bytes() == (run / 'api-derived-default.json').read_bytes()
    assert descriptor.stat().st_size == 9587
    assert sha(descriptor) == '1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3'
    apk = run / 'IndependentAppearanceConsumer-unsigned.apk'
    assert sha(apk) == receipt['apk']['sha256'] and apk.stat().st_size == receipt['apk']['bytes']
    inventory = json.loads((run / 'apk-inventory.json').read_text())
    with zipfile.ZipFile(apk) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)) == 22
        assert [name for name in names if name == 'assets' or name.startswith('assets/')] == ['assets/MixerAppearanceV2/descriptor.json']
        assert archive.read('assets/MixerAppearanceV2/descriptor.json') == descriptor.read_bytes()
        assert set(inventory) == set(names)
        for name in names:
            assert hashlib.sha256(archive.read(name)).hexdigest() == inventory[name]['sha256'], name
    build_receipt = json.loads((run / 'generated-build-receipt.json').read_text())
    assert build_receipt['qualification'] == 'local-unsigned-cross-build-only'
    assert build_receipt['source_tree_sha256'] == build_receipt['source_tree_after_sha256']
    assert build_receipt['appearance_descriptor']['sha256'] == sha(descriptor)
    assert receipt['classes_match_frozen_producer_exactly'] == 160
    for path in [BASE / 'final-review.md', BASE / 'finalize_review.py']:
        text = path.read_text()
        assert text.endswith('\n') and all(line == line.rstrip() for line in text.splitlines())
    accepted = {
        'schema_version': 1, 'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'accepted-for-selected-development-data-packaging-slice-only',
        'reviewer_lane': 'android_descriptor_packaging_review', 'actionable_product_findings': [],
        'binding_selection_sha256': '30171f00f98ed7e27c8f9654f0c997a7c9672e282697a7a4c8fa7bfca1d98582',
        'source_base_revision': '99d6384306ea17643b70c472f93b57418c674f86',
        'producer_handoff_sha256': expected_handoff, 'producer_seal_sha256': expected_seal,
        'producer_packet_files_reverified': len(producer_seal['files']),
        'source_archive_sha256': '2f6268251008747bcb60dbacba44d8d8a7dfb30f7b3b55d8c1caa4e16d9e70c5',
        'selected_source_sha256': inspection['selected_source_sha256'], 'source_files': len(inspection['source_files']),
        'changed_paths': inspection['changed_paths'], 'preaccess_baseline_preserved': True,
        'unique_independent_vectors_passed': len(receipt['vectors']),
        'independent_exact_source_python_test_methods': 20,
        'producer_debug_release_swift_scope': 'Exact-source output hashes and assertions reviewed; duplicate broad suites not rerun.',
        'fresh_cli_and_actual_complete_unsigned_cross_build': True,
        'independent_apk': receipt['apk'],
        'descriptor': {'bytes': descriptor.stat().st_size, 'sha256': sha(descriptor)},
        'fresh_real_swift_and_java_codec_validation': True,
        'fresh_classes_match_frozen_producer': 160,
        'retained_command_output_pairs_audited': commands,
        'retained_review_setup_failures': [
            {'attempt': 'independent-run-1', 'scope': 'Version probe invoked resolved swift-driver name; no product build ran.'},
            {'attempt': 'independent-run-2', 'scope': 'Standalone D8 version probe lacked configured JAVA_HOME; no product build ran.'}],
        'product_test_or_build_failures_observed': [],
        'cleanup': receipt['cleanup'],
        'product_producer_root_metadata_modified_by_reviewer': False,
        'native_capture_ui_device_or_general_process_discovery_started': False,
        'direct_driver_semantics_under_recomputed_local_lock': 'Not claimed; layout-only acceptance of bounded nonsemantic data verified.',
        'source_observation_scope': 'Local before/after observation only; no race-free sandbox or signed authority.',
        'pending': receipt['pending'] + ['Physical design/accessibility/device matrix', 'External immutable published SDK/FieldLog qualification'],
        'public_V2_accepted': False, 'arbitrary_sdk_compatibility_accepted': False, 'release_or_GA_qualified': False,
        'command': [sys.executable, str(pathlib.Path(__file__).resolve())],
        'finalizer_sha256': sha(pathlib.Path(__file__).resolve()),
        'final_review_sha256': sha(BASE / 'final-review.md'),
    }
    (BASE / 'acceptance.json').write_text(json.dumps(accepted, indent=2, sort_keys=True) + '\n')
    files = {}
    for path in sorted(BASE.rglob('*')):
        assert not path.is_symlink(), str(path)
        if path.is_file() and path.name != 'seal.json':
            files[path.relative_to(BASE).as_posix()] = {'bytes': path.stat().st_size, 'sha256': sha(path)}
    seal = {'schema_version': 1, 'scope': 'Independent source/host/unsigned packaging development acceptance only',
            'files': files, 'external_owned_files': {
                'docs/android-default-appearance-packaging-implementation-review.md': {
                    'bytes': (ROOT / 'docs/android-default-appearance-packaging-implementation-review.md').stat().st_size,
                    'sha256': sha(ROOT / 'docs/android-default-appearance-packaging-implementation-review.md')}}}
    (BASE / 'seal.json').write_text(json.dumps(seal, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': accepted['status'], 'vectors': len(receipt['vectors']),
                      'acceptance_sha256': sha(BASE / 'acceptance.json'), 'seal_sha256': sha(BASE / 'seal.json'),
                      'sealed_files': len(files), 'bytes': sum(row['bytes'] for row in files.values())}, sort_keys=True))


if __name__ == '__main__':
    main()
