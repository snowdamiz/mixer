#!/usr/bin/env python3
"""Audit recorded owner evidence and retained artifacts without rebuilding code."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
OWNER = ROOT / 'vm/verification/capability-native/2026-10-23-final'
FREEZE = '76372fd254e646141e991b3289b14c8380f13ea68602b21d4aa746080fddc8cf'
REFERENCE = 'cc0ac37abf45c59df7c85f59ebbb038af7c0a251'
LEGACY_SYMBOLS = {
    'invoke', 'invoke_numeric_v2', 'invoke_table_memory_v3', 'validate',
    'validate_numeric_v2', 'validate_table_memory_v3',
    *('session_' + operation + '_v1' for operation in ('create', 'invoke', 'read', 'write', 'cancel', 'close')),
}
NATIVE_SYMBOLS = {
    *('capability_' + operation + '_v1' for operation in ('validate', 'take', 'post', 'limit_deadline', 'ack_exit', 'expire')),
    *('capability_session_' + operation + '_v1' for operation in ('create', 'startup', 'enable', 'invoke', 'wake', 'read', 'write', 'cancel', 'close')),
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def check_file(path, expected):
    data = path.read_bytes()
    assert sha(data) == expected, str(path)
    return data


def main():
    owner_bytes = (OWNER / 'receipt.json').read_bytes()
    owner = json.loads(owner_bytes)
    assert owner['source_manifest_sha256'] == FREEZE
    manifest = check_file(ROOT / owner['source_manifest'], FREEZE)
    assert manifest == check_file(ROOT / 'vm/verification/capability-native/source-freeze.sha256', FREEZE)
    assert manifest == check_file(OUT / 'source-freeze.sha256', FREEZE)
    entries = [line.split('  ', 1) for line in manifest.decode().splitlines()]
    assert len(entries) == owner['source_files'] == 90
    assert len({path for _, path in entries}) == 90
    for digest, path in entries:
        check_file(ROOT / path, digest)
    for path, digest in owner['root_owned_inputs'].items():
        check_file(ROOT / path, digest)
    check_file(ROOT / 'vm/verification/capability-native/verify.py', owner['verification_driver_sha256'])
    legacy = owner['unchanged_legacy_inputs']
    assert len(legacy) == 14
    for path, digest in legacy.items():
        live = check_file(ROOT / path, digest)
        baseline = subprocess.check_output(['git', 'show', REFERENCE + ':' + path], cwd=ROOT)
        assert live == baseline, path

    commands = owner['commands']
    assert len(commands) == 76 and len({c['name'] for c in commands}) == 76
    logs = {}
    for command in commands:
        assert command['exit_code'] == 0, command['name']
        logs[command['name']] = check_file(ROOT / command['log'], command['sha256']).decode()
    required = {'format', 'fixed-payload-parity', 'clippy-default', 'clippy-all'}
    assert required <= logs.keys()
    for name, version in owner['versions'].items():
        assert logs['version-' + name].strip() == version

    test_counts = {}
    test_summaries = {}
    for name, expected in owner['test_counts'].items():
        summaries = re.findall(r'^test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;', logs[name], re.M)
        assert summaries and all(int(failed) == 0 for _, failed, _ in summaries), name
        count = {'passed': sum(int(passed) for passed, _, _ in summaries),
                 'ignored': sum(int(ignored) for _, _, ignored in summaries)}
        assert count == expected, (name, count, expected)
        test_counts[name] = count
        test_summaries[name] = len(summaries)
    assert test_counts['default-debug'] == test_counts['default-release'] == {'passed': 91, 'ignored': 8}
    assert test_counts['all-debug'] == test_counts['all-release'] == {'passed': 185, 'ignored': 9}
    for mode in ('debug', 'release'):
        assert test_counts['oracles-' + mode] == {'passed': 9, 'ignored': 0}
        ignored = set(re.findall(r'^test (\S+) \.\.\. ignored', logs['all-' + mode], re.M))
        executed = set(re.findall(r'^test (\S+) \.\.\. ok', logs['oracles-' + mode], re.M))
        assert len(ignored) == 9 and ignored <= executed
        for test, passed in [('review_session_lifetime', 1), ('capability_registry', 1),
                             ('capability_ffi_public', 4), ('capability_ffi_allocations', 1)]:
            assert test_counts[test + '-' + mode] == {'passed': passed, 'ignored': 0}
        assert 'closed_in_flight_storage_counts_until_destructor_finishes ... ok' in logs['review_session_lifetime-' + mode]
        assert 'mixed_pool_retains_closed_native_work_and_final_destructor_then_retires_handle ... ok' in logs['capability_registry-' + mode]
        assert 'retry succeeded;no quarantine/terminal/exit fabricated' in logs['capability_ffi_allocations-' + mode]
        for test in ('uncommitted_take_and_unwind_latches_cannot_be_cleared_by_success',
                     'poisoned_ledger_pins_capacity_without_fabricated_ack',
                     'quarantined_unpoisoned_close_success_never_clears_reclamation_latch'):
            assert 'capability_ffi::session::tests::' + test + ' ... ok' in logs['all-' + mode]

    symbol_counts = {}
    for label, recorded in owner['symbols'].items():
        actual = sorted(set(re.findall(r'\b_mixer_vm_\w+', logs[label + '-symbols'])))
        expected = LEGACY_SYMBOLS | (NATIVE_SYMBOLS if label in ('native', 'all') else set())
        assert actual == recorded == sorted('_mixer_vm_' + name for name in expected)
        symbol_counts[label] = len(actual)
    assert symbol_counts == {'default': 12, 'guest': 12, 'native': 27, 'all': 27}
    assert len(owner['c_smokes']) == 14
    for name, output in owner['c_smokes'].items():
        assert output == logs[name + '-run'].strip() and 'passed' in output
    for label in ('native', 'all'):
        assert 'passed27 status/alias checks' in owner['c_smokes'][label + '-capability_ffi_smoke']

    provenance_info = owner['additional_review_archive_provenance']
    provenance_bytes = check_file(ROOT / provenance_info['path'], provenance_info['sha256'])
    provenance = json.loads(provenance_bytes)
    assert provenance['source_manifest_sha256'] == FREEZE
    check_file(ROOT / provenance_info['script'], provenance_info['script_sha256'])
    assert provenance['script_sha256'] == provenance_info['script_sha256']
    assert len(provenance['commands']) == 2
    for command in provenance['commands']:
        assert command['exit_code'] == 0
        check_file(ROOT / command['log'], command['sha256'])
        assert '--features' in command['argv'] and 'experimental-capability-native' in command['argv']
    assert provenance['archives']['release']['matches_primary_native_release']
    assert provenance['archives']['release']['sha256'] == owner['artifacts']['native']['archive_sha256']
    for mode, archive in provenance['archives'].items():
        assert archive['matches_native_only_rebuild']
        check_file(Path(archive['path']), archive['sha256'])

    cross_artifacts = {}
    target = Path(owner['environment']['CARGO_TARGET_DIR'])
    for label, rust_target in [('ios-arm64', 'aarch64-apple-ios'), ('android-arm64', 'aarch64-linux-android')]:
        recorded = owner['cross_builds'][label]
        assert recorded['executed'] is False and recorded['rust_compile_time_layout_assertions'] is True
        paths = {'archive_sha256': target / rust_target / 'release/libmixer_vm.a',
                 'object_sha256': target / (label + '.o'),
                 'linked_client_sha256': target / (label + '-linked-client')}
        cross_artifacts[label] = {}
        for key, path in paths.items():
            data = check_file(path, recorded[key])
            cross_artifacts[label][key] = {'path': str(path.relative_to(ROOT)), 'sha256': sha(data), 'bytes': len(data)}
        architecture = logs[label + '-file']
        assert ('Mach-O 64-bit executable arm64' if label == 'ios-arm64' else 'ELF 64-bit LSB pie executable, ARM aarch64') in architecture
        cross_artifacts[label]['file_output'] = architecture.strip()

    public = json.loads((OUT / 'receipt.json').read_bytes())
    assert public['freeze_sha256'] == FREEZE and public['independent_public_checks_passed']
    assert public['source_export_unchanged'] and public['live_source_matches_at_end']
    for command in public['commands']:
        assert command['exit_code'] == 0
        check_file(ROOT / command['output'], command['output_sha256'])
    for name, digest in public['review_source_sha256'].items():
        check_file(OUT / name, digest)
    assert len(public['runs']) == 2
    for run in public['runs']:
        result = run['result']
        assert result['passed'] and result['public_c_checks'] >= 4500
        assert result['take_close_races'] == result['ack_close_races'] == 48
        mode = run['configuration']
        assert public['archives'][mode]['sha256'] == provenance['archives'][mode]['sha256']
    assert owner['source_unchanged_during_checks']
    assert (OWNER / 'receipt.json').read_bytes() == owner_bytes, 'owner receipt changed during audit'
    for digest, path in entries:
        check_file(ROOT / path, digest)

    (OUT / 'owner-receipt.json').write_bytes(owner_bytes)
    (OUT / 'owner-archive-provenance.json').write_bytes(provenance_bytes)
    audit = {
        'schema': 1, 'completed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command': [sys.executable, str(Path(__file__).resolve())], 'cwd': str(ROOT),
        'python_version': sys.version,
        'audit_driver_sha256': sha(Path(__file__).read_bytes()),
        'owner_receipt_path': str((OWNER / 'receipt.json').relative_to(ROOT)),
        'owner_receipt_sha256': sha(owner_bytes), 'owner_archive_provenance_sha256': sha(provenance_bytes),
        'source_manifest_sha256': FREEZE, 'verified_live_source_inputs': len(entries),
        'verified_unchanged_legacy_inputs': len(legacy), 'legacy_reference': REFERENCE,
        'verified_main_command_logs': len(commands), 'verified_supplemental_archive_logs': 2,
        'test_counts_reparsed': test_counts, 'test_summary_records': test_summaries,
        'all_nine_normally_ignored_oracle_names_matched_explicit_successes_per_mode': True,
        'symbol_counts_reparsed': symbol_counts, 'c_smoke_logs_matched': 14,
        'retained_native_archives_match_independent_public_runs': True,
        'retained_cross_artifacts_rehashed': cross_artifacts,
        'historical_host_feature_artifacts': {
            'recorded_by_owner': owner['artifacts'],
            'scope': 'Common host target paths were overwritten across feature modes. Default/guest/all archive and dylib hashes are owner build-time records, audited through source-bound driver and command logs; prior binaries are not claimed rehashed or bit-reproducible. Native release archive is independently retained, rehashed, and linked.'},
        'rebuild_variance': {
            'note': 'Native-only debug V2 and later V3 differ with unchanged 90-source freeze after feature/build-mode changes. Cause not investigated; no bit-reproducible-build claim. Both actual independent client runs retained.',
            'owner_note_sha256': sha((OWNER / 'archive-provenance-initial-check.txt').read_bytes()),
            'superseded_v2_receipt_sha256': sha((OUT / 'attempt-2/receipt.json').read_bytes()),
            'initial_mismatch_build_log_sha256': sha((OWNER / 'review-archive-debug-initial.log').read_bytes())},
        'passed': True, 'scope': 'Independent receipt/log/source/artifact audit, not a duplicate owner test run or mobile execution',
    }
    audit_path = OUT / 'owner-audit.json'
    audit_path.write_text(json.dumps(audit, indent=2) + '\n')
    output = json.dumps({'passed': True, 'source_inputs': 90, 'owner_logs': 78, 'legacy_inputs': 14,
                         'c_smokes': 14, 'retained_cross_artifacts': 6, 'owner_receipt_sha256': sha(owner_bytes)}) + '\n'
    output_path = OUT / 'owner-audit-run.log'
    output_path.write_text(output)
    public.update(owner_matrix_audit_pending=False, independent_scoped_review_passed=True,
                  owner_matrix_audit={'path': str(audit_path.relative_to(ROOT)), 'sha256': sha(audit_path.read_bytes()),
                                      'owner_receipt_sha256': sha(owner_bytes), 'passed': True,
                                      'output': str(output_path.relative_to(ROOT)), 'output_sha256': sha(output.encode())},
                  blocking_findings=[],
                  archive_provenance='Source-bound owner supplemental build/copy logs audited; exact V3 archive SHA256 matched before independent actual C debug/release link/run; release matches primary native matrix archive')
    public['limitations'][0] = 'Public races are bounded stress, not exhaustive model checking; owner barrier/unwind/poison/destructor test source and hash-bound successful logs separately audited'
    (OUT / 'receipt.json').write_text(json.dumps(public, indent=2) + '\n')
    print(output, end='')


if __name__ == '__main__':
    main()
