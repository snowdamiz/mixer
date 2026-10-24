#!/usr/bin/env python3
"""Read-only host packet check; future root-owned runtime-N outputs are outside its membership."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    packet_path = HERE / 'packet-seal.json'
    packet = json.loads(packet_path.read_text())
    if packet['schema'] != 1 or packet['scope'] != 'frozen-host-runner-cleanup-only':
        raise ValueError('unsupported packet contract')
    expected = packet['files']
    observed = set()
    for relative in packet['membershipRoots']:
        path = ROOT / relative
        members = path.rglob('*') if path.is_dir() else [path]
        for member in members:
            if member.is_symlink():
                raise ValueError('symlink in frozen host packet ' + str(member))
            if member.is_file():
                observed.add(str(member.relative_to(ROOT)))
    if observed != set(expected):
        raise ValueError('frozen host packet membership changed')
    for relative, identity in expected.items():
        path = Path(relative)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('unexpected packet path')
        if not (relative == 'docs/android-coordinator-runner-cleanup.md'
                or relative.startswith('verification/android-coordinator-runner-cleanup/')):
            raise ValueError('path outside owned host packet')
        actual = ROOT / relative
        if actual.resolve() != actual or not actual.is_file():
            raise ValueError('unexpected actual packet path ' + relative)
        if actual.stat().st_size != identity['bytes'] or sha(actual) != identity['sha256']:
            raise ValueError('host packet bytes changed ' + relative)
    receipt = json.loads((HERE / 'host-review-1/receipt.json').read_text())
    if (receipt['status'] != 'passed-host-cleanup-and-preserved-guards-only'
            or receipt['hostExtractionTestsPassed'] != 20 or receipt['preservedRunnerGuardTestsPassed'] != 4
            or receipt['nativeRuntime'] != 'NOT RUN' or receipt['nativeInstancesStarted'] != 0
            or not receipt['sourceUnchanged'] or not receipt['allOwnedExtractionsAbsent']):
        raise ValueError('host receipt is not the expected scoped pass')
    built = ROOT / 'verification/android-coordinator-join/candidate-2'
    for relative, expected_hash in packet['frozenCandidate2Bindings'].items():
        if sha(built / relative) != expected_hash:
            raise ValueError('frozen candidate2 binding changed ' + relative)
    source_files = json.loads((built / 'source-lock.json').read_text())['files']
    source_closure = hashlib.sha256(json.dumps(source_files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if len(source_files) != 105 or source_closure != packet['frozenSourceClosureSHA256']:
        raise ValueError('frozen source closure changed')
    for relative, expected_hash in source_files.items():
        for path in [built / 'inputs' / relative, ROOT / relative]:
            if sha(path) != expected_hash:
                raise ValueError('frozen or live source changed ' + str(path))
    original = ROOT / 'verification/android-coordinator-join/run.py'
    if sha(original) != packet['originalFrozenRunnerSHA256']:
        raise ValueError('original runner changed')
    print(json.dumps({'status': 'passed-frozen-host-packet-check-only', 'packetSHA256': sha(packet_path),
        'sealedFiles': len(expected), 'correctedRunnerSHA256': sha(HERE / 'run.py'),
        'frozenCandidateInputs': 105, 'hostTestsPassed': 24, 'nativeRuntimeByThisPacket': 'NOT RUN',
        'runtimeOutputsInHostPacket': False, 'nativeCommandOrTargetDiscovery': False}, sort_keys=True))


if __name__ == '__main__':
    main()
