#!/usr/bin/env python3
"""Seal or verify only this newly owned source-only packet."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
members = []
for path in sorted(HERE.rglob('*')):
    if path.is_file() and path.name != 'seal.json':
        data = path.read_bytes()
        members.append({'path': str(path.relative_to(HERE)), 'bytes': len(data),
                        'sha256': hashlib.sha256(data).hexdigest()})
value = {'schema': 1, 'member_base': 'packet-relative', 'members': members,
         'member_count': len(members), 'total_bytes': sum(m['bytes'] for m in members),
         'scope': 'unselected minimal subtraction proposal; necessary G3 obstruction; no implementation',
         'source_sha256': json.loads((HERE / 'source-assembly.json').read_text())['proposed_sha256']}
seal = HERE / 'seal.json'
if '--verify' in sys.argv:
    if json.loads(seal.read_text()) != value:
        raise ValueError('frozen packet differs')
else:
    seal.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
print(json.dumps({'members': value['member_count'], 'bytes': value['total_bytes'],
                  'sha256': hashlib.sha256(seal.read_bytes()).hexdigest(), 'verified': '--verify' in sys.argv}, sort_keys=True))
