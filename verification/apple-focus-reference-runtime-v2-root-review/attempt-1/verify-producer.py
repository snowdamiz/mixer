#!/usr/bin/env python3
"""Data-only binding of frozen preparation; no native or producer code runs."""
import datetime
import hashlib
import json
from pathlib import Path
import stat
import sys
import tarfile

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PRODUCER = ROOT / 'verification/apple-focus-reference-runtime-v2'
HANDOFF = '78ada9ff4aa3392e07f4fdf71a0eb563c67c8fde920388609372b09a771f3668'
PACKET = '8a6be8d06285c3fd25bdb9bc2c589ea87a7677d8a6b9b6e0545b23076cd6a7b6'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def stable(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def require(value, message):
    if not value:
        raise ValueError(message)


def verify(path, expected):
    info = path.lstat()
    require(path.resolve() == path and stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'Noncanonical input: ' + str(path))
    actual = {'kind': 'file', 'bytes': info.st_size, 'mode': stat.S_IMODE(info.st_mode), 'sha256': sha(path.read_bytes())}
    require(actual == expected, 'Changed input: ' + str(path))


def main():
    output = BASE / 'producer-binding.json'
    require(not output.exists(), 'Preserve prior binding')
    handoff_raw = (PRODUCER / 'handoff.json').read_bytes()
    require(sha(handoff_raw) == HANDOFF, 'Changed handoff')
    handoff = json.loads(handoff_raw)
    require(sha(stable(handoff['members'])) == handoff['memberTreeSHA256'], 'Changed handoff member tree')
    for relative, row in handoff['members'].items():
        verify(ROOT / relative, row)
    raw = (PRODUCER / 'packet.json').read_bytes()
    require(sha(raw) == PACKET == handoff['packetSHA256'], 'Changed packet')
    packet = json.loads(raw)
    inputs = json.loads((PRODUCER / 'input-lock.json').read_bytes())
    for relative, row in inputs.items():
        verify(ROOT / relative, row)
    host = json.loads((PRODUCER / 'host-attempt-7/receipt.json').read_bytes())
    require(host['passed'] is True and (host['testsRun'], host['failures'], host['errors'], host['skipped']) == (111, 0, 0, 0), 'Host controls failed')
    require(host['inputBindings'] == inputs and host['ownedSources'] == packet['ownedSources'], 'Host source closure differs')
    require(sha(stable(inputs)) == host['inputTreeSHA256'], 'Host input tree mismatch')
    for name, row in host['outputs'].items():
        verify(PRODUCER / 'host-attempt-7' / name, row)
    manifest = json.loads((PRODUCER / 'runtime-source-manifest.json').read_bytes())
    require(sha(stable(manifest['files'])) == manifest['treeSHA256'], 'Runtime source tree differs')
    with tarfile.open(PRODUCER / 'runtime-sources.tar.gz', 'r:gz') as archive:
        members = archive.getmembers()
        files = {m.name: m for m in members if m.isfile()}
        directories = {m.name.rstrip('/') for m in members if m.isdir()}
        require(len(files) + len(directories) == len(members), 'Nonregular or duplicate archive member')
        require(set(files) == set(manifest['files']) and directories == set(manifest['directories']), 'Runtime archive inventory differs')
        for name, member in files.items():
            data = archive.extractfile(member).read()
            row = manifest['files'][name]
            require(sha(data) == row['sha256'] and len(data) == row['bytes'] and member.mode == row['mode'], 'Runtime archived source differs')
        require(all(m.mode == manifest['directoryMode'] for m in members if m.isdir()), 'Runtime archive directory mode differs')
    for flag in ['nativeExecuted', 'runtimeSelected', 'compileRerun', 'runPassed', 'completeCaseSet', 'cursorCompletionCredit', 'fullSixCaseQualification', 'nativeKeyboardQualification', 'carrierAccepted', 'gaAccepted']:
        require(packet[flag] is False and handoff[flag] is False, 'Preparation scope changed: ' + flag)
    require(handoff['cleanup']['remainingOwnedScratch'] == [] and handoff['cleanup']['ownedHostTemporaryDirectoriesAbsent'] is True, 'Owned scratch remains')
    result = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'command': [sys.executable, str(Path(__file__).relative_to(ROOT))], 'python': sys.version,
              'verifierSHA256': sha(Path(__file__).read_bytes()), 'handoffSHA256': HANDOFF, 'packetSHA256': PACKET,
              'status': 'producer-preparation-bound-independent-review-pending',
              'handoffMembersVerified': len(handoff['members']), 'lockedInputsVerified': len(inputs),
              'runtimeSourceArchiveMembersVerified': len(members), 'hostControlsPassed': 111,
              'sourceTreeSHA256': packet['sourceTreeSHA256'], 'productArchiveSHA256': packet['productArchiveSHA256'],
              'rootImportedOrExecutedProducerCode': False, 'nativeExecuted': False, 'runtimeSelected': False,
              'runPassed': False, 'carrierAccepted': False, 'gaAccepted': False,
              'limitations': ['Independent importer/driver review pending.', 'No simulator creation or selected-run approval.', 'Retained compilation only; no new native evidence.']}
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ['status', 'handoffMembersVerified', 'lockedInputsVerified', 'runtimeSourceArchiveMembersVerified', 'hostControlsPassed']}))


if __name__ == '__main__':
    main()
