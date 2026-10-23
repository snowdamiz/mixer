#!/usr/bin/env python3
"""Match implementing-lane receipts and raw outputs to the immutable source pin.

This audits existing evidence; it does not independently rerun those commands.
"""
from pathlib import Path
import datetime
import hashlib
import json
import os
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PIN = '16f6175441565adf5d1a2dc13bf2a591e65518e6'
EVIDENCE = ROOT / 'services/verification/http-v2-2026-10-22'


def check(value, reason):
    if not value:
        raise RuntimeError(reason)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def main():
    output = HERE / 'evidence' / '16f6175-matched-evidence-final.json'
    check(not output.exists(), 'evidence report already exists')
    report = {'schema': 1, 'status': 'running', 'source_revision': PIN,
              'scope': __doc__, 'script_sha256': digest(Path(__file__).read_bytes()),
              'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'invocation': [os.sys.executable, '-B', str(Path(__file__))],
              'python_version': os.sys.version, 'commands': []}

    def git(*args):
        command = ['/usr/bin/git', *args]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, check=False)
        report['commands'].append({'argv': command, 'working_directory': str(ROOT), 'exit_code': result.returncode,
                                   'stdout_bytes': len(result.stdout), 'stdout_sha256': digest(result.stdout),
                                   'stderr_bytes': len(result.stderr), 'stderr_sha256': digest(result.stderr)})
        check(result.returncode == 0, 'git evidence command failed')
        return result.stdout

    try:
        report['git_version'] = git('--version').decode().strip()
        receipt = load(EVIDENCE / 'receipt.json')
        source = receipt['testedSource']
        check(source['sha256'] == '15a98c124cbe66d7b1d4635f58d57aaff6e0d6512141e531042a295c8e16ac36', 'implementer source digest differs')
        check(digest(json.dumps(source['files'], sort_keys=True, separators=(',', ':')).encode()) == source['sha256'], 'source manifest digest invalid')
        for row in source['files']:
            check(digest(git('cat-file', 'blob', PIN + ':' + row['path'])) == row['sha256'], 'source pin mismatch: ' + row['path'])
        report['implementer_source'] = {'sha256': source['sha256'], 'files_matched_to_pin': len(source['files']), 'all_matched': True}
        mappings = load(EVIDENCE / 'manifest.json')['mapping']
        for row in mappings:
            data = (ROOT / row['repositoryPath']).read_bytes()
            check(digest(data) == row['sha256'] and len(data) == row['bytes'], 'preserved raw evidence mismatch: ' + row['repositoryPath'])
            check(git('cat-file', 'blob', PIN + ':' + row['repositoryPath']) == data, 'evidence not immutable at pin')
        report['preserved_outputs'] = {'matched_files': len(mappings), 'manifest_sha256': digest((EVIDENCE / 'manifest.json').read_bytes()), 'all_size_hash_and_pin_matched': True}

        unit = load(EVIDENCE / 'unit/receipt.json')
        check(unit['source'] == source, 'unit manifest not same source')
        check(all(row['exitCode'] == 0 for row in unit['commands']), 'implementer unit command failed')
        rows = [json.loads(line) for line in (EVIDENCE / 'unit/services-race.stdout').read_text().splitlines()]
        passed = [row['Test'] for row in rows if row.get('Action') == 'pass' and row.get('Test')]
        skipped_tests = [row['Test'] for row in rows if row.get('Action') == 'skip' and row.get('Test')]
        skipped_packages = [row['Package'] for row in rows if row.get('Action') == 'skip' and not row.get('Test')]
        check(len(passed) == 839 and not skipped_tests and not any(row.get('Action') == 'fail' for row in rows), 'Go raw output counts/failure/skip differ')
        cli = (EVIDENCE / 'unit/cli-tests.stdout').read_text()
        check(re.search(r'Test run with 15 tests(?: in 0 suites)? passed', cli) is not None, 'CLI raw test summary differs')
        report['unit_output_audit'] = {'go_passed_executions_including_subtests': len(passed), 'cli_tests': 15,
                                      'go_failed': 0, 'go_skipped_tests': len(skipped_tests), 'packages_without_test_files': skipped_packages,
                                      'audit_harness_correction': 'Initial audit wrongly treated Go package-level skip events for three packages without test files as skipped tests. Raw output has 839 passed Test events and zero skipped Test events; initial failed audit report is retained.',
                                      'vet_exit_code': unit['commands'][0]['exitCode'],
                                      'postprocessor_correction': unit['postprocessorFailure'],
                                      'independent_rerun': False}

        pg = load(EVIDENCE / 'postgres/receipt.json')
        for path, sha in pg['sourceSHA256'].items():
            check(digest(git('cat-file', 'blob', PIN + ':services/' + path)) == sha, 'PostgreSQL manifest source differs: ' + path)
        raw = (EVIDENCE / 'postgres/real-postgres-tests.stdout').read_text()
        top = re.findall(r'^--- PASS: (Test\S+) ', raw, re.MULTILINE)
        total = re.findall(r'^\s*--- PASS: (Test\S+) ', raw, re.MULTILINE)
        check(len(top) == 13 and len(total) == 46 and not re.search(r'--- (?:FAIL|SKIP):', raw), 'PostgreSQL raw counts differ')
        check(pg['status'] == 'passed' and pg['privateClusterRemoved'] and not pg['mockDatabase'], 'PostgreSQL receipt failure or mock')
        check(all(row['exitCode'] == 0 for row in pg['commands']), 'PostgreSQL recorded command failure')
        for key, row in pg['tools'].items():
            check(row['sha256'] and row['path'], 'missing PostgreSQL executable provenance ' + key)
        migration = 'services/release/migrations/001_release.sql'
        migration_raw = git('cat-file', 'blob', PIN + ':' + migration)
        check(migration_raw == git('cat-file', 'blob', PIN + '^:' + migration), 'v2 changed migration001')
        report['postgres_output_audit'] = {'version': pg['postgresVersion'], 'mock_database': pg['mockDatabase'],
                                           'top_level_functions': len(top), 'executions_including_subtests': len(total),
                                           'private_cluster_removed': pg['privateClusterRemoved'], 'failed': 0, 'skipped': 0,
                                           'migration001_sha256': digest(migration_raw), 'migration001_unchanged_from_parent': True,
                                           'independent_database_rerun': False,
                                           'tools_recorded': pg['tools']}

        http = load(EVIDENCE / 'http/receipt.json')
        check(http['testedSource'] == source and http['status'] == 'passed-local-http-v1-v2-public-swift-verification', 'HTTP source/status differs')
        check(all(row['exitCode'] == row['expectedExitCode'] for row in http['commands']), 'HTTP command outcome differs')
        reports = [load(EVIDENCE / ('http/swift-http-v' + str(version) + '.stdout')) for version in [1, 2]]
        check(all(row['status'] == 'passed' and row['protocol'] == i + 1 and not row['versionFallback'] and not row['redirects'] for i, row in enumerate(reports)), 'Swift HTTP raw reports differ')
        check(len(reports[0]['verifiedGrants']) == 0 and len(reports[1]['verifiedGrants']) == 2, 'typed authority metadata differs')
        check(http['oldBinaryRefusesUpgradedSnapshotWithoutMutation'] and http['restartPreservesV1BytesAndV2VerifiedGrants'], 'old binary/restart evidence differs')
        report['http_output_audit'] = {'requests': len(http['requests']), 'swift_reports': reports,
                                      'old_binary_refuses_schema2_without_mutation': True,
                                      'restart_preserves_v1_bytes_and_v2_grants': True,
                                      'optimized_python_invocation': receipt['httpInvocation'], 'independent_rerun': False,
                                      'scope': 'Actual loopback HTTP to public Swift verifier; bounded small TEST payloads and typed metadata only.'}
        legacy = load(EVIDENCE / 'legacy-v1/receipt.json')
        check(legacy['status'] == 'passed', 'legacy CLI/HTTP/VM receipt failed')
        report['legacy_regression_audit'] = {'status': legacy['status'], 'receipt_sha256': digest((EVIDENCE / 'legacy-v1/receipt.json').read_bytes()),
                                             'independent_rerun': False, 'limitation': 'Legacy harness consumes existing VM binary; no independent source-build attestation or physical-device claim.'}
        report['status'] = 'matched-implementer-source-and-preserved-raw-evidence'
    except BaseException as error:
        report['status'], report['failure'] = 'failed', str(error)
        raise
    finally:
        output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'source': report['implementer_source'], 'outputs': report['preserved_outputs'], 'report': str(output)}, indent=2))


if __name__ == '__main__':
    main()
