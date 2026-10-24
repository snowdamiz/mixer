#!/usr/bin/env python3
"""Read-only Apple compile evidence and Mach-O replay; no compiler/native calls."""
import argparse
import datetime
import hashlib
import io
import json
from pathlib import Path
import platform
import re
import struct
import subprocess
import sys
import tarfile
import traceback

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
APPLE = ROOT / 'verification/apple-native-appearance-v2'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def macho(data):
    assert len(data) >= 32
    magic, cpu, subtype, filetype, count, command_bytes, flags, reserved = struct.unpack_from('<8I', data)
    assert magic == 0xfeedfacf and cpu == 0x100000c
    assert 32 + command_bytes <= len(data)
    position = 32
    builds, libraries, identities = [], [], []
    for _ in range(count):
        command, size = struct.unpack_from('<II', data, position)
        assert size >= 8 and size % 8 == 0 and position + size <= 32 + command_bytes
        if command == 0x32:
            assert size >= 24
            target, minimum, sdk, tools = struct.unpack_from('<IIII', data, position + 8)
            builds.append({'platform': target, 'minimumOS': minimum, 'sdk': sdk})
        if command in {0xc, 0xd, 0x80000018, 0x8000001f, 0x80000023}:
            assert size >= 24
            offset = struct.unpack_from('<I', data, position + 8)[0]
            assert 24 <= offset < size
            name = data[position + offset:position + size].split(b'\0', 1)[0].decode()
            (identities if command == 0xd else libraries).append(name)
        position += size
    assert position == 32 + command_bytes
    return {'cpu': 'arm64', 'cpuSubtype': subtype, 'fileType': filetype,
            'buildVersions': builds, 'loadLibraries': libraries, 'installNames': identities}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'headless-cover-(?:baselines|final-coordinates)(?:-[0-9]+)?', args.candidate)
    assert re.fullmatch(r'apple-headless-review-[0-9]+', args.output)
    out = BASE / args.output
    out.mkdir()
    checks, reads, summary, warnings = [], {}, {}, []

    def read(path):
        data = path.read_bytes()
        reads[str(path.relative_to(ROOT))] = sha(data)
        return data

    def obj(path):
        return json.loads(read(path))

    def check(condition, name):
        assert condition, name
        checks.append(name)

    status, error = 'failed', None
    try:
        candidate = APPLE / args.candidate
        lock = obj(candidate / 'source-lock.json')
        result = obj(candidate / 'result.json')
        integrity = obj(candidate / 'integrity.json')
        manifest = lock['sha256']
        closure = sha(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode())
        check(len(manifest) == integrity['sourceCount'] == 36, 'bounded-source-count')
        check(closure == result['sourceClosureSHA256'] == integrity['sourceClosureSHA256'], 'source-closure-digest')
        check(integrity['sourceLockSHA256'] == sha(read(candidate / 'source-lock.json')), 'producer-source-lock-hash')
        check(integrity['commandsSHA256'] == sha(read(candidate / 'commands.json')), 'producer-command-hash')
        check(integrity['resultSHA256'] == sha(read(candidate / 'result.json')), 'producer-result-hash')
        check(integrity['liveSourceClosureMatched'] and integrity['artifactArchiveMatched'], 'producer-integrity-status')
        check(result['productCompiled'] and result['harnessCompiled'], 'compile-status')
        check(result['target'] == 'arm64-apple-ios17.0-simulator', 'declared-compile-target')
        check(not result['nativeExecuted'] and not result['guiExecuted'] and not result['visualQualified'], 'native-boundary-explicit')
        for name, expected in manifest.items():
            path = ROOT / name
            check(path.resolve().is_relative_to(ROOT) and not path.is_symlink(), 'bounded-source:' + name)
            data = read(path)
            check(sha(data) == expected, 'current-source:' + name)
            capture = out / 'inputs' / name
            capture.parent.mkdir(parents=True, exist_ok=True)
            capture.write_bytes(data)
            check(sha(capture.read_bytes()) == expected, 'reviewer-captured-source:' + name)
        source_archive = obj(candidate / 'source-archive.json')
        check(source_archive['files'] == manifest, 'complete-source-archive-file-set')
        source_tar = candidate / source_archive['archive']
        check(source_tar.parent == candidate and sha(read(source_tar)) == source_archive['sha256']
              == integrity['sourceArchiveSHA256'], 'source-archive-digest')
        with tarfile.open(fileobj=io.BytesIO(read(source_tar)), mode='r:*') as package:
            source_members = package.getmembers()
            check(len(source_members) == len(manifest), 'source-archive-member-count')
            check({item.name for item in source_members} == set(manifest), 'source-archive-member-names')
            for member in source_members:
                check(member.isfile() and sha(package.extractfile(member).read()) == manifest[member.name],
                      'captured-producer-source:' + member.name)
        for name, expected in integrity['toolingSHA256'].items():
            check(Path(name).name == name and sha(read(candidate / name)) == expected, 'producer-tooling:' + name)
        commands = obj(candidate / 'commands.json')
        modules = obj(candidate / 'module-build-commands.json')
        deployment = obj(candidate / 'deployment-targets.json')
        swift_commands, simulator_compiles, host_compiles = [], [], []
        for index, command in enumerate(commands + modules):
            check(command['exitCode'] == 0, 'command-success:' + str(index))
            argv = command['argv']
            allowed = (argv[:2] in [['xcodebuild', '-version'], ['xcrun', 'swiftc'], ['xcrun', 'vtool'],
                                   ['xcrun', '--sdk'], ['git', 'rev-parse']]
                       or argv in [['python3', 'native/apple/appearance-v2/build-check.py'], ['python3', '--version']]
                       or Path(argv[0]).name == 'cover-geometry-definitions')
            check(allowed, 'headless-command-kind:' + str(index))
            if command['stderr']:
                warnings.append({'argv': argv, 'stderr': command['stderr']})
            if argv[:2] == ['xcrun', 'swiftc'] and '-o' in argv:
                swift_commands.append(command)
                if '-target' in argv:
                    simulator_compiles.append(command)
                    check(argv[argv.index('-target') + 1] == result['target'], 'swift-target:' + str(index))
                    check(argv[argv.index('-sdk') + 1].endswith('/iPhoneSimulator27.1.sdk'), 'swift-sdk:' + str(index))
                else:
                    host_compiles.append(command)
                    check(argv[argv.index('-o') + 1].startswith('/tmp/mixer-native-appearance-v2-cover-final-host/'),
                          'bounded-pure-host-output:' + str(index))
        check(len(simulator_compiles) == 4 and len(host_compiles) == 3, 'separate-product-and-pure-host-compiles')
        compiled_sources = set()
        for command in swift_commands:
            for item in command['argv']:
                if item.endswith('.swift'):
                    path = Path(item)
                    if not path.is_absolute():
                        path = ROOT / path
                    name = str(path.relative_to(ROOT))
                    check(name in manifest, 'compiled-source-in-lock:' + name)
                    compiled_sources.add(name)
        supporting = {'native/apple/appearance-v2/Info.plist', 'native/apple/appearance-v2/build-check.py',
                      'native/apple/appearance-v2/default-descriptor.swift', 'native/apple/appearance-v2/run.py'}
        check(compiled_sources == set(manifest) - supporting, 'exact-compiled-swift-source-set')
        artifacts = obj(candidate / 'artifact-manifest.json')
        check(artifacts['files'] == result['artifacts'], 'result-and-archive-file-metadata')
        check(artifacts['files'] == obj(candidate / 'artifact-members.json'), 'artifact-member-manifest')
        archive = candidate / artifacts['archive']
        check(archive.parent == candidate and sha(read(archive)) == artifacts['sha256'], 'compiled-archive-digest')
        members = {}
        with tarfile.open(fileobj=io.BytesIO(read(archive)), mode='r:*') as package:
            for member in package.getmembers():
                check(member.isfile() and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts,
                      'plain-native-archive-member:' + member.name)
                check(member.name not in members, 'unique-native-archive-member:' + member.name)
                members[member.name] = package.extractfile(member).read()
        simulator_names = {'headless-cover-final-harness', 'libMixerCore.dylib', 'libMixerUI.dylib', 'libMixerAppearanceInternal.dylib'}
        expected_names = simulator_names | {'host/cover-geometry-definitions', 'host/libMixerCore.dylib', 'host/libMixerUI.dylib'}
        check(set(members) == set(artifacts['files']) == expected_names, 'exact-four-simulator-and-three-host-artifacts')
        binaries = {}
        for name, metadata in artifacts['files'].items():
            data = members[name]
            check(sha(data) == metadata['sha256'] and len(data) == metadata['bytes'], 'native-artifact-digest:' + name)
            parsed = macho(data)
            executable = name in {'headless-cover-final-harness', 'host/cover-geometry-definitions'}
            check(parsed['fileType'] == (2 if executable else 6), 'native-file-type:' + name)
            check(len(parsed['buildVersions']) == 1, 'one-actual-binary-platform:' + name)
            if name in simulator_names:
                check(parsed['buildVersions'][0]['platform'] == 7 and parsed['buildVersions'][0]['minimumOS'] == 17 << 16,
                      'actual-binary-simulator-minimum17:' + name)
            else:
                check(parsed['buildVersions'][0]['platform'] == 1, 'pure-host-macos-artifact:' + name)
            if not executable:
                check(parsed['installNames'] == ['@rpath/' + Path(name).name], 'dylib-install-name:' + name)
            binaries[name] = parsed
        check({'@rpath/libMixerCore.dylib', '@rpath/libMixerUI.dylib', '@rpath/libMixerAppearanceInternal.dylib'}
              <= set(binaries['headless-cover-final-harness']['loadLibraries']), 'harness-loads-actual-three-modules')
        check(set(deployment) == simulator_names, 'all-four-retained-vtool-targets')
        for name, value in deployment.items():
            check('platform IOSSIMULATOR' in value and 'minos 17.0' in value, 'retained-vtool-target:' + name)
        host = obj(candidate / 'host-pure-result.json')
        check(sha(read(candidate / 'host-pure-result.json')) == integrity['hostPureResultSHA256'], 'host-pure-result-integrity')
        check(host['executable'] == artifacts['files']['host/cover-geometry-definitions'], 'host-results-bind-actual-executable')
        check(host['exitCode'] == 0 and host['passed'] and host['hostPureExecuted'] and result['hostPureExecuted'], 'pure-host-result-pass')
        check(not host['nativeExecuted'] and not host['guiExecuted'] and not host['visualQualified'], 'pure-host-not-native-qualification')
        check(host['sourceClosureSHA256'] == closure, 'host-results-bind-source-closure')
        expected_outcomes = {'logical-touch-is-empty-before-snap', 'final-row-overlap-exact-19-over64',
                             'same-helper-rejects-final-cover-overlap', 'disjoint-final-foreground-admitted',
                             'logical-carrier-fit-before-snap', 'same-helper-rejects-final-carrier-spill',
                             'actual-group-bounds-required-besides-mask', 'nested-parent-scroll-alias-final-edges'}
        check(len(host['outcomes']) == 8 and all(item['passed'] for item in host['outcomes'])
              and {item['name'] for item in host['outcomes']} == expected_outcomes, 'eight-production-helper-outcomes')
        check(obj(candidate / 'host-pure-stdout.json') == host['outcomes'], 'raw-host-output-binds-outcomes')
        check(read(candidate / 'host-pure-stderr.txt') == b'', 'pure-host-no-stderr')
        historical = APPLE / 'headless-cover-baselines'
        historical_lock = obj(historical / 'source-lock.json')
        historical_result = obj(historical / 'result.json')
        historical_artifacts = obj(historical / 'artifact-manifest.json')
        historical_archive = historical / historical_artifacts['archive']
        check(sha(read(historical_archive)) == historical_artifacts['sha256'], 'historical-compile-archive-digest')
        with tarfile.open(fileobj=io.BytesIO(read(historical_archive)), mode='r:*') as package:
            for member in package.getmembers():
                data = package.extractfile(member).read()
                metadata = historical_artifacts['files'][member.name]
                check(sha(data) == metadata['sha256'] and len(data) == metadata['bytes'], 'historical-compile-member:' + member.name)
        derivation = obj(BASE / 'cover-snap-counterexample-1/derivation.json')
        check(derivation['overlapExact'] == '19/64', 'independent-snap-counterexample-retained')
        for name, expected in derivation['sourceSHA256'].items():
            check(historical_lock['sha256'][name] == expected, 'counterexample-binds-historical-source:' + name)
            check(sha(read(BASE / 'cover-snap-counterexample-1/inputs' / name)) == expected,
                  'captured-counterexample-source:' + name)
        for name, expected in manifest.items():
            check(sha(read(ROOT / name)) == expected, 'final-source-unchanged:' + name)
        summary = {'candidate': args.candidate, 'sourceCount': len(manifest), 'compiledSources': len(compiled_sources),
                   'sourceClosureSHA256': closure, 'commands': len(commands + modules), 'hostPureAssertions': 8,
                   'binaryArchiveSHA256': artifacts['sha256'], 'nativeBinaries': binaries,
                   'historicalCompileOnly': {'candidate': 'headless-cover-baselines',
                                             'sourceClosureSHA256': historical_result['sourceClosureSHA256'],
                                             'disposition': 'Superseded after independent final-coordinate counterexample; no native qualification.'}}
        status = 'passed-apple-headless-source-and-artifact-review-native-pending'
    except Exception as failure:
        error = repr(failure)
        (out / 'failure.log').write_text(traceback.format_exc())
    receipt = {'status': status, 'error': error,
               'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'command': [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
               'pythonVersion': platform.python_version(), 'reviewerScriptSHA256': sha(Path(__file__).read_bytes()),
               'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'sourceTree': subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=ROOT, text=True).strip(),
               'checks': checks, 'summary': summary, 'evidenceSHA256': reads, 'retainedCompileWarnings': warnings,
               'scope': 'Independent read-only baseline/cover source assessment, file/hash/command replay and direct parsing of retained arm64 Mach-O artifacts. No new compiler, GUI, image view, native runtime, target discovery or product suite commands.',
               'nativeAcceptance': False,
               'pending': ['Opaque cover held/release/cancel glass suppression, actual hit/one-toggle/accessibility ownership.',
                           'Current baseline/layout/negative fixtures on resumed native runtime.',
                           'Physical phones, IME/AT breadth, native engine coordinator, signed/bootstrap V2, published packages, stores and GA.']}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': status, 'checks': len(checks), 'evidenceFiles': len(reads), 'error': error,
                      'receipt': str(out / 'receipt.json')}))
    return 0 if status.startswith('passed-') else 1


if __name__ == '__main__':
    sys.exit(main())
