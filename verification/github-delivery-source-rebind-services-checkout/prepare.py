"""Select only completed frozen reviews and the reviewed services checkout repair."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PARENT = ROOT / 'verification/github-delivery-host-proof-and-vm-checkout'
REVIEW = ROOT / 'verification/swift-semantic-adapter-root-review'
BASE = '9398732c23648a82097d5a72b02b1c77af818e41'
PACKETS = [
    ('swift-guarded-snapshot-prepaid-input-owner-affine-refusal', '2270f59809b80c49df907a7ea9c20faf4dd45735cabad275ae61065efc19c50b'),
    ('swift-guarded-snapshot-prepaid-affine-refusal-independent', '25eb5a5f02059ab38953f9435bef2e308e2e946290c231ebd922459e20dd679d'),
    ('swift-guarded-snapshot-string-provider-source-rebind', '3782b36c05e5ef0d4037cdac26834b31f3db1978250ba25abd2a869e4c5b90ab'),
    ('swift-guarded-snapshot-string-provider-rebind-independent', '7048717734e68adc9ee56be046217232818322b4baad0dabb978444e02c229af'),
    ('swift-guarded-snapshot-owned-provider-callee-interfaces', 'e98916beff1a3c8b912e96591fbd573b8d570aa38cc4390a13fa20658290dce0'),
    ('swift-guarded-snapshot-owned-provider-callee-independent', '050da55a398e839075dd841e81d4da580f74a97adf2d6346b0d8e44587680e16'),
    ('ci-services-sparse-checkout', '244417580cacbd04fcb79685e5a15d376314320d9c70f40be49d2df2194f071f'),
    ('ci-services-sparse-checkout-independent', '6bae587208e85ebf4f7c9ddaa9687a713053436fe9e8887f7d0e82960aa47e5d'),
]
ACTIVE = ['swift-guarded-snapshot-provider-callee-source-correction',
          'swift-guarded-snapshot-callee-source-correction-independent',
          'swift-guarded-snapshot-actual-owner-rust-selection']
ROOT_FILES = [
    'release-owned-provider-callee-interfaces.py', 'guarded-snapshot-owned-provider-callee-interfaces-frozen-release.json',
    'release-string-provider-source-rebind.py', 'guarded-snapshot-string-provider-source-rebind-frozen-release.json',
    'release-prepaid-input-owner-affine-refusal.py', 'guarded-snapshot-prepaid-input-owner-affine-refusal-frozen-release.json',
    'two-interface-reviews-release-metadata.json', 'return-owned-provider-callee-interfaces.py',
    'guarded-snapshot-owned-provider-callee-interfaces-return.json', 'accept-affine-and-current-string.py',
    'guarded-snapshot-prepaid-affine-refusal-host-acceptance.json',
    'guarded-snapshot-string-provider-source-rebind-host-acceptance.json',
    'accept-services-checkout.py', 'services-sparse-checkout-host-acceptance.json',
]
for folder in ['affine-source-review-root-check', 'string-source-review-root-check', 'services-checkout-root-check']:
    ROOT_FILES.extend(folder + '/' + n for n in ['plan.json', 'receipt.json', 'stdout', 'stderr'])
ACCEPT = {'guarded-snapshot-prepaid-affine-refusal-host-acceptance.json': 'cc2a0954afd77ccd843d93f37f71bad22504391844e2edcaaa46bae98c51fd28',
    'guarded-snapshot-string-provider-source-rebind-host-acceptance.json': '07dcf216a6371f54e6ceb85a16d55614a23388395eab212c79f5ec9f3de73a90',
    'services-sparse-checkout-host-acceptance.json': '093f13fb9e7fd968a5c7b5b2927b10d76c96abbd7d58085512991400840d308b',
    'guarded-snapshot-owned-provider-callee-interfaces-return.json': 'd497b65fed7324ffa52b5a90a2c8b8c2bdd323c59a2a574a5b38d44667f0dc49'}
sha = lambda data: hashlib.sha256(data).hexdigest()
def row(path):
    assert path.is_file() and not path.is_symlink()
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': sha(data)}
def save(path, value):
    with path.open('x') as stream: json.dump(value, stream, indent=2); stream.write('\n')
def untracked(folder):
    raw = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z', '--', folder], cwd=ROOT, timeout=10)
    return [row(ROOT / p) for p in raw.decode().split('\0') if p]

assert not (OUT / 'release-selection.json').exists()
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, timeout=10, text=True).strip() == BASE
assert not subprocess.check_output(['git', 'diff', '--cached', '--name-only'], cwd=ROOT, timeout=10)
for name, digest in PACKETS: assert row(ROOT / 'verification' / name / 'seal.json')['sha256'] == digest
for name, digest in ACCEPT.items(): assert row(REVIEW / name)['sha256'] == digest
assert (ROOT / '.github/workflows/verify.yml').read_bytes() == (ROOT / 'verification/ci-services-sparse-checkout/workflow-candidate.yml').read_bytes()
ci = json.loads((PARENT / 'terminal-ci-attempt1.json').read_bytes())
assert ci['commit'] == BASE and ci['jobs_passed'] == 5 and ci['jobs_cancelled'] == 1 and not ci['CI_passed']
w = json.loads((ROOT / 'work-graph.json').read_bytes())
g = json.loads((ROOT / 'gates/ga.json').read_bytes())
c = w['packages'][7]['fixtureCacheStateContractCandidate']
assert c == g['gates'][1]['fixtureCacheStateContractCandidate']
b = c['scalar_cursor_host_acceptance']['real_profile_adapter_preparation']['next_header_preparation']['retained_profile_composition_preparation']['real_binding_preparation']['real_profile_loader_binding']['next_adoption_lane']['guarded_snapshot_export_contract_review']['composition_source_preparation']['bootstrap_host_boundary']
b['provider_callee_source_correction'].update({'status': 'frozen-root-custody-complete-fresh-independent-review-active',
    'seal_sha256': 'e80dd24b7cb7e18c97abb1effa705cbc2b7882b36ac8e439a181bc6cf3a6dfb1', 'members': 219, 'bytes': 13305313,
    'independent_owner': '/root/swift_callee_source_correction_independent',
    'independent_ownership': 'verification/swift-guarded-snapshot-callee-source-correction-independent',
    'root_frozen_release': row(REVIEW / 'guarded-snapshot-provider-callee-source-correction-frozen-release.json')})
c['services_CI_sparse_checkout'].update({'status': 'root-accepted-local-selection-awaiting-remote-changed-job',
    'accepted': True, 'root_acceptance': row(REVIEW / 'services-sparse-checkout-host-acceptance.json'),
    'independent_seal_sha256': PACKETS[-1][1], 'independent_controls': 12, 'linux_packages': 6})
scope = 'Bounded accepted current-source string rebind and synthetic affine input-owner correction; returned incomplete callee proposal; independently reviewed services CI sparse checkout and terminal parent CI evidence'
c['guarded_snapshot_source_rebind_services_checkout_delivery'] = {'status': 'prepared-for-authorized-nonforce-push',
    'base': BASE, 'packets': len(PACKETS), 'directory': str(OUT.relative_to(ROOT)), 'scope': scope,
    'active_lanes_excluded': ACTIVE, 'canonical_product_changed': False, 'CI_pending': True,
    'root_funding_or_runtime_native_OTA_GA': False}
g['gates'][1]['fixtureCacheStateContractCandidate'] = copy.deepcopy(c)
assert [p['id'] for p in w['packages']] == [f'W{i:02}' for i in range(1,19)]
assert [x['id'] for x in g['gates']] == [f'G{i:02}' for i in range(1,39)]
assert sum(x['status']=='running' for x in g['gates']) == 8 and sum(x['status']=='planned' for x in g['gates']) == 30
assert w['packages'][4]['privateOwnerEffectContractCandidate'] == g['gates'][4]['privateOwnerEffectContractCandidate']
for name, value in [('work-graph.json', w), ('gates/ga.json', g)]: (ROOT / name).write_text(json.dumps(value, indent=2)+'\n')
paragraph = ('A coherent checkpoint is prepared for delivery: the bounded accepted current-provider string rebind and synthetic affine input-owner correction, the returned incomplete callee proposal, and the services checkout repair. '
    'Twelve independent checkout controls and all 153 selected source files pass, with existing service commands and the Go pin unchanged; the full changed remote race job remains pending. '
    'The callee correction is frozen and under fresh independent review, while the actual Rust ownership interface is being mapped; both are excluded from this checkpoint. '
    'No actual Rust acquisition, current whole-host string bound, external prices, root funding, native/runtime or GA acceptance is claimed.')
for name in ['PLAN.md','STATUS.md']:
    path = ROOT / name; text = path.read_text()
    marker = '## Resumed checkpoint\n\n' if name == 'PLAN.md' else '# Implementation status\n\n'
    assert marker in text
    path.write_text(text.replace(marker, marker+paragraph+'\n\n', 1))
subprocess.run(['git','diff','--check','--','PLAN.md','STATUS.md','work-graph.json','gates/ga.json','.github/workflows/verify.yml'],cwd=ROOT,timeout=10,check=True)
source = (PARENT / 'deliver.py').read_text()
source = source.replace('BASE = "a96712bbd79ff4c0709d2811dd2846b4a0ea0096"', 'BASE = "'+BASE+'"')
source = source.replace('release["packet_count"] == 6', 'release["packet_count"] == 8')
source = source.replace('startswith("verification/github-delivery-owned-binding-source-review/")','startswith("verification/github-delivery-host-proof-and-vm-checkout/")')
for old,new in zip(['swift-guarded-snapshot-owned-provider-callee-interfaces','swift-guarded-snapshot-string-provider-source-rebind','swift-guarded-snapshot-prepaid-input-owner-affine-refusal'],ACTIVE):
    source = source.replace('"verification/'+old+'/"','"verification/'+new+'/"')
source = source.replace('Record host proof reviews and narrow VM CI checkout','Record source rebind reviews and narrow services CI checkout')
source = source.replace('active_callee_string_rebind_and_affine_correction_lanes_excluded','active_callee_correction_review_and_Rust_selection_lanes_excluded')
source = source.replace('timeout=60','timeout=45')
source = source.replace('"direct_child_reaped": True,','"owned_pid": child.pid, "owned_pgid": child.pid, "direct_child_reaped": True,')
with (OUT / 'deliver.py').open('x') as stream: stream.write(source)
release = {'schema':1,'ready':True,'packets':[{'path':n,'seal_sha256':s} for n,s in PACKETS], 'packet_count':8,
    'root_and_source_files':[row(REVIEW/n) for n in ROOT_FILES]+[row(ROOT/'.github/workflows/verify.yml')]+untracked('verification/github-delivery-owned-binding-source-review'),
    'parent_delivery_files':untracked(str(PARENT.relative_to(ROOT))), 'canonical_paths':['.github/workflows/verify.yml'],
    'scope':scope,'active_lanes_excluded':ACTIVE}
save(OUT/'release-selection.json',release)
save(OUT/'metadata-validation.json',{'schema':1,'passed':True,'at':datetime.now(timezone.utc).isoformat(),
    'command':sys.argv,'python':sys.version,'script_sha256':row(Path(__file__).resolve())['sha256'],
    'python_executable_sha256':sha(Path(sys.executable).resolve().read_bytes()),'source_revision':BASE,
    'metadata_files':[row(ROOT/n) for n in ['PLAN.md','STATUS.md','work-graph.json','gates/ga.json']],
    'root_acceptances_and_return':[row(REVIEW/n) for n in ACCEPT], 'gates':{'running':8,'planned':30,'passed':0}})
print(json.dumps({'prepared':True,'packets':8,'root_source_files':len(release['root_and_source_files']),
    'parent_receipt_files':len(release['parent_delivery_files']),'commit_or_push_executed':False}))
