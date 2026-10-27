"""New one-shot release after producer-only mode hardening; prior failed preflight retained."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PACKET = ROOT / 'verification/swift-guarded-snapshot-provider-callee-source-correction'
OUT = HERE / 'guarded-snapshot-provider-callee-source-correction-frozen-release.json'
assert not OUT.exists()
sha = lambda b: hashlib.sha256(b).hexdigest()
raw = (PACKET / 'seal.json').read_bytes()
assert sha(raw) == 'e80dd24b7cb7e18c97abb1effa705cbc2b7882b36ac8e439a181bc6cf3a6dfb1'
seal = json.loads(raw)
names = [m['path'] for m in seal['members']]
assert len(names) == len(set(names)) == seal['member_count'] == 219
assert sum(m['bytes'] for m in seal['members']) == seal['bytes'] == 13305313
assert all(not p.is_symlink() for p in PACKET.rglob('*'))
assert {str(p.relative_to(PACKET)) for p in PACKET.rglob('*') if p.is_file()} == set(names) | {'seal.json'}
for m in seal['members']:
    rel = Path(m['path'])
    assert not rel.is_absolute() and '..' not in rel.parts
    p = PACKET / rel
    data = p.read_bytes()
    assert len(data) == m['bytes'] and sha(data) == m['sha256']
    assert not stat.S_IMODE(p.stat().st_mode) & 0o222
return_path = HERE / 'guarded-snapshot-owned-provider-callee-interfaces-return.json'
assert sha(return_path.read_bytes()) == 'd497b65fed7324ffa52b5a90a2c8b8c2bdd323c59a2a574a5b38d44667f0dc49'
receipt = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'status': 'frozen-root-custody-complete-awaiting-fresh-independent-review',
    'packet': str(PACKET.relative_to(ROOT)), 'seal_sha256': sha(raw), 'members': 219, 'bytes': 13305313,
    'root_return_sha256': sha(return_path.read_bytes()),
    'root_script_sha256': sha(Path(__file__).read_bytes()),
    'proposal_sha256': sha((PACKET / 'proposal.json').read_bytes()),
    'frontiers_sha256': sha((PACKET / 'source-closure-frontiers.json').read_bytes()),
    'scope': 'R1-R3 partial source closure, exact ActualT=u64 and nineteen range work/storage contexts; all five contains auto-borrow/helper contexts',
    'known_shell_not_complete_price': True, 'partial_range_source_obligations_mandatory': True,
    'root_acceptance': False, 'compiler_authorized': False, 'prices_funding_runtime_OTA_GA_selected': False}
with OUT.open('x') as stream:
    json.dump(receipt, stream, indent=2)
    stream.write('\n')
print(json.dumps({'release': str(OUT.relative_to(ROOT)), 'sha256': sha(OUT.read_bytes()), 'members': 219, 'bytes': 13305313}))
