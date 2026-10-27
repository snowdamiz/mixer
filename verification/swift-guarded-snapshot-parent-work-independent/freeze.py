#!/usr/bin/env python3
"""Seal/check only this independent review folder; data hashes only."""
import hashlib
import json
from pathlib import Path
import platform
import sys

HERE = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot():
    members = []
    for path in sorted(HERE.rglob('*')):
        if path.is_file() and path != HERE/'seal.json':
            data = path.read_bytes()
            members.append({'path': path.relative_to(HERE).as_posix(), 'bytes': len(data), 'sha256': digest(data)})
    review = json.loads((HERE/'review.json').read_bytes())
    return {
        'schema': 1,
        'status': review['status'],
        'source_members': 145,
        'source_tree_sha256': review['source_tree_sha256'],
        'producer_seal_sha256': review['producer_seal_sha256'],
        'member_count': len(members),
        'member_bytes': sum(x['bytes'] for x in members),
        'members': members,
        'independent_checks': review['independent_reconciliation']['checks'],
        'formula': review['formula'],
        'full_P0_or_whole_quote_or_root_policy_or_operational_grant': False,
        'source146_rebinding_accepted': False,
        'native_OTA_FieldLog_customer_GA_accepted': False,
        'python': platform.python_version(),
        'seal_command': [sys.executable, str(HERE/'freeze.py')],
        'scope': 'Python data hashes only; no compiler/product/native/capture/process inventory',
    }


def main():
    expected = (json.dumps(snapshot(), sort_keys=True, indent=2)+'\n').encode()
    if '--check-only' in sys.argv:
        if (HERE/'seal.json').read_bytes() != expected:
            raise AssertionError('independent packet changed after freeze')
    else:
        if (HERE/'seal.json').exists():
            raise AssertionError('refuse to replace an existing seal')
        (HERE/'seal.json').write_bytes(expected)
    print(json.dumps({'passed': True, 'seal_sha256': digest(expected), 'member_count': json.loads(expected)['member_count'], 'member_bytes': json.loads(expected)['member_bytes'], 'mode': 'check-only' if '--check-only' in sys.argv else 'seal'}))


if __name__ == '__main__':
    main()
