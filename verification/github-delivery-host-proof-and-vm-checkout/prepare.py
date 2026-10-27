"""Prepare an exact allowlist for accepted host proofs and the VM checkout repair."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PARENT = ROOT / 'verification/github-delivery-owned-binding-source-review'
REVIEW = ROOT / 'verification/swift-semantic-adapter-root-review'
BASE = 'a96712bbd79ff4c0709d2811dd2846b4a0ea0096'
PACKETS = [
    ('swift-guarded-snapshot-owned-provider-work-storage-independent', 'aeb00877856dacca762ba9c885d043ed4b785cabe811e8f31251eaa55e4ada6b'),
    ('swift-guarded-snapshot-string-exact-binding-independent', '5cc1e09727426ae84ef0c078c7a20153886d72495a1b4949ee31f69e6a37c956'),
    ('swift-guarded-snapshot-prepaid-input-owner-independent', '0d9c3d4eb6e99a9daa34f2a8ee798c739b0c6e9c41b35b6ef54c2e900684caa2'),
    ('swift-guarded-snapshot-prepaid-input-owner-correction', 'f3e4ac2543fde4fe7b1e03019fb49bbb5ba9aca078097e5aeb0fc972703de7a3'),
    ('swift-guarded-snapshot-prepaid-input-owner-correction-independent', 'a64f0cbb775265509b98bea63faca5e144e6d4b8f685898251ea12d506c8840a'),
    ('ci-vm-sparse-checkout', '1083e3aca3eefb82921b54ef76f7232163668bf359870f82ff38c20dbbc91550'),
]
ACTIVE = ['swift-guarded-snapshot-owned-provider-callee-interfaces',
          'swift-guarded-snapshot-string-provider-source-rebind',
          'swift-guarded-snapshot-prepaid-input-owner-affine-refusal']
ROOT_FILES = ['accept-owned-provider-work-storage.py', 'accept-string-exact-binding.py',
    'guarded-snapshot-owned-provider-work-storage-host-acceptance.json',
    'guarded-snapshot-string-exact-binding-host-acceptance.json',
    'return-prepaid-input-owner.py', 'guarded-snapshot-prepaid-input-owner-return.json',
    'release-prepaid-input-owner-correction.py', 'guarded-snapshot-prepaid-input-owner-correction-frozen-release.json',
    'return-prepaid-input-owner-correction.py', 'guarded-snapshot-prepaid-input-owner-correction-return.json',
    'record-affine-refusal-and-ci-retry.py', 'affine-refusal-and-ci-retry-metadata.json',
    'owned-provider-work-storage-root-check/plan.json', 'owned-provider-work-storage-root-check/receipt.json',
    'owned-provider-work-storage-root-check/stdout', 'owned-provider-work-storage-root-check/stderr',
    'owned-string-exact-binding-root-check/plan.json',
    'owned-string-exact-binding-root-check/0-receipt.json', 'owned-string-exact-binding-root-check/0-stdout', 'owned-string-exact-binding-root-check/0-stderr',
    'owned-string-exact-binding-root-check/1-receipt.json', 'owned-string-exact-binding-root-check/1-stdout', 'owned-string-exact-binding-root-check/1-stderr']
ACCEPTANCES = {
    'guarded-snapshot-owned-provider-work-storage-host-acceptance.json': '64f53d4ee70bb98b7684bc3dcf1f53b5e5b86c34c1a82a2930d362cdcc9d647a',
    'guarded-snapshot-string-exact-binding-host-acceptance.json': '273dcc49104e828609298ca30f5a19b0162ba56092b49e1fdb46375a1f3b003d',
    'guarded-snapshot-prepaid-input-owner-return.json': '1d3ce2645c959673393c60b0e1b61f938e9be2d8f3758416e45392a3e3542d28',
    'guarded-snapshot-prepaid-input-owner-correction-return.json': '97aa4d370d6c490e37302ad036e2af029cb6607972147c40c7dd63c410a28c9c',
}
sha = lambda data: hashlib.sha256(data).hexdigest()
def row(path):
    assert path.is_file() and not path.is_symlink()
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': sha(data)}
def write(path, value):
    with path.open('x') as stream: json.dump(value, stream, indent=2); stream.write('\n')

assert not (OUT / 'release-selection.json').exists()
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, timeout=10, text=True).strip() == BASE
assert not subprocess.check_output(['git', 'diff', '--cached', '--name-only'], cwd=ROOT, timeout=10)
for name, digest in PACKETS:
    assert row(ROOT / 'verification' / name / 'seal.json')['sha256'] == digest
for name, digest in ACCEPTANCES.items():
    assert row(REVIEW / name)['sha256'] == digest
ci = json.loads((PARENT / 'ci-jobs-7.stdout').read_text())
assert ci['headSha'] == BASE and ci['attempt'] == 2
assert sum(j['conclusion'] == 'success' for j in ci['jobs']) == 5
vm, = [j for j in ci['jobs'] if j['name'] == 'vm']
assert vm['status'] == 'in_progress'
assert all(s['conclusion'] == 'success' for s in vm['steps'][:5])
ci_packet = ROOT / 'verification/ci-vm-sparse-checkout'
assert (ROOT / '.github/workflows/verify.yml').read_bytes() == (ci_packet / 'workflow-candidate.yml').read_bytes()
audit = json.loads((ci_packet / 'receipt.json').read_text())
assert audit['result'] == 'local-sparse-materialization-and-offline-generators-pass'
assert audit['selected_files'] == 464 and audit['selected_bytes'] == 20395752

work = json.loads((ROOT / 'work-graph.json').read_text())
gates = json.loads((ROOT / 'gates/ga.json').read_text())
c = work['packages'][7]['fixtureCacheStateContractCandidate']
assert c == gates['gates'][1]['fixtureCacheStateContractCandidate']
parent_ci = c['guarded_snapshot_owned_binding_source_review_delivery']['CI']
parent_ci.update({'latest_state': 'attempt2-VM-running-five-prior-jobs-pass', 'attempt': 2,
    'observation': row(PARENT / 'ci-jobs-7.stdout'), 'VM_checkout_debug_release_passed': True,
    'CI_passed': False})
c['VM_CI_sparse_checkout'] = {'status': 'local-audit-passed-remote-workflow-pending',
    'packet': 'verification/ci-vm-sparse-checkout', 'seal_sha256': PACKETS[-1][1],
    'files': 464, 'bytes': 20395752, 'actual_local_Git_sparse_materialization': True,
    'offline_generators_passed': 2, 'VM_commands_unchanged': True, 'other_jobs_unchanged': True,
    'remote_fetch_or_full_VM_tests_verified': False, 'product_changed': False}
c['guarded_snapshot_host_proof_vm_checkout_delivery'] = {'status': 'prepared-for-authorized-nonforce-push',
    'base': BASE, 'packets': len(PACKETS), 'directory': str(OUT.relative_to(ROOT)),
    'scope': 'Bounded accepted original-source string/provider accounting proofs; both returned acquisition models and independent failures; source-only CI checkout repair',
    'active_lanes_excluded': ACTIVE, 'canonical_product_changed': False, 'CI_pending': True,
    'root_funding_or_runtime_native_OTA_GA': False}
gates['gates'][1]['fixtureCacheStateContractCandidate'] = copy.deepcopy(c)
assert [p['id'] for p in work['packages']] == [f'W{i:02}' for i in range(1, 19)]
assert [g['id'] for g in gates['gates']] == [f'G{i:02}' for i in range(1, 39)]
assert sum(g['status'] == 'running' for g in gates['gates']) == 8
assert sum(g['status'] == 'planned' for g in gates['gates']) == 30
assert work['packages'][4]['privateOwnerEffectContractCandidate'] == gates['gates'][4]['privateOwnerEffectContractCandidate']
for name, value in [('work-graph.json', work), ('gates/ga.json', gates)]:
    (ROOT / name).write_text(json.dumps(value, indent=2) + '\n')
paragraph = ('A coherent checkpoint is prepared for delivery: accepted original-source string binding and conditional provider accounting, both returned acquisition-model reviews, and a narrow VM CI checkout repair. The real local sparse checkout contains 464 files (20,395,752 bytes); both offline generators and all selected source hashes pass, with every VM command unchanged. Remote validation of the changed workflow remains pending. Parent `a96712b` VM retry has passed checkout, debug and release tests and is still running; its first checkout-timeout attempt is retained. Three active source/correction lanes are excluded from this delivery. No canonical product change, root funding, native/runtime or GA acceptance is claimed.')
for name in ['PLAN.md', 'STATUS.md']:
    path = ROOT / name
    text = path.read_text()
    marker = '## Resumed checkpoint\n\n' if name == 'PLAN.md' else '# Implementation status\n\n'
    assert marker in text
    path.write_text(text.replace(marker, marker + paragraph + '\n\n', 1))
subprocess.run(['git', 'diff', '--check', '--', 'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json', '.github/workflows/verify.yml'], cwd=ROOT, timeout=10, check=True)

source = (PARENT / 'deliver.py').read_text()
assert 'BASE = "b20cd3bcd83f9110fbbc62ce60a265373f2a85e5"' in source
source = source.replace('BASE = "b20cd3bcd83f9110fbbc62ce60a265373f2a85e5"', 'BASE = "' + BASE + '"')
source = source.replace('release["packet_count"] == 7', 'release["packet_count"] == 6')
source = source.replace('startswith("verification/github-delivery-host-constructor-outer-review/")', 'startswith("verification/github-delivery-owned-binding-source-review/")')
old_active = ['swift-guarded-snapshot-string-exact-binding-independent', 'swift-guarded-snapshot-prepaid-input-owner-independent', 'swift-guarded-snapshot-owned-provider-work-storage-independent']
for old, new in zip(old_active, ACTIVE):
    source = source.replace('"verification/' + old + '/"', '"verification/' + new + '/"')
source = source.replace('Record immutable binding source and provider review candidates', 'Record host proof reviews and narrow VM CI checkout')
source = source.replace('active_string_acquisition_and_accounting_review_lanes_excluded', 'active_callee_string_rebind_and_affine_correction_lanes_excluded')
with (OUT / 'deliver.py').open('x') as stream: stream.write(source)
parent_names = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z', '--', str(PARENT.relative_to(ROOT))], cwd=ROOT, timeout=10).decode().split('\0')
release = {'schema': 1, 'ready': True, 'packets': [{'path': n, 'seal_sha256': s} for n, s in PACKETS],
    'packet_count': len(PACKETS),
    'root_and_source_files': [row(REVIEW / n) for n in ROOT_FILES] + [row(ROOT / '.github/workflows/verify.yml')],
    'parent_delivery_files': [row(ROOT / n) for n in parent_names if n],
    'canonical_paths': ['.github/workflows/verify.yml'],
    'scope': c['guarded_snapshot_host_proof_vm_checkout_delivery']['scope'],
    'active_lanes_excluded': ACTIVE}
write(OUT / 'release-selection.json', release)
write(OUT / 'metadata-validation.json', {'schema': 1, 'passed': True, 'at': datetime.now(timezone.utc).isoformat(),
    'command': sys.argv, 'python': sys.version, 'script_sha256': sha(Path(__file__).read_bytes()),
    'python_executable_sha256': sha(Path(sys.executable).resolve().read_bytes()), 'source_revision': BASE,
    'metadata_files': [row(ROOT / n) for n in ['PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json']],
    'acceptance_and_return_references': [row(REVIEW / n) for n in ACCEPTANCES],
    'gates': {'running': 8, 'planned': 30, 'passed': 0},
    'scope': 'Full package/gate identifiers, paired metadata, frozen root receipt hashes, exact CI retry observation and tested checkout candidate; authored whitespace'})
print(json.dumps({'prepared': True, 'packets': len(PACKETS), 'root_and_source_files': len(release['root_and_source_files']),
                  'parent_receipt_files': len(release['parent_delivery_files']), 'commit_or_push_executed': False}))
