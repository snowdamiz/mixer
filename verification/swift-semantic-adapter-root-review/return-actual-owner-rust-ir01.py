"""Record the independently reproduced IR01 failure without replaying it."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PACKET = ROOT / 'verification/swift-guarded-snapshot-actual-owner-rust-independent'
DEST = OUT / 'guarded-snapshot-actual-owner-Rust-IR01-return.json'

def row(path):
    assert path.is_file() and not path.is_symlink()
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

assert not DEST.exists(), 'One-shot; do not replay'
assert row(PACKET / 'seal.json')['sha256'] == 'e9d55089795d317048040be973e518ff9ce841d7f39cb1449b930d7ae066990c'
seal = json.loads((PACKET / 'seal.json').read_bytes())
assert len(seal['members']) == seal['member_count'] == 49
assert sum(item['bytes'] for item in seal['members']) == seal['member_bytes'] == 2172470
names = {'seal.json'}
for item in seal['members']:
    name = PurePosixPath(item['path'])
    assert not name.is_absolute() and '..' not in name.parts and str(name) not in names
    actual = row(PACKET / name)
    assert actual['bytes'] == item['bytes'] and actual['sha256'] == item['sha256']
    names.add(str(name))
assert {str(path.relative_to(PACKET)) for path in PACKET.rglob('*') if path.is_file()} == names
finding = json.loads((PACKET / 'finding-retirement.json').read_bytes())
run = json.loads((PACKET / 'commands/witness-run-001/receipt.json').read_bytes())
assert finding['observed']['after_complete_token_release_storage'] == 0
assert finding['observed']['before_storage'] == 1000000 and finding['observed']['live_proof_source_bytes'] == 1947
assert run['exit_code'] == 101 and not run['desired_property_passed'] and run['source_unchanged']
assert run['waited'] and run['owned_process_group_absent'] and not run['timed_out']
value = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'status': 'candidate-returned-for-IR01-required-accounting-correction',
    'candidate_accepted': False, 'independent_seal': row(PACKET / 'seal.json'),
    'members_verified': 49, 'member_bytes': 2172470, 'finding': row(PACKET / 'finding-retirement.json'),
    'witness': row(PACKET / 'retirement_witness.inc.rs'), 'run': row(PACKET / 'commands/witness-run-001/receipt.json'),
    'root_source_review': 'Reviewed shared correlation carriers, acquisition retirement/release and actual ordered outer caller; retained witness validates real proof pointer and guards while complete acquisition storage becomes zero.',
    'reachability': 'Generic production-core invariant failure under private host fixture construction. Current outer caller destroys child first; native bridge refuses complete retirement and production admission remains Pending.',
    'correction': {'ownership': 'verification/swift-guarded-snapshot-actual-owner-rust-retirement-correction',
        'status': 'selected-source-correction-active-compiler-roster-not-yet-released',
        'interface': row(PACKET / 'correction-interface.json'),
        'policy': 'Set a permanent non-renewable issued-correlation-scope obligation before publication. Every issued scope retains acquisition storage with no Complete token or reset/discharge route, including matched/refused/extracted/forgotten outcomes and after child destruction.',
        'new_owner_layout_and_capture_bytes': 'unpriced; prior source/MIR/layout pricing cannot be carried over',
        'joint_retirement_protocol': 'future unselected work'},
    'additional_root_compiler_or_runtime_commands': 0, 'native_funding_OTA_or_GA_accepted': False}
with DEST.open('x') as stream:
    json.dump(value, stream, indent=2)
    stream.write('\n')
w = json.loads((ROOT / 'work-graph.json').read_bytes())
g = json.loads((ROOT / 'gates/ga.json').read_bytes())
c = w['packages'][7]['fixtureCacheStateContractCandidate']
assert c == g['gates'][1]['fixtureCacheStateContractCandidate']
b = c['scalar_cursor_host_acceptance']['real_profile_adapter_preparation']['next_header_preparation']['retained_profile_composition_preparation']['real_binding_preparation']['real_profile_loader_binding']['next_adoption_lane']['guarded_snapshot_export_contract_review']['composition_source_preparation']['bootstrap_host_boundary']
s = b['actual_owner_Rust_selection']
s['implementation_status'] = 'frozen-candidate-returned-for-independent-IR01-accounting-failure'
s['independent_review_status'] = 'frozen-one-targeted-witness-reproduces-premature-storage-release'
s['implementation_accepted'] = False
s['IR01_root_return'] = row(DEST)
s['correction'] = copy.deepcopy(value['correction'])
g['gates'][1]['fixtureCacheStateContractCandidate'] = copy.deepcopy(c)
for name, data in [('work-graph.json',w),('gates/ga.json',g)]:
    (ROOT / name).write_text(json.dumps(data,indent=2)+'\n')
for name in ['PLAN.md','STATUS.md']:
    path = ROOT / name
    text = path.read_text()
    start = text.index('The actual Rust input-owner slice is selected')
    end = text.index('\n\n',start)
    new = ('The isolated actual Rust input-owner candidate is returned for correction after independent review reproduces IR01: the generic acquisition token releases its storage while a correlated validator proof and four loader guards remain alive. The exact failed Debug witness is retained; all 49 review members pass root custody checks. The current outer caller destroys its child first and the native bridge refuses completion, so no reachable native refund is established. A separate correction permanently retains acquisition charge after any correlation scope is issued, including every matched/refused/extracted/forgotten result; source work is active and validation remains pending. Added ownership storage and capture costs remain unpriced. The corrected callee interface retains bounded partial acceptance after seven fresh methods, 1,473 adverse controls and 532 equalities; thirty work and storage contexts remain unpriced. Root funding, native acquisition and GA acceptance remain pending.')
    path.write_text(text[:start]+new+text[end:])
subprocess.run(['git','diff','--check','--','PLAN.md','STATUS.md','work-graph.json','gates/ga.json'],cwd=ROOT,timeout=10,check=True)
metadata = ROOT / 'verification/console-session-and-checkout-root-review/retirement-metadata-validation.json'
with metadata.open('x') as stream:
    json.dump({'passed': True, 'metadata_files': [row(ROOT / p) for p in ['PLAN.md','STATUS.md','work-graph.json','gates/ga.json']],
        'root_return': row(DEST), 'script': row(Path(__file__).resolve()), 'GA_verified': 0},stream,indent=2)
    stream.write('\n')
print(json.dumps({'IR01_candidate_returned': True,'review_members_verified':49,'correction_source_active':True,'native_or_GA_acceptance':False}))
