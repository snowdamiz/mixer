"""Record observed correction return and exact-commit CI cancellation/retry."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_name('affine-refusal-and-ci-retry-metadata.json')
assert not OUT.exists()
sha = lambda data: hashlib.sha256(data).hexdigest()
def row(relative):
    path = ROOT / relative
    data = path.read_bytes()
    return {'path': relative, 'bytes': len(data), 'sha256': sha(data)}

names = ['PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json']
before = [row(name) for name in names]
work = json.loads((ROOT / 'work-graph.json').read_text())
gates = json.loads((ROOT / 'gates/ga.json').read_text())
c = work['packages'][7]['fixtureCacheStateContractCandidate']
assert c == gates['gates'][1]['fixtureCacheStateContractCandidate']
b = c['scalar_cursor_host_acceptance']['real_profile_adapter_preparation']['next_header_preparation']['retained_profile_composition_preparation']['real_binding_preparation']['real_profile_loader_binding']['next_adoption_lane']['guarded_snapshot_export_contract_review']['composition_source_preparation']['bootstrap_host_boundary']
returned = row('verification/swift-semantic-adapter-root-review/guarded-snapshot-prepaid-input-owner-correction-return.json')
assert returned['sha256'] == '97aa4d370d6c490e37302ad036e2af029cb6607972147c40c7dd63c410a28c9c'
b['prepaid_input_owner_correction'].update({
    'status': 'frozen-and-returned-after-fresh-independent-C1-C2-failures',
    'seal_sha256': 'f3e4ac2543fde4fe7b1e03019fb49bbb5ba9aca078097e5aeb0fc972703de7a3',
    'members': 61, 'bytes': 1323422,
    'root_frozen_release': row('verification/swift-semantic-adapter-root-review/guarded-snapshot-prepaid-input-owner-correction-frozen-release.json'),
    'independent_review_seal_sha256': 'a64f0cbb775265509b98bea63faca5e144e6d4b8f685898251ea12d506c8840a',
    'independent_passed_methods': 7, 'independent_failed_methods': 4, 'independent_failure_records': 6,
    'root_return': returned, 'accepted': False,
    'findings': ['early refusal allows retry and storage release with live unowned selected Files',
                 'synthetic session extent and nested identity accept floats through coercing equality'],
})
b['prepaid_input_owner_affine_refusal'] = {
    'status': 'focused-C1-C2-correction-active', 'owner': '/root/swift_prepaid_input_owner_affine_refusal',
    'ownership': 'verification/swift-guarded-snapshot-prepaid-input-owner-affine-refusal',
    'correction_contract': row('verification/swift-guarded-snapshot-prepaid-input-owner-correction-independent/correction-contract.json'),
    'scope': 'owning consuming early refusal and strict nested synthetic session types before equality',
    'accepted': False, 'compiler_authorized': False, 'operational_grant': False,
}
delivery = c['guarded_snapshot_owned_binding_source_review_delivery']
terminal = row('verification/github-delivery-owned-binding-source-review/terminal-ci-attempt1.json')
retry = row('verification/github-delivery-owned-binding-source-review/vm-retry-request.json')
assert terminal['sha256'] == '6d03fe097d188f8f2276a7c47f6882319d15712be1f10736c6be16e9ad793178'
delivery['status'] = 'pushed-attempt1-five-pass-VM-checkout-timeout-single-job-retry-requested'
delivery['CI'] = {'run': 40538740144, 'url': 'https://github.com/snowdamiz/mixer/actions/runs/40538740144',
    'attempt1': {'status': 'completed', 'conclusion': 'cancelled', 'jobs_passed': 5, 'jobs_cancelled': 1,
        'VM_tests_ran': False, 'terminal_receipt': terminal},
    'retry_request': retry, 'retry_scope': 'VM job122311014684 only',
    'latest_state': 'single-job-retry-requested-new-attempt-not-yet-observed', 'CI_passed': False}
gates['gates'][1]['fixtureCacheStateContractCandidate'] = copy.deepcopy(c)
assert len(work['packages']) == 18 and len(gates['gates']) == 38
assert sum(g['status'] == 'running' for g in gates['gates']) == 8
assert sum(g['status'] == 'planned' for g in gates['gates']) == 30
assert work['packages'][4]['privateOwnerEffectContractCandidate'] == gates['gates'][4]['privateOwnerEffectContractCandidate']
for name, value in [('work-graph.json', work), ('gates/ga.json', gates)]:
    (ROOT / name).write_text(json.dumps(value, indent=2) + '\n')

lead = ('The input-owner correction is returned after fresh independent review: seven methods pass and four desired-property methods fail, preserving six failure records. Early refusal can permit retry and storage release with live selected Files; synthetic session equality also accepts float identity fields. A focused C1–C2 correction now runs alongside the complete string-source rebind and fourteen callee-interface derivation. Checkpoint `a96712b` CI attempt 1 has five passing jobs and VM cancelled after its 20-minute checkout fetch timeout; all eight VM tool/test steps were skipped. One VM-only retry is requested, preserving that cancelled attempt. Original-source string binding and conditional provider accounting retain their bounded acceptance. Actual acquisition, current-source string selection, root funding, runtime/native qualification and all GA gates remain pending.')
for name in ['PLAN.md', 'STATUS.md']:
    path = ROOT / name
    text = path.read_text()
    old = next(p for p in text.split('\n\n') if p.startswith('The exact string-binding correction now has bounded root acceptance'))
    text = text.replace(old, lead, 1)
    text = text.replace('[CI](https://github.com/snowdamiz/mixer/actions/runs/40538740144) is running for this exact commit;',
                        '[CI](https://github.com/snowdamiz/mixer/actions/runs/40538740144) was running at push; attempt 1 later ended with five passing jobs and VM checkout timeout, followed by a VM-only retry request;')
    path.write_text(text)
subprocess.run(['git', 'diff', '--check', '--', *names], cwd=ROOT, check=True, timeout=10)
for name, expected in [('.github/workflows/hosted.yml', 'fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57'),
                       ('hosted/lib/mixer_hosted/browser_auth/store.ex', '8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299')]:
    assert row(name)['sha256'] == expected
assert not subprocess.check_output(['git', 'diff', '--cached', '--name-only'], cwd=ROOT, timeout=10)
with OUT.open('x') as stream:
    json.dump({'at': datetime.now(timezone.utc).isoformat(), 'before': before,
               'after': [row(n) for n in names], 'protected_hashes_unchanged': True,
               'GA_gates_verified': 0, 'root_return': returned, 'terminal': terminal, 'retry': retry}, stream, indent=2)
    stream.write('\n')
print(json.dumps({'receipt': str(OUT.relative_to(ROOT)), 'sha256': sha(OUT.read_bytes()), 'GA_verified': 0}))
