#!/usr/bin/env python3
"""Freeze and execute SDK/native-packet data checks; never launch a device."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OFFICIAL = Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swiftc')
ANDROID = Path('/Users/andreyyurlov/Library/org.swift.swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android')
JDK = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise RuntimeError(message)


def main():
    name = sys.argv[1] if len(sys.argv) == 2 else 'candidate-1'
    out = HERE / name
    out.mkdir(exist_ok=False)
    archive = out / '.build/source'
    paths = {ROOT / 'sdk/Package.swift', ROOT / 'Package.swift', ROOT / 'contracts/ui-v1.json',
             ROOT / 'scripts/ci/check-sdk-package.py', HERE / 'verify.py',
             HERE / 'PacketConsumer.swift', HERE / 'PacketConsumer.java'}
    for directory in ['sdk/Sources', 'sdk/Tests']:
        paths.update(p for p in (ROOT / directory).rglob('*') if p.is_file())
    for name in ['Json.java', 'UiPacket.java']:
        paths.add(ROOT / 'native/android/app/src/dev/mixer/android' / name)
    sources = {}
    for path in sorted(paths):
        relative = path.relative_to(ROOT)
        data = path.read_bytes()
        sources[str(relative)] = sha(data)
        target = archive / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    digest = sha(json.dumps(sources, sort_keys=True, separators=(',', ':')).encode())
    (out / 'input-lock.json').write_text(json.dumps({'files': sources, 'tree_sha256': digest}, indent=2) + '\n')
    receipt = {
        'status': 'running', 'source_tree_sha256': digest, 'source_file_count': len(sources),
        'head_at_start': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'commands': [], 'artifacts': {},
        'scope': 'Data encoder only. Exact frozen SDK host Debug/Release tests, existing production Java decoder interoperation, public Swift event round trip, and iOS/Android modules. No native presentation, JNI, widget, signed-health, target runtime, physical parity, publication or GA qualification.',
    }

    def save():
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')

    def run(name, args, env=None, cwd=archive, timeout=600):
        argv = list(map(str, args))
        start = time.monotonic()
        result = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=timeout)
        log = out / (name + '.log')
        log.write_bytes(result.stdout)
        receipt['commands'].append({'name': name, 'argv': argv, 'cwd': str(cwd),
            'exit_code': result.returncode, 'elapsed_seconds': time.monotonic() - start,
            'environment_overrides': {'DEVELOPER_DIR': env['DEVELOPER_DIR']} if env else {},
            'log': str(log.relative_to(ROOT)), 'log_sha256': sha(result.stdout)})
        save()
        print(name + ': ' + str(result.returncode), flush=True)
        if result.returncode:
            receipt['status'] = 'failed: ' + name
            save()
            raise RuntimeError(receipt['status'])
        return result.stdout.decode(errors='replace').strip()

    apple = dict(os.environ, DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
    android = dict(os.environ, DEVELOPER_DIR='/Applications/Xcode_26.6.app/Contents/Developer')
    run('host-swift-version', ['swift', '--version'], apple)
    run('java-version', [JDK / 'java', '-version'])
    run('official-swift-version', [OFFICIAL, '--version'], android)
    ios_sdk = run('iphoneos-sdk', ['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], apple)
    run('sdk-manifest-parity', ['python3', 'scripts/ci/check-sdk-package.py'], apple)
    for mode in ['debug', 'release']:
        run('sdk-' + mode, ['swift', 'test', '--package-path', 'sdk', '-c', mode,
            '-Xswiftc', '-warnings-as-errors'], apple)

    consumer = archive / 'consumer'
    consumer.mkdir()
    manifest = '''// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "PacketConsumer", platforms: [.macOS(.v14)],
    dependencies: [.package(path: "../sdk")], targets: [.executableTarget(name: "PacketConsumer",
        dependencies: [.product(name: "MixerUI", package: "sdk")], path: "Sources")],
    swiftLanguageModes: [.v6])
'''
    (consumer / 'Package.swift').write_text(manifest)
    (out / 'consumer-Package.swift').write_text(manifest)
    (consumer / 'Sources').mkdir()
    (consumer / 'Sources/main.swift').write_bytes((archive / (HERE / 'PacketConsumer.swift').relative_to(ROOT)).read_bytes())
    packets = out / '.build/packets'
    run('public-consumer-emit', ['swift', 'run', '--package-path', consumer, '-c', 'release',
        '-Xswiftc', '-warnings-as-errors', 'PacketConsumer', 'emit', packets], apple)
    java_out = out / '.build/java'
    java_out.mkdir()
    java_source = archive / 'native/android/app/src/dev/mixer/android'
    run('javac-production-decoder', [JDK / 'javac', '--release', '17', '-Xlint:all', '-Werror', '-d', java_out,
        java_source / 'Json.java', java_source / 'UiPacket.java',
        archive / (HERE / 'PacketConsumer.java').relative_to(ROOT)])
    run('java-production-decoder', [JDK / 'java', '-cp', java_out, 'dev.mixer.android.PacketConsumer', packets])
    run('public-consumer-return-events', ['swift', 'run', '--package-path', consumer, '-c', 'release',
        '-Xswiftc', '-warnings-as-errors', 'PacketConsumer', 'verify-events', packets], apple)
    for path in sorted(packets.glob('*.json')):
        receipt['artifacts'][str(path.relative_to(ROOT))] = {'sha256': sha(path.read_bytes()), 'bytes': path.stat().st_size}

    receipt['android_sdk_metadata'] = {str(p): sha(p.read_bytes()) for p in [ANDROID / 'swift-sdk.json', ANDROID / 'swift-toolset.json']}
    for platform, compiler, flags, env in [
        ('ios', 'swiftc', ['-target', 'arm64-apple-ios17.0', '-sdk', ios_sdk], apple),
        ('android', OFFICIAL, ['-target', 'aarch64-unknown-linux-android30', '-sdk', ANDROID / 'ndk-sysroot',
            '-resource-dir', ANDROID / 'swift-resources/usr/lib/swift-aarch64'], android),
    ]:
        folder = out / '.build' / platform
        folder.mkdir()
        for module in ['MixerCore', 'MixerUI', 'MixerGuest']:
            output = folder / (module + '.swiftmodule')
            inputs = sorted((archive / 'sdk/Sources' / module).glob('*.swift'))
            run(platform + '-' + module, [compiler, '-swift-version', '6', '-warnings-as-errors', '-parse-as-library',
                '-emit-module', '-module-name', module, '-emit-module-path', output, '-module-cache-path', folder / 'cache',
                '-I', folder] + flags + inputs, env)
            require(output.is_file(), 'module output ' + module)
            receipt['artifacts'][str(output.relative_to(ROOT))] = {'sha256': sha(output.read_bytes()), 'bytes': output.stat().st_size}
    require(all(sha((ROOT / path).read_bytes()) == value and sha((archive / path).read_bytes()) == value
                for path, value in sources.items()), 'source changed during checks')
    receipt.update(status='passed', completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   unchanged_live_and_archive_source_checks=len(sources) * 2)
    save()
    print('PASS: ' + str(out / 'receipt.json'), flush=True)


if __name__ == '__main__':
    main()
