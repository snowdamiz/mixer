#!/usr/bin/env python3
"""Reproduce this source/host-only independent review without native commands."""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import platform
import re
import struct
import subprocess
import sys
import tarfile
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = HERE.parent / 'apple-toggle-keyboard-focus-v3-preparation'
SEAL = '85534f657be3e1a0bda34fe830dc29636065eb602401b4386b3076c35a108c21'
SELECTION = ROOT / 'verification/apple-toggle-keyboard-focus-v3-root-review/selection.json'
SELECTION_SHA = '703d2c5db1e79b8eaf4b17fba95bd660de598cf575ed861b08b6c70115bdeb28'
EXPECTED_FINDINGS = [
    'test_CONTRACT_replay_rejects_regressing_host_receipt_time',
    'test_CONTRACT_wrong_route_search_cannot_satisfy_selected_route',
    'test_CONTRACT_wrong_target_poll_cannot_supply_enabled_window',
]


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
def read(path): return json.loads(path.read_bytes())
def require(condition, message):
    if not condition: raise ValueError(message)


def manifest_inputs():
    require(sha(PRODUCER / 'packet-seal.json') == SEAL, 'Pinned preparation seal changed')
    require(sha(SELECTION) == SELECTION_SHA, 'Pinned root selection changed')
    seal = read(PRODUCER / 'packet-seal.json')
    require(len(seal['files']) == 92, 'Selected seal no longer has 92 entries')
    for name, expected in seal['files'].items():
        path = ROOT / name
        require(path.is_file() and not path.is_symlink() and sha(path) == expected, 'Selected input differs: ' + name)
    for folder, count in [('apple-toggle-keyboard-focus', 81), ('apple-toggle-keyboard-focus-v2', 70)]:
        previous = read(HERE.parent / folder / 'packet-seal.json')
        require(len(previous['files']) == count, 'Previous seal count differs')
        for name, expected in previous['files'].items():
            path = ROOT / name
            require(path.is_file() and not path.is_symlink() and sha(path) == expected, 'Previous sealed input differs: ' + name)
    require(sha(PRODUCER / 'built-app.tar.gz') == 'b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393', 'Original app archive changed')
    for name in ['keyboard_oracle.py', 'built-app.tar.gz', 'source-lock.json']:
        require(sha(PRODUCER / name) == sha(HERE.parent / 'apple-toggle-keyboard-focus-v2' / name), 'V2 immutable byte reuse changed: ' + name)
    actual = {str(p.relative_to(PRODUCER / 'source')): sha(p) for p in sorted((PRODUCER / 'source').rglob('*')) if p.is_file()}
    require(actual == read(PRODUCER / 'source-lock.json')['sha256'], 'Original source map changed')
    require(hashlib.sha256(canonical(actual)).hexdigest() == 'f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46', 'Original source closure changed')
    return seal


def binary_version(data):
    if data[:4] in [b'\xca\xfe\xba\xbe', b'\xca\xfe\xba\xbf']:
        wide = data[:4] == b'\xca\xfe\xba\xbf'
        count = struct.unpack_from('>I', data, 4)[0]
        require(0 < count <= 16, 'Bounded fat Mach-O architectures')
        architectures = []
        for index in range(count):
            entry = struct.unpack_from('>IIQQII' if wide else '>IIIII', data, 8 + index * (32 if wide else 20))
            cpu, subtype, offset, length = entry[:4]
            require(offset + length <= len(data), 'Fat Mach-O slice bound')
            architectures.append((cpu, offset, length))
        selected = [item for item in architectures if item[0] == 0x100000c]
        require(len(selected) == 1, 'One arm64 Mach-O slice required')
        _, offset, length = selected[0]
        return {**binary_version(data[offset:offset + length]), 'fatArchitectures': len(architectures)}
    require(data[:4] == b'\xcf\xfa\xed\xfe', 'Expected thin little-endian arm64 Mach-O')
    magic, cpu, subtype, kind, count, size, flags, reserved = struct.unpack_from('<8I', data)
    require(cpu == 0x100000c, 'Expected arm64 CPU')
    offset = 32
    for _ in range(count):
        command, length = struct.unpack_from('<II', data, offset)
        require(length >= 8 and offset + length <= 32 + size, 'Malformed Mach-O load command')
        if command == 0x32:
            _, _, target, minimum, sdk, tools = struct.unpack_from('<6I', data, offset)
            version = lambda value: f'{value >> 16}.{(value >> 8) & 255}.{value & 255}'
            return {'platform': target, 'minimum': version(minimum), 'sdk': version(sdk), 'cpu': 'arm64'}
        offset += length
    raise ValueError('LC_BUILD_VERSION absent')


def runner_provenance():
    manifest = read(PRODUCER / 'build-products-manifest.json')
    receipt = read(PRODUCER / 'runner-binary-receipt.json')
    archive = PRODUCER / 'test-runner-products.tar.gz'
    require(sha(archive) == manifest['productArchiveSHA256'] == receipt['archiveSHA256'], 'Runner archive differs')
    require(hashlib.sha256(canonical(manifest['products'])).hexdigest() == manifest['productTreeSHA256'] == receipt['productTreeSHA256'], 'Runner tree binding differs')
    require(hashlib.sha256(canonical(manifest['sourceFiles'])).hexdigest() == manifest['sourceTreeSHA256'] == receipt['sourceTreeSHA256'], 'Runner source closure differs')
    require(all(sha(ROOT / name) == expected for name, expected in manifest['sourceFiles'].items()), 'Built runner source differs')
    binaries = {}
    with tarfile.open(archive, 'r:gz') as tar:
        members = tar.getmembers()
        require({item.name for item in members} == set(manifest['products']) and len(members) == len(manifest['products']), 'Archive entry set differs')
        for item in members:
            expected = manifest['products'][item.name]
            require(not pathlib.PurePosixPath(item.name).is_absolute() and '..' not in pathlib.PurePosixPath(item.name).parts, 'Unsafe archive entry')
            require(item.mode == int(expected['mode'], 8), 'Archive mode differs')
            if expected['kind'] == 'directory':
                require(item.isdir(), 'Expected regular directory')
                continue
            require(item.isfile() and item.size == expected['bytes'], 'Expected regular bound file')
            data = tar.extractfile(item).read()
            require(hashlib.sha256(data).hexdigest() == expected['sha256'], 'Archive payload differs')
            if item.name in receipt['binaries']:
                require(hashlib.sha256(data).hexdigest() == receipt['binaries'][item.name]['sha256'], 'Binary provenance differs')
                binaries[item.name] = binary_version(data)
    require(len(binaries) == 2 and all(v['platform'] == 7 for v in binaries.values()), 'Expected two simulator-only binaries')
    return {'sourceTreeSHA256': manifest['sourceTreeSHA256'], 'productTreeSHA256': manifest['productTreeSHA256'], 'archiveSHA256': sha(archive), 'archiveEntries': len(members), 'independentlyParsedMachO': binaries, 'recordedBuildToolVersions': manifest['versions'], 'recompiled': False}


def command(argv):
    before = time.monotonic()
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=60, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    count = re.search(r'Ran (\d+) tests? in ', result.stderr)
    failures = sorted(set(re.findall(r'^FAIL: (test_\w+)', result.stderr, re.MULTILINE)))
    return {'argv': argv, 'cwd': str(ROOT), 'exitCode': result.returncode, 'elapsedSeconds': time.monotonic() - before, 'testsRun': int(count.group(1)) if count else None, 'failingMethods': failures, 'stdout': result.stdout, 'stderr': result.stderr}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--check', action='store_true'); args = parser.parse_args()
    if not args.check:
        require(not (HERE / 'review-seal.json').exists(), 'Independent review is sealed; use --check for read-only reproduction')
    seal = manifest_inputs()
    bound_before = {name: sha(ROOT / name) for name in seal['files']}
    binaries = runner_provenance()
    commands = [
        command([sys.executable, '-B', str(PRODUCER / 'run.py'), 'verify']),
        command([sys.executable, '-B', str(HERE / 'execute_producer_controls.py')]),
        command([sys.executable, '-B', str(HERE.parent / 'apple-toggle-keyboard-focus-v2/test_keyboard.py')]),
        command([sys.executable, '-B', str(HERE / 'test_independent.py')]),
        command([sys.executable, '-B', str(HERE / 'test_independent.py'), '--witnesses']),
    ]
    require(commands[0]['exitCode'] == 0, 'Producer read-only preflight failed')
    require(commands[1]['exitCode'] == 0 and commands[1]['testsRun'] == 44, 'Sealed 44 controls failed')
    require(commands[2]['exitCode'] == 0 and commands[2]['testsRun'] == 29, 'Unchanged 29 V2 controls failed')
    require(commands[3]['exitCode'] == 1 and commands[3]['testsRun'] == 17 and commands[3]['failingMethods'] == EXPECTED_FINDINGS, 'Independent outcome differs; inspect raw output')
    require(commands[4]['exitCode'] == 0, 'Independent witness capture failed')
    witnesses = json.loads(commands[4]['stdout'])
    require(bound_before == {name: sha(ROOT / name) for name in seal['files']}, 'Review changed selected sealed inputs')
    scratch = HERE / '.scratch'
    if scratch.is_dir():
        require(not list(scratch.iterdir()), 'Host test scratch cleanup incomplete')
        scratch.rmdir()
    receipt = {'schema': 'mixer.apple-toggle.keyboard-v3-independent-source-host-review.1', 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': 'CHANGES_REQUIRED_DIAGNOSTIC_CONTRACT', 'scope': 'Independent source/host review only; no native authorization or acceptance', 'sourceRevisionContext': read(SELECTION)['sourceRevisionContext'], 'revisionSource': 'Pinned selection context; no Git operation performed', 'preparationSealSHA256': SEAL, 'selectionSHA256': SELECTION_SHA, 'boundFilesVerifiedBeforeAndAfter': len(bound_before), 'priorSealEntriesVerified': {'originalKeyboard': 81, 'v2Keyboard': 70}, 'boundInputTreeSHA256': hashlib.sha256(canonical(bound_before)).hexdigest(), 'versions': {'python': sys.version, 'executable': sys.executable, 'host': platform.platform()}, 'runnerBuildProvenance': binaries, 'commands': commands, 'independentTests': {'methods': 17, 'contractFindingMethods': 3, 'passingMethods': 14, 'failingMethods': EXPECTED_FINDINGS, 'wrongPollSubcases': 3, 'unittestFailureRecords': 5}, 'producerTestsPassed': 44, 'unchangedV2TestsPassed': 29, 'cleanup': {'hostScratchAbsent': not scratch.exists(), 'nativeResourcesCreated': 0, 'otherProjectProcessesTouched': False}, 'nativeExecuted': False, 'compiled': False, 'computerUseOrScreenCapture': False, 'physicalDevicesQueried': False, 'gitQueriedOrChanged': False, 'nativeKeyboardQualification': False, 'carrierAccepted': False, 'gaAccepted': False}
    if args.check:
        review_seal = read(HERE / 'review-seal.json')
        for name, expected in review_seal['files'].items():
            require(sha(ROOT / name) == expected, 'Independent review file changed: ' + name)
        print(json.dumps({'status': receipt['status'], 'reproducedExpectedFindings': commands[3]['failingMethods'], 'producerControlsPassed': 44, 'unchangedV2ControlsPassed': 29, 'independentMethodsRun': 17, 'sealedFilesVerified': len(review_seal['files']), 'nativeExecuted': False}, sort_keys=True))
    else:
        (HERE / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
        (HERE / 'finding-witnesses.json').write_text(json.dumps(witnesses, indent=2, sort_keys=True) + '\n')
        print(json.dumps({key: receipt[key] for key in ['status', 'preparationSealSHA256', 'boundFilesVerifiedBeforeAndAfter', 'producerTestsPassed', 'unchangedV2TestsPassed', 'independentTests', 'nativeExecuted']}, sort_keys=True))


if __name__ == '__main__': main()
