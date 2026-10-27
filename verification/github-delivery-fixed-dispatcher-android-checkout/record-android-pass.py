"""Record the terminal Android job without claiming the still-running Engine run passed."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DEST = OUT / 'terminal-android-owner-host.json'
assert not DEST.exists(), 'One-shot; do not replay'

def row(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

ci = json.loads((OUT / 'ci-jobs-1.stdout').read_bytes())
assert ci['headSha'] == 'd04fd5cc71bc72061f18203e414b90869129b4ca'
assert ci['databaseId'] == 40567963687 and ci['attempt'] == 1
job = next(j for j in ci['jobs'] if j['name'] == 'android-owner-host')
assert job['status'] == 'completed' and job['conclusion'] == 'success'
assert len(job['steps']) == 8 and all(s['status'] == 'completed' and s['conclusion'] == 'success' for s in job['steps'])
checkout = next(s for s in job['steps'] if s['name'] == 'Run actions/checkout@v4')
seconds = (datetime.fromisoformat(checkout['completedAt']) - datetime.fromisoformat(checkout['startedAt'])).total_seconds()
assert seconds == 3
value = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'commit': ci['headSha'],
    'run_id': ci['databaseId'], 'job_id': job['databaseId'], 'url': job['url'], 'attempt': 1,
    'conclusion': 'success', 'steps_passed': 8, 'steps_skipped': 0, 'checkout_seconds': seconds,
    'raw_observation': row(OUT / 'ci-jobs-1.stdout'), 'whole_Engine_terminal': False,
    'scope': 'New sparse checkout and all existing Android JVM owner, concrete renderer and environment host checks pass in GitHub CI.',
    'native_runtime_physical_or_GA_accepted': False}
with DEST.open('x') as stream:
    json.dump(value, stream, indent=2); stream.write('\n')
w = json.loads((ROOT / 'work-graph.json').read_bytes()); g = json.loads((ROOT / 'gates/ga.json').read_bytes())
for target in [w['packages'][4], g['gates'][4]]:
    target['ownerHostSparseCheckout'].update({'remote_CI_passed': True, 'remote_checkout_seconds': seconds,
        'terminal_android_owner_job': row(DEST)})
    target['ownerHostSparseCheckout']['delivery'].update({'status': 'pushed-Android-owner-job-passed-full-Engine-and-Phoenix-pending',
        'terminal_android_owner_job': row(DEST)})
for name, data in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(data, indent=2) + '\n')
for name in ['PLAN.md', 'STATUS.md']:
    path = ROOT / name; text = path.read_text()
    old = 'Engine and Phoenix CI are pending; active new Rust implementation/review and the next checkout proposal were excluded.'
    new = 'The Android owner job passes all eight steps on attempt one with a three-second checkout; full Engine and Phoenix CI remain pending. Active new Rust implementation/review and the next checkout proposal were excluded.'
    assert text.count(old) == 1
    path.write_text(text.replace(old, new))
assert w['packages'][4]['privateOwnerEffectContractCandidate'] == g['gates'][4]['privateOwnerEffectContractCandidate']
assert w['packages'][7]['fixtureCacheStateContractCandidate'] == g['gates'][1]['fixtureCacheStateContractCandidate']
subprocess.run(['git', 'diff', '--check', '--', 'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json'], check=True, timeout=10)
print(json.dumps({'Android_owner_job_passed': True, 'steps': 8, 'checkout_seconds': seconds, 'whole_Engine_pending': True}))
