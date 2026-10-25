#!/usr/bin/env python3
"""Bind an unsuccessful independent review without promoting its scope."""
import datetime
import hashlib
import json
from pathlib import Path
import stat
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
REVIEW = ROOT / 'verification/apple-focus-reference-runtime-v2-independent-review'
IDENTITY = 'cf24502cf1201e22848628bf1e5254bb708b529006eb707c632b051e46ebb2f1'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    target = BASE / 'independent-decision.json'
    assert not target.exists(), 'Preserve prior decision'
    raw = (REVIEW / 'handoff.json').read_bytes()
    assert sha(raw) == IDENTITY
    handoff = json.loads(raw)
    stable = (json.dumps(handoff['members'], indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    assert sha(stable) == handoff['memberTreeSHA256']
    for name, row in handoff['members'].items():
        path = ROOT / name
        info = path.lstat()
        assert path.resolve() == path and stat.S_ISREG(info.st_mode) and info.st_nlink == 1, name
        assert {'kind': 'file', 'bytes': info.st_size, 'mode': stat.S_IMODE(info.st_mode), 'sha256': sha(path.read_bytes())} == row, name
    assert handoff['reviewedHandoffSHA256'] == sha((ROOT / 'verification/apple-focus-reference-runtime-v2/handoff.json').read_bytes())
    assert handoff['reviewedPacketSHA256'] == sha((ROOT / 'verification/apple-focus-reference-runtime-v2/packet.json').read_bytes())
    assert handoff['reviewReceiptSHA256'] == sha((REVIEW / 'attempt-2/receipt.json').read_bytes())
    assert (handoff['producerControlsPassed'], handoff['independentControls'], handoff['independentControlsPassed'], handoff['independentFailures'], handoff['independentErrors']) == (111, 33, 23, 10, 0)
    assert handoff['approvedForNativeDispatch'] is False and handoff['nativeExecuted'] is False
    assert handoff['allFrozenInputsUnchanged'] is True and handoff['frozenInputCount'] == 124
    result = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'command': [sys.executable, str(Path(__file__).relative_to(ROOT))], 'python': sys.version,
              'verifierSHA256': sha(Path(__file__).read_bytes()), 'reviewHandoffSHA256': IDENTITY,
              'status': 'v2-rejected-for-native-dispatch-versioned-repair-assigned',
              'reviewMembersVerified': len(handoff['members']), 'reviewerFrozenInputCount': 124,
              'producerControlsPassed': 111, 'independentControlsPassed': 23, 'independentControlsFailed': 10,
              'findings': handoff['findings'], 'cleanup': handoff['cleanup'],
              'rootImportedOrExecutedProducerOrReviewerCode': False,
              'nativeExecuted': False, 'runtimeSelected': False, 'runPassed': False, 'carrierAccepted': False, 'gaAccepted': False}
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['status', 'reviewMembersVerified', 'producerControlsPassed', 'independentControlsPassed', 'independentControlsFailed']}))


if __name__ == '__main__':
    main()
