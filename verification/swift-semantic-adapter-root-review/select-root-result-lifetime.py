"""Select the exact minimum accessible-result lifetime repair, not full funding."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DEST = OUT / 'guarded-snapshot-root-result-lifetime-selection.json'
assert not DEST.exists(), 'One-shot; do not replay'

def row(path):
    assert path.is_file() and not path.is_symlink()
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

contract_dir = ROOT / 'verification/swift-guarded-snapshot-root-result-lifetime-contract'
oracle_dir = ROOT / 'verification/swift-guarded-snapshot-root-result-preaccess'
assert row(contract_dir / 'seal.json')['sha256'] == '5cbf7f3c49baa7e8db9a61ee720a9e5eee0d81241a580d8997b75fad6030c4eb'
packets = []
for directory, seal_name, key in [(contract_dir, 'seal.json', 'members'), (oracle_dir, 'freeze.json', 'files')]:
    seal = json.loads((directory / seal_name).read_bytes())
    rows = []
    for item in seal[key]:
        actual = row(directory / item['path'])
        assert actual['bytes'] == item['bytes'] and actual['sha256'] == item['sha256']
        rows.append(actual)
    rows.append(row(directory / seal_name))
    assert {r['path'] for r in rows} == {str(p.relative_to(ROOT)) for p in directory.rglob('*') if p.is_file()}
    packets.append({'directory': str(directory.relative_to(ROOT)), 'members': rows})
assert len(packets[0]['members']) == 8 and len(packets[1]['members']) == 10
value = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT))],
    'status': 'selected-isolated-accessible-result-original-root-lifetime-source-repair',
    'contract': row(contract_dir / 'contract.json'), 'signatures': row(contract_dir / 'signature-contract.rs.txt'),
    'producer_roster': row(contract_dir / 'test-roster.json'), 'preaccess_seal': row(oracle_dir / 'freeze.json'),
    'packets': packets, 'ownership': 'verification/swift-guarded-snapshot-root-result-lifetime-implementation',
    'changed_distribution_members': ['src/experimental_swift_reactor/retained_profile_loader_v1.rs', 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'],
    'root_review': 'Real original attempt-root reference and separate owner borrow; opaque complete correlation/admitted/final families. Remove public raw selected extraction. Fixed synchronous leaf retains root while moving raw payload internally. Borrow-only original diagnostics and separate child-account lifetime. All refusal/setup/error variants preserve original resources.',
    'required_private_transition_inventory': True, 'IR01_barrier_must_remain': True,
    'source_work_authorized': True, 'compiler_or_host_execution_released': False,
    'planned_command_ceiling': {'compiler_commands': 21, 'production_metadata_and_complete_MIR': 1,
        'test_binary_builds': 2, 'negative_probes': 18, 'filtered_host_runs': 2,
        'version_queries': 1, 'each_seconds_max': 55, 'simultaneous_compilers': 1,
        'note': 'Exact source and command roster must be reviewed before launch. No blind retries or extra probes; concrete repairs return to root.'},
    'no_native_File_or_VM_fixture_execution': True, 'no_new_distribution_or_host11_changes': True,
    'forgotten_result_root_funding_or_shutdown_accepted': False,
    'full_ownership_or_useful_joint_retirement_accepted': False, 'new_prices_or_layouts_accepted': False,
    'production_selector_custody_native_healthy_close_FieldLog_OTA_GA_accepted': False}
w = json.loads((ROOT / 'work-graph.json').read_bytes()); g = json.loads((ROOT / 'gates/ga.json').read_bytes())
c = w['packages'][7]['fixtureCacheStateContractCandidate']; assert c == g['gates'][1]['fixtureCacheStateContractCandidate']
b = c['scalar_cursor_host_acceptance']['real_profile_adapter_preparation']['next_header_preparation']['retained_profile_composition_preparation']['real_binding_preparation']['real_profile_loader_binding']['next_adoption_lane']['guarded_snapshot_export_contract_review']['composition_source_preparation']['bootstrap_host_boundary']
old = 'A minimum lifetime contract and independent preaccess oracles are being prepared; new source work is not yet selected.'
new = 'The minimum accessible-result lifetime repair is selected with an opaque original-root carrier, fixed consuming leaf operation and independent preaccess checks. Isolated source work proceeds in two files; exact compiler execution awaits root review. Forgotten-result/root funding, shutdown and full ownership remain pending.'
texts = {}
for name in ['PLAN.md', 'STATUS.md']:
    text = (ROOT / name).read_text(); assert text.count(old) == 1
    texts[name] = text.replace(old, new)
with DEST.open('x') as stream:
    json.dump(value, stream, indent=2); stream.write('\n')
b['actual_owner_Rust_selection']['correction']['IR02_source_repair'] = {
    'status': value['status'], 'root_selection': row(DEST), 'ownership': value['ownership'],
    'source_work_authorized': True, 'compiler_or_host_execution_released': False,
    'implementation_accepted': False, 'full_funding_or_ownership_accepted': False}
g['gates'][1]['fixtureCacheStateContractCandidate'] = copy.deepcopy(c)
for name, data in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(data, indent=2) + '\n')
for name, text in texts.items(): (ROOT / name).write_text(text)
print(json.dumps({'source_repair_selected': True, 'frozen_packet_files': 18, 'compiler_execution_released': False, 'full_funding_accepted': False}))
