"""Record changed VM success, parent VM retry success, and third fresh review."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
PARENT = ROOT / 'verification/github-delivery-owned-binding-source-review'
assert not (OUT / 'vm-pass-metadata.json').exists()
sha = lambda data: hashlib.sha256(data).hexdigest()
def row(path):
    raw = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(raw), 'sha256': sha(raw)}
parent_path = PARENT / 'ci-jobs-10.stdout'
parent = json.loads(parent_path.read_text())
assert parent['headSha'] == 'a96712bbd79ff4c0709d2811dd2846b4a0ea0096' and parent['attempt'] == 2
assert parent['status'] == 'completed' and parent['conclusion'] == 'success'
assert len(parent['jobs']) == 6 and all(j['conclusion'] == 'success' for j in parent['jobs'])
assert sum(len(j['steps']) for j in parent['jobs']) == 64
assert all(s['conclusion'] == 'success' for j in parent['jobs'] for s in j['steps'])
vm = next(j for j in parent['jobs'] if j['name'] == 'vm')
assert vm['databaseId'] == 122330260131
terminal_path = PARENT / 'terminal-ci-attempt2.json'
assert not terminal_path.exists()
terminal = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'commit': parent['headSha'],
    'run': parent['databaseId'], 'attempt': 2, 'status': 'completed', 'conclusion': 'success',
    'jobs_passed': 6, 'steps_passed': 64, 'observation': row(parent_path),
    'retry_job': vm['databaseId'], 'retry_scope': 'VM only; other five successful jobs retained from attempt1',
    'original_cancelled_attempt': row(PARENT / 'terminal-ci-attempt1.json'),
    'original_cancelled_attempt_reclassified': False, 'url': parent['url'],
    'scope': 'Exact unchanged parent commit aggregate CI after VM-only retry; no native/device/OTA/GA qualification'}
with terminal_path.open('x') as stream: json.dump(terminal, stream, indent=2); stream.write('\n')
current_path = OUT / 'ci-jobs-3.stdout'
current = json.loads(current_path.read_text())
assert current['headSha'] == '9398732c23648a82097d5a72b02b1c77af818e41' and current['attempt'] == 1
assert current['status'] == 'in_progress'
vm = next(j for j in current['jobs'] if j['name'] == 'vm')
assert vm['databaseId'] == 122334423808 and vm['conclusion'] == 'success'
assert len(vm['steps']) == 12 and all(s['conclusion'] == 'success' for s in vm['steps'])
assert sum(j['conclusion'] == 'success' for j in current['jobs']) == 3

w = json.loads((ROOT / 'work-graph.json').read_text())
g = json.loads((ROOT / 'gates/ga.json').read_text())
c = w['packages'][7]['fixtureCacheStateContractCandidate']
assert c == g['gates'][1]['fixtureCacheStateContractCandidate']
b = c['scalar_cursor_host_acceptance']['real_profile_adapter_preparation']['next_header_preparation']['retained_profile_composition_preparation']['real_binding_preparation']['real_profile_loader_binding']['next_adoption_lane']['guarded_snapshot_export_contract_review']['composition_source_preparation']['bootstrap_host_boundary']
release_path = ROOT / 'verification/swift-semantic-adapter-root-review/guarded-snapshot-prepaid-input-owner-affine-refusal-frozen-release.json'
release = json.loads(release_path.read_text())
assert row(release_path)['sha256'] == 'ef722611a7318031cdf656622263096f629741eb93008405688ce827aa631d39'
b['prepaid_input_owner_affine_refusal'].update({'status': 'frozen-root-custody-complete-fresh-independent-review-active',
    'seal_sha256': release['seal_sha256'], 'members': 67, 'bytes': 1728034,
    'root_frozen_release': row(release_path), 'producer_methods_passed': 110,
    'producer_new_methods': 23, 'producer_reused_regression_methods': 87,
    'independent_review_owner': '/root/swift_prepaid_affine_refusal_independent',
    'independent_review_ownership': 'verification/swift-guarded-snapshot-prepaid-affine-refusal-independent',
    'accepted': False})
delivery = c['guarded_snapshot_owned_binding_source_review_delivery']
delivery['status'] = 'pushed-aggregate-CI-success-after-VM-only-retry-original-cancellation-retained'
delivery['CI'].update({'latest_state': 'completed-success-after-VM-only-retry', 'status': 'completed',
    'conclusion': 'success', 'attempt': 2, 'jobs_passed': 6, 'jobs_in_progress': 0, 'steps_passed': 64,
    'observation': row(parent_path), 'observation_sha256': row(parent_path)['sha256'],
    'terminal_receipt': row(terminal_path), 'CI_passed': True})
c['guarded_snapshot_host_proof_vm_checkout_delivery']['CI'].update({'status': 'in_progress',
    'conclusion': '', 'attempt': 1, 'observation': row(current_path),
    'observation_sha256': row(current_path)['sha256'], 'jobs_passed': 3, 'jobs_in_progress': 3, 'passed': False})
c['VM_CI_sparse_checkout'].update({'status': 'changed-VM-job-all-twelve-steps-passed-other-workflow-jobs-pending',
    'remote_fetch_verified': True, 'full_VM_tests_verified': True, 'VM_job': vm['databaseId'],
    'VM_steps_passed': 12, 'remote_VM_success_observation': row(current_path)})
g['gates'][1]['fixtureCacheStateContractCandidate'] = copy.deepcopy(c)
assert len(w['packages']) == 18 and len(g['gates']) == 38
assert sum(x['status'] == 'running' for x in g['gates']) == 8
assert sum(x['status'] == 'planned' for x in g['gates']) == 30
assert w['packages'][4]['privateOwnerEffectContractCandidate'] == g['gates'][4]['privateOwnerEffectContractCandidate']
for name, value in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(value, indent=2) + '\n')
lead = ('Checkpoint `9398732` is pushed with 547 selected paths and six frozen packets: accepted original-source string binding and conditional provider accounting, both returned acquisition-model reviews, and the VM CI checkout repair. The changed VM job passes all twelve steps after its seven-second checkout; [current CI](https://github.com/snowdamiz/mixer/actions/runs/40545367451) has three passing jobs and three still running. Parent `a96712b` now has six passing jobs and 64 steps after its VM-only retry; the five earlier successes and original checkout cancellation retain their own attempt attribution. The source/correction lanes were excluded from the push. Canonical product sources, actual root funding, runtime/native and GA acceptance remain unchanged.')
review_paragraph = ('All three new candidates are now frozen and under fresh independent review: current-provider string provenance, fourteen callee-cost interfaces, and the C1–C2 affine input-owner correction. The latest input model passes 110 producer/regression methods, including all four returned desired-property failures, but has no independent acceptance yet. No current whole-host string bound, callee price, acquisition authority, root funding or operational grant is selected.')
for name in ['PLAN.md', 'STATUS.md']:
    path = ROOT / name
    text = path.read_text()
    old = next(p for p in text.split('\n\n') if p.startswith('Checkpoint `9398732` is pushed'))
    text = text.replace(old, lead, 1)
    old = next(p for p in text.split('\n\n') if p.startswith('The current-provider string rebind and fourteen-callee cost packets are now frozen'))
    path.write_text(text.replace(old, review_paragraph, 1))
subprocess.run(['git', 'diff', '--check', '--', 'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json'], cwd=ROOT, timeout=10, check=True)
assert not subprocess.check_output(['git', 'diff', '--cached', '--name-only'], cwd=ROOT, timeout=10)
with (OUT / 'vm-pass-metadata.json').open('x') as stream:
    json.dump({'at': datetime.now(timezone.utc).isoformat(), 'parent_terminal': row(terminal_path),
        'current_VM_pass': row(current_path), 'fresh_input_review_release': row(release_path),
        'metadata': [row(ROOT / n) for n in ['PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json']],
        'GA_verified': 0}, stream, indent=2); stream.write('\n')
print(json.dumps({'parent_CI': 'all-six-pass-after-VM-retry', 'current_CI': 'three-pass-three-running',
    'changed_VM': 'all-twelve-steps-pass', 'reviews_active': 3, 'parent_terminal_sha256': row(terminal_path)['sha256']}))
