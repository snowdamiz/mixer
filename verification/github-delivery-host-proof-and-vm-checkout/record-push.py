"""Record exact delivered checkpoint and observed in-progress CI."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
assert not (OUT / 'push-metadata.json').exists()
sha = lambda data: hashlib.sha256(data).hexdigest()
def row(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': sha(data)}
receipt = json.loads((OUT / 'receipt.json').read_text())
assert row(OUT / 'receipt.json')['sha256'] == '1605214820923836052b2bc06932395251e4e3b63fd85a224a1df7ad3b46555b'
assert receipt['commit'] == '9398732c23648a82097d5a72b02b1c77af818e41' and receipt['pushed']
assert receipt['committed_paths'] == 547
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, timeout=10, text=True).strip() == receipt['commit']
ci, = json.loads((OUT / 'ci-runs-1.stdout').read_text())
assert ci['databaseId'] == 40545367451 and ci['headSha'] == receipt['commit'] and ci['status'] == 'in_progress'
work = json.loads((ROOT / 'work-graph.json').read_text())
gates = json.loads((ROOT / 'gates/ga.json').read_text())
c = work['packages'][7]['fixtureCacheStateContractCandidate']
assert c == gates['gates'][1]['fixtureCacheStateContractCandidate']
d = c['guarded_snapshot_host_proof_vm_checkout_delivery']
d.update({'status': 'pushed-exact-commit-CI-in-progress', 'commit': receipt['commit'], 'tree': receipt['tree'],
    'paths': 547, 'pushed': True, 'force': False, 'receipt': row(OUT / 'receipt.json'),
    'manifest_sha256': receipt['manifest_sha256'],
    'CI': {'run': ci['databaseId'], 'status': ci['status'], 'conclusion': ci['conclusion'],
           'url': ci['url'], 'observation': row(OUT / 'ci-runs-1.stdout'), 'passed': False}})
c['VM_CI_sparse_checkout'].update({'status': 'pushed-local-audit-passed-remote-CI-in-progress',
    'commit': receipt['commit'], 'CI_run': ci['databaseId']})
parent_obs = ROOT / 'verification/github-delivery-owned-binding-source-review/ci-jobs-8.stdout'
parent = json.loads(parent_obs.read_text())
assert parent['attempt'] == 2 and parent['status'] == 'in_progress'
c['guarded_snapshot_owned_binding_source_review_delivery']['CI']['observation'] = row(parent_obs)
gates['gates'][1]['fixtureCacheStateContractCandidate'] = copy.deepcopy(c)
assert len(work['packages']) == 18 and len(gates['gates']) == 38
assert sum(g['status'] == 'running' for g in gates['gates']) == 8
assert sum(g['status'] == 'planned' for g in gates['gates']) == 30
assert work['packages'][4]['privateOwnerEffectContractCandidate'] == gates['gates'][4]['privateOwnerEffectContractCandidate']
for name, value in [('work-graph.json', work), ('gates/ga.json', gates)]:
    (ROOT / name).write_text(json.dumps(value, indent=2) + '\n')
new = ('Checkpoint `9398732` is pushed with 547 selected paths and six frozen packets: accepted original-source string binding and conditional provider accounting, both returned acquisition-model reviews, and a narrow VM CI checkout repair. The real local sparse checkout contains 464 files (20,395,752 bytes); both offline generators and all selected source hashes pass, with every VM command unchanged. [CI](https://github.com/snowdamiz/mixer/actions/runs/40545367451) is running for this exact changed workflow. Parent `a96712b` VM retry has passed checkout, debug and release tests and is still running; its first checkout-timeout attempt is retained. Three active source/correction lanes were excluded. Canonical product sources, actual root funding, runtime/native and GA acceptance remain unchanged.')
for name in ['PLAN.md', 'STATUS.md']:
    path = ROOT / name
    text = path.read_text()
    old = next(p for p in text.split('\n\n') if p.startswith('A coherent checkpoint is prepared for delivery:'))
    path.write_text(text.replace(old, new, 1))
for name, expected in receipt['protected_work_unchanged'].items():
    assert row(ROOT / name)['sha256'] == expected
subprocess.run(['git', 'diff', '--check', '--', 'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json'], cwd=ROOT, timeout=10, check=True)
assert not subprocess.check_output(['git', 'diff', '--cached', '--name-only'], cwd=ROOT, timeout=10)
with (OUT / 'push-metadata.json').open('x') as stream:
    json.dump({'at': datetime.now(timezone.utc).isoformat(), 'commit': receipt['commit'],
        'metadata': [row(ROOT / n) for n in ['PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json']],
        'CI_run': ci['databaseId'], 'protected_work_unchanged': True, 'GA_verified': 0}, stream, indent=2)
    stream.write('\n')
print(json.dumps({'commit': receipt['commit'], 'CI': ci['url'], 'metadata_updated': True}))
