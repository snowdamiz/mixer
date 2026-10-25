#!/usr/bin/env python3
"""Freeze/verify only reviewer-owned files and the reviewed producer identity."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import stat
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
DOC = ROOT / 'docs/apple-focus-reference-diagnostic-v1-independent-review.md'
PRODUCER = ROOT / 'verification/apple-focus-reference-diagnostic-v1/handoff.json'
EXPECTED = '9f066db167168e8ab0c78b2147f857ba3980d965a69b681e566e5e185f6a0d3c'


def stable(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def row(path):
    info = path.lstat()
    assert stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and path.resolve() == path
    return {'kind': 'file', 'bytes': info.st_size, 'mode': stat.S_IMODE(info.st_mode), 'sha256': sha(path.read_bytes())}


def main(action):
    assert row(PRODUCER)['sha256'] == EXPECTED, 'Reviewed producer identity changed'
    producer = json.loads(PRODUCER.read_bytes())
    assert all(row(ROOT / name) == item for name, item in producer['members'].items()), 'Producer member changed'
    receipt = json.loads((BASE / 'receipt.json').read_bytes())
    assert receipt['controlsRun'] == 74 and receipt['controlsPassed'] == 66 and len(receipt['failedControls']) == 8
    assert receipt['passed'] is False and receipt['nativeExecuted'] is False and receipt['runtimeSelected'] is False
    assert receipt['reviewSources']['review.py'] == row(BASE / 'review.py')
    for name, item in receipt['outputs'].items():
        assert row(BASE / name) == item
    paths = sorted(p for p in BASE.iterdir() if p.is_file() and p.name != 'handoff.json') + [DOC]
    assert not any(p.is_dir() for p in BASE.iterdir()), 'Unretired reviewer scratch'
    members = {str(p.relative_to(ROOT)): row(p) for p in paths}
    path = BASE / 'handoff.json'
    if action == 'freeze':
        assert not path.exists(), 'Retain previous independent handoff'
        handoff = {'schema': 'mixer.apple-focus-reference-independent-frozen-review.1',
                   'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   'command': [sys.executable, '-B', str(Path(__file__).resolve()), 'freeze'], 'cwd': str(ROOT), 'python': sys.version,
                   'reviewedProducerHandoffSHA256': EXPECTED, 'members': members, 'memberTreeSHA256': sha(stable(members)),
                   'controlsRun': 74, 'controlsPassed': 66, 'failedControls': receipt['failedControls'], 'reviewPassed': False,
                   'disposition': receipt['disposition'], 'nativeExecuted': False, 'runtimeSelected': False,
                   'compileRerun': False, 'physicalPhones': 'disconnected-deferred', 'runPassed': False, 'gaAccepted': False}
        path.write_bytes(stable(handoff))
    else:
        handoff = json.loads(path.read_bytes())
        assert handoff['members'] == members and handoff['memberTreeSHA256'] == sha(stable(members)), 'Review changed'
        assert handoff['reviewedProducerHandoffSHA256'] == EXPECTED
    print(json.dumps({'frozenReviewFilesVerified': True, 'handoffSHA256': row(path)['sha256'], 'members': len(members),
                      'reviewPassed': False, 'controlsRun': 74, 'controlsPassed': 66, 'nativeExecuted': False}, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['freeze', 'verify'])
    main(parser.parse_args().action)
