#!/usr/bin/env python3
"""Compact derivative handoff; historical packets remain hash-bound references."""
import argparse
import datetime
import json
from pathlib import Path
import sys
import prepare as p


def members():
    rows = {str((p.ROOT / 'docs/apple-focus-reference-runtime-v5-namespace-correction.md').relative_to(p.ROOT)):
            p.row(p.ROOT / 'docs/apple-focus-reference-runtime-v5-namespace-correction.md')}
    for path in sorted(p.BASE.rglob('*')):
        if path.is_file() and path.name != 'handoff.json':
            rows[str(path.relative_to(p.ROOT))] = p.row(path)
    return rows


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['freeze', 'verify']); args = parser.parse_args()
    verified = p.verify()
    path = p.BASE / 'handoff.json'
    if args.action == 'freeze':
        p.require(not path.exists(), 'Preserve previous frozen correction handoff')
        attempts = sorted(p.BASE.glob('attempt-*/receipt.json'))
        p.require(bool(attempts), 'Finite correction controls required')
        receipt = json.loads(attempts[-1].read_bytes())
        p.require(receipt['controlsPassed'] and all(receipt['cleanup'][name] for name in
                  ['ownedControlsScratchAbsent', 'ownedSyntheticNativeRunAbsent', 'productInputScratchAbsent']), 'Controls/cleanup incomplete')
        rows = members()
        handoff = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   'command': [sys.executable, '-B', str(p.BASE / 'freeze.py'), 'freeze'], 'python': sys.version,
                   'pythonExecutable': str(Path(sys.executable).resolve()),
                   'scope': 'V5-001 prefix correction only; independent root review and fresh selection pending',
                   'packetSHA256': verified['packetSHA256'], 'originalV5PacketSHA256': p.ORIGINAL_PACKET,
                   'originalV5HandoffSHA256': p.HANDOFF, 'independentV5HandoffSHA256': p.REVIEW_HANDOFF,
                   'memberTreeSHA256': p.sha(p.stable(rows)), 'members': rows,
                   'controlsReceipt': str(attempts[-1].relative_to(p.ROOT)), 'controlsReceiptSHA256': p.row(attempts[-1])['sha256'],
                   'testsRun': receipt['testsRun'], 'testsPassed': receipt['testsPassed'],
                   'cleanup': receipt['cleanup'], 'nativeExecuted': False, 'runtimeSelected': False,
                   'independentRootReviewPending': True, 'freshRootSelectionRequired': True,
                   'gaAccepted': False, 'physicalPhones': 'disconnected-deferred'}
        with path.open('xb') as stream:
            stream.write(p.stable(handoff))
    else:
        handoff = json.loads(path.read_bytes())
        p.require(members() == handoff['members'], 'Frozen correction members changed')
        p.require(p.sha(p.stable(handoff['members'])) == handoff['memberTreeSHA256'], 'Frozen correction tree digest differs')
    print(json.dumps({'handoffSHA256': p.row(path)['sha256'], 'membersVerified': len(handoff['members']),
                      'packetSHA256': verified['packetSHA256'], 'nativeExecuted': False}, sort_keys=True))


if __name__ == '__main__':
    main()
