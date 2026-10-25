#!/usr/bin/env python3
"""Freeze or verify only this compact independent review and producer handoff."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import stat
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PRODUCER = ROOT / 'verification/apple-focus-reference-runtime-v5-namespace-correction'
DOC = ROOT / 'docs/apple-focus-reference-runtime-v5-namespace-review.md'
EXPECTED = 'bfc528c7786e681f964e93e9f022bae13dc9dd0ebd8b9f343f44f1834004d631'


def stable(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def row(path):
    info = path.lstat()
    assert path.resolve() == path and stat.S_ISREG(info.st_mode) and info.st_nlink == 1
    raw = path.read_bytes()
    return {'kind': 'file', 'mode': stat.S_IMODE(info.st_mode), 'bytes': len(raw), 'sha256': sha(raw)}


def members():
    paths = [DOC] + sorted(path for path in BASE.rglob('*') if path.is_file() and path.name != 'handoff.json')
    assert not any(path.is_dir() for path in BASE.iterdir()), 'Review scratch must be absent'
    return {str(path.relative_to(ROOT)): row(path) for path in paths}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['freeze', 'verify'])
    args = parser.parse_args()
    assert row(PRODUCER / 'handoff.json')['sha256'] == EXPECTED
    producer = json.loads((PRODUCER / 'handoff.json').read_bytes())
    assert len(producer['members']) == 36
    assert all(row(ROOT / name) == expected for name, expected in producer['members'].items())
    assert sha(stable(producer['members'])) == producer['memberTreeSHA256']
    receipt = json.loads((BASE / 'receipt.json').read_bytes())
    assert receipt['passed'] and receipt['checksPassed'] == 37 and receipt['error'] is None
    assert receipt['cleanup']['ownedScratchAbsent'] and receipt['cleanup']['producerUnchanged']
    assert row(BASE / 'review.py') == receipt['reviewSource']
    path = BASE / 'handoff.json'
    if args.action == 'freeze':
        assert not path.exists(), 'Preserve frozen independent handoff'
        rows = members()
        handoff = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'command': [sys.executable, '-B', str(BASE / 'freeze.py'), 'freeze'],
            'python': sys.version, 'pythonExecutable': str(Path(sys.executable).resolve()),
            'status': 'source-and-host-packaging-accepted', 'findingCount': 0,
            'scope': 'Three V5-001 output prefixes and immutable product staging only',
            'producerHandoffSHA256': EXPECTED, 'producerMembersVerified': 36,
            'producerPacketSHA256': receipt['producerPacketSHA256'],
            'runtimeArchiveSHA256': receipt['runtimeArchiveSHA256'],
            'reviewChecksPassed': receipt['checksPassed'], 'members': rows,
            'memberTreeSHA256': sha(stable(rows)), 'nativeSelected': False,
            'nativeExecuted': False, 'gaAccepted': False, 'freshRootNativeSelectionRequired': True,
            'physicalPhones': 'disconnected-deferred', 'cleanup': receipt['cleanup']}
        with path.open('xb') as stream:
            stream.write(stable(handoff))
    else:
        handoff = json.loads(path.read_bytes())
        assert members() == handoff['members']
        assert sha(stable(handoff['members'])) == handoff['memberTreeSHA256']
    print(json.dumps({'handoffSHA256': row(path)['sha256'], 'membersVerified': len(handoff['members']),
        'producerMembersVerified': 36, 'checksPassed': 37, 'status': handoff['status'],
        'nativeSelected': False, 'nativeExecuted': False}, sort_keys=True))


if __name__ == '__main__':
    main()
