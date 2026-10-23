#!/usr/bin/env python3
"""Native request exit receipts. No devices, production or trust-store changes."""
import concurrent.futures
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
LOGS = OUT / 'logs'
SWIFT = '/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift'
SDKS = '/Users/andreyyurlov/.swiftpm/swift-sdks'
XENV = {'DEVELOPER_DIR': '/Applications/Xcode_26.6.app/Contents/Developer'}
JDK = '/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home'
JENV = {'JAVA_HOME': JDK, 'PATH': JDK + '/bin:' + os.environ['PATH']}


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def capture(command, environment=None):
    return subprocess.run(command, cwd=ROOT, env=os.environ | (environment or {}),
                          text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def source():
    files = []
    for folder in [ROOT / 'sdk', ROOT / 'capabilities']:
        files += [p for p in folder.rglob('*') if p.is_file() and not {'.build', '.swiftpm', 'verification', '__pycache__'}.intersection(p.relative_to(folder).parts)]
    entries = [{'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size,
                'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)]
    encoded = json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()
    return {'algorithm': 'SHA256 of canonical JSON source entries sorted by path; sdk and capabilities excluding build/verification artifacts',
            'digest': hashlib.sha256(encoded).hexdigest(), 'files': entries}


def run(job):
    name, command, scope, environment = job
    started = now()
    result = capture(command, environment)
    path = LOGS / (name + '.log')
    path.write_text(result.stdout)
    record = {'name': name, 'command': command, 'cwd': str(ROOT), 'startedAt': started,
              'endedAt': now(), 'exitCode': result.returncode,
              'output': str(path.relative_to(ROOT)), 'outputSHA256': hashlib.sha256(path.read_bytes()).hexdigest(), 'scope': scope}
    if environment:
        record['environment'] = environment
    print(name + ': ' + str(result.returncode), flush=True)
    return record


def main():
    LOGS.mkdir(parents=True, exist_ok=True)
    before = source()
    (OUT / 'source-manifest.json').write_text(json.dumps(before, indent=2) + '\n')
    baseline = capture(['git', 'show', 'b4f13ec9a78b882380a6cfba0a9607990ca9babe:capabilities/schema/hashes.json'])
    prior = json.loads(baseline.stdout)
    current = json.loads((ROOT / 'capabilities/schema/hashes.json').read_text())
    wire_unchanged = {k: v for k, v in current.items() if k != 'nativeImplementationSHA256'} == {k: v for k, v in prior.items() if k != 'nativeImplementationSHA256'}
    head = capture(['git', 'rev-parse', 'HEAD']).stdout.strip()
    tree = capture(['git', 'rev-parse', 'HEAD^{tree}']).stdout.strip()
    commands = [run(('generated-check', ['python3', 'capabilities/tools/generate.py', '--check'],
                     'owned generator covers new helpers; generated models/dispatch remain unchanged; wire hashes preserved', None))]
    android = [SWIFT, 'build', '--package-path', 'capabilities', '--swift-sdks-path', SDKS, '--swift-sdk', 'aarch64-unknown-linux-android28']
    jobs = [
        ('capability-debug-tests', ['swift', 'test', '--package-path', 'capabilities', '--scratch-path', 'capabilities/.build/exit-debug'],
         'macOS complete capability tests including 13 native exit tests and existing HTTP/codec/storage behavior', None),
        ('capability-release-tests', ['swift', 'test', '--package-path', 'capabilities', '-c', 'release', '--scratch-path', 'capabilities/.build/exit-release'],
         'macOS optimized complete capability suite; observed request success/cancel/close races', None),
        ('sdk-parity-tests', ['swift', 'test', '--package-path', 'sdk'],
         'existing Core/UI/Apple SDK tests; no physical-device evidence', None),
        ('ios-build', ['swift', 'build', '--package-path', 'sdk', '--target', 'MixerCapabilities', '--triple', 'arm64-apple-ios17.0', '--sdk',
                       '/Applications/Xcode.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS27.1.sdk',
                       '--scratch-path', 'capabilities/.build/http-ios', '-Xswiftc', '-warnings-as-errors'],
         'official iOS arm64 SDK target compilation only; warnings treated as errors; no signing/device run', None),
        ('android-build', android + ['--static-swift-stdlib', '-c', 'release', '--product', 'capability-probe', '--scratch-path',
                                     'capabilities/.build/http-android', '-Xlinker', '-lssl', '-Xlinker', '-lcrypto', '-Xlinker', '-lz'],
         'official Android SDK aarch64 API28 static probe cross-compile with explicit SDK curl SSL/crypto/zlib dependencies; no APK/runtime receipt', XENV),
        ('android-test-build', android + ['-c', 'release', '--build-tests', '-Xswiftc', '-enable-testing', '--scratch-path', 'capabilities/.build/http-android-tests'],
         'official Android SDK dynamic Swift Testing runner and native exit tests compile only; not executed', XENV),
        ('wasi-build', [SWIFT, 'build', '--package-path', 'sdk', '--swift-sdks-path', SDKS, '--swift-sdk', 'swift-6.3.3-RELEASE_wasm',
                        '--triple', 'wasm32-unknown-wasip1', '-c', 'release', '--target', 'MixerCapabilities', '--scratch-path', 'capabilities/.build/http-wasm'],
         'official WASI guest module compile preserving legacy path; concrete installed adapters/lease excluded; not linked/executed', XENV),
        ('thread-sanitizer', ['swift', 'test', '--package-path', 'capabilities', '--scratch-path', 'capabilities/.build/exit-tsan', '--sanitize', 'thread',
                              '--filter', 'NativeCapabilityExitTests|NativeHTTPTransportTests'],
         'macOS native HTTP and exit-observation suites; owned code instrumented; system frameworks uninstrumented; concurrent duplicate lease and close/cancel races', None),
        ('java-build', [JDK + '/bin/javac', '--release', '8', '-Xlint:all,-options', '-Werror', '-d', 'capabilities/.build/java']
                       + [str(p.relative_to(ROOT)) for p in sorted((ROOT / 'capabilities/java').rglob('*.java'))] + ['capabilities/Tests/Java/CapabilityCodecTests.java'],
         'Java8 codec compilation including regenerated native source identity', JENV),
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        commands += list(executor.map(run, jobs))
    commands += [run(('java-tests', [JDK + '/bin/java', '-cp', 'capabilities/.build/java', 'mixer.capabilities.CapabilityCodecTests'],
                      'unchanged Java codec/ownership regression parity', JENV)),
                 run(('codec-differential', ['python3', 'capabilities/tools/codec-differential.py'],
                      'owned Swift/Java strict codec differential parity; schema v1 unchanged', JENV))]
    after = source()
    unchanged = before == after
    passed = unchanged and wire_unchanged and all(r['exitCode'] == 0 for r in commands)
    receipt = {
        'schema': 1, 'recordedAt': now(), 'baselineRevision': head, 'baselineTree': tree,
        'source': before, 'sourceUnchangedDuringRun': unchanged,
        'evidenceRunnerSHA256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'commands': commands,
        'contracts': current, 'wireSchemaUnchanged': wire_unchanged,
        'nativeImplementationIdentity': {'previous': prior['nativeImplementationSHA256'], 'current': current['nativeImplementationSHA256'],
                                         'reason': 'additive closed installed-adapter lifecycle changes native source and requires installed binary identity update; v1 schemas/codecs/dispatch unchanged'},
        'environment': {'host': platform.platform(), 'python': sys.version,
                        'swift': capture(['swift', '--version']).stdout.strip(), 'xcode': capture(['xcodebuild', '-version']).stdout.strip(),
                        'androidSwift': capture([SWIFT, '--version'], XENV).stdout.strip(),
                        'androidManifestHostXcode': capture(['xcodebuild', '-version'], XENV).stdout.strip(),
                        'javac': capture([JDK + '/bin/javac', '-version']).stdout.strip()},
        'assertions': {'closedConcreteAdapterObservation': True, 'terminalAndExitSeparate': True,
                       'installedSlotsRetainedUntilJoin': True, 'ordinaryInstalledSubmitAlsoJoins': True,
                       'hostCloseDeinitObserverIndependent': True, 'legacyClosureNotTrustedForExit': True,
                       'noGlobalProcessCapClaim': True, 'noOSDestructionOrRollbackClaim': True,
                       'noGuestImportOrCABIChange': True, 'noPhysicalDeviceReceipt': True, 'noGAGatePassed': True},
        'limitations': [
            'URLProtocol fixtures bypass real TLS/network parsing; delegate callback control establishes native observation ordering, not kernel socket/process reclamation',
            'ThreadSanitizer instruments owned code only; system frameworks are opaque',
            'Per-request storage exit is method return with local descriptors closed; persistent shared store descriptors remain open; committed effects cannot be rolled back by cancellation',
            'Host quota is per instance; no new global process/session/native-operation cap or no-unwind proof is supplied',
            'Physical iOS/Android lifecycle and trust/runtime qualification remain pending; phones disconnected and no device commands attempted',
            'Rust mailbox bridge, identity/configuration/grant composition, signing, stores, immutable published-package FieldLog consumption and accountable independent GA reviews remain pending',
        ],
        'scopedChecksPassed': passed,
    }
    (OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'scopedChecksPassed': passed, 'sourceUnchangedDuringRun': unchanged, 'sourceDigest': before['digest'],
                      'wireSchemaUnchanged': wire_unchanged, 'receipt': str((OUT / 'receipt.json').relative_to(ROOT))}), flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
