#!/usr/bin/env python3
"""Compact immutable handoff; verification never imports the selected composition."""
import argparse
import datetime
import json
from pathlib import Path
import prepare as p


def inventory():
    result = {}
    roots = [p.BASE, p.ROOT / 'docs/apple-focus-system-runtime-preparation.md']
    for root in roots:
        paths = sorted(root.rglob('*')) if root.is_dir() else [root]
        for path in paths:
            if path.is_file() and path not in {p.BASE / 'handoff.json', p.BASE / 'handoff.sha256'}:
                # The handoff command is written after the seal exists; its
                # actual terminal receipt is separately retained, never circular.
                if any(path.is_relative_to(p.BASE / name) for name in ['commands/seal', 'commands/verify']):
                    continue
                p.require(not any(part.startswith(('prepare-owned-', 'controls-owned-')) for part in path.parts),
                          'Owned scratch remains')
                result[str(path.relative_to(p.ROOT))] = p.row(path)
    return result


def main(action):
    verified = p.verify()
    path = p.BASE / 'handoff.json'
    if action == 'seal':
        p.require(not path.exists(), 'Preserve prior handoff')
        members = inventory()
        handoff = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   'status': 'prepared-host-controls-only-awaiting-independent-review',
                   'packetSHA256': verified['packetSHA256'], 'members': members,
                   'memberTreeSHA256': p.sha(p.stable(members)), 'nativeExecuted': False,
                   'nativeSelected': False, 'physicalPhones': 'disconnected-deferred', 'gaAccepted': False}
        path.write_bytes(p.stable(handoff))
        (p.BASE / 'handoff.sha256').write_text(p.sha(path.read_bytes()) + '  handoff.json\n')
    else:
        handoff = json.loads(path.read_bytes())
        p.require(p.sha(p.stable(handoff['members'])) == handoff['memberTreeSHA256'], 'Handoff member tree differs')
        p.require(inventory() == handoff['members'], 'Handoff inventory differs')
        p.require(handoff['packetSHA256'] == verified['packetSHA256'], 'Sealed packet differs')
    print(json.dumps({'handoffSHA256': p.sha(path.read_bytes()), 'members': len(handoff['members']),
                      'packetSHA256': verified['packetSHA256'], 'nativeExecuted': False}, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['seal', 'verify'])
    main(parser.parse_args().action)
