"""One-shot final exact manifest; no test, runtime, Git or network activity."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
sha = lambda b: hashlib.sha256(b).hexdigest()
assert not (OUT / 'seal.json').exists()
assert not (OUT / 'owned-scratch').exists()
review = json.loads((OUT / 'review.json').read_text())
capture = json.loads((OUT / 'capture.json').read_text())
commands = json.loads((OUT / 'commands.json').read_text())
assert review['result'] == 'accept-checkout-selection-with-explicit-limits'
assert review['owned_scratch_removed']
for row in [capture, *commands]:
    assert row['pid'] == row['pgid']
    assert row['exit'] == 0 and not row['timed_out']
    assert row['owned_child_reaped'] and row['owned_group_absent']
    assert not row['signals_sent']
assert capture['audit_sha256'] == sha((OUT / 'audit.py').read_bytes())
assert capture['capture_sha256'] == sha((OUT / 'capture.py').read_bytes())
rows = []
for path in sorted(OUT.rglob('*')):
    assert not path.is_symlink()
    if path.is_file():
        body = path.read_bytes()
        rows.append({'path': str(path.relative_to(OUT)), 'bytes': len(body), 'sha256': sha(body)})
seal = {'schema': 1, 'member_count': len(rows), 'member_bytes': sum(x['bytes'] for x in rows),
        'tree_sha256': sha(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()),
        'members': rows, 'producer_seal_sha256': review['producer_seal_sha256'],
        'base': review['base'], 'workflow_sha256': review['workflow_sha256'],
        'scope': 'independent services CI checkout selection, complete selected source custody, offline Linux package enumeration and producer fixture evidence review',
        'acceptance': 'checkout selection only; full remote services job and race suite pending; producer numeric PID/PGID unavailable',
        'GA_gate_accepted': False}
with (OUT / 'seal.json').open('x') as stream:
    json.dump(seal, stream, indent=2)
    stream.write('\n')
print(json.dumps({'seal_sha256': sha((OUT / 'seal.json').read_bytes()),
                  'member_count': seal['member_count'], 'member_bytes': seal['member_bytes'],
                  'tree_sha256': seal['tree_sha256']}))
