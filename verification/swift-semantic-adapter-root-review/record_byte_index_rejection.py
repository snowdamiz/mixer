"""Record exact immutable source-review rejection; no candidate execution."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_name('byte-index-proposal-rejection.json')
assert not OUT.exists(), 'one-shot receipt already exists'

def binding(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

packets = [
    ('verification/swift-cache-state-byte-index-independent/seal.json',
     'c4162bea405595b62fcb576ed616a5ff75ab6c6401c56092e7f0b3946a857883'),
    ('verification/swift-cache-state-byte-index-independent/ownership-addendum-seal.json',
     '9c2f5373e6e7f583db69c66cdf252d7029242351f249b639fca55c42b78ece67'),
]
verified = []
for name, digest in packets:
    path = ROOT / name
    assert binding(path)['sha256'] == digest
    packet = json.loads(path.read_bytes())
    rows = packet['members']
    assert len(rows) == packet['member_count'] == len({r['path'] for r in rows})
    assert sum(r['bytes'] for r in rows) == packet['member_bytes']
    for row in rows:
        member = ROOT / row['path']
        assert member.is_relative_to(path.parent) and not member.is_symlink()
        assert binding(member) == {k: row[k] for k in ('bytes', 'sha256')}
    verified.append({'path': name, 'sha256': digest, 'members': len(rows),
                     'bytes': packet['member_bytes']})
base = ROOT / 'verification/swift-cache-state-byte-index-independent'
bound = json.loads((base / 'G4-independent-bound.json').read_bytes())
floor = bound['selected_model_assignment_necessary_floor']
assert floor['guaranteed_outputs'] == 384
assert floor['read_scalars_per_output'] == 24
assert floor['write_scalars_per_output'] == 21
assert (384 * (24 + 21) + 15) // 16 == floor['scalar_groups'] == 1080
assert floor['scalar_groups'] > bound['cap'] == 768
selected = (ROOT / 'verification/swift-cache-state-g6-complete/ledger.py').read_text()
proposed = (ROOT / 'verification/swift-cache-state-byte-index-proposal/source_checks.py').read_text()
assert "with t.site(538,'merge caller-only boundary'):" in selected
assert 'merge received-unit statement continuation; implicit unit/callee return owned G4' in selected
assert 'merge_arg_thin merge_param_thin merge_call' in proposed
assert 'merge_unit_return merge_unit_received' in proposed
receipt = {
    'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'command': sys.argv, 'python': sys.version,
    'script': binding(Path(__file__)),
    'context_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'status': 'Exact byte-index source proposal rejected under unchanged selected component grammar',
    'packets': verified,
    'G4_assignment_only_necessary_floor': floor,
    'G4_cap': 768,
    'findings': ['BI-IR-01', 'BI-IR-02', 'BI-IR-03', 'BI-IR-04'],
    'other_group_claims_accepted': False,
    'G6_caller_partition': 'Retain four selected caller-only G6 operations; no implicit G3 reassignment or duplicate ownership',
    'finite_models': {'sort': 12016, 'prefix': 96128, 'addresses': 896, 'padding_cleanup': 64},
    'finite_models_are_Rust_qualification': False,
    'scope': 'Necessary floor rejects this exact algorithm/accounting proposal only; no impossibility claim for different algorithms. Exact unchanged C3 body/suffix bindings and finite model results retained.',
    'layout_amendment_selected': False, 'implementation_selected': False,
    'all_caps_unchanged': [256, 2560, 2568, 768, 640, 640, 248],
    'whole29344_lifetime_accepted': False, 'compiler_or_runtime_execution': False,
    'native_or_capture_started': False, 'GA_qualified': False,
}
OUT.write_text(json.dumps(receipt, indent=2) + '\n')
node = {'status': receipt['status'], 'root_receipt': OUT.relative_to(ROOT).as_posix(),
        'root_sha256': binding(OUT)['sha256'], 'independent_packets': verified,
        'G4_necessary_floor': 1080, 'G4_cap': 768,
        'implementation_or_layout_selected': False,
        'next': 'Distinct cached-head source-only proposal active; complete correction3 role/lifetime inventory active'}
for name, top in (('work-graph.json', 'packages'), ('gates/ga.json', 'gates')):
    path = ROOT / name
    data = json.loads(path.read_bytes())
    target = next(r['fixtureCacheStateContractCandidate'] for r in data[top] if 'fixtureCacheStateContractCandidate' in r)
    target['source_accounting_supplement']['byte_index_proposal'] = node
    path.write_text(json.dumps(data, indent=2) + '\n')
print(json.dumps({'receipt': OUT.relative_to(ROOT).as_posix(), **binding(OUT),
                  'verified_members': sum(p['members'] for p in verified),
                  'G4_necessary_floor': 1080, 'G4_cap': 768}))
