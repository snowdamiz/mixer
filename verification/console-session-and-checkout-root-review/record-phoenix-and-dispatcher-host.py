"""Record terminal delivered CI and the first bounded dispatcher host result once."""
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
DISPATCHER = ROOT / 'verification/console-fixed-workspace-dispatcher'
DEST = OUT / 'phoenix-and-dispatcher-host-checkpoint.json'

def row(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def read(path):
    return json.loads(path.read_bytes())

def save(path, data):
    with path.open('x') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')

assert not DEST.exists(), 'One-shot; do not replay'
ci = read(DELIVERY / 'ci-jobs-7.stdout')
assert ci['headSha'] == 'ee9f6dc77f88259e2b143fc81dc1085b34a4a943'
assert ci['databaseId'] == 40563355266 and ci['attempt'] == 1
assert ci['status'] == 'completed' and ci['conclusion'] == 'success'
assert len(ci['jobs']) == 1 and len(ci['jobs'][0]['steps']) == 13
assert all(s['status'] == 'completed' and s['conclusion'] == 'success' for s in ci['jobs'][0]['steps'])
host = read(DISPATCHER / 'host-receipt.json')
release = read(DISPATCHER / 'host-execution-release.json')
assert host['execution_plan_sha256'] == release['execution_plan_sha256'] == '1a998b33cbd9df8a7ff2cbcef790f35e7a29c4c3b867fb5c3abca574bfe69500'
assert host['status'] == 'failed' and host['exit_code'] == 1
assert host['scratch_removed'] and host['direct_child_reaped'] and host['owned_group_absent']
assert not host['cleanup_error'] and not host['runner_error'] and not host['postrun_original_changes']
assert host['postrun_original_hashes_verified'] == 985
assert row(DISPATCHER / 'host.stdout.txt')['sha256'] == host['output_sha256']
raw = (DISPATCHER / 'host.stdout.txt').read_text()
assert 'Result: 18/19 passed' in raw and 'assert function_exported?(Dispatcher, :dispatch, 3)' in raw
assert 'COMPILED 35 ordinary/new modules' in raw
w = read(ROOT / 'work-graph.json'); g = read(ROOT / 'gates/ga.json')
c = w['packages'][7]['fixtureCacheStateContractCandidate']
assert c == g['gates'][1]['fixtureCacheStateContractCandidate']
assert w['packages'][4]['privateOwnerEffectContractCandidate'] == g['gates'][4]['privateOwnerEffectContractCandidate']
terminal = {'schema': 1, 'commit': ci['headSha'], 'run_id': ci['databaseId'], 'url': ci['url'],
    'attempt': 1, 'conclusion': 'success', 'jobs_passed': 1, 'steps_passed': 13, 'steps_skipped': 0,
    'raw_observation': row(DELIVERY / 'ci-jobs-7.stdout'),
    'scope': 'Existing Phoenix CI at delivered ee9f6dc7. Active uncommitted dispatcher and stopped callback work are excluded.',
    'dispatcher_session_provider_native_or_GA_accepted': False}
save(DELIVERY / 'terminal-phoenix.json', terminal)
for target in [w['packages'][13], g['gates'][21]]:
    delivery = target['browserSessionConsumer']['delivery']
    delivery.update({'status': 'pushed-Console-and-Phoenix-passed-Engine-pending', 'terminal_phoenix': row(DELIVERY / 'terminal-phoenix.json')})
    for run in delivery['runs']:
        if run['databaseId'] == ci['databaseId']:
            run.update({'status': 'completed', 'conclusion': 'success'})
    dispatcher = target['fixedWorkspaceDispatcher']
    dispatcher.update({'status': 'source-prepared-initial-host-harness-correction-pending',
        'compiler_or_host_execution_released': True, 'host_execution_release': row(DISPATCHER / 'host-execution-release.json'),
        'initial_host_receipt': row(DISPATCHER / 'host-receipt.json'), 'initial_host_passed': False,
        'initial_host_tests_passed': 18, 'initial_host_tests_total': 19,
        'initial_host_failure': 'Export-introspection test ran before module load; exact output preserved. ParallelCompiler option warning also needs harness correction.',
        'initial_owned_cleanup_confirmed': True, 'targeted_harness_correction_selected': True,
        'corrected_host_execution_released': False, 'implementation_accepted': False})
c['SwiftSparseCheckout']['delivery'].update({'status': 'pushed-Console-and-Phoenix-passed-Engine-pending', 'terminal_phoenix': row(DELIVERY / 'terminal-phoenix.json')})
g['gates'][1]['fixtureCacheStateContractCandidate'] = copy.deepcopy(c)
texts = {}
for name in ['PLAN.md', 'STATUS.md']:
    text = (ROOT / name).read_text()
    old = 'Console CI now passes all nine steps on attempt one, including the new session consumer; Phoenix and Engine remain pending.'
    new = 'Console CI passes all nine steps and Phoenix all thirteen steps on attempt one; Engine remains pending.'
    assert text.count(old) == 1
    text = text.replace(old, new)
    old = 'source work is authorized, while its exact host command closure awaits root review.'
    new = 'its first bounded host run compiles 35 modules and passes eighteen of nineteen tests. The remaining test queried exports before loading the module; a focused harness correction is selected, with the failed output and confirmed process/scratch cleanup preserved.'
    assert text.count(old) == 1
    texts[name] = text.replace(old, new)
for name, data in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(data, indent=2) + '\n')
for name, text in texts.items():
    (ROOT / name).write_text(text)
subprocess.run(['git', 'diff', '--check', '--', 'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json'], check=True, timeout=10)
save(DEST, {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT))], 'python': sys.version,
    'terminal_phoenix': row(DELIVERY / 'terminal-phoenix.json'), 'initial_dispatcher_host': row(DISPATCHER / 'host-receipt.json'),
    'metadata_files': [row(ROOT / name) for name in ['PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json']],
    'W08_G02_equal': True, 'W05_G05_equal': True, 'GA_verified': 0})
print(json.dumps({'Phoenix': 'passed-all-13-steps', 'dispatcher': '18-of-19-targeted-harness-correction-pending', 'GA_verified': 0}))
