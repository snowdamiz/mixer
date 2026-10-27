#!/usr/bin/env python3
"""Data-only freeze of the distinct P0 source146 preparation candidate."""
import hashlib
import json
from pathlib import Path
import platform
import sys
HERE = Path(__file__).resolve().parent


def snapshot():
    members = []
    for p in sorted(HERE.rglob('*')):
        if p.is_file() and p != HERE/'seal.json':
            b = p.read_bytes()
            members.append({'path': p.relative_to(HERE).as_posix(), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()})
    c = json.loads((HERE/'candidate.json').read_bytes())
    return {'schema': 1, 'status': c['status'], 'member_count': len(members), 'member_bytes': sum(m['bytes'] for m in members), 'members': members, 'source_members': 146, 'source_tree_sha256': c['source_tree_sha256'], 'prior_review_seal_sha256': 'ffdd027f5550f315fb7c63dcee7e532e7aea1d4be39c478d225f8f6ed09a7b2b', 'formula': c['formula'], 'checks': c['checks'], 'cross_review_complete': False, 'selected_policy_or_operational_grant': False, 'full_P0_work_storage_or_host_quote': False, 'compiler_invocations': 0, 'native_OTA_FieldLog_customer_GA': False, 'python': platform.python_version(), 'seal_command': [sys.executable, str(HERE/'freeze.py')]}


def main():
    data = (json.dumps(snapshot(), sort_keys=True, indent=2)+'\n').encode()
    if '--check-only' in sys.argv:
        if (HERE/'seal.json').read_bytes() != data:
            raise AssertionError('frozen source146 candidate changed')
    else:
        if (HERE/'seal.json').exists():
            raise AssertionError('refuse to replace an existing seal')
        (HERE/'seal.json').write_bytes(data)
    s = json.loads(data)
    print(json.dumps({'passed': True, 'seal_sha256': hashlib.sha256(data).hexdigest(), 'member_count': s['member_count'], 'member_bytes': s['member_bytes'], 'mode': 'check-only' if '--check-only' in sys.argv else 'freeze'}))


if __name__ == '__main__':
    main()
