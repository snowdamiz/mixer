"""Record exact terminal Console CI for the delivered session source once."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
assert not (OUT / 'terminal-console.json').exists(), 'One-shot; do not replay'

def row(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

receipt = json.loads((OUT / 'receipt.json').read_bytes())
ci = json.loads((OUT / 'ci-jobs-1.stdout').read_bytes())
assert receipt['commit'] == ci['headSha'] == 'ee9f6dc77f88259e2b143fc81dc1085b34a4a943'
assert receipt['pushed'] and ci['attempt'] == 1 and ci['conclusion'] == 'success'
assert len(ci['jobs']) == 1 and len(ci['jobs'][0]['steps']) == 9
assert all(s['status'] == 'completed' and s['conclusion'] == 'success' for s in ci['jobs'][0]['steps'])
checkout = next(s for s in ci['jobs'][0]['steps'] if s['name'] == 'Run actions/checkout@v4')
seconds = (datetime.fromisoformat(checkout['completedAt']) - datetime.fromisoformat(checkout['startedAt'])).total_seconds()
terminal = {'schema': 1, 'commit': ci['headSha'], 'run_id': ci['databaseId'], 'url': ci['url'],
    'attempt': 1, 'conclusion': 'success', 'jobs_passed': 1, 'steps_passed': 9, 'steps_skipped': 0,
    'checkout_seconds': seconds, 'raw_observation': row(OUT / 'ci-jobs-1.stdout'),
    'scope': 'Delivered frontend session consumer with full console host regression, strict typecheck and production build. This does not qualify backend session admission or actual browser/provider behavior.',
    'backend_browser_provider_native_customer_or_GA_accepted': False}
with (OUT / 'terminal-console.json').open('x') as stream:
    json.dump(terminal, stream, indent=2); stream.write('\n')
w = json.loads((ROOT / 'work-graph.json').read_bytes()); g = json.loads((ROOT / 'gates/ga.json').read_bytes())
for target in [w['packages'][13], g['gates'][21]]:
    delivery = target['browserSessionConsumer']['delivery']
    delivery.update({'status': 'pushed-Console-passed-Phoenix-and-Engine-pending', 'terminal_console': row(OUT / 'terminal-console.json')})
    for run in delivery['runs']:
        if run['databaseId'] == ci['databaseId']:
            run.update({'status': 'completed', 'conclusion': 'success'})
    target['browserSessionConsumer']['remote_console_passed'] = True
    target['latestConsoleCI'] = 'ee9f6dc7 Console CI passes all nine steps on attempt one, including delivered frontend session source, full host tests, typecheck and production build. Backend/browser/provider/GA acceptance remains pending.'
w['packages'][13]['nextImplementation'] = 'Implement the selected private fixed workspace dispatcher, review its exact ordinary host compiler closure before execution, then independently review. Real session/cookie lifecycle/provider and default Repo/RLS integration remain pending; stopped callback work is not replayed.'
c = w['packages'][7]['fixtureCacheStateContractCandidate']; assert c == g['gates'][1]['fixtureCacheStateContractCandidate']
c['SwiftSparseCheckout']['delivery'].update({'status': 'pushed-Console-passed-Phoenix-and-Engine-pending', 'terminal_console': row(OUT / 'terminal-console.json')})
g['gates'][1]['fixtureCacheStateContractCandidate'] = copy.deepcopy(c)
for name, data in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(data, indent=2) + '\n')
for name in ['PLAN.md', 'STATUS.md']:
    path = ROOT / name; text = path.read_text()
    old = 'Console, Phoenix and Engine CI are pending.'
    new = 'Console CI now passes all nine steps on attempt one, including the new session consumer; Phoenix and Engine remain pending.'
    assert text.count(old) == 1
    path.write_text(text.replace(old, new))
for path, digest in receipt['protected_work_unchanged'].items(): assert row(ROOT / path)['sha256'] == digest
assert not subprocess.run(['git', 'diff', '--cached', '--name-only'], capture_output=True, check=True, timeout=10).stdout
subprocess.run(['git', 'diff', '--check', '--', 'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json'], check=True, timeout=10)
print(json.dumps({'commit': ci['headSha'], 'Console_passed': True, 'checkout_seconds': seconds, 'other_CI_pending': True}))
