#!/usr/bin/env python3
"""Freeze ordinary Android engine sources; host tests, Java wire and Android link."""
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
JDK = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin')
SWIFT = Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift')
SDKS = Path('/Users/andreyyurlov/Library/org.swift.swiftpm/swift-sdks')
ART = SDKS / 'swift-6.3.3-RELEASE_android.artifactbundle/swift-android'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, label):
    if not condition:
        raise RuntimeError(label)


def main():
    out = HERE / (sys.argv[1] if len(sys.argv) == 2 else 'candidate-1')
    out.mkdir(exist_ok=False)
    source = out / '.build/source'
    inputs = {ROOT / 'sdk/Package.swift', ROOT / 'native/android/engine/Package.swift',
        HERE / 'verify.py', HERE / 'Consumer.swift', HERE / 'EnginePackets.java',
        ROOT / 'verification/ui-native-packet-root-review/acceptance.json'}
    for directory in ['sdk/Sources', 'native/android/engine/Sources', 'native/android/engine/Tests']:
        inputs.update(p for p in (ROOT / directory).rglob('*') if p.is_file())
    for name in ['Json.java', 'UiPacket.java']:
        inputs.add(ROOT / 'native/android/app/src/dev/mixer/android' / name)
    inputs.add(ROOT / 'native/android/tests/ContractTests.java')
    manifest = {}
    for path in sorted(inputs):
        rel = path.relative_to(ROOT)
        data = path.read_bytes()
        manifest[str(rel)] = sha(data)
        copied = source / rel
        copied.parent.mkdir(parents=True, exist_ok=True)
        copied.write_bytes(data)
    (out / 'input-lock.json').write_text(json.dumps(manifest, indent=2) + '\n')
    receipt = {'status': 'running', 'commands': [], 'artifacts': {},
        'head_at_start': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'source_tree_sha256': sha(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()),
        'source_files': len(manifest), 'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Ordinary Android engines adopt data-only SDK encoder. Host tests and Java production decoding plus official arm64 Android shared-library build; no device, JNI execution, UI styling, signed health, physical parity, release or GA authority.'}

    def save():
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')

    def run(name, argv, env=None):
        start = time.monotonic()
        result = subprocess.run(list(map(str, argv)), cwd=source, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=600)
        log = out / (name + '.log')
        log.write_bytes(result.stdout)
        receipt['commands'].append({'name': name, 'argv': list(map(str, argv)), 'cwd': str(source),
            'environment_overrides': {'DEVELOPER_DIR': env['DEVELOPER_DIR']} if env else {},
            'exit_code': result.returncode, 'elapsed_seconds': time.monotonic() - start,
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
    run('swift-version', ['swift', '--version'], apple)
    run('java-version', [JDK / 'java', '-version'])
    run('android-swift-version', [SWIFT, '--version'], android)
    for mode in ['debug', 'release']:
        run('engine-' + mode, ['swift', 'test', '--package-path', 'native/android/engine', '-c', mode,
            '-Xswiftc', '-warnings-as-errors'], apple)
    packets = out / '.build/packets'
    # The checklist product is dynamic; the reusable document runtime is static.
    # Exercise separate consumers to avoid linking duplicate SDK copies together.
    for flavor in ['checklist', 'document']:
        consumer = source / ('consumer-' + flavor)
        (consumer / 'Sources').mkdir(parents=True)
        packages = '.package(path: "../native/android/engine")'
        products = '.product(name: "MixerAndroidEngine", package: "engine")'
        flags = ['-Xswiftc', '-DCHECKLIST']
        if flavor == 'document':
            packages += ', .package(path: "../sdk")'
            products = '.product(name: "MixerAndroidRuntime", package: "engine"), .product(name: "MixerUI", package: "sdk")'
            flags = []
        package = f'''// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "EnginePacketConsumer", platforms: [.macOS(.v14)],
    dependencies: [{packages}], targets: [.executableTarget(name: "EnginePacketConsumer",
        dependencies: [{products}], path: "Sources")], swiftLanguageModes: [.v6])
'''
        (consumer / 'Package.swift').write_text(package)
        (out / (flavor + '-Package.swift')).write_text(package)
        (consumer / 'Sources/main.swift').write_bytes((source / (HERE / 'Consumer.swift').relative_to(ROOT)).read_bytes())
        run('public-' + flavor + '-packet', ['swift', 'run', '--package-path', consumer, '-c', 'release',
            '-Xswiftc', '-warnings-as-errors'] + flags + ['EnginePacketConsumer', packets], apple)
    java = out / '.build/java'
    java.mkdir()
    decoder = source / 'native/android/app/src/dev/mixer/android'
    run('javac-production-decoder', [JDK / 'javac', '--release', '17', '-Xlint:all', '-Werror', '-d', java,
        decoder / 'Json.java', decoder / 'UiPacket.java', source / 'native/android/tests/ContractTests.java',
        source / (HERE / 'EnginePackets.java').relative_to(ROOT)])
    run('java-existing-contracts', [JDK / 'java', '-cp', java, 'dev.mixer.android.ContractTests'])
    run('java-engine-packets', [JDK / 'java', '-cp', java, 'dev.mixer.android.EnginePackets', packets])
    run('android-link', [SWIFT, 'build', '--package-path', 'native/android/engine', '--swift-sdks-path', SDKS,
        '--swift-sdk', 'aarch64-unknown-linux-android28', '-c', 'release', '-Xswiftc', '-warnings-as-errors'], android)
    libraries = list((source / 'native/android/engine/.build').glob('aarch64-*/release/libMixerAndroidEngine.so'))
    require(len(libraries) == 1, 'single Android shared library')
    readelf = ART / 'android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64/bin/llvm-readelf'
    run('android-elf', [readelf, '-h', '-d', libraries[0]])
    for path in libraries + sorted(packets.glob('*.json')):
        receipt['artifacts'][str(path.relative_to(ROOT))] = {'sha256': sha(path.read_bytes()), 'bytes': path.stat().st_size}
    for path, digest in manifest.items():
        require(sha((ROOT / path).read_bytes()) == digest and sha((source / path).read_bytes()) == digest, 'source ' + path)
    receipt.update(status='passed', completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   unchanged_live_archive_bindings=2 * len(manifest))
    save()
    print('PASS: ' + str(out / 'receipt.json'), flush=True)


if __name__ == '__main__':
    main()
