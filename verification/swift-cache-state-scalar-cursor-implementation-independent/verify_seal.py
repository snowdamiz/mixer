#!/usr/bin/env python3
"""Read-only packet seal and immutable external input verification."""
import hashlib, json, pathlib
root = pathlib.Path(__file__).resolve().parent
repo = root.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
seal = json.loads((root / 'seal.json').read_text())
for row in seal['members']:
    path = root / row['path']
    assert path.is_relative_to(root) and path.is_file()
    assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], row['path']
assert len(seal['members']) == seal['member_count']
assert sum(row['bytes'] for row in seal['members']) == seal['total_bytes']
for row in seal['external_inputs']:
    assert sha(repo / row['path']) == row['sha256'], row['path']
assert not list(root.rglob('__pycache__')) and not list(root.glob('.scratch*'))
assert not (root / 'evidence/independent-debug').exists()
assert not (root / 'evidence/independent-optimized').exists()
print(json.dumps({'seal_sha256': sha(root / 'seal.json'), 'members_verified': len(seal['members']),
    'bytes_verified': seal['total_bytes'], 'external_inputs_verified': len(seal['external_inputs']),
    'decision': seal['decision'], 'canonical_integration_selected': False}, indent=2))
