"""Accept only the independently reviewed finite obligation inventory once."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DEST = OUT / 'root-bound-work-storage-delta-acceptance.json'

def read(path):
    return json.loads(path.read_bytes())

def row(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

assert not DEST.exists(), 'One-shot; do not replay'
packets = []
for name, expected, count in [
    ('swift-root-bound-work-storage-delta', '1b077039023f424fb72f9e32902f329e3257edb50a4ab99aa42192149271cb29', 25),
    ('swift-root-bound-work-storage-delta-independent', 'addd2beb80ae25174c210563bffc9122cbe655f69420170ad16305eaeef544ec', 41),
]:
    directory = ROOT / 'verification' / name
    seal = directory / 'seal.json'
    assert row(seal)['sha256'] == expected
    data = read(seal)
    assert data['member_count'] == len(data['members']) == count
    for entry in data['members']:
        actual = row(directory / entry['path'])
        assert actual['bytes'] == entry['bytes'] and actual['sha256'] == entry['sha256']
    actual_members = {str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file()}
    assert actual_members == {e['path'] for e in data['members']} | {'seal.json'}
    packets.append({'seal': row(seal), 'members_verified': count, 'member_bytes': data['member_bytes'], 'tree_sha256': data['tree_sha256']})
review_dir = ROOT / 'verification/swift-root-bound-work-storage-delta-independent'
review = read(review_dir / 'result.json')
assert review['concrete_producer_defects'] == [] and review['producer_check_runs'] == 1
assert review['producer_check_passed'] and review['independent_inventory_controls_passed'] == 8
assert review['independent_layout_proposal_and_synthetic_arithmetic_controls_passed'] == 11
assert review['source_tree']['candidate'] == '91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f'
assert all(review[k] is False for k in ['work_prices_accepted', 'storage_prices_accepted', 'layouts_accepted', 'backing_peak_funding_accepted', 'full_ownership_or_durable_funding_accepted', 'compiler_runtime_run', 'GA_accepted'])
acceptance = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT))], 'python': sys.version,
    'status': 'accepted-finite-source-MIR-obligation-inventory-and-conditional-layout-frontier-only',
    'source_revision_for_tools': '6f116c6a41994fcab5fa0d203198dc139dae9829',
    'candidate_source146_tree': review['source_tree']['candidate'], 'baseline_source146_tree': review['source_tree']['baseline'],
    'packets': packets, 'independent_result': row(review_dir / 'result.json'),
    'root_review': 'Verified both frozen memberships and all66 members; read complete independent source/accounting review and complete layout proposal. Original-root representation, carried payload backing, child token and permanent IR01 acquisition charge remain distinct. Relocated leaf work is counted once. Raw MIR counts are not dynamic work or simultaneous peaks.',
    'accepted_scope': review['accepted_scope'],
    'finite_coverage': {'types': 16, 'handwritten_dependency_bodies': 24, 'constructor_shim_occurrences': 24, 'arguments': 65, 'locals_returns': 580, 'candidate_MIR_rows': 2873, 'baseline_MIR_rows': 2084, 'positive_unresolved_work_obligations': 12, 'positive_unresolved_storage_obligations': 12},
    'independent_inventory_controls': 8, 'independent_proposal_arithmetic_controls': 11,
    'conditional_layout_frontier': {'named_shapes': 28, 'actual_anonymous_closure': True, 'diagnostic_strategy_qualified': False, 'compiler_released': False, 'compiler_executed': False},
    'root_runtime_replayed': False, 'canonical_source_integrated': False,
    'work_storage_prices_or_layouts_accepted': False, 'backing_peak_or_funding_accepted': False,
    'durable_root_funding_full_ownership_or_GA_accepted': False, 'pending': review['unresolved']}
with DEST.open('x') as stream:
    json.dump(acceptance, stream, indent=2)
    stream.write('\n')
w = read(ROOT / 'work-graph.json'); g = read(ROOT / 'gates/ga.json')
c = w['packages'][7]['fixtureCacheStateContractCandidate']
assert c == g['gates'][1]['fixtureCacheStateContractCandidate']
b = c['scalar_cursor_host_acceptance']['real_profile_adapter_preparation']['next_header_preparation']['retained_profile_composition_preparation']['real_binding_preparation']['real_profile_loader_binding']['next_adoption_lane']['guarded_snapshot_export_contract_review']['composition_source_preparation']['bootstrap_host_boundary']
repair = b['actual_owner_Rust_selection']['correction']['IR02_source_repair']
repair['new_work_storage_delta_status'] = acceptance['status']
repair['work_storage_delta'] = {'status': acceptance['status'], 'root_acceptance': row(DEST), 'packets': packets,
    'source_MIR_inventory_accepted': True, 'positive_unresolved_obligations': 24,
    'work_storage_prices_or_layouts_accepted': False, 'backing_peak_funding_full_ownership_accepted': False,
    'layout_preparation_ownership': 'verification/swift-root-bound-work-storage-layout-probe',
    'layout_compiler_released': False, 'canonical_source_integrated': False, 'GA_accepted': False}
g['gates'][1]['fixtureCacheStateContractCandidate'] = copy.deepcopy(c)
texts = {}
for name in ['PLAN.md', 'STATUS.md']:
    text = (ROOT / name).read_text()
    old = 'New work/storage accounting is being prepared offline.'
    new = 'The new work/storage obligation inventory has bounded offline acceptance after independent reconstruction of 65 arguments, 580 local/return places and 2,873 selected MIR rows, with nineteen fresh inventory/proposal controls. It preserves 24 positive unresolved work/storage obligations and counts relocated leaf work once. A conditional layout proposal covers 28 named shapes plus the actual closure; no compiler query, numerical price, backing bound or funding is accepted.'
    assert text.count(old) == 1
    texts[name] = text.replace(old, new)
for name, value in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(value, indent=2) + '\n')
for name, text in texts.items():
    (ROOT / name).write_text(text)
subprocess.run(['git', 'diff', '--check', '--', 'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json'], check=True, timeout=10)
print(json.dumps({'accepted': 'finite source/MIR obligation inventory only', 'packet_members_verified': 66,
    'work_storage_obligations_unresolved': 24, 'layout_compiler_executed': False, 'GA_verified': 0}))
