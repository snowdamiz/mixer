"""One-shot complete custody release of string provider-source rebind candidate for fresh review."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / 'verification/swift-guarded-snapshot-string-provider-source-rebind'
OUT = Path(__file__).with_name('guarded-snapshot-string-provider-source-rebind-frozen-release.json')
assert not OUT.exists()
sha = lambda data: hashlib.sha256(data).hexdigest()
raw = (PACKET / 'seal.json').read_bytes()
assert sha(raw) == '3782b36c05e5ef0d4037cdac26834b31f3db1978250ba25abd2a869e4c5b90ab'
seal = json.loads(raw)
names = [m['path'] for m in seal['members']]
assert len(names) == len(set(names)) == 657
assert sum(m['bytes'] for m in seal['members']) == 128097360
assert all(not p.is_symlink() for p in PACKET.rglob('*'))
assert {str(p.relative_to(PACKET)) for p in PACKET.rglob('*') if p.is_file()} == set(names) | {'seal.json'}
for member in seal['members']:
    relative = Path(member['path'])
    assert not relative.is_absolute() and '..' not in relative.parts
    body = (PACKET / relative).read_bytes()
    assert len(body) == member['bytes'] and sha(body) == member['sha256']
assert seal['source_tree_sha256'] == 'acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d'
receipt = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'status': 'complete-custody-released-for-fresh-independent-review',
    'packet': str(PACKET.relative_to(ROOT)), 'seal_sha256': sha(raw), 'members': 657, 'bytes': 128097360,
    'source_tree_sha256': seal['source_tree_sha256'],
    'root_HEAD': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, timeout=10, text=True).strip(),
    'tool': {'argv': sys.argv, 'python': sys.version, 'script_sha256': sha(Path(__file__).read_bytes()),
             'executable_sha256': sha(Path(sys.executable).resolve().read_bytes())},
    'complete_membership_and_all_digests_match': True,
    'scope': 'Root custody only; exact current-source typed graph, complete constant/allocation transport, and caller conditions still require fresh independent review',
    'candidate_accepted': False, 'current_source_L_str_or_root_funding_selected': False,
    'runtime_native_OTA_GA': False}
with OUT.open('x') as stream: json.dump(receipt, stream, indent=2); stream.write('\n')
print(json.dumps({'path': str(OUT.relative_to(ROOT)), 'sha256': sha(OUT.read_bytes()), 'members': 657, 'bytes': 128097360}))
