#!/usr/bin/env python3
"""Reconstruct only the released producer's exact146 source and host11."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
PRODUCER = ROOT / 'verification/swift-guarded-snapshot-actual-owner-rust-implementation'

def fingerprint(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

manifest = json.loads((PRODUCER / 'final-source-manifest.json').read_text())
assert manifest['member_count'] == 146
assert len(manifest['members']) == 146
assert not (PACKET / 'source').exists(), 'Never overwrite a prepared correction.'
members = []
for member in manifest['members']:
    source = PRODUCER / 'source/vm' / member['path']
    data = source.read_bytes()
    assert len(data) == member['bytes']
    assert hashlib.sha256(data).hexdigest() == member['sha256']
    target = PACKET / 'source/vm' / member['path']
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    members.append(fingerprint(source))
host = sorted((PRODUCER / 'source/host').rglob('*'))
host = [path for path in host if path.is_file()]
assert len(host) == 11
for source in host:
    target = PACKET / 'source/host' / source.relative_to(PRODUCER / 'source/host')
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
(PACKET / 'source-origin.json').write_text(json.dumps({
    'schema': 1,
    'producer_seal': fingerprint(PRODUCER / 'seal.json'),
    'producer_source_manifest': fingerprint(PRODUCER / 'final-source-manifest.json'),
    'producer_source_tree': manifest['tree_sha256'],
    'source_members': members,
    'host_members': [fingerprint(path) for path in host],
    'scope': 'Released source reconstruction only; no compiler/test/native/fixture execution.',
}, indent=2) + '\n')
print(json.dumps({'source_members': len(members), 'host_members': len(host), 'compiler': False}))
