"""One-shot narrow IR01 acceptance; IR02 and full ownership remain open."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PACKET = ROOT / 'verification/swift-guarded-snapshot-actual-owner-rust-retirement-independent'
DEST = OUT / 'guarded-snapshot-actual-owner-Rust-retirement-token-scope-acceptance.json'

def row(path):
    assert path.is_file() and not path.is_symlink()
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

assert not DEST.exists(), 'One-shot; do not replay'
assert row(PACKET / 'seal.json')['sha256'] == 'feb1ed71043022fb2d2cd98dd07ee14800f7828b9d8a325a3a9f5411a000f387'
seal = json.loads((PACKET / 'seal.json').read_bytes())
names = {'seal.json'}
for item in seal['members']:
    name = PurePosixPath(item['path'])
    assert not name.is_absolute() and '..' not in name.parts and str(name) not in names
    actual = row(PACKET / name)
    assert actual['bytes'] == item['bytes'] and actual['sha256'] == item['sha256']
    names.add(str(name))
assert len(seal['members']) == 222 and sum(item['bytes'] for item in seal['members']) == 21678842
assert names == {str(path.relative_to(PACKET)) for path in PACKET.rglob('*') if path.is_file()}
summary = json.loads((PACKET / 'command-summary.json').read_bytes())
assert summary['all_owned_groups_absent'] and summary['compiler_invocations'] == 3 and summary['host_runs'] == 2
assert summary['methods_each'] == 31 and summary['unchanged_producer_each'] == 25 and summary['independent_each'] == 6
cleanup = json.loads((PACKET / 'cleanup.json').read_bytes())
assert cleanup['all_reaped_and_exact_groups_absent'] and cleanup['build_directory_absent']
finding = json.loads((PACKET / 'finding-root-result-lifetime.json').read_bytes())
assert finding['id'] == 'IR02' and seal['IR01_scoped_token_refund_repair'] and seal['IR02_root_result_lifetime_open']
value = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT))], 'python': sys.version,
    'status': 'accepted-only-live-ledger-IR01-retention-root-result-lifetime-open',
    'source146_tree': seal['source146_tree'], 'tested_source146_tree': seal['tested_source146_tree'],
    'independent_seal': row(PACKET / 'seal.json'), 'members_verified': 222, 'member_bytes': 21678842,
    'command_summary': row(PACKET / 'command-summary.json'), 'cleanup': row(PACKET / 'cleanup.json'),
    'methods_per_mode': 31, 'unchanged_producer_methods': 25, 'independent_methods': 6,
    'binary_vectors': 51, 'provenance_mutations': 230, 'optional_resource_shapes': 2, 'read_schedules': 12,
    'IR01_accepted_scope': 'Once a correlation scope is issued, the original live bootstrap ledger cannot receive a Complete token or whole-storage refund; the sticky obligation has no reset/discharge route, including refusal/extraction/forget/child destruction.',
    'IR02': row(PACKET / 'finding-root-result-lifetime.json'),
    'IR02_source_review': 'Opaque production facade returns a result with no original-root lifetime. Both-mode compiled facade helper consumes owner and returns that same carrier; generic-core witness retains actual proof and guards after ledger end. No private File fabrication in facade helper. Current concrete outer destroys child before owner and returns only scalar observations.',
    'full_ownership_accepted': False, 'useful_joint_retirement_accepted': False,
    'native_reachable_escape_or_refund_established': False, 'prices_and_layouts_accepted': False,
    'original_harness_failure_preserved': True, 'root_runtime_replay': False,
    'followon_status': 'Minimum accessible-result lifetime contract and independent preaccess oracles being prepared; mechanism/source execution not yet selected.',
    'followon_contract_ownership': 'verification/swift-guarded-snapshot-root-result-lifetime-contract',
    'followon_preaccess_ownership': 'verification/swift-guarded-snapshot-root-result-preaccess',
    'native_root_funding_FieldLog_OTA_or_GA_accepted': False}
w = json.loads((ROOT / 'work-graph.json').read_bytes()); g = json.loads((ROOT / 'gates/ga.json').read_bytes())
c = w['packages'][7]['fixtureCacheStateContractCandidate']; assert c == g['gates'][1]['fixtureCacheStateContractCandidate']
b = c['scalar_cursor_host_acceptance']['real_profile_adapter_preparation']['next_header_preparation']['retained_profile_composition_preparation']['real_binding_preparation']['real_profile_loader_binding']['next_adoption_lane']['guarded_snapshot_export_contract_review']['composition_source_preparation']['bootstrap_host_boundary']
old = 'Root verifies all 1,487 frozen members and releases independent review; implementation acceptance remains pending.'
new = 'Root accepts only the live-ledger IR01 token/refund repair after 31 passing methods in each independent mode, including 51 binary vectors, 230 provenance mutations in both optional-resource shapes and twelve read schedules. A separate IR02 finding shows owned results can outlive the original ledger; current outer-caller order is safe, but full root/result lifetime remains unproved. The exact facade signature, host witness and initial harness failure are preserved. A minimum lifetime contract and independent preaccess oracles are being prepared; new source work is not yet selected.'
texts = {}
for name in ['PLAN.md', 'STATUS.md']:
    text = (ROOT / name).read_text(); assert text.count(old) == 1
    texts[name] = text.replace(old, new)
with DEST.open('x') as stream:
    json.dump(value, stream, indent=2); stream.write('\n')
correction = b['actual_owner_Rust_selection']['correction']
correction.update({'status': value['status'], 'IR01_scoped_accepted': True, 'implementation_accepted': False,
    'root_scoped_acceptance': row(DEST), 'independent_review_ownership': str(PACKET.relative_to(ROOT)),
    'IR02': value['IR02'], 'root_result_lifetime_accepted': False,
    'independent_methods_per_mode': 31, 'original_harness_failure_preserved': True,
    'next_contract_ownership': value['followon_contract_ownership'], 'next_preaccess_ownership': value['followon_preaccess_ownership']})
g['gates'][1]['fixtureCacheStateContractCandidate'] = copy.deepcopy(c)
for name, data in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(data, indent=2) + '\n')
for name, text in texts.items(): (ROOT / name).write_text(text)
subprocess.run(['git', 'diff', '--check', '--', 'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json'], timeout=10, check=True)
print(json.dumps({'IR01_live_ledger_scope_accepted': True, 'IR02_open': True, 'members_verified': 222, 'GA_accepted': False}))
