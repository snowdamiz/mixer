#!/usr/bin/env python3
"""Read-only owner audit plus exact bindings for the root's linked flow probes."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OWNER = ROOT / 'verification/capability-cold-start-runtime'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def need(value, message):
    if not value:
        raise RuntimeError(message)


def read(path):
    return json.loads(path.read_text())


def check_file(path, digest):
    need(sha(path) == digest, 'changed file: ' + str(path))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    sealed = OWNER / 'final-receipt.json'
    check_file(sealed, '32d31ae27e2665dd92ba6d4e0fcfed59a9402ff18bc2a64004518c7d5db69661')
    seal = read(sealed)
    fixture_path = ROOT / 'verification/capability-concrete-ci-fixture-fix/receipt.json'
    check_file(fixture_path, '456eca14c71afbf0b09aac1863d1c7cd183d54697b767f29d86d0393a82bd999')
    fixture = read(fixture_path)
    need(fixture['status'] == 'both Wasm fixture variants byte-identical and six XCTest functions passed', 'fixture result')
    for command in fixture['commands']:
        check_file(fixture_path.parent / command['log'], command['log_sha256'])
        need(command['exit_code'] == 0, 'fixture command')
    for name, key in [('fixture-parity.swift', 'probe_sha256'), ('initial-run.py', 'driver_sha256'),
                      ('initial-receipt.json', 'initial_receipt_sha256'), ('run.py', 'corrected_driver_sha256'),
                      ('reconcile.py', 'reconciliation_driver_sha256')]:
        check_file(fixture_path.parent / name, fixture[key])
    check_file(Path(fixture['artifact']['path']), fixture['artifact']['sha256'])
    review_path = ROOT / 'verification/capability-cold-start-runtime-review/receipt.json'
    check_file(review_path, '5276f4101996b47e8d3c32b517e152ec44fbc11fa51a26c3499c87032a2fa889')
    review = read(review_path)
    check_file(review_path.parent / 'file-manifest.sha256', review['file_manifest_sha256'])
    review_files = 0
    for line in (review_path.parent / 'file-manifest.sha256').read_text().splitlines():
        digest, name = line.split('  ', 1)
        check_file(review_path.parent / name, digest)
        review_files += 1
    need(review_files == review['evidence_files'] and not review['actionable_findings'], 'review result')
    need(review['owner_final_seal']['sha256'] == sha(sealed), 'review same owner')
    manifest = OWNER / 'file-manifest.sha256'
    check_file(manifest, seal['file_manifest_sha256'])
    evidence_count = 0
    for line in manifest.read_text().splitlines():
        digest, name = line.split('  ', 1)
        check_file(OWNER / name, digest)
        evidence_count += 1
    need(evidence_count == seal['evidence_files'], 'owner evidence count')
    primary = read(OWNER / '2026-10-23-candidate-1/receipt.json')
    source = Path(primary['export'])
    counts = dict(sources=0, logs=0, artifacts=0, dependencies=0, baseline_git=0)
    for name, digest in seal['receipts'].items():
        path = OWNER / name / 'receipt.json'
        check_file(path, digest)
        receipt = read(path)
        need(receipt['status'].startswith(('scoped tests passed', 'scoped consumer/opacity/cross checks passed')), 'owner status')
        for item, expected in receipt['source_files'].items():
            check_file(Path(receipt.get('export', str(source))) / item, expected)
            counts['sources'] += 1
        for command in receipt['commands']:
            check_file(OWNER / name / command['log'], command['log_sha256'])
            need(command['exit_code'] == command.get('expected_exit', 0), 'owner command result')
            if 'expected_tests' in command:
                need(command['observed_test_counts'][-1] == command['expected_tests'], 'owner test count')
            counts['logs'] += 1
        for mode, entry in receipt.get('artifacts', {}).items():
            if 'path' in entry:
                check_file(Path(entry['path']), entry['sha256'])
                counts['artifacts'] += 1
            else:
                for kind, value in entry.items():
                    if isinstance(value, dict) and 'path' in value:
                        check_file(Path(value['path']), value['sha256'])
                        counts['artifacts'] += 1
                    elif isinstance(value, str):
                        check_file(OWNER / '.build' / name / mode / kind, value)
                        counts['artifacts'] += 1
        for item, expected in receipt.get('dependency_inputs', {}).items():
            check_file(Path(item), expected)
            counts['dependencies'] += 1
    for name, digest in primary['source_files'].items():
        if name in primary['own_files']:
            if name == fixture['source']:
                need(digest == fixture['old_sha256'], 'old fixture is frozen owner input')
                check_file(ROOT / name, fixture['new_sha256'])
            else:
                check_file(ROOT / name, digest)
        else:
            data = subprocess.check_output(['git', 'show', primary['baseline_revision'] + ':' + name], cwd=ROOT)
            need(hashlib.sha256(data).hexdigest() == digest, 'baseline: ' + name)
            counts['baseline_git'] += 1
    dependency_path = Path(primary['dependency_receipt']['path'])
    check_file(dependency_path, primary['dependency_receipt']['sha256'])
    dependency = read(dependency_path)
    for retained in dependency['retained_products'].values():
        for item, digest in retained['files'].items():
            check_file(Path(retained['directory']) / item, digest)
            counts['dependencies'] += 1
    for item, digest in primary['native_files'].items():
        check_file(Path(primary['native_directory']) / item, digest)
        counts['dependencies'] += 1
    derived = read(OWNER / '2026-10-23-derived-final/receipt.json')
    for name, digest in derived['original_source_files'].items():
        if name in primary['source_files']:
            need(digest == primary['source_files'][name], 'derived original: ' + name)
    check_file(OWNER / '2026-10-23-derived-final/test-only.patch', derived['test_only_patch_sha256'])
    supplemental = read(OWNER / '2026-10-23-supplemental-final/receipt.json')
    for name, digest in supplemental['supplemental_files'].items():
        check_file(OWNER / name, digest)
    flows = {}
    probe_digest = sha(HERE / 'ColdStartFlowProbe.swift')
    for mode in ['debug', 'release', 'tsan']:
        path = HERE / ('final-' + mode + '-1') / 'receipt.json'
        result = read(path)
        need(result['status'] == 'four root flows passed', 'root flow result')
        need(result['mode'] == mode and result['probe_sha256'] == probe_digest, 'same root probe')
        need(result['owner_source_manifest_sha256'] == primary['source_manifest_sha256'], 'same final source')
        check_file(ROOT / result['owner'], result['owner_receipt_sha256'])
        check_file(Path(result['probe_source']), probe_digest)
        check_file(Path(result['binary']['path']), result['binary']['sha256'])
        check_file(HERE / 'run.py', result['driver_sha256'])
        need(result['artifacts'] == primary['artifacts'][mode], 'same owner artifact')
        need(len(result['commands']) == 2, 'root command count')
        for command in result['commands']:
            need(command['exit_code'] == 0, 'root command result')
            check_file(path.parent / command['log'], command['log_sha256'])
        text = (path.parent / 'execute.log').read_text()
        need(text.count('PASS ') == 5 and 'PASS 4 coordinator flow cases' in text, 'root flow observations')
        flows[mode] = {'receipt': str(path.relative_to(ROOT)), 'sha256': sha(path), 'cases': 4}
    record = {
        'status': 'owner and independent review evidence audited; twelve root flow executions and byte-identical CI fixture repair passed',
        'owner_final_receipt': {'path': str(sealed.relative_to(ROOT)), 'sha256': sha(sealed)},
        'owner_file_manifest_sha256': sha(manifest), 'owner_evidence_files': evidence_count,
        'source_manifest_sha256': primary['source_manifest_sha256'],
        'source_count': len(primary['source_files']), 'binding_counts': counts,
        'new_production_files': seal['new_production_files'],
        'root_probe_sha256': probe_digest, 'root_driver_sha256': sha(HERE / 'run.py'),
        'root_audit_sha256': sha(Path(__file__)), 'root_flows': flows,
        'independent_review': {'path': str(review_path.relative_to(ROOT)), 'sha256': sha(review_path), 'evidence_files': review_files, 'original_case_executions': 6, 'close_calls': 144},
        'test_only_ci_fixture_repair': {'path': str(fixture_path.relative_to(ROOT)), 'sha256': sha(fixture_path), 'source': fixture['source'], 'frozen_sha256': fixture['old_sha256'], 'current_sha256': fixture['new_sha256']},
        'root_source_review': 'Reviewed facade, control, worker, timer, configuration and same-instance durable/concrete composition. Independent source and held health-write/close races found no actionable defect.',
        'scope': [
            'Signed fixture scaffold credited to transition candidate3; root flow assertions are original.',
            'Actual private signed store, native validation/startup/enable, monotonic timer and retirement; only wall clock is controlled.',
            'Early milestone reports cause later timer-only health; actually committed healthy provenance restarts after root expiry.',
            'Seventeenth owner is rejected before directory creation; thirty-two cancelled opens per mode return capacity after cleanup.',
            'Synthetic milestone reports are not real UI or FieldLog evidence.',
            'Owner derived internal invoke is absent from production; no public guest event delivery is qualified.',
            'TSan does not instrument Rust or platform internals; cross compilation is not a physical-device run.',
            'No published-consumer, device, store, customer, full Swift guest or GA gate is completed.'
        ]
    }
    output = HERE / 'receipt.json'
    if args.check:
        need(read(output) == record, 'root audit receipt changed')
    else:
        output.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'receipt_sha256': sha(output), 'binding_counts': counts, 'root_flow_executions': 12}))


if __name__ == '__main__':
    main()
