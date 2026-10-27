"""Record the exact non-force push and three observed workflow runs."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'push-metadata.json'
assert not OUT.exists()

def row(p):
    raw = p.read_bytes()
    return {'path': str(p.relative_to(ROOT)), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

receipt = json.loads((HERE / 'receipt.json').read_bytes())
commit = 'b231f3d405c06bfb348f193d46a348af0529bd84'
assert receipt['commit'] == commit and receipt['pushed'] and not receipt['force']
assert receipt['committed_paths'] == 492 and len(receipt['canonical_paths']) == 11
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,timeout=10,text=True).strip() == commit
runs = json.loads((HERE / 'ci-runs-1.stdout').read_bytes())
assert len(runs) == 3 and all(x['headSha'] == commit for x in runs)
assert {x['name'] for x in runs} == {'Console checks','Phoenix foundation checks','Owned engine checks'}
w = json.loads((ROOT / 'work-graph.json').read_bytes())
g = json.loads((ROOT / 'gates/ga.json').read_bytes())
delivery = w['packages'][13]['firstPageReturn']['delivery']
delivery.update({'status': 'pushed-three-workflows-observed-not-terminal', 'commit': commit,
    'tree': receipt['tree'], 'paths': 492, 'pushed': True, 'force': False,
    'receipt': row(HERE / 'receipt.json'), 'manifest_sha256': receipt['manifest_sha256'],
    'CI': {'observation': row(HERE / 'ci-runs-1.stdout'), 'runs': runs, 'all_passed': False}})
g['gates'][21]['firstPageReturn']['delivery'] = copy.deepcopy(delivery)
c = w['packages'][7]['fixtureCacheStateContractCandidate']
assert c == g['gates'][1]['fixtureCacheStateContractCandidate']
c['guarded_snapshot_actual_owner_selection_console_delivery'] = copy.deepcopy(delivery)
g['gates'][1]['fixtureCacheStateContractCandidate'] = copy.deepcopy(c)
w['packages'][13]['nextImplementation'] = 'Observe changed console/Phoenix/Engine CI for b231f3d. Select the exact authenticated same-origin session integration prerequisite for production App; preserve unavailable builds/releases and the stopped hosted review boundary.'
for name, value in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(value, indent=2) + '\n')
for name in ['PLAN.md', 'STATUS.md']:
    p = ROOT / name
    text = p.read_text()
    old = 'it is validated locally and awaits delivery.'
    assert text.count(old) == 1
    p.write_text(text.replace(old, 'it is pushed in checkpoint `b231f3d` with 492 selected paths and four frozen contract/review packets. '
        'Console and Phoenix CI are running, while Engine CI is queued; none is yet terminal.'))
for path, digest in receipt['protected_work_unchanged'].items():
    assert row(ROOT / path)['sha256'] == digest
subprocess.run(['git','diff','--check','--','PLAN.md','STATUS.md','work-graph.json','gates/ga.json'],cwd=ROOT,timeout=10,check=True)
assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,timeout=10)
with OUT.open('x') as stream:
    json.dump({'at': datetime.now(timezone.utc).isoformat(), 'commit': commit,
        'script': row(Path(__file__).resolve()), 'delivery_receipt': row(HERE / 'receipt.json'),
        'metadata': [row(ROOT / p) for p in ['PLAN.md','STATUS.md','work-graph.json','gates/ga.json']],
        'CI_runs': runs, 'protected_work_unchanged': True, 'GA_verified': 0}, stream, indent=2)
    stream.write('\n')
print(json.dumps({'commit': commit, 'pushed_paths': 492, 'CI_runs': len(runs), 'terminal_CI': False}))
