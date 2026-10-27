#!/usr/bin/env python3
"""Seal this source-only candidate after its recorded check has passed."""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent

def sha(data):
    return hashlib.sha256(data).hexdigest()

def calculate():
    assert json.loads((HERE/'command-receipt.json').read_text())['status'] == 'passed'
    paths = [p for p in sorted(HERE.rglob('*')) if p.is_file() and p.name != 'seal.json']
    assert all('__pycache__' not in p.parts for p in paths)
    members = [{'path': p.relative_to(HERE).as_posix(), 'bytes': p.stat().st_size,
                'sha256': sha(p.read_bytes())} for p in paths]
    return {'schema': 1, 'members': members, 'member_count': len(members),
            'tree_sha256': sha(json.dumps(members, sort_keys=True, separators=(',', ':')).encode()),
            'scope': 'Finite frozen-source ingress/WASI logical-work candidate only; independent review and runtime admission pending.'}

def main():
    value = calculate()
    path = HERE/'seal.json'
    if '--write' in sys.argv:
        assert not path.exists()
        path.write_text(json.dumps(value, indent=2)+'\n')
    else:
        assert json.loads(path.read_text()) == value
    print(json.dumps({'member_count': value['member_count'], 'tree_sha256': value['tree_sha256']}))

if __name__ == '__main__':
    main()
