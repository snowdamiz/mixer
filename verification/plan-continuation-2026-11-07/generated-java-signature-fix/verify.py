#!/usr/bin/env python3
"""Reproduce only pure/fake-child bootstrap and read-only-Git sparse controls."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INTEGRATION = HERE.parent / 'generated-java-ci-integration'
OWNED = [INTEGRATION / 'bootstrap.py', INTEGRATION / 'test_bootstrap.py']


def identity(file):
    data = file.read_bytes()
    return {'path': str(file.relative_to(ROOT)), 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest()}


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15).stdout


def main():
    records = []
    receipt = {'schema': 1, 'observed_utc': datetime.now(timezone.utc).isoformat(),
               'head': git('rev-parse', 'HEAD').decode().strip(),
               'head_tree': git('rev-parse', 'HEAD^{tree}').decode().strip(),
               'git_version': git('--version').decode().strip(),
               'python': sys.version, 'python_executable': sys.executable, 'platform': sys.platform,
               'scope': 'Pure/fake-child bootstrap; sparse controls additionally run bounded read-only Git.',
               'commands': records, 'owned_sources': [identity(p) for p in OWNED]}
    for optimized in (False, True):
        for test_name in ('test_bootstrap', 'test_sparse_checkout'):
            label = test_name + ('-optimized' if optimized else '-normal')
            argv = [sys.executable, '-B'] + (['-O'] if optimized else []) + [str(INTEGRATION / (test_name + '.py'))]
            started = time.monotonic()
            result = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            stdout, stderr = HERE / (label + '.stdout'), HERE / (label + '.stderr')
            stdout.write_bytes(result.stdout)
            stderr.write_bytes(result.stderr)
            records.append({'label': label, 'argv': argv, 'cwd': str(ROOT), 'timeout_seconds': 60,
                            'exit_code': result.returncode, 'elapsed_seconds': time.monotonic() - started,
                            'stdout': identity(stdout), 'stderr': identity(stderr)})
            print(label + ': exit ' + str(result.returncode), result.stderr.decode().strip())
    # Compare the authored fixture with the exact immutable failure stdout.
    spec = importlib.util.spec_from_file_location('signature_receipt_tests', INTEGRATION / 'test_bootstrap.py')
    tests = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tests)
    receipt['trust_policy'] = {
        'authority': 'Existing Commands.run must verify pkgutil exit 0 and terminal custody before returning.',
        'command': ['/usr/sbin/pkgutil', '--check-signature', '<downloaded official host archive>'],
        'streams': 'Parse the complete combined stdout/stderr; unknown fields or diagnostics refuse.',
        'statuses': [status.value for status in tests.B.PackageTrustStatus],
        'notarization': 'Mandatory trusted Apple notary service for Developer ID status; optional for legacy trusted-by-macOS/Mac OS X status, but must be trusted when present.',
        'timestamp': 'Exactly one trusted timestamp, valid UTC calendar date, no later than every certificate expiry.',
        'chain': [{'ordinal': i, 'identity': name, 'sha256': fingerprint}
                  for i, (name, fingerprint) in enumerate(tests.B.HOST_CERTIFICATES, 1)],
        'grammar': 'One package header (filename is not an admission credential), one exact status, optional/required notary field as above, trusted timestamp, exactly three complete numbered certificates. Each certificate requires valid expiry and exact SHA256 fingerprint. No leftover nonblank lines, control characters or duplicate fields. Report limit 16384 characters.',
        'scope': 'Only existing official Swift 6.3.3 host extraction; no approved-signed-extension policy, checksum-only admission, ignore-signature flag, installer registration or fallback.',
        'primary_identity_source': 'https://www.swift.org/install/macos/package_installer/',
        'primary_security_context': 'https://support.apple.com/guide/security/sec3ad8e6e53/web',
        'format_evidence': 'Exact immutable stdout from run 42427563693 attempt 1 job 128569025677; not a universal macOS output specification.',
        'compatibility_limit': 'Unknown status, renewed certificates, different chains, missing timestamps or changed report grammar require explicit policy review; fail closed.'}
    receipt['preserved_source_constraints'] = {
        'profile': 'mixer.android-source-pair.8', 'source_input_count': tests.B.SOURCE_INPUT_COUNT,
        'source_input_sha256': tests.B.SOURCE_INPUT_SHA256,
        'consumers': [m + '-' + f for m in ('debug', 'release') for f in ('original', 'relocated', 'exported')],
        'consumer_java_count': 18, 'minimum_free_bytes': tests.B.MINIMUM_FREE_BYTES,
        'bootstrap_seconds': 1200, 'bootstrap_command_seconds': 300, 'integration_seconds': 2400,
        'producer_jobs': 2, 'source_profile_runner_workflow_metadata_locks': 'No edits in this lane; parent owns rebinding and metadata.',
        'historical_processes_native_runtime_v5_phones': 'No probes, signalling, native runtime, downloads or installation performed.'}
    receipt['next_ordinary_ci'] = 'Parent must review patch, rebind owned delivery metadata as needed, commit/push under parent authority and run ordinary generated-Java CI on the new exact head. Confirm pkgutil exit 0/report admission, payload expansion, official inspect, six consumers, tamper controls and terminal cleanup. This local receipt does not establish hosted success or GA.'
    receipt['reproduce'] = 'python3 -B verification/plan-continuation-2026-11-07/generated-java-signature-fix/verify.py'
    receipt['fixture_matches_observed_stdout'] = tests.OFFICIAL_SIGNATURE.encode() == (HERE / 'observed-signature.stdout').read_bytes()
    baseline = json.loads((HERE / 'baseline-evidence.json').read_text())
    receipt['frozen_artifact_files_unchanged'] = all(
        identity(ROOT / entry['path']) == entry for entry in baseline['frozen_artifact_files'])
    acquisition = HERE.parent / 'ci-e725-generated-java-failure/acquisition.json'
    receipt['acquisition_unchanged'] = identity(acquisition)['sha256'] == baseline['acquisition_sha256']
    receipt['owned_sources_unchanged_during_tests'] = receipt['owned_sources'] == [identity(p) for p in OWNED]
    relative = [str(p.relative_to(ROOT)) for p in OWNED]
    diff_check = subprocess.run(['git', 'diff', '--check', '--', *relative], cwd=ROOT,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
    receipt['diff_check'] = {'argv': ['git', 'diff', '--check', '--', *relative],
                             'exit_code': diff_check.returncode,
                             'stdout': diff_check.stdout.decode(), 'stderr': diff_check.stderr.decode()}
    patch = HERE / 'change.patch'
    patch.write_bytes(git('diff', '--', *relative))
    receipt['patch'] = identity(patch)
    receipt['baseline_red'] = {'command': [sys.executable, '-B', str(INTEGRATION / 'test_bootstrap.py'),
                                          'BootstrapControls.test_observed_official_signature_expands_private_payload'],
                              'exit_code': 1, 'stderr': identity(HERE / 'red.stderr'),
                              'reason': 'Original substring guard rejects observed successful pkgutil report before expansion.'}
    receipt['qualification'] = 'Local controls only; ordinary hosted CI execution remains required.'
    receipt['passed'] = all(r['exit_code'] == 0 for r in records) and diff_check.returncode == 0 and all(
        receipt[key] for key in ('fixture_matches_observed_stdout', 'frozen_artifact_files_unchanged',
                                'acquisition_unchanged', 'owned_sources_unchanged_during_tests'))
    (HERE / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('receipt:', 'PASS' if receipt['passed'] else 'FAIL')
    return 0 if receipt['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
