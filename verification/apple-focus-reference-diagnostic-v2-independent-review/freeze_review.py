#!/usr/bin/env python3
"""Freeze/verify only V2 reviewer files and immutable predecessor identities."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import stat
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
DOC = ROOT / 'docs/apple-focus-reference-diagnostic-v2-independent-review.md'
IDENTITIES = {
    'apple-focus-reference-diagnostic-v1': '9f066db167168e8ab0c78b2147f857ba3980d965a69b681e566e5e185f6a0d3c',
    'apple-focus-reference-diagnostic-v1-independent-review': 'd70da20d45323be52138a6efdbd2d53c74efbd521620584b228bf9f03e3eedbb',
    'apple-focus-reference-diagnostic-v2': '07776c2af95bcc58e126b4ceb0f0dee39dec1138ea96bc9e33bc8a4a0393a3a0',
}


def stable(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def row(path):
    info = path.lstat()
    assert stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and path.resolve() == path
    return {'kind': 'file', 'bytes': info.st_size, 'mode': stat.S_IMODE(info.st_mode), 'sha256': sha(path.read_bytes())}


def main(action):
    for name, identity in IDENTITIES.items():
        path = ROOT / 'verification' / name / 'handoff.json'
        assert row(path)['sha256'] == identity, 'Predecessor changed'
        handoff = json.loads(path.read_bytes())
        assert all(row(ROOT / member) == value for member, value in handoff['members'].items())
        assert sha(stable(handoff['members'])) == handoff['memberTreeSHA256']
    receipt = json.loads((BASE / 'receipt.json').read_bytes())
    assert receipt['passed'] is True and receipt['totalControlsRun'] == receipt['totalControlsPassed'] == 137
    assert receipt['replayedEarlierControls'] == receipt['replayedEarlierControlsPassed'] == 74
    assert receipt['additionalControlsRun'] == receipt['additionalControlsPassed'] == 63
    assert receipt['failedControls'] == [] and receipt['nativeExecuted'] is False and receipt['runtimeSelected'] is False
    assert receipt['reviewSources']['review.py'] == row(BASE / 'review.py')
    assert all(row(BASE / name) == value for name, value in receipt['outputs'].items())
    replay = json.loads((BASE / 'earlier-74-controls-receipt.json').read_bytes())
    assert all(row(BASE / name) == value for name, value in replay['outputs'].items())
    assert not any(path.is_dir() for path in BASE.iterdir()), 'Unretired scratch'
    paths = sorted(path for path in BASE.iterdir() if path.is_file() and path.name != 'handoff.json') + [DOC]
    members = {str(path.relative_to(ROOT)): row(path) for path in paths}
    path = BASE / 'handoff.json'
    if action == 'freeze':
        assert not path.exists(), 'Preserve frozen reviewer handoff'
        handoff = {'schema': 'mixer.apple-focus-reference-v2-independent-frozen-review.1',
                   'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   'command': [sys.executable, '-B', str(Path(__file__).resolve()), 'freeze'], 'cwd': str(ROOT), 'python': sys.version,
                   'predecessorHandoffIdentities': IDENTITIES, 'members': members, 'memberTreeSHA256': sha(stable(members)),
                   'reviewPassed': True, 'controlsRun': 137, 'controlsPassed': 137, 'earlierControlsReplayed': 74,
                   'additionalControls': 63, 'disposition': receipt['disposition'], 'selectedRunProvenanceImporterPresent': False,
                   'nativeExecuted': False, 'runtimeSelected': False, 'compileRerun': False, 'completeCaseSet': False,
                   'runPassed': False, 'gaAccepted': False, 'physicalPhones': 'disconnected-deferred'}
        path.write_bytes(stable(handoff))
    else:
        handoff = json.loads(path.read_bytes())
        assert handoff['members'] == members and handoff['memberTreeSHA256'] == sha(stable(members)), 'Review changed'
        assert handoff['predecessorHandoffIdentities'] == IDENTITIES
    print(json.dumps({'frozenReviewFilesVerified': True, 'handoffSHA256': row(path)['sha256'], 'members': len(members),
                      'reviewPassed': True, 'controlsRun': 137, 'controlsPassed': 137, 'nativeExecuted': False, 'runtimeSelected': False}, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['freeze', 'verify'])
    main(parser.parse_args().action)
