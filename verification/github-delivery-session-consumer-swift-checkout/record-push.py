"""One-shot post-push metadata; exact delivery receipt remains immutable."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
assert not (OUT / 'post-push-metadata.json').exists(), 'One-shot; do not replay'

def row(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

receipt = json.loads((OUT / 'receipt.json').read_bytes())
assert receipt['pushed'] and not receipt['force']
assert subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, check=True, timeout=10).stdout.decode().strip() == receipt['commit']
runs = json.loads((OUT / 'ci-runs-1.stdout').read_bytes())
assert len(runs) == 3 and all(item['headSha'] == receipt['commit'] for item in runs)
delivery = {'status': 'pushed-remote-CI-pending', 'commit': receipt['commit'], 'tree': receipt['tree'],
    'paths': receipt['committed_paths'], 'pushed': True, 'force': False, 'receipt': row(OUT / 'receipt.json'),
    'manifest': row(OUT / 'manifest.json'), 'CI_observation': row(OUT / 'ci-runs-1.stdout'),
    'runs': runs, 'active_Rust_and_backend_lanes_excluded': True, 'GA_accepted': False}
w = json.loads((ROOT / 'work-graph.json').read_bytes()); g = json.loads((ROOT / 'gates/ga.json').read_bytes())
for target in [w['packages'][13], g['gates'][21]]:
    target['browserSessionConsumer'].update({'delivery_pending': False, 'delivery': copy.deepcopy(delivery)})
c = w['packages'][7]['fixtureCacheStateContractCandidate']
assert c == g['gates'][1]['fixtureCacheStateContractCandidate']
c['SwiftSparseCheckout'].update({'delivery_pending': False, 'delivery': copy.deepcopy(delivery)})
g['gates'][1]['fixtureCacheStateContractCandidate'] = copy.deepcopy(c)
assert w['packages'][4]['privateOwnerEffectContractCandidate'] == g['gates'][4]['privateOwnerEffectContractCandidate']
for name, data in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(data, indent=2) + '\n')
for name in ['PLAN.md', 'STATUS.md']:
    path = ROOT / name
    text = path.read_text()
    old = 'Remote validation of this candidate remains pending.'
    new = 'The accepted session consumer and Swift checkout change are pushed together as `ee9f6dc7` with 450 selected paths; Console, Phoenix and Engine CI are pending. Active Rust and backend selection lanes were excluded.'
    assert text.count(old) == 1
    path.write_text(text.replace(old, new))
subprocess.run(['git', 'diff', '--check', '--', 'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json'], check=True, timeout=10)
value = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'delivery': delivery,
    'metadata_files': [row(ROOT / name) for name in ['PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json']],
    'W08_G02_equal': True, 'W05_G05_equal': True, 'GA_verified': 0}
with (OUT / 'post-push-metadata.json').open('x') as stream:
    json.dump(value, stream, indent=2)
    stream.write('\n')
print(json.dumps({'recorded_commit': receipt['commit'], 'CI_runs': len(runs), 'GA_verified': 0}))
