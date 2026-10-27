"""Record the exact authorized delivery and first observed queued CI run."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
assert not (OUT / 'push-metadata.json').exists()
def row(p):
    raw = p.read_bytes()
    return {'path': str(p.relative_to(ROOT)), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
receipt = json.loads((OUT / 'receipt.json').read_bytes())
assert receipt['commit'] == 'd6af73813244c330a979afb83b45f53490ff5b29' and receipt['pushed']
assert receipt['committed_paths'] == 1546 and not receipt['force']
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, timeout=10, text=True).strip() == receipt['commit']
ci, = json.loads((OUT / 'ci-runs-1.stdout').read_bytes())
assert ci['databaseId'] == 40551094236 and ci['headSha'] == receipt['commit'] and ci['status'] == 'queued'
w = json.loads((ROOT / 'work-graph.json').read_bytes())
g = json.loads((ROOT / 'gates/ga.json').read_bytes())
c = w['packages'][7]['fixtureCacheStateContractCandidate']
assert c == g['gates'][1]['fixtureCacheStateContractCandidate']
d = c['guarded_snapshot_source_rebind_services_checkout_delivery']
d.update({'status': 'pushed-exact-commit-CI-queued', 'commit': receipt['commit'], 'tree': receipt['tree'],
    'paths': 1546, 'pushed': True, 'force': False, 'receipt': row(OUT / 'receipt.json'),
    'manifest_sha256': receipt['manifest_sha256'], 'CI': {'run': ci['databaseId'], 'status': ci['status'],
    'conclusion': ci['conclusion'], 'url': ci['url'], 'observation': row(OUT / 'ci-runs-1.stdout'), 'passed': False}})
c['services_CI_sparse_checkout'].update({'status': 'pushed-local-selection-accepted-remote-CI-queued',
    'commit': receipt['commit'], 'CI_run': ci['databaseId']})
g['gates'][1]['fixtureCacheStateContractCandidate'] = copy.deepcopy(c)
assert len(w['packages']) == 18 and len(g['gates']) == 38
assert sum(x['status'] == 'running' for x in g['gates']) == 8 and sum(x['status'] == 'planned' for x in g['gates']) == 30
assert w['packages'][4]['privateOwnerEffectContractCandidate'] == g['gates'][4]['privateOwnerEffectContractCandidate']
for name, value in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(value, indent=2) + '\n')
paragraph = ('Checkpoint `d6af738` is pushed with 1,546 selected paths and eight frozen packets: bounded accepted current-provider string rebind and synthetic affine input-owner correction, the returned incomplete callee proposal, and the services CI checkout repair. '
    'Twelve independent checkout controls and all 153 selected input files pass, with every existing services command and the Go pin unchanged. '
    '[CI](https://github.com/snowdamiz/mixer/actions/runs/40551094236) is queued for this exact changed workflow; full remote service race validation remains pending. '
    'The separate callee correction/review and actual Rust ownership selection were excluded. No actual Rust acquisition, current whole-host string bound, external prices, root funding, native/runtime or GA acceptance is claimed.')
for name in ['PLAN.md', 'STATUS.md']:
    p = ROOT / name
    text = p.read_text()
    old = next(part for part in text.split('\n\n') if part.startswith('A coherent checkpoint is prepared for delivery:'))
    p.write_text(text.replace(old, paragraph, 1))
for name, expected in receipt['protected_work_unchanged'].items(): assert row(ROOT / name)['sha256'] == expected
subprocess.run(['git','diff','--check','--','PLAN.md','STATUS.md','work-graph.json','gates/ga.json'], cwd=ROOT, timeout=10, check=True)
assert not subprocess.check_output(['git','diff','--cached','--name-only'], cwd=ROOT, timeout=10)
with (OUT / 'push-metadata.json').open('x') as stream:
    json.dump({'at':datetime.now(timezone.utc).isoformat(), 'commit':receipt['commit'],
        'metadata':[row(ROOT/n) for n in ['PLAN.md','STATUS.md','work-graph.json','gates/ga.json']],
        'CI_run':ci['databaseId'], 'observed_status':ci['status'], 'protected_work_unchanged':True, 'GA_verified':0}, stream, indent=2)
    stream.write('\n')
print(json.dumps({'commit':receipt['commit'], 'CI':ci['url'], 'observed_status':ci['status'], 'metadata_updated':True}))
