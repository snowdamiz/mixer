"""Release a complete frozen candidate for independent review, without acceptance."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACKET = ROOT / 'verification/swift-guarded-snapshot-actual-owner-rust-implementation'
OUT = HERE / 'guarded-snapshot-actual-owner-Rust-frozen-release.json'
assert not OUT.exists()

def sha(raw): return hashlib.sha256(raw).hexdigest()
def row(p):
    raw = p.read_bytes()
    return {'path': str(p.relative_to(ROOT)), 'bytes': len(raw), 'sha256': sha(raw)}

seal_path = PACKET / 'seal.json'
assert row(seal_path)['sha256'] == '3592011c00794c12dcb76cecc41d4d2913e01a3d6e97612f3ce90f10cb4e5e23'
seal = json.loads(seal_path.read_bytes())
members = seal['members']
assert len(members) == seal['member_count'] == 1799
assert sum(m['bytes'] for m in members) == seal['member_bytes'] == 209640941
assert sha(json.dumps(members, sort_keys=True, separators=(',', ':')).encode()) == seal['tree_sha256'] == '43de4376805a601db9be4b0dcc94ede6d8b2a362487cd32a304df545d28919d7'
names = set()
for member in members:
    rel = Path(member['path'])
    assert not rel.is_absolute() and '..' not in rel.parts and member['path'] not in names
    names.add(member['path'])
    p = PACKET / rel
    assert p.is_file() and not p.is_symlink() and not stat.S_IMODE(p.stat().st_mode) & 0o222
    actual = row(p)
    assert actual['bytes'] == member['bytes'] and actual['sha256'] == member['sha256']
assert {str(p.relative_to(PACKET)) for p in PACKET.rglob('*') if p.is_file()} == names | {'seal.json'}
assert not any(p.is_symlink() for p in PACKET.rglob('*'))
assert not (PACKET / 'build').exists()
commands = json.loads((PACKET / 'command-summary.json').read_bytes())
assert commands['compiler_invocations'] == 16 and commands['host_runs'] == 5
assert commands['all_exact_owned_groups_absent'] and commands['all_owned_children_reaped']
assert commands['compiler_intervals_disjoint'] and commands['layout_queries'] == 0
for mode in ['debug', 'opt']:
    assert '15 passed; 0 failed' in (PACKET / 'commands' / ('run-' + mode + '-proof-error') / 'stdout').read_text()
head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,timeout=10,text=True).strip()
assert head == 'b231f3d405c06bfb348f193d46a348af0529bd84'
receipt = {
    'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'status': 'frozen-custody-released-for-independent-source-MIR-and-host-review',
    'seal': row(seal_path), 'members_verified': 1799, 'member_bytes_verified': 209640941,
    'tree_sha256': seal['tree_sha256'], 'final_source146_tree': seal['source146_tree'],
    'final_source_manifest': row(PACKET / 'final-source-manifest.json'),
    'command_summary': row(PACKET / 'command-summary.json'), 'cleanup': row(PACKET / 'cleanup.json'),
    'root_script': row(Path(__file__).resolve()), 'python': sys.version,
    'revision_attribution': {
        'producer_recorded_historical_frozen_baseline': '9398732c23648a82097d5a72b02b1c77af818e41',
        'root_selection_and_dispatch_orchestration_revision': 'd6af73813244c330a979afb83b45f53490ff5b29',
        'observed_root_release_HEAD': head,
        'contemporaneous_producer_git_HEAD_query': False,
        'rule': 'Exact command source manifests/trees and tool identities establish tested bytes. Historical baseline is not a claim about Git HEAD at command execution; later console commit changes no Rust source origin.',
    },
    'producer_report': {'final_filtered_methods_per_mode': 15, 'compiler_invocations': 16,
        'filtered_runs': 5, 'complete_MIR_items': 6207, 'semantic_independent_review_pending': True},
    'independent_ownership': 'verification/swift-guarded-snapshot-actual-owner-rust-independent',
    'independent_compiler_budget_not_yet_selected': True,
    'native_acquisition_root_funding_canonical_integration_or_GA_accepted': False,
}
with OUT.open('x') as stream:
    json.dump(receipt, stream, indent=2)
    stream.write('\n')
print(json.dumps({'release': row(OUT), 'members_verified': 1799, 'independent_review_released': True, 'acceptance': False}))
