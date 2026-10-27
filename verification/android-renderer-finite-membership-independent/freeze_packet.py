#!/usr/bin/env python3
"""Freeze only the bounded independent review directory after terminal cleanup."""
from pathlib import Path
import datetime
import hashlib
import json
import os

D = Path(__file__).resolve().parent
assert not (D / 'scratch').exists()
assert not (D / 'failure.json').exists()
members = []
for base, dirs, files in os.walk(D, followlinks=False):
    for name in dirs + files:
        assert not (Path(base) / name).is_symlink()
    for name in files:
        path = Path(base) / name
        if path == D / 'seal.json':
            continue
        data = path.read_bytes()
        members.append({'path': path.relative_to(D).as_posix(), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
members.sort(key=lambda item: item['path'])
seal = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'closed-independent-finite-component-review-no-material-defects',
        'producer_seal_sha256': 'e901741635c6827b0d14b70c51248ea64a5a4071defd0d8a4c58c9fbdb904f93',
        'source_revision_context': '6450104dc3b02d0f4d4e572c6b05ad7fdc6657b2',
        'source_context': '1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd',
        'member_count': len(members), 'member_bytes': sum(item['bytes'] for item in members), 'members': members,
        'scope': 'Six exact finite direct host classifiers only; producer 142 rows reviewed and 37 independent calls passed; all original enclosing cases pending',
        'complete_matrix_canonical_native_OTA_GA_accepted': False, 'physical_native_cleanup_credit': False}
(D / 'seal.json').write_text(json.dumps(seal, indent=2) + '\n')
for item in members:
    data = (D / item['path']).read_bytes()
    assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256']
assert {path.relative_to(D).as_posix() for path in D.rglob('*') if path.is_file()} == {item['path'] for item in members} | {'seal.json'}
print(json.dumps({'seal_sha256': hashlib.sha256((D / 'seal.json').read_bytes()).hexdigest(), 'members': len(members), 'member_bytes': seal['member_bytes']}, indent=2))
