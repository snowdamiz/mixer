"""Record terminal CI for the exact pushed source-rebind/services checkpoint."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'terminal-ci-attempt1.json'
assert not OUT.exists()

def row(p):
    raw = p.read_bytes()
    return {'path': str(p.relative_to(ROOT)), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

ci = json.loads((HERE / 'ci-jobs-7.stdout').read_bytes())
assert ci['headSha'] == 'd6af73813244c330a979afb83b45f53490ff5b29'
assert ci['databaseId'] == 40551094236 and ci['attempt'] == 1
assert ci['status'] == 'completed' and ci['conclusion'] == 'success'
assert len(ci['jobs']) == 6
assert all(j['status'] == 'completed' and j['conclusion'] == 'success' for j in ci['jobs'])
steps = [s for j in ci['jobs'] for s in j['steps']]
assert len(steps) == 64 and all(s['conclusion'] == 'success' for s in steps)
receipt = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'commit': ci['headSha'], 'run': ci['databaseId'], 'url': ci['url'], 'attempt': 1,
    'status': 'completed', 'conclusion': 'success', 'passed_jobs': 6, 'passed_steps': 64,
    'skipped_steps': 0, 'observation': row(HERE / 'ci-jobs-7.stdout'),
    'command_receipt': row(HERE / 'ci-jobs-7.command.json'),
    'script': row(Path(__file__).resolve()), 'python': sys.version,
    'scope': 'Remote existing Engine workflow for d6af738, including the changed services checkout. No pending local Rust ownership or console change is qualified by this run.',
    'GA_verified': 0}
with OUT.open('x') as stream:
    json.dump(receipt, stream, indent=2)
    stream.write('\n')
w = json.loads((ROOT / 'work-graph.json').read_bytes())
g = json.loads((ROOT / 'gates/ga.json').read_bytes())
c = w['packages'][7]['fixtureCacheStateContractCandidate']
assert c == g['gates'][1]['fixtureCacheStateContractCandidate']
d = c['guarded_snapshot_source_rebind_services_checkout_delivery']
d.update({'status': 'pushed-all-six-Engine-jobs-and64-steps-passed-attempt1', 'CI_pending': False,
    'terminal_CI': row(OUT)})
d['CI'].update({'status': 'completed', 'conclusion': 'success', 'passed': True,
    'observation': row(HERE / 'ci-jobs-7.stdout'), 'jobs': [{k: j[k] for k in ['name', 'status', 'conclusion']} for j in ci['jobs']],
    'attempt': 1, 'passed_jobs': 6, 'passed_steps': 64, 'skipped_steps': 0})
c['services_CI_sparse_checkout']['terminal_workflow_evidence'] = row(OUT)
g['gates'][1]['fixtureCacheStateContractCandidate'] = copy.deepcopy(c)
for name, value in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(value, indent=2) + '\n')
for name in ['PLAN.md', 'STATUS.md']:
    p = ROOT / name
    text = p.read_text()
    old = ('has passed services, VM, Android host and the Swift cache fixture jobs. Services checkout took four seconds '
           'and all eight steps passed, including vet and race tests. The two remaining Swift jobs are still running.')
    assert text.count(old) == 1
    p.write_text(text.replace(old, 'passes all six jobs and 64 steps on attempt one, with no skipped steps. '
        'The changed services checkout took four seconds; its full vet and race tests pass.'))
subprocess.run(['git', 'diff', '--check', '--', 'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json'], cwd=ROOT, timeout=10, check=True)
print(json.dumps({'terminal_receipt': row(OUT), 'passed_jobs': 6, 'passed_steps': 64, 'GA_verified': 0}))
