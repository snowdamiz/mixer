#!/usr/bin/env python3
"""Read-only verification of this independent review handoff."""
import hashlib
import json
import pathlib
import stat

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]

def verify():
    path = HERE / 'handoff.json'
    raw = path.read_bytes()
    packet = json.loads(raw)
    actual = {str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file() and p != path}
    actual.add('docs/apple-focus-system-join-correction-review.md')
    assert actual == set(packet['members'])
    for relative, expected in packet['members'].items():
        member = ROOT / relative
        data = member.read_bytes()
        assert len(data) == expected['bytes'] and hashlib.sha256(data).hexdigest() == expected['sha256'], relative
        assert stat.S_IMODE(member.stat().st_mode) == expected['mode'] == 0o444, relative
    assert stat.S_IMODE(path.stat().st_mode) == 0o444
    return {'passed': True, 'members': len(packet['members']),
            'handoffSHA256': hashlib.sha256(raw).hexdigest(), 'nativePass': False,
            'scope': 'Independent sealed frozen V7 replay host review only'}

if __name__ == '__main__':
    print(json.dumps(verify(), sort_keys=True))
