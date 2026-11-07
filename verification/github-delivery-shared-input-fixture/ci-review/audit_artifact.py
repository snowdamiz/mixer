#!/usr/bin/env python3
"""Offline audit of retained attempt-one diagnostic artifact; no external calls."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ARTIFACT = HERE / 'artifact'
CANDIDATE = ARTIFACT / 'verification/cache-fixture-shared-input-candidate'
EXPECTED_HEAD = 'fe8f4857954cc5cabc25bf5b4fe5657bb414838a'
EXPECTED_TREE = 'e7f4a5b9be6138d66f2ca48befd9684a86e25cfe'
FAILED_METHOD = 'test_checks_active_under_optimized_python'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def rows(base):
    return [{'path': p.relative_to(base).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)}
            for p in sorted(base.rglob('*')) if p.is_file()]


def tree(items):
    return hashlib.sha256(json.dumps(items, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def main():
    archive = HERE / 'diagnostic-run-40790391653-attempt-1.zip'
    assert sha(archive) == 'cf09a7e676de302a84c4035d646c17ed44839bff65833ba2af3e0ef58ec7c048'
    observation = load(HERE / 'remote-observation.json')
    assert observation['head'] == EXPECTED_HEAD and observation['tree'] == EXPECTED_TREE
    assert observation['run_id'] == 40790391653 and observation['run_attempt'] == 1
    seal = load(CANDIDATE / 'seal.json')
    assert sha(CANDIDATE / 'seal.json') == 'db6ba0fcb4c66f5a38dd0f93ce9dc381a869b12fbf8eda7ecb8f5b3f57bfeca7'
    assert all(sha(CANDIDATE / row['path']) == row['sha256'] and
               (CANDIDATE / row['path']).stat().st_size == row['bytes'] for row in seal['members'])
    assert tree(seal['members']) == seal['tree_sha256']
    review_base = ARTIFACT / 'verification/cache-fixture-shared-input-review'
    review = load(review_base / 'seal.json')
    assert sha(review_base / 'seal.json') == '6b5b13ac132044f25c624f83dcf457b3ce39f013bc0a350ccf5da24f2b24acac'
    assert all(sha(ARTIFACT / row['path']) == row['sha256'] for row in review['members'])
    assert tree(review['members']) == review['tree_sha256']
    integration_seal = HERE / 'integration-review-seal-at-delivered-head.json'
    assert sha(integration_seal) == 'ef4690fa83901f5927e617bd41ea3d8ba470e58df6dde45744a8435ac60665b7'
    assert integration_seal.read_bytes() == (ROOT / 'verification/cache-fixture-overlay-independent/seal.json').read_bytes()
    workflow = ARTIFACT / '.github/workflows/cache-fixture-shared-input-diagnostic.yml'
    workflow_hash = sha(workflow)
    assert workflow_hash == '50f55de2d34606f93a0687413d8a542e47d843c8481a2bc958f13e2407c26bbf'
    assert workflow.read_bytes() == (CANDIDATE / 'workflow/cache-fixture-shared-input-diagnostic.yml').read_bytes()
    pack = CANDIDATE / 'materialized/pack'
    manifest = load(pack / 'manifest.json')
    assert [row for row in rows(pack) if row['path'] != 'manifest.json'] == manifest['members']
    assert tree(manifest['members']) == manifest['tree_sha256']
    assert sha(pack / 'manifest.json') == '86c104696aca726a47715cde9e6beedfd0522f5f9ec7f3e68d4fed4de1368d07'
    assert sha(pack / 'source/regression/independent_tests.rs') == 'f7d62c01e251642677e22f7595af9683f9c451f1db43683be5d2ef86fedba141'
    frozen_manifest = ARTIFACT / 'verification/swift-cache-state-ci/pack/manifest.json'
    assert sha(frozen_manifest) == 'd1caf2069e17ac1beff6707d6e084ea49d18382bc959d73d5184ec49cb7886b9'
    logs = CANDIDATE / 'logs'
    materialization_lines = (logs / 'materialization.stdout').read_text().splitlines()
    assert materialization_lines[:2] == [EXPECTED_HEAD, EXPECTED_TREE]
    preflight = json.loads(materialization_lines[4])
    materialized = load(CANDIDATE / 'materialized/materialization.json')
    postflight = load(logs / 'candidate-postflight.stdout')
    assert preflight == postflight
    assert materialized['status'] == 'passed-exact-materialization'
    assert len(materialized['copies']) == 87 and sum(row['source'] == 'frozen-base' for row in materialized['copies']) == 83
    assert materialized['hardlinks_used'] is False and materialized['compiler_or_product_executed'] is False
    assert preflight['inputs'] == materialized['inputs']
    runner_text = (logs / 'runner-controls.stderr').read_text()
    materializer_text = (logs / 'materializer-controls.stderr').read_text()
    parse = lambda text: [{'method': m[0], 'result': m[1]} for m in re.findall(r'^(test_\w+) \([^\n]+\) \.\.\. (ok|FAIL|ERROR)$', text, re.M)]
    runner_tests, materializer_tests = parse(runner_text), parse(materializer_text)
    assert len(runner_tests) == 36 and len(materializer_tests) == 9
    assert [row['method'] for row in runner_tests if row['result'] != 'ok'] == [FAILED_METHOD]
    assert all(row['result'] == 'ok' for row in materializer_tests)
    assert "ModuleNotFoundError: No module named \\'materialize_pack\\'" in runner_text
    failure_stack = runner_text.split('======================================================================\n', 1)[1]
    assert not list(ARTIFACT.rglob('*custody-hold*'))
    assert not any('/runs/' in row['path'] for row in load(HERE / 'artifact-inventory.json')['members'])
    descendant = load(logs / 'descendant-control/control.json')
    child = descendant['receipt']['commands'][0]
    assert all(child[key] is True for key in ['timed_out', 'child_returned', 'owned_group_gone', 'owned_group_killed'])
    assert child['custody_hold'] is False and descendant['custody_hold'] is False and child['exit'] == -9
    deadlines = {stage: load(logs / ('deadline-' + stage + '-control.json')) for stage in ['postflight', 'retention']}
    assert all(d['receipt']['commands'] == [] and d['receipt']['cleanup']['deadline_expired'] is True and
               d['receipt']['cleanup']['removed'] is False and d['scratch_preserved_at_assertion'] is True
               for d in deadlines.values())
    report = {
        'schema': 1, 'reviewed_utc': datetime.now(timezone.utc).isoformat(),
        'command': ['python3', '-B', 'verification/github-delivery-shared-input-fixture/ci-review/audit_artifact.py'],
        'python': sys.version, 'source_revision': EXPECTED_HEAD, 'source_tree': EXPECTED_TREE,
        'scope': 'Read-only actual CI artifact and source binding review; no local child, compiler, Rust, Swift, native, UI, Git, dispatch, retry or held-process probe',
        'artifact': {'id': 12861426383, 'bytes': archive.stat().st_size, 'sha256': sha(archive), 'file_count': 134},
        'run': {'id': 40790391653, 'attempt': 1, 'status': 'completed', 'conclusion': 'failure', 'job_id': 123173894863},
        'bindings': {'candidate_seal_sha256': sha(CANDIDATE / 'seal.json'), 'candidate_tree_sha256': seal['tree_sha256'],
                     'source_review_seal_sha256': sha(review_base / 'seal.json'), 'source_review_tree_sha256': review['tree_sha256'],
                     'integration_review_seal_sha256': sha(integration_seal), 'integration_review_binding': 'Exact raw source at delivered head plus local preflight; not included in workflow sparse artifact',
                     'workflow_sha256': workflow_hash, 'materialized_pack_tree_sha256': manifest['tree_sha256'],
                     'accepted_rust_source_sha256': sha(pack / 'source/regression/independent_tests.rs'),
                     'frozen_manifest_sha256': sha(frozen_manifest), 'all_sealed_candidate_source_members_exact': True,
                     'all_materialized_pack_members_exact': True, 'preflight_equals_postflight': True},
        'host_observed': {'python': materialization_lines[2], 'os': materialization_lines[3]},
        'focused_controls': {'runner_total': 36, 'runner_passed': 35, 'runner_failed': [FAILED_METHOD],
                             'materializer_total': 9, 'materializer_passed': 9,
                             'runner_elapsed_seconds': 2.090, 'materializer_elapsed_seconds': 1.029,
                             'runner_methods': runner_tests, 'materializer_methods': materializer_tests},
        'failure': {'method': FAILED_METHOD, 'test_runner_line': 49, 'runner_import_line': 5,
                    'phase': 'Python optimized-check subprocess import, before member-path guard and before complete fixture step',
                    'root_exception': "ModuleNotFoundError: No module named 'materialize_pack'",
                    'assertion': "Expected b'Noncanonical member path' absent from subprocess stderr", 'raw_stack': failure_stack,
                    'cause': 'Source-file runpy.run_path does not add candidate sibling directory to module search path; -c subprocess inherits repository working directory'},
        'cleanup': {'materialization': '87 ordinary copies retained intentionally for diagnostic upload',
                    'descendant_control': {'direct_child_returned': child['child_returned'], 'owned_group_gone': child['owned_group_gone'],
                                           'custody_hold': child['custody_hold'], 'exit': child['exit'], 'elapsed_seconds': child['elapsed_seconds']},
                    'deadline_controls': {stage: {'no_commands': not d['receipt']['commands'], 'deadline_expired': d['receipt']['cleanup']['deadline_expired'],
                                                'scratch_preserved_at_assertion': d['scratch_preserved_at_assertion'],
                                                'cleanup_elapsed_seconds': d['receipt']['cleanup_elapsed_seconds'],
                                                'unittest_including_teardown_passed': True} for stage, d in deadlines.items()},
                    'archive_custody_hold_file_count': 0,
                    'optimized_check_cleanup_limit': 'No standalone command/group receipt retained for subprocess.run; it returned to the failing assertion. No process probe performed.',
                    'other_command_cleanup_limit': '35 successful unittest results include teardown. Most individual child receipts were removed with owned test scratch; do not infer unretained details.'},
        'complete_fixture': {'step': 'skipped', 'fixture_invocations': 0, 'fixture_child_commands_observed': 0,
                             'declared_child_commands': 103, 'declared_compiler': '1.98.1-aarch64-apple-darwin',
                             'compiler_identity_or_availability_observed': False,
                             'synthetic_missing_compiler_controls_are_availability_evidence': False,
                             'rust_test_regression_claimed': False, 'speedup_or_equivalence_claimed': False},
        'proposal': {'path': 'verification/cache-fixture-controls-correction/proposal.diff',
                     'change': 'Add cwd=HERE only to the optimized-Python control subprocess call',
                     'sha256': sha(ROOT / 'verification/cache-fixture-controls-correction/proposal.diff'),
                     'in_process_verification': 'verification/cache-fixture-controls-correction/proposal-verification.json',
                     'actual_corrected_subprocess_and_full_controls': 'pending; no automatic second run'},
        'acceptance': {'runtime_release_or_GA': False, 'frozen_baseline_preserved': True,
                       'original_full_Debug_timeout_remains_failed': True, 'native_runtime_checks': 'paused; none attempted'},
    }
    (HERE / 'review.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': 'passed-artifact-review', 'runner_passed': 35, 'runner_failed': 1,
                      'materializer_passed': 9, 'complete_fixture': 'skipped', 'all_source_bindings_exact': True}))


if __name__ == '__main__':
    main()
