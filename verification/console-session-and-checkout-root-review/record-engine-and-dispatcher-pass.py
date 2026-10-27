"""Record delivered Engine CI and the frozen producer's bounded host success once."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DELIVERY = ROOT / 'verification/github-delivery-session-consumer-swift-checkout'
PRODUCER = ROOT / 'verification/console-fixed-workspace-dispatcher'
DEST = OUT / 'engine-and-dispatcher-pass-checkpoint.json'

def row(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def read(path):
    return json.loads(path.read_bytes())

def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')

assert not DEST.exists(), 'One-shot; do not replay'
ci = read(DELIVERY / 'ci-jobs-9.stdout')
assert ci['headSha'] == 'ee9f6dc77f88259e2b143fc81dc1085b34a4a943'
assert ci['databaseId'] == 40563355142 and ci['attempt'] == 1
assert ci['status'] == 'completed' and ci['conclusion'] == 'success' and len(ci['jobs']) == 6
assert sum(len(j['steps']) for j in ci['jobs']) == 64
assert all(j['status'] == 'completed' and j['conclusion'] == 'success' for j in ci['jobs'])
assert all(s['status'] == 'completed' and s['conclusion'] == 'success' for j in ci['jobs'] for s in j['steps'])
swift = next(j for j in ci['jobs'] if j['name'] == 'swift')
checkout = next(s for s in swift['steps'] if s['name'] == 'Run actions/checkout@v4')
seconds = (datetime.fromisoformat(checkout['completedAt']) - datetime.fromisoformat(checkout['startedAt'])).total_seconds()
assert seconds == 11
assert row(PRODUCER / 'freeze.json')['sha256'] == 'fb45ab6c0574170596f5665f8cdfac6b352f02c1086839de5ed7a0f49a11e175'
frozen = read(PRODUCER / 'freeze.json')
assert len(frozen['members']) == 90
for entry in frozen['members']:
    actual = row(PRODUCER / entry['path'])
    assert actual['bytes'] == entry['bytes'] and actual['sha256'] == entry['sha256']
manifest = read(PRODUCER / 'source-manifest.json')
assert len(manifest['members']) == 35
for entry in manifest['members']:
    actual = row(ROOT / entry['path'])
    assert actual['bytes'] == entry['bytes'] and actual['sha256'] == entry['sha256']
host = read(PRODUCER / 'host-attempt-3-receipt.json')
assert host['status'] == 'passed' and host['exit_code'] == 0
assert host['scratch_removed'] and host['direct_child_reaped'] and host['owned_group_absent']
assert host['postrun_original_changes'] == [] and host['postrun_original_hashes_verified'] == 985
assert row(PRODUCER / 'host-attempt-3.stdout.txt')['sha256'] == host['output_sha256']
raw = (PRODUCER / 'host-attempt-3.stdout.txt').read_text()
assert 'compile_warnings=0 runtime_warnings=0' in raw
assert 'RESULT {"total":19,"failures":0,"excluded":0,"skipped":0}' in raw
terminal = {'schema': 1, 'commit': ci['headSha'], 'run_id': ci['databaseId'], 'url': ci['url'],
    'attempt': 1, 'conclusion': 'success', 'jobs_passed': 6, 'steps_passed': 64, 'steps_skipped': 0,
    'swift_checkout_seconds': seconds, 'raw_observation': row(DELIVERY / 'ci-jobs-9.stdout'),
    'scope': 'Delivered ee9f6dc7 Engine CI, including the accepted Swift sparse checkout. Uncommitted Android checkout, backend dispatcher and isolated Rust repair are excluded.',
    'native_physical_or_GA_accepted': False}
save(DELIVERY / 'terminal-engine-attempt1.json', terminal)
w = read(ROOT / 'work-graph.json'); g = read(ROOT / 'gates/ga.json')
c = w['packages'][7]['fixtureCacheStateContractCandidate']
assert c == g['gates'][1]['fixtureCacheStateContractCandidate']
for target in [w['packages'][13], g['gates'][21]]:
    delivery = target['browserSessionConsumer']['delivery']
    delivery.update({'status': 'pushed-all-three-CI-runs-passed-attempt-one', 'terminal_engine': row(DELIVERY / 'terminal-engine-attempt1.json')})
    for run in delivery['runs']:
        if run['databaseId'] == ci['databaseId']:
            run.update({'status': 'completed', 'conclusion': 'success'})
    target['fixedWorkspaceDispatcher'].update({'status': 'producer-host-passed-independent-review-active',
        'corrected_host_execution_released': True, 'producer_host_passed': True,
        'producer_host_tests': 19, 'producer_compile_warnings': 0, 'producer_runtime_warnings': 0,
        'producer_freeze': row(PRODUCER / 'freeze.json'), 'producer_receipt': row(PRODUCER / 'receipt.json'),
        'producer_host_receipt': row(PRODUCER / 'host-attempt-3-receipt.json'),
        'earlier_harness_failures_preserved': 2, 'all_attempts_owned_cleanup_confirmed': True,
        'independent_ownership': 'verification/console-fixed-workspace-dispatcher-independent',
        'implementation_accepted': False})
c['SwiftSparseCheckout'].update({'remote_CI_passed': True, 'remote_checkout_seconds': seconds})
c['SwiftSparseCheckout']['delivery'].update({'status': 'pushed-all-three-CI-runs-passed-attempt-one', 'terminal_engine': row(DELIVERY / 'terminal-engine-attempt1.json')})
g['gates'][1]['fixtureCacheStateContractCandidate'] = copy.deepcopy(c)
texts = {}
for name in ['PLAN.md', 'STATUS.md']:
    text = (ROOT / name).read_text()
    old = 'Console CI passes all nine steps and Phoenix all thirteen steps on attempt one; Engine remains pending.'
    new = 'Console and Phoenix CI pass, and Engine passes all six jobs and 64 steps on attempt one with no skipped steps. The changed Swift checkout took eleven seconds.'
    assert text.count(old) == 1
    text = text.replace(old, new)
    old = 'its first bounded host run compiles 35 modules and passes eighteen of nineteen tests. The remaining test queried exports before loading the module; a focused harness correction is selected, with the failed output and confirmed process/scratch cleanup preserved.'
    new = 'its corrected bounded host run compiles 35 modules with no warnings and passes all nineteen tests. Both earlier harness failures and confirmed cleanup remain preserved; fresh independent source/host review is active.'
    assert text.count(old) == 1
    texts[name] = text.replace(old, new)
for name, data in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(data, indent=2) + '\n')
for name, text in texts.items():
    (ROOT / name).write_text(text)
subprocess.run(['git', 'diff', '--check', '--', 'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json'], check=True, timeout=10)
save(DEST, {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'python': sys.version,
    'terminal_engine': row(DELIVERY / 'terminal-engine-attempt1.json'), 'producer_receipt': row(PRODUCER / 'receipt.json'),
    'producer_members_verified': 90, 'live_source_inputs_verified': 35,
    'metadata_files': [row(ROOT / name) for name in ['PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json']],
    'implementation_acceptance_pending_independent_review': True, 'GA_verified': 0})
print(json.dumps({'Engine': '6-jobs-64-steps-pass-attempt1', 'dispatcher_producer': '19-passed', 'independent_pending': True}))
