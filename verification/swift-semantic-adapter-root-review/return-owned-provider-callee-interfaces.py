"""Record focused independently reproduced source-closure gaps without replay."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_name('guarded-snapshot-owned-provider-callee-interfaces-return.json')
assert not OUT.exists()
sha = lambda data: hashlib.sha256(data).hexdigest()
custody = []
for name, digest, count, total in [
    ('swift-guarded-snapshot-owned-provider-callee-interfaces', 'e98916beff1a3c8b912e96591fbd573b8d570aa38cc4390a13fa20658290dce0', 230, 14925640),
    ('swift-guarded-snapshot-owned-provider-callee-independent', '050da55a398e839075dd841e81d4da580f74a97adf2d6346b0d8e44587680e16', 90, 6113083),
]:
    packet = ROOT / 'verification' / name
    raw = (packet / 'seal.json').read_bytes()
    assert sha(raw) == digest
    seal = json.loads(raw)
    names = [m['path'] for m in seal['members']]
    assert len(names) == len(set(names)) == count == seal['member_count']
    assert sum(m['bytes'] for m in seal['members']) == total
    assert all(not p.is_symlink() for p in packet.rglob('*'))
    assert {str(p.relative_to(packet)) for p in packet.rglob('*') if p.is_file()} == set(names) | {'seal.json'}
    for member in seal['members']:
        relative = Path(member['path'])
        assert not relative.is_absolute() and '..' not in relative.parts
        body = (packet / relative).read_bytes()
        assert len(body) == member['bytes'] and sha(body) == member['sha256']
    custody.append({'path': str(packet.relative_to(ROOT)), 'seal_sha256': digest, 'members': count, 'bytes': total})
review = ROOT / 'verification/swift-guarded-snapshot-owned-provider-callee-independent'
contract_path = review / 'correction-contract.json'
assert sha(contract_path.read_bytes()) == '85161323e1ea8d101dd71db0f0466d452d964a7b3f25ad80b209891e14fb6320'
contract = json.loads(contract_path.read_text())
assert [f['id'] for f in contract['findings']] == ['R1', 'R2', 'R3']
validation = json.loads((review / 'final-validation.json').read_text())
assert validation['all_previous_successful_children_reaped_and_groups_absent']
for command in validation['receipt_history']:
    if command['child_spawned']:
        assert command['exit_code'] == 0 and command['postflight_ok'] and command['owned_process_group_absent_after_reap']
    else:
        assert command['exit_code'] is None
receipt = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'status': 'returned-callee-source-closure-for-focused-R1-R3-correction', 'custody': custody,
    'complete_membership_and_all_member_hashes_checked': True,
    'root_HEAD': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, timeout=10, text=True).strip(),
    'correction_contract': str(contract_path.relative_to(ROOT)), 'correction_contract_sha256': sha(contract_path.read_bytes()),
    'root_source_inspection': [
        {'file': 'official-source/library/core/src/num/uint_macros.rs', 'line': 2989, 'finding': 'three written casts absent from overflowing_add_adapter source ledger'},
        {'file': 'official-source/library/core/src/intrinsics/mod.rs', 'line': 2613, 'finding': 'selected macro runtime fn and callable/unit interfaces require explicit source charges'},
        {'file': 'official-source/library/core/src/option.rs', 'line': 633, 'finding': 'contains composite must cover is_some receiver and matches expansion'},
    ],
    'independent_internal_arithmetic_component_checks': 5344,
    'independent_raw_LLVM_signature_rows': 23, 'independent_short_scan_cases': 144, 'phase_sums': 15,
    'internal_arithmetic_is_not_complete_source_closure': True,
    'frozen_input_members': 1245, 'inherited_packets': 15,
    'documented_inherited_pycache_exclusion_preserved_without_import_or_mutation': True,
    'two_reviewer_child_free_preflight_failures_preserved': True,
    'candidate_closed_prices_or_root_funding_selected': False, 'candidate_accepted': False,
    'runtime_native_OTA_GA': False, 'scope': 'Root full packet custody and actual cited source inspection; no compiler or test replay',
    'tool': {'argv': sys.argv, 'python': sys.version, 'script_sha256': sha(Path(__file__).read_bytes()),
             'executable_sha256': sha(Path(sys.executable).resolve().read_bytes())}}
with OUT.open('x') as stream: json.dump(receipt, stream, indent=2); stream.write('\n')
print(json.dumps({'path': str(OUT.relative_to(ROOT)), 'sha256': sha(OUT.read_bytes()), 'accepted': False}))
