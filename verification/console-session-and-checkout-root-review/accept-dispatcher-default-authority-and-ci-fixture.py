"""Accept the scoped default-authority host result and test-only CI correction once."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
AUTH = ROOT / 'verification/console-dispatcher-default-authority-slice'
REVIEW = ROOT / 'verification/console-dispatcher-authority-preaccess'
CI = ROOT / 'verification/console-dispatcher-dead-admission-ci-correction'
AUTH_DEST = OUT / 'fixed-dispatcher-default-authority-acceptance.json'
CI_DEST = OUT / 'fixed-dispatcher-dead-admission-ci-acceptance.json'

def read(path):
    return json.loads(path.read_bytes())

def row(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')

assert not AUTH_DEST.exists() and not CI_DEST.exists(), 'One-shot; do not replay'
for directory, digest, count in [(AUTH, '3700d4fd7f89a52de22967e510289745f8ed8aad3bbf7ff7e0a0c2fa88a9fa33', 386),
                                  (CI, '494481ce665e0de68e11b6fac176bce2477aff353f121c4752896945be367cc0', 26)]:
    assert row(directory / 'freeze.json')['sha256'] == digest
    frozen = read(directory / 'freeze.json')
    assert len(frozen['files']) == count
    for expected in frozen['files']:
        assert row(ROOT / expected['path']) == expected
    assert {p for p in directory.rglob('*') if p.is_file()} == {ROOT / x['path'] for x in frozen['files']} | {directory / 'freeze.json'}
review_members = set()
for freeze in REVIEW.glob('*freeze.json'):
    for expected in read(freeze)['members']:
        actual = row(REVIEW / expected['path'])
        assert actual['bytes'] == expected['bytes'] and actual['sha256'] == expected['sha256']
        review_members.add(REVIEW / expected['path'])
    review_members.add(freeze)
assert review_members == {p for p in REVIEW.rglob('*') if p.is_file()}
assert len(review_members) == 25
review = read(REVIEW / 'candidate-6-terminal-review.json')
assert review['actionable_findings'] == [] and not review['reviewer_runtime_replay']
host_path = AUTH / 'candidate-6/execution/receipt.json'
host = read(host_path)
assert row(host_path)['sha256'] == review['execution_receipt_sha256']
assert host['status'] == 'passed' and host['elapsed_seconds'] < 55
assert host['exunit_result'] == {'total': 7, 'failures': 0, 'skipped': 0, 'excluded': 0}
assert host['original_input_changes'] == host['original_input_read_errors'] == []
assert len(host['owned_processes']) == 8
assert all(p['direct_child_reaped'] and p['process_group_absent'] and not p['cleanup_errors'] for p in host['owned_processes'])
assert all(host['cleanup'][key] is True for key in ['all_owned_children_reaped_and_groups_absent', 'postgres_port_closed', 'postmaster_pid_file_absent', 'fixture_tls_port_closed', 'tls_key_directory_removed_at_start', 'scratch_removed'])
assert all(host['postrun_observations'].values())
assert all(host['component_cleanup'][key] is True for key in ['admission_absent', 'default_owner_absent', 'default_repo_absent', 'owner_alive_before_normal_stop', 'owner_dependencies_alive_before_normal_stop', 'owner_normal_stop', 'owned_components_stopped', 'ephemeral_tls_key_directory_removed'])
for name, digest in host['outputs'].items():
    assert row(host_path.parent / name)['sha256'] == digest
raw = (host_path.parent / 'default-authority-tests.stdout.txt').read_text()
assert 'COMPILED 39 frozen ordinary modules; warnings=0' in raw
assert 'COMPILED 3 test modules; warnings=0' in raw
assert 'RESULT {"total":7,"failures":0,"skipped":0,"excluded":0}' in raw
plan = read(AUTH / 'candidate-6/execution-plan.json')
pins = plan['selected_inputs'] + plan['tool_files'] + [p for d in plan['dependencies'] for p in d['files']]
for expected in pins:
    path = Path(expected['path']); path = path if path.is_absolute() else ROOT / path
    data = path.read_bytes()
    assert len(data) == expected['bytes'] and hashlib.sha256(data).hexdigest() == expected['sha256']
assert len(pins) == 1003
auth = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'python': sys.version,
    'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT))],
    'status': 'accepted-actual-default-verifier-and-restricted-default-Repo-local-host-slice',
    'producer_seal': row(AUTH / 'freeze.json'), 'producer_members_verified': 386,
    'review_members': [row(p) for p in sorted(review_members)], 'independent_terminal_review': row(REVIEW / 'candidate-6-terminal-review.json'),
    'host_receipt': row(host_path), 'source_revision': host['source_revision'], 'source_tree': host['source_tree'],
    'exact_inputs_verified': len(pins), 'host_tests_passed': 7, 'skipped': 0, 'warnings': 0,
    'scope': 'Private fixed dispatcher with actual registered ConfiguredVerifier and default restricted Repo, synthetic local JWKS TLS trust and PostgreSQL17.11 disposable host database; explicit normal fixture owner shutdown.',
    'accepted_method_evidence': review['method_evidence'], 'context_projection_scope': review['context_projection_scope'],
    'root_review': 'Read complete test fixture and migrations, all lifecycle and runner corrections, raw terminal output and independent review. Verified producer and review freezes,1003 current pins,12 output hashes, exact seven terminal passes, normal owner stop with dependencies live, Admission and all owned OS cleanup. No runtime replay by root.',
    'earlier_failures_preserved': ['candidate2 migration pool', 'candidate3 table count', 'candidate4 Admission teardown'],
    'source_only_candidates_preserved': [1, 5], 'actual_default_Repo_success_accepted': True,
    'session_or_cookie_authority_accepted': False, 'production_provider_or_supervised_lifecycle_accepted': False,
    'pending': review['pending'], 'GA_accepted': False, 'delivery_pending': True}
save(AUTH_DEST, auth)

ci_host = read(CI / 'regression-v2-receipt.json'); analysis = read(CI / 'terminal-analysis.json')
assert ci_host['status'] == 'passed' and ci_host['elapsed_seconds'] < 55
assert ci_host['all_owned_children_cleanup_confirmed'] and ci_host['scratch_removed']
assert ci_host['postrun_original_changes'] == [] and ci_host['postrun_original_inputs_verified'] == 988
assert len(ci_host['phases']) == 6 and all(p['status'] == 'passed' and p['direct_child_reaped'] and p['owned_group_absent'] for p in ci_host['phases'])
assert row(CI / 'regression-v2.stdout.txt')['sha256'] == ci_host['output_sha256']
raw_ci = (CI / 'regression-v2.stdout.txt').read_text()
observed = [json.loads(line.removeprefix('PHASE_RESULT ')) for line in raw_ci.splitlines() if line.startswith('PHASE_RESULT ')]
assert observed == analysis['phase_results']
for result, name, total, failed, calls in zip(observed, ['original-dead', 'corrected-absent', 'corrected-dead', 'corrected-live-refused', 'corrected-malformed-refused'], [6,19,6,6,6], [6,0,0,6,6], [0,31,31,0,0]):
    assert result['phase'] == name and result['result'] == {'total':total,'failures':failed,'skipped':0,'excluded':0}
    assert result['setup_failures'] == failed and result['dispatch_calls'] == calls
    assert result['pointer_preserved'] and result['registered_key_owner_absent'] and result['repo_not_started']
for marker in analysis['compile']['raw_markers']:
    assert marker in raw_ci
canonical = ROOT / analysis['canonical_test']['path']
assert row(canonical)['sha256'] == analysis['canonical_test']['sha256'] == 'e03227fde20ef946e538c17ed41b4d7d50d7fba88ef737c50e9caceb7c47e3ea'
ci = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'python': sys.version,
    'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT))],
    'status': 'accepted-test-only-dead-admission-CI-fixture-correction', 'packet_seal': row(CI / 'freeze.json'),
    'packet_members_verified': 26, 'canonical_file': row(canonical), 'host_receipt': row(CI / 'regression-v2-receipt.json'),
    'terminal_analysis': row(CI / 'terminal-analysis.json'), 'original_failure_reproduced': True,
    'corrected_absent_tests_passed': 19, 'corrected_dead_tests_passed': 6,
    'live_and_malformed_expected_setup_rejections': 12, 'rejected_state_dispatch_calls': 0,
    'compile_runtime_warnings': 0, 'selected_test_format_passed': True, 'owned_cleanup_confirmed': True,
    'root_review': 'Only setup changes. Require no KeyOwner, allow absent or actual dead ETS reference, reject live/malformed state before dispatch, assert Admission fails closed and preserve pointer/default Repo. Read full regression bootstrap and runner; exact phase counts, setup stackframes, trace counts and clean teardown independently checked from raw outputs.',
    'product_implementation_changed': False, 'remote_CI_passed': False, 'delivery_pending': True, 'GA_accepted': False}
save(CI_DEST, ci)
w = read(ROOT / 'work-graph.json'); g = read(ROOT / 'gates/ga.json')
for target in [w['packages'][13], g['gates'][21]]:
    dispatcher = target['fixedWorkspaceDispatcher']
    dispatcher.update({'status': 'accepted-private-fixed-dispatcher-with-actual-defaults-host-qualification',
        'actual_default_Repo_success_accepted': True,
        'accepted_scope': auth['scope']})
    dispatcher['default_authority_candidate'].update({'status': auth['status'], 'root_acceptance': row(AUTH_DEST),
        'producer_seal': row(AUTH / 'freeze.json'), 'independent_terminal_review': row(REVIEW / 'candidate-6-terminal-review.json'),
        'terminal_candidate': 6, 'host_tests_passed': 7, 'host_warnings': 0, 'host_skipped': 0,
        'actual_default_Repo_success_accepted': True, 'next_lifecycle_correction_runtime_released': True,
        'normal_fixture_owner_and_OS_cleanup_confirmed': True, 'delivery_pending': True,
        'pending': review['pending']})
    dispatcher['component_test_correction'].update({'status': ci['status'], 'root_acceptance': row(CI_DEST),
        'implementation_accepted': True, 'runtime_released': True, 'corrected_absent_passed': 19, 'corrected_dead_passed': 6,
        'live_malformed_expected_setup_rejections': 12, 'remote_CI_passed': False, 'delivery_pending': True})
texts = {}
for name in ['PLAN.md', 'STATUS.md']:
    text = (ROOT / name).read_text()
    old = 'Actual default verifier/default Repo qualification remains pending: the bounded host fixture now completes all seven authorization method bodies, but teardown fails on a stale Admission reference and ExUnit invalidates all seven. Two earlier setup failures and all owned OS cleanup receipts are preserved; explicit fixture lifecycle correction is being prepared.'
    new = 'Actual default verifier/default Repo now has bounded local host qualification after all seven methods pass with zero warnings and complete Admission/component/OS cleanup. It covers real signed-token verification, restricted PostgreSQL17.11 reads, tenant denials, canonical pagination, committed revocation and transaction-context refusal. Independent review verifies all 1,003 inputs and terminal evidence. The three earlier failed fixtures remain preserved. Production provider/supervised lifecycle, server-held session-token provenance and browser/HTTP integration remain pending.'
    assert text.count(old) == 1
    text = text.replace(old, new)
    old = 'a narrow fixture correction is being prepared.'
    new = 'a test-only correction now passes nineteen absent-pointer and six dead-pointer tests while preserving the pointer and rejecting live/malformed tables before dispatch. The original six setup failures are reproduced; corrected remote CI remains pending.'
    assert text.count(old) == 1
    texts[name] = text.replace(old, new)
assert w['packages'][13]['fixedWorkspaceDispatcher'] == g['gates'][21]['fixedWorkspaceDispatcher']
for name, value in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(value, indent=2) + '\n')
for name, text in texts.items():
    (ROOT / name).write_text(text)
subprocess.run(['git', 'diff', '--check', '--', canonical.relative_to(ROOT), 'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json'], check=True, timeout=10)
print(json.dumps({'accepted_actual_default_host_tests': 7, 'accepted_CI_correction_passes': 25,
    'expected_live_malformed_rejections': 12, 'canonical_product_changes': 0, 'canonical_test_changes': 1, 'GA_verified': 0}))
