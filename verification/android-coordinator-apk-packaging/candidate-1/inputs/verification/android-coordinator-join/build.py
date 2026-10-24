#!/usr/bin/env python3
"""Freeze/build a real private ordinary Android join APK. Never discovers or runs devices."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tarfile
import zipfile
from owned_process import execute

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SDK = Path('/opt/homebrew/share/android-commandlinetools')
JDK = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
SWIFT = Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift')
SWIFT_SDKS = Path('/Users/andreyyurlov/.swiftpm/swift-sdks')
ART = SWIFT_SDKS / 'swift-6.3.3-RELEASE_android.artifactbundle/swift-android'
NDK = ART / 'android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64'
RUNTIME = ART / 'swift-resources/usr/lib/swift-aarch64/android'
BT = SDK / 'build-tools/37.0.0'
JAR = SDK / 'platforms/android-37.0/android.jar'
DESCRIPTOR = 'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json'
PRODUCT_NAMES = ['Json', 'UiPacket', 'AppearanceDescriptorV2', 'AppearanceGeometryV2',
                 'AppearanceResolverV2', 'AppearanceNativePathsV2', 'NativeEnvironmentV2',
                 'InstalledAppearanceV2', 'NativeAppearanceViewsV2', 'NativeRenderer',
                 'NativeBridge', 'NativeCoordinatorV2']
PRODUCT = ['native/android/app/src/dev/mixer/android/' + name + '.java' for name in PRODUCT_NAMES]
PACKAGE = 'dev.mixer.android.coordinatorjoin'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', required=True, help='fresh retained directory; never overwritten')
    args = parser.parse_args()
    if not re.fullmatch(r'candidate-[0-9]+', args.attempt):
        parser.error('fresh candidate-N required')
    out = HERE / args.attempt
    out.mkdir()
    build = out / '.build'
    build.mkdir()
    env = dict(os.environ, JAVA_HOME=str(JDK),
               DEVELOPER_DIR='/Applications/Xcode_26.6.app/Contents/Developer',
               PATH=str(JDK / 'bin') + os.pathsep + os.environ['PATH'])
    commands = []
    receipt = {'schema': 1, 'status': 'building', 'commands': commands,
               'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'runtime': 'NOT RUN: Mac locked, root runtime dispatch pending',
               'nativeAcceptance': False, 'gaAcceptance': False,
               'environment': {'JAVA_HOME': str(JDK), 'DEVELOPER_DIR': env['DEVELOPER_DIR'],
                               'ANDROID_HOME': str(SDK), 'swiftSDK': 'aarch64-unknown-linux-android28'},
               'compiledMinAPI': 36, 'actuallyQualifiedRuntimeAPI': None,
               'sourceSDKTargetTripleAPI': 28,
               'limitations': ['headless build only; no emulator/simulator/device query or launch',
                   'native bounded join assertions NOT RUN; smoke/partial matrix is not full native fault/IME/lifecycle qualification',
                   'publicActivityV1 unchanged; no public bootstrap or signed transport permission',
                   'physical devices, immutable external FieldLog, store, operational and GA gates pending']}

    def run(name, argv, timeout=180):
        argv = list(map(str, argv))
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        completed = execute(argv, cwd=ROOT, env=env, timeout=timeout)
        output, code = completed.stdout, completed.returncode
        log = out / (name + '.log')
        log.write_bytes(output)
        commands.append({'name': name, 'argv': argv, 'cwd': str(ROOT), 'exitCode': code,
                         'startedUTC': started, 'finishedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                         'output': log.name, 'sha256': sha(log),
                         'ownedCommandGroupCleanup': completed.groupCleanup})
        print(name + ': exit ' + str(code), flush=True)
        if code:
            print(output.decode(errors='replace')[-12000:], flush=True)
            raise RuntimeError(name + ' failed; full output retained')
        return output.decode(errors='replace').strip()

    try:
        receipt['sourceRevision'] = run('source-revision', ['git', 'rev-parse', 'HEAD'])
        receipt['sourceTree'] = run('source-tree', ['git', 'rev-parse', 'HEAD^{tree}'])
        run('source-status', ['git', 'status', '--short'])
        inputs = set(PRODUCT)
        inputs.update(['AGENTS.md', 'mixer-product-plan.md', 'THIRD_PARTY.yml',
                       'native/android/engine/Package.swift', 'sdk/Package.swift',
                       'native/android/bridge/jni.c', 'native/android/bridge/mixer_android.h',
                       'native/android/bridge/mixer_android_v2.h', DESCRIPTOR,
                       'docs/android-native-v2-coordinator-contract.md', 'docs/android-native-v2-coordinator.md',
                       'docs/android-native-resume-2026-10-24.md',
                       'verification/android-native-appearance-v2/candidate-16-root-review/acceptance.json',
                       'verification/android-native-appearance-v2/emulator-session.json'])
        for folder in ['sdk/Sources', 'sdk/Tests', 'native/android/engine/Sources', 'native/android/engine/Tests']:
            inputs.update(str(path.relative_to(ROOT)) for path in (ROOT / folder).rglob('*') if path.is_file())
        inputs.update(str(path.relative_to(ROOT)) for path in HERE.iterdir()
                      if path.is_file() and path.name != '.gitignore')
        source_hashes = {}
        for relative in sorted(inputs):
            target = out / 'inputs' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
            source_hashes[relative] = sha(target)
        receipt['sourceClosureSHA256'] = hashlib.sha256(json.dumps(source_hashes, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        save(out / 'source-lock.json', {'sourceRevision': receipt['sourceRevision'],
             'sourceClosureSHA256': receipt['sourceClosureSHA256'], 'files': source_hashes})
        freeze = lambda relative: out / 'inputs' / relative
        versions = {}
        version_commands = [('python', [sys.executable, '--version']), ('swift', [SWIFT, '--version']),
            ('clang', [NDK / 'bin/aarch64-linux-android28-clang', '--version']),
            ('java', [JDK / 'bin/java', '--version']), ('javac', [JDK / 'bin/javac', '--version']),
            ('d8', [BT / 'd8', '--version']), ('aapt2', [BT / 'aapt2', 'version']),
            ('zipalign', [BT / 'zipalign', '-h']), ('apksigner', [BT / 'apksigner', 'version'])]
        # zipalign help intentionally exits 2; its executable hash and tool package identify it instead.
        version_commands = [item for item in version_commands if item[0] != 'zipalign']
        for name, command in version_commands:
            versions[name] = run(name + '-version', command)
        receipt['versions'] = versions
        run('headless-runner-guards', [sys.executable, '-B', freeze('verification/android-coordinator-join/test_runner.py')])
        tools = [SWIFT, SWIFT.parent / 'swift-frontend', NDK / 'bin/clang', NDK / 'bin/llvm-readelf',
                 JDK / 'bin/java', JDK / 'bin/javac', JDK / 'bin/javap', BT / 'aapt2',
                 BT / 'zipalign', BT / 'lib/apksigner.jar', BT / 'lib/d8.jar', JAR,
                 NDK.parents[3] / 'source.properties', BT / 'source.properties',
                 ART.parent / 'info.json']
        receipt['tools'] = {str(path): {'realPath': str(path.resolve()), 'sha256': sha(path),
                                       'bytes': path.stat().st_size} for path in tools}
        run('swift-sdk-description', [SWIFT, 'sdk', 'list', '--swift-sdks-path', SWIFT_SDKS])
        swift_build = build / 'swift'
        run('ordinary-swift-android-release', [SWIFT, 'build', '--package-path', freeze('native/android/engine'),
            '--scratch-path', swift_build, '--swift-sdks-path', SWIFT_SDKS,
            '--swift-sdk', 'aarch64-unknown-linux-android28', '--product', 'MixerAndroidEngine', '-c', 'release'], timeout=600)
        engines = list(swift_build.glob('*/release/libMixerAndroidEngine.so'))
        if len(engines) != 1:
            raise RuntimeError('unique actual Swift Android engine output required: ' + str(engines))
        libdir = build / 'apk/lib/arm64-v8a'
        libdir.mkdir(parents=True)
        engine = engines[0]
        shutil.copy2(engine, libdir / engine.name)
        run('ordinary-jni-ndk-link', [NDK / 'bin/aarch64-linux-android28-clang', '-shared', '-fPIC', '-O2',
            '-Wall', '-Wextra', '-Werror', '-I', freeze('native/android/bridge'), freeze('native/android/bridge/jni.c'),
            '-L', engine.parent, '-lMixerAndroidEngine', '-Wl,-z,max-page-size=16384', '-Wl,--no-undefined',
            '-o', libdir / 'libmixer_android_jni.so'])
        dependencies = {}
        system = {'libc.so', 'libdl.so', 'libm.so', 'liblog.so', 'libandroid.so'}
        pending = list(libdir.glob('*.so'))
        while pending:
            library = pending.pop()
            dynamic = run('elf-dynamic-' + library.name, [NDK / 'bin/llvm-readelf', '-d', library])
            needed = re.findall(r'\(NEEDED\).*\[([^\]]+)\]', dynamic)
            dependencies[library.name] = needed
            headers = run('elf-headers-' + library.name, [NDK / 'bin/llvm-readelf', '-h', '-lW', library])
            if 'AArch64' not in headers:
                raise RuntimeError('native ABI mismatch ' + library.name)
            loads = [line.split()[-1] for line in headers.splitlines() if line.strip().startswith('LOAD ')]
            if not loads or any(int(value, 16) < 16384 for value in loads):
                raise RuntimeError('ELF page alignment below 16KiB ' + library.name)
            for name in needed:
                if name in system or (libdir / name).exists():
                    continue
                found = next((path for path in [RUNTIME / name, NDK / 'sysroot/usr/lib/aarch64-linux-android' / name]
                              if path.is_file()), None)
                if found is None:
                    raise RuntimeError('unresolved native dependency ' + name)
                shutil.copy2(found, libdir / name)
                pending.append(libdir / name)
        receipt['nativeDependencies'] = dependencies
        symbols = run('ordinary-engine-exports', [NDK / 'bin/llvm-readelf', '--dyn-syms', '--wide', libdir / engine.name])
        for symbol in ['mixer_android_create', 'mixer_android_destroy', 'mixer_android_prepare_v2',
                       'mixer_android_commit_v2', 'mixer_android_abort_v2']:
            if not any(line.rstrip().endswith(' ' + symbol) and ' UND ' not in line for line in symbols.splitlines()):
                raise RuntimeError('missing actual ordinary Swift export ' + symbol)
        production = build / 'production-classes'
        production.mkdir()
        empty = build / 'empty-sourcepath'
        empty.mkdir()
        run('production-java17-sdk37', [JDK / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror',
            '-sourcepath', empty, '-classpath', JAR, '-d', production, *[freeze(path) for path in PRODUCT]])
        test_classes = build / 'test-classes'
        test_classes.mkdir()
        run('private-harness-java17-sdk37', [JDK / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror',
            '-sourcepath', empty, '-classpath', str(production) + os.pathsep + str(JAR), '-d', test_classes,
            freeze('verification/android-coordinator-join/CoordinatorJoinActivity.java'),
            freeze('verification/android-coordinator-join/CoordinatorJoinInstrumentation.java')])
        # The exact production class bytes compiled above are included with the harness, not recompiled with substitutes.
        receipt['coordinatorClassSHA256'] = sha(production / 'dev/mixer/android/NativeCoordinatorV2.class')
        run('production-coordinator-bytecode', [JDK / 'bin/javap', '-c', '-p', '-classpath', production,
            'dev.mixer.android.NativeCoordinatorV2'])
        dex = build / 'dex'
        dex.mkdir()
        run('joined-dex-min36', [BT / 'd8', '--min-api', '36', '--lib', JAR, '--output', dex,
            *sorted(production.rglob('*.class')), *sorted(test_classes.rglob('*.class'))])
        unsigned = build / 'unsigned.apk'
        run('private-package-manifest', [BT / 'aapt2', 'link', '-I', JAR, '--manifest',
            freeze('verification/android-coordinator-join/AndroidManifest.xml'),
            '--min-sdk-version', '36', '--target-sdk-version', '37', '-o', unsigned])
        with zipfile.ZipFile(unsigned, 'a') as archive:
            for path in sorted(libdir.glob('*.so')):
                archive.write(path, 'lib/arm64-v8a/' + path.name, compress_type=zipfile.ZIP_STORED)
            for path in sorted(dex.glob('*.dex')):
                archive.write(path, path.name, compress_type=zipfile.ZIP_DEFLATED)
            archive.write(freeze(DESCRIPTOR), 'assets/MixerAppearanceV2/descriptor.json', compress_type=zipfile.ZIP_DEFLATED)
            archive.write(freeze('verification/android-coordinator-join/operations.json'),
                          'assets/CoordinatorJoin/operations.json', compress_type=zipfile.ZIP_DEFLATED)
        aligned = build / 'aligned.apk'
        run('private-apk-align-16k', [BT / 'zipalign', '-f', '-P', '16', '4', unsigned, aligned])
        key = build / 'disposable-debug.keystore'
        try:
            env['MIXER_JOIN_DEBUG_PASS'] = secrets.token_urlsafe(32)
            run('disposable-debug-key', [JDK / 'bin/keytool', '-genkeypair', '-keystore', key,
                '-storepass:env', 'MIXER_JOIN_DEBUG_PASS', '-keypass:env', 'MIXER_JOIN_DEBUG_PASS', '-alias', 'debug', '-keyalg', 'RSA',
                '-keysize', '2048', '-validity', '30', '-dname', 'CN=Mixer Disposable Private Join Test'])
            apk = build / 'coordinator-join.apk'
            run('private-debug-apk-sign', [BT / 'apksigner', 'sign', '--ks', key, '--ks-pass', 'env:MIXER_JOIN_DEBUG_PASS',
                '--key-pass', 'env:MIXER_JOIN_DEBUG_PASS', '--out', apk, aligned])
        finally:
            key.unlink(missing_ok=True)
            env.pop('MIXER_JOIN_DEBUG_PASS', None)
        # Do not retain a private key or a password in evidence commands/logs. This is disposable debug signing only.
        for command in commands:
            if command['name'] in ('disposable-debug-key', 'private-debug-apk-sign'):
                arguments = command['argv']
                for index, argument in enumerate(arguments):
                    if argument in ('-storepass', '-keypass', '--ks-pass', '--key-pass'):
                        arguments[index + 1] = '<redacted-disposable-debug-password>'
        signing = run('private-debug-signature-cert', [BT / 'apksigner', 'verify', '--verbose', '--print-certs', apk])
        cert = re.findall(r'certificate SHA-256 digest: ([0-9a-f]{64})', signing)
        if len(cert) != 1:
            raise RuntimeError('exactly one disposable debug signer certificate required')
        receipt['debugCertificateSHA256'] = cert[0]
        run('private-apk-alignment-check', [BT / 'zipalign', '-c', '-P', '16', '-v', '4', apk])
        manifest = run('private-apk-manifest-dump', [BT / 'aapt2', 'dump', 'xmltree', apk, '--file', 'AndroidManifest.xml'])
        if 'MixerActivity' in manifest or PACKAGE not in manifest or 'CoordinatorJoinInstrumentation' not in manifest:
            raise RuntimeError('private package boundary failed')
        with zipfile.ZipFile(apk) as archive:
            entries = archive.namelist()
            if any('HostLeaves' in entry or entry.endswith('.keystore') for entry in entries):
                raise RuntimeError('forbidden test leaf/key packaged')
            if hashlib.sha256(archive.read('assets/MixerAppearanceV2/descriptor.json')).hexdigest() != sha(freeze(DESCRIPTOR)):
                raise RuntimeError('packaged descriptor bytes drifted')
            save(out / 'apk-entries.json', {info.filename: {'bytes': info.file_size,
                 'sha256': hashlib.sha256(archive.read(info.filename)).hexdigest()} for info in archive.infolist()})
        artifacts = {str(path.relative_to(build)): {'bytes': path.stat().st_size, 'sha256': sha(path)}
                     for folder in [production, test_classes, dex, libdir] for path in sorted(folder.rglob('*')) if path.is_file()}
        artifacts['coordinator-join.apk'] = {'bytes': apk.stat().st_size, 'sha256': sha(apk)}
        with tarfile.open(out / 'built-artifacts.tar.gz', 'w:gz') as archive:
            for relative in sorted(artifacts):
                archive.add(build / relative, arcname=relative, recursive=False)
        save(out / 'built-artifacts.json', artifacts)
        receipt['apkSHA256'] = sha(apk)
        receipt['descriptorSHA256'] = sha(freeze(DESCRIPTOR))
        receipt['builtArchiveSHA256'] = sha(out / 'built-artifacts.tar.gz')
        receipt['compiledProductionSources'] = PRODUCT
        receipt['hostLeavesPackaged'] = False
        receipt['privateKeyRetained'] = False
        receipt['sourceUnchanged'] = all(sha(ROOT / path) == value for path, value in source_hashes.items())
        if not receipt['sourceUnchanged']:
            raise RuntimeError('source closure changed during build; retain attempt, do not accept')
        receipt['status'] = 'actual-private-apk-built-runtime-NOT-RUN'
    except BaseException as failure:
        receipt['status'] = 'failed-attempt-retained'
        receipt['failure'] = repr(failure)
        raise
    finally:
        # Defensive redaction also applies to failed signing attempts.
        for command in commands:
            if command['name'] in ('disposable-debug-key', 'private-debug-apk-sign'):
                for index, argument in enumerate(command['argv']):
                    if argument in ('-storepass', '-keypass', '--ks-pass', '--key-pass'):
                        command['argv'][index + 1] = '<redacted-disposable-debug-password>'
        (build / 'disposable-debug.keystore').unlink(missing_ok=True)
        receipt['finishedUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save(out / 'receipt.json', receipt)
        save(out / 'artifact-seal.json', {str(path.relative_to(out)): {'bytes': path.stat().st_size, 'sha256': sha(path)}
             for path in sorted(out.rglob('*')) if path.is_file() and '.build' not in path.relative_to(out).parts
             and path.name != 'artifact-seal.json'})


if __name__ == '__main__':
    main()
