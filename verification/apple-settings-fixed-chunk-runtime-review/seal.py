#!/usr/bin/env python3
"""Seal/read-only reverify independent review and all exact accepted inputs."""
import datetime
import hashlib
import json
from pathlib import Path
import stat
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]


def stable(value): return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
def sha(raw): return hashlib.sha256(raw).hexdigest()
def require(value, message):
    if not value: raise ValueError(message)


def row(path):
    info = path.lstat()
    require(path.resolve() == path and stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'Canonical regular file required')
    raw = path.read_bytes()
    return {'kind': 'file', 'mode': stat.S_IMODE(info.st_mode), 'bytes': len(raw), 'sha256': sha(raw)}


def inventory():
    result = {}
    for path in [*sorted(BASE.rglob('*')), ROOT / 'docs/apple-settings-fixed-chunk-runtime-review.md']:
        if path in {BASE / 'handoff.json', BASE / 'handoff.sha256'}: continue
        if any(path.is_relative_to(BASE / name) for name in ['commands/seal', 'commands/verify']): continue
        if not path.is_file(): continue
        require(not any(part.startswith(('review-owned-', 'host-fixture')) for part in path.parts), 'Owned scratch remains')
        result[str(path.relative_to(ROOT))] = row(path)
    return result


def verify_inputs():
    source = json.loads((BASE / 'attempt-2/source-verification.json').read_bytes())
    require(source['passed'] is True and source['handoffMembers'] == 66 and source['acceptedReferences'] == 116, 'Source review incomplete')
    for name, expected in source['inputs'].items():
        require(not any(word in name.lower() for word in ['catalog-inspector', 'authority-driver', 'worker-transport']), 'Excluded input')
        require(row(ROOT / name) == expected, 'Accepted input changed: ' + name)
    producer = ROOT / 'verification/apple-settings-fixed-chunk-runtime-preparation'
    require(sha((producer / 'handoff.json').read_bytes()) == 'bcb2b7135eaa594b6a6ac0a84866cf0877ec1a3cb0264b1a51fcc33afd0860b2', 'Producer handoff differs')
    require(sha((producer / 'packet.json').read_bytes()) == '2a1804ce1a6ece3b7b2125f4aa677e40c54f31846d94f3fec13e1f74d786eed7', 'Producer packet differs')
    controls = json.loads((BASE / 'attempt-2/host-attempt/receipt.json').read_bytes())
    require(controls['passed'] and controls['testsRun'] == 16 and controls['failures'] == controls['errors'] == controls['skipped'] == 0,
            'Final controls incomplete')
    require(controls['acceptedInputsAndPacketUnchanged'] and controls['ownedScratchAbsent'] and controls['hostFixtureRemoved'], 'Input/scratch invariants differ')
    command = json.loads((BASE / 'commands/attempt-2/receipt.json').read_bytes())
    require(command['exitCode'] == 0 and command['timedOut'] is False and command['signals'] == []
            and command['ownedProcessGroup']['state'] == 'absent', 'Terminal command outcome differs')
    for name in ['stdout', 'stderr']:
        raw = (BASE / 'commands/attempt-2' / (name + '.log')).read_bytes()
        require(command['streams'][name] == {'bytes': len(raw), 'sha256': sha(raw), 'eof': True, 'readerFailed': False}, 'Stream binding differs')
    require(command['sourceSHA256'] == sha((BASE / 'attempt-2/review-source.py').read_bytes()) == sha((BASE / 'review.py').read_bytes()),
            'Executed review source differs')
    decision = json.loads((BASE / 'review.json').read_bytes())
    require(decision['status'] == 'source-and-host-packaging-accepted' and decision['blockingFindings'] == []
            and decision['nativeSelected'] is False and decision['nativeExecuted'] is False, 'Scoped decision differs')
    return decision


def main():
    action = sys.argv[1]
    require(action in {'seal', 'verify'}, 'Expected seal/verify')
    decision = verify_inputs()
    if action == 'seal':
        require(not (BASE / 'handoff.json').exists(), 'Preserve handoff')
        members = inventory()
        handoff = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'status': decision['status'], 'packetSHA256': decision['packetSHA256'],
            'producerHandoffSHA256': decision['producerHandoffSHA256'], 'members': members,
            'memberTreeSHA256': sha(stable(members)), 'nativeSelected': False, 'nativeExecuted': False,
            'physicalPhones': 'disconnected-deferred', 'gaAccepted': False}
        (BASE / 'handoff.json').write_bytes(stable(handoff))
        (BASE / 'handoff.sha256').write_text(sha(stable(handoff)) + '  handoff.json\n')
    else:
        handoff = json.loads((BASE / 'handoff.json').read_bytes())
        require(handoff['members'] == inventory() and handoff['memberTreeSHA256'] == sha(stable(handoff['members'])), 'Sealed inventory changed')
        require(handoff['packetSHA256'] == decision['packetSHA256'], 'Sealed packet differs')
    print(json.dumps({'passed': True, 'handoffSHA256': sha((BASE / 'handoff.json').read_bytes()),
        'members': len(handoff['members']), 'packetSHA256': decision['packetSHA256'], 'nativeSelected': False, 'nativeExecuted': False}, sort_keys=True))


if __name__ == '__main__': main()
