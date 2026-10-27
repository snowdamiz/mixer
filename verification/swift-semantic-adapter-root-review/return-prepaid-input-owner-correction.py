"""One-shot custody/source disposition; never reruns candidate tests."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_name('guarded-snapshot-prepaid-input-owner-correction-return.json')
assert not OUT.exists()
sha = lambda data: hashlib.sha256(data).hexdigest()
specs = [
    ('swift-guarded-snapshot-prepaid-input-owner-correction', 'f3e4ac2543fde4fe7b1e03019fb49bbb5ba9aca078097e5aeb0fc972703de7a3', 61, 1323422),
    ('swift-guarded-snapshot-prepaid-input-owner-correction-independent', 'a64f0cbb775265509b98bea63faca5e144e6d4b8f685898251ea12d506c8840a', 34, 829896),
]
custody = []
for name, expected, count, size in specs:
    packet = ROOT / 'verification' / name
    raw = (packet / 'seal.json').read_bytes()
    assert sha(raw) == expected
    seal = json.loads(raw)
    names = [m['path'] for m in seal['members']]
    assert len(names) == len(set(names)) == seal['member_count'] == count
    assert sum(m['bytes'] for m in seal['members']) == seal['member_bytes'] == size
    assert all(not p.is_symlink() for p in packet.rglob('*'))
    assert {str(p.relative_to(packet)) for p in packet.rglob('*') if p.is_file()} == set(names) | {'seal.json'}
    for member in seal['members']:
        relative = Path(member['path'])
        assert not relative.is_absolute() and '..' not in relative.parts
        data = (packet / relative).read_bytes()
        assert len(data) == member['bytes'] and sha(data) == member['sha256'], member['path']
    custody.append({'path': str(packet.relative_to(ROOT)), 'seal_sha256': expected, 'members': count, 'bytes': size})

review = ROOT / 'verification/swift-guarded-snapshot-prepaid-input-owner-correction-independent'
report = json.loads((review / 'report.json').read_text())
for cmd in report['commands']:
    receipt = json.loads((review / cmd['path'] / 'receipt.json').read_text())
    assert receipt['exit'] == cmd['exit'] and not receipt['timed_out']
    assert receipt['inputs_unchanged'] and receipt['child_reaped'] and receipt['owned_group_absent']
    assert receipt['input_members'] == 443
    for item in receipt['outputs']:
        data = (ROOT / item['path']).read_bytes()
        assert len(data) == item['bytes'] and sha(data) == item['sha256']
assert 'FAILED (failures=6)' in (review / 'commands/required-properties/stderr').read_text()
assert report['fresh_independent_controls'] == {'methods': 11, 'passing': 7, 'failed': 4, 'producer_tests_imported_or_replayed': False, 'producer_fixtures_imported': False}
contract = review / 'correction-contract.json'
assert [row['id'] for row in json.loads(contract.read_text())['requirements']] == ['C1', 'C2']
receipt = {
    'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'status': 'returned-host-model-correction-for-C1-C2',
    'root_HEAD': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, timeout=10, text=True).strip(),
    'custody': custody, 'complete_membership_and_command_output_checks': True,
    'fresh_independent_methods_passed': 7, 'desired_property_methods_failed': 4, 'failure_records': 6,
    'positive_witness_exit_is_reproduction_not_acceptance': True,
    'correction_contract': str(contract.relative_to(ROOT)), 'correction_contract_sha256': sha(contract.read_bytes()),
    'root_source_inspection': {'file': 'verification/swift-guarded-snapshot-prepaid-input-owner-correction/model.py',
        'lines': [553, 566, 612, 620, 652, 654, 661, 667, 672],
        'findings': ['early refusal precedes consuming-attempt state and selected ownership',
                     'complete retirement can forget refused selected carrier and four live Files',
                     'session extent and nested identity use coercing equality before typed correspondence']},
    'minimum_existing_open_plus_correlation_direction_retained': True,
    'same_handle_route_selected': False, 'original_failed_candidates_and_attempts_preserved': True,
    'candidate_model_accepted': False, 'root_policy_or_funding_or_operational_OTA_GA': False,
    'tool': {'argv': sys.argv, 'python': sys.version,
             'executable_sha256': sha(Path(sys.executable).resolve().read_bytes()), 'script_sha256': sha(Path(__file__).read_bytes())},
    'scope': 'pure host root custody and source inspection; no compiler/test/runtime replay',
}
with OUT.open('x') as stream:
    json.dump(receipt, stream, indent=2)
    stream.write('\n')
print(json.dumps({'path': str(OUT.relative_to(ROOT)), 'sha256': sha(OUT.read_bytes()), 'correction_contract_sha256': sha(contract.read_bytes()), 'accepted': False}))
