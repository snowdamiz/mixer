"""Record observed CI and failed isolated authority fixtures once; no runtime replay."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DELIVERY = ROOT / 'verification/github-delivery-lifetime-review-capability-checkout'
AUTHORITY = ROOT / 'verification/console-dispatcher-default-authority-slice'
DEST = OUT / 'capability-ci-and-authority-fixtures-checkpoint.json'
COMMIT = '6f116c6a41994fcab5fa0d203198dc139dae9829'

def read(path):
    return json.loads(path.read_bytes())

def row(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')

assert not DEST.exists(), 'One-shot; do not replay'
engine = read(DELIVERY / 'ci-jobs-8.stdout')
phoenix = read(DELIVERY / 'ci-jobs-7.stdout')
assert engine['headSha'] == phoenix['headSha'] == COMMIT
assert engine['databaseId'] == 40570933553 and phoenix['databaseId'] == 40570933769
assert engine['attempt'] == phoenix['attempt'] == 1
assert engine['status'] == phoenix['status'] == 'completed'
assert engine['conclusion'] == 'success' and phoenix['conclusion'] == 'failure'
assert len(engine['jobs']) == 6 and sum(len(j['steps']) for j in engine['jobs']) == 64
assert all(s['conclusion'] == 'success' for j in engine['jobs'] for s in j['steps'])
capability = next(j for j in engine['jobs'] if j['name'] == 'swift-capability-native')
checkout = next(s for s in capability['steps'] if s['name'] == 'Run actions/checkout@v4')
seconds = (datetime.fromisoformat(checkout['completedAt']) - datetime.fromisoformat(checkout['startedAt'])).total_seconds()
assert seconds == 10 and len(capability['steps']) == 10
remote = read(DELIVERY / 'phoenix-remote-artifact/receipt.json')
for name in ['format', 'compile']:
    command = next(c for c in remote['commands'] if c['label'] == name)
    assert command['exit_code'] == 0
    assert row(DELIVERY / ('phoenix-remote-artifact/' + name + '.log'))['sha256'] == command['sha256']
tests = next(c for c in remote['commands'] if c['label'] == 'tests')
assert tests['exit_code'] == 2
assert row(DELIVERY / 'phoenix-remote-artifact/tests.log')['sha256'] == tests['sha256']
raw = (DELIVERY / 'phoenix-remote-artifact/tests.log').read_text()
assert 'Result: 677/683 passed, 2 skipped' in raw and 'Failed: 6 tests' in raw
assert raw.count('code:  assert :persistent_term.get({Admission, KeyOwner}, :absent) == :absent') == 6
assert remote['cleanup'] == {'postgres_stopped': True, 'scratch_removed': True}
terminal_engine = {'schema': 1, 'commit': COMMIT, 'run_id': engine['databaseId'], 'url': engine['url'],
    'attempt': 1, 'conclusion': 'success', 'jobs_passed': 6, 'steps_passed': 64, 'steps_skipped': 0,
    'capability_checkout_seconds': seconds, 'capability_job_steps_passed': 10,
    'raw_observation': row(DELIVERY / 'ci-jobs-8.stdout'),
    'scope': 'Delivered engine checks and capability sparse checkout; local work/storage and default-authority candidates excluded.',
    'physical_native_or_GA_accepted': False}
terminal_phoenix = {'schema': 1, 'commit': COMMIT, 'run_id': phoenix['databaseId'], 'url': phoenix['url'],
    'attempt': 1, 'conclusion': 'failure', 'format_passed': True, 'compile_passed': True,
    'raw_result_summary': 'Result: 677/683 passed, 2 skipped', 'failed_tests': 6,
    'failure': 'All six dispatcher component methods fail setup because persistent_term is a retained ETS reference instead of absent. No registered owner was found; dead-reference fixture correction is under preparation.',
    'remote_fixture_cleanup': remote['cleanup'], 'raw_observation': row(DELIVERY / 'ci-jobs-7.stdout'),
    'artifact_extraction': row(DELIVERY / 'phoenix-remote-artifact-extraction.json'),
    'remote_receipt': row(DELIVERY / 'phoenix-remote-artifact/receipt.json'),
    'tests_log': row(DELIVERY / 'phoenix-remote-artifact/tests.log'),
    'scope': 'Ordinary existing GitHub CI observation, not independent callback acceptance or local broad-harness replay.',
    'GA_accepted': False}
save(DELIVERY / 'terminal-engine-attempt1.json', terminal_engine)
save(DELIVERY / 'terminal-phoenix-dispatcher-fixture-failure.json', terminal_phoenix)

w = read(ROOT / 'work-graph.json'); g = read(ROOT / 'gates/ga.json')
def update_delivery(value):
    if isinstance(value, dict):
        if value.get('commit') == COMMIT and 'runs' in value:
            value.update({'status': 'pushed-Engine-passed-Phoenix-dispatcher-fixture-failed',
                'terminal_Engine': row(DELIVERY / 'terminal-engine-attempt1.json'),
                'terminal_Phoenix': row(DELIVERY / 'terminal-phoenix-dispatcher-fixture-failure.json')})
            for run in value['runs']:
                if run['databaseId'] in [engine['databaseId'], phoenix['databaseId']]:
                    run['status'] = 'completed'
                    run['conclusion'] = 'success' if run['databaseId'] == engine['databaseId'] else 'failure'
        for child in value.values():
            update_delivery(child)
    elif isinstance(value, list):
        for child in value:
            update_delivery(child)
for value in [w, g]:
    update_delivery(value)
for target in [w['packages'][7], g['gates'][1]]:
    target['capabilityHostSparseCheckout'].update({'status': 'accepted-delivered-and-remote-capability-job-passed',
        'remote_CI_passed': True, 'remote_checkout_seconds': seconds, 'remote_job_steps_passed': 10})
for target in [w['packages'][13], g['gates'][21]]:
    dispatcher = target['fixedWorkspaceDispatcher']
    dispatcher['format_correction'].update({'status': 'accepted-delivered-remote-format-and-compile-passed',
        'remote_formatter_passed': True, 'remote_compile_passed': True, 'remote_CI_passed': False})
    dispatcher['component_test_correction'] = {'status': 'source-preparation-for-dead-admission-reference-CI-fixture',
        'ownership': 'verification/console-dispatcher-dead-admission-ci-correction',
        'remote_failure': row(DELIVERY / 'terminal-phoenix-dispatcher-fixture-failure.json'),
        'implementation_accepted': False, 'runtime_released': False, 'GA_accepted': False}
    candidate = dispatcher['default_authority_candidate']
    candidate.update({'status': 'candidate4-method-bodies-complete-terminal-teardown-failed-lifecycle-correction-pending',
        'candidate_1_preexecution_cleanup_and_time_bound_corrections_pending': False,
        'candidate_2_failure': 'Migration fixture pool had one connection; zero methods ran.',
        'candidate_3_failure': 'Fixture expected13 tables instead of the exact12; zero methods ran.',
        'candidate_4_failure': 'Seven method bodies completed; setup_all teardown found stale Admission reference, invalidating all seven. No clean-pass acceptance.',
        'candidate_4_receipt': row(AUTHORITY / 'candidate-4/execution/receipt.json'),
        'candidate_4_independent_review': row(ROOT / 'verification/console-dispatcher-authority-preaccess/candidate-4-terminal-review.json'),
        'owned_OS_cleanup_confirmed_all_runs': True, 'actual_default_Repo_success_accepted': False,
        'next_lifecycle_correction_runtime_released': False})

texts = {}
for name in ['PLAN.md', 'STATUS.md']:
    text = (ROOT / name).read_text()
    old = 'The correction is pushed in `6f116c6a`; new CI remains pending.'
    new = 'The correction is pushed in `6f116c6a`; remote formatting and compilation pass. Phoenix then fails all six dispatcher component methods in setup because a prior suite leaves a stale admission-table reference; a narrow fixture correction is being prepared.'
    assert text.count(old) == 1
    text = text.replace(old, new)
    old = 'Engine and Phoenix CI are pending. Active default-authority and work/storage lanes are excluded; remote checkout duration, dependency resolution and complete job outcomes remain pending.'
    new = 'Engine CI passes all six jobs and 64 steps on attempt one without skips. The capability job passes all ten steps, including a ten-second checkout. Phoenix passes formatting and compilation but fails six dispatcher fixture setups. Active default-authority and work/storage lanes are excluded from this delivery.'
    assert text.count(old) == 1
    text = text.replace(old, new)
    old = 'Actual default verifier/default Repo success and database authority remain pending.'
    new = 'Actual default verifier/default Repo qualification remains pending: the bounded host fixture now completes all seven authorization method bodies, but teardown fails on a stale Admission reference and ExUnit invalidates all seven. Two earlier setup failures and all owned OS cleanup receipts are preserved; explicit fixture lifecycle correction is being prepared.'
    assert text.count(old) == 1
    texts[name] = text.replace(old, new)
assert w['packages'][13]['fixedWorkspaceDispatcher'] == g['gates'][21]['fixedWorkspaceDispatcher']
assert w['packages'][7]['capabilityHostSparseCheckout'] == g['gates'][1]['capabilityHostSparseCheckout']
for name, value in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(value, indent=2) + '\n')
for name, text in texts.items():
    (ROOT / name).write_text(text)
subprocess.run(['git', 'diff', '--check', '--', 'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json'], check=True, timeout=10)
save(DEST, {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT))],
    'python': sys.version, 'source_revision': COMMIT, 'terminal_engine': row(DELIVERY / 'terminal-engine-attempt1.json'),
    'terminal_phoenix': row(DELIVERY / 'terminal-phoenix-dispatcher-fixture-failure.json'),
    'authority_candidate4': row(AUTHORITY / 'candidate-4/execution/receipt.json'),
    'metadata': [row(ROOT / name) for name in ['PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json']],
    'GA_verified': 0, 'runtime_replayed': False})
print(json.dumps({'status': 'recorded', 'engine_jobs_passed': 6, 'engine_steps_passed': 64, 'capability_checkout_seconds': seconds,
    'Phoenix_passed': False, 'authority_fixture_passed': False, 'GA_verified': 0}))
