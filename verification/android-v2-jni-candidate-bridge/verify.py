#!/usr/bin/env python3
"""Snapshot, build and exercise production JNI separately from derived faults."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
JDK = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
SDK = Path('/opt/homebrew/share/android-commandlinetools')
SWIFT = Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift')
SDKS = Path('/Users/andreyyurlov/Library/org.swift.swiftpm/swift-sdks')
NDK = SDKS / 'swift-6.3.3-RELEASE_android.artifactbundle/swift-android/android-ndk-r27d'
LLVM = NDK / 'toolchains/llvm/prebuilt/darwin-x86_64/bin'
JAR = SDK / 'platforms/android-37.0/android.jar'
EXPORTS = ['create', 'exchange', 'destroy', 'prepareV2', 'commitV2', 'abortV2']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', args.candidate):
        parser.error('one bounded directory name required')
    out = HERE / args.candidate
    out.mkdir(exist_ok=False)
    source = out / '.build/source'
    source.mkdir(parents=True)
    paths = set(subprocess.check_output(['git', 'ls-files', '-z', '--', 'sdk', 'native/android/engine',
                                        'native/android/app/src', 'native/android/bridge'], cwd=ROOT).decode().strip('\0').split('\0'))
    paths.update(['AGENTS.md', 'mixer-product-plan.md', 'docs/android-engine-v2-transactions.md',
                  'docs/android-engine-v2-c-bridge.md', 'docs/android-v2-jni-candidate-bridge.md'])
    paths.update(str(p.relative_to(ROOT)) for p in HERE.iterdir() if p.is_file())
    manifest = {}
    for name in sorted(paths):
        src, dst = ROOT / name, source / name
        assert src.is_file() and not src.is_symlink(), name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        manifest[name] = sha(dst)
    (out / 'source-manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    tree = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    with tarfile.open(out / 'source.tar.gz', 'w:gz') as archive:
        for name in sorted(paths):
            archive.add(source / name, arcname=name, recursive=False)
    receipt = {'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'sourceTreeDigestSHA256': tree, 'sourceManifestSHA256': sha(out / 'source-manifest.json'),
               'sourceArchiveSHA256': sha(out / 'source.tar.gz'), 'status': 'running',
               'startedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'commands': [], 'artifacts': {}, 'assertions': {},
               'scope': 'Actual host JVM JNI with unmodified Swift Debug/Release libraries; separate exact test-derived JNI/Java fault injection; production arm64 API28 cross-link and Java release17/D8 min28. No Android runtime, device, emulator or native attachment execution.',
               'pending': ['Generated entry must forward the three V2 C exports and package its header in the same integration slice',
                           'Activity/native coordinator prepare-attach-commit join and opt-in',
                           'Android runtime and final physical-phone qualification',
                           'Dynamic UInt64 sign-bit token issuance and counter exhaustion',
                           'Signed presentation and FieldLog immutable published package qualification'],
               'cleanup': 'No emulator/device discovery, boot or runtime used; no disposable instances created.'}

    def save():
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')

    def run(label, argv, env=None):
        argv = [str(x) for x in argv]
        log = out / (label + '.log')
        started = time.monotonic()
        with log.open('wb') as stream:
            result = subprocess.run(argv, cwd=source, env=dict(os.environ, **(env or {})),
                                    stdout=stream, stderr=subprocess.STDOUT, timeout=900)
        receipt['commands'].append({'label': label, 'argv': argv, 'cwd': str(source),
                                    'environment': env or {}, 'exitCode': result.returncode,
                                    'seconds': time.monotonic() - started,
                                    'log': str(log.relative_to(ROOT)), 'sha256': sha(log)})
        save()
        print(label, result.returncode, flush=True)
        if result.returncode:
            for line in log.read_text(errors='replace').splitlines()[-15:]:
                print(line[:400], flush=True)
            raise RuntimeError(label)
        return log

    def retain(src, name):
        dst = out / 'artifacts' / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        receipt['artifacts'][str(dst.relative_to(ROOT))] = sha(dst)
        return dst

    def assertions(label, log, kind):
        text = log.read_text()
        match = re.fullmatch(r'PASS ([0-9]+) ' + kind + r' assertions\n', text)
        assert match, text[-4000:]
        receipt['assertions'][label] = int(match.group(1))

    try:
        for label, argv in [('swift-version', ['swift', '--version']),
                            ('clang-version', ['clang', '--version']),
                            ('java-version', [JDK / 'bin/java', '--version']),
                            ('javac-version', [JDK / 'bin/javac', '--version']),
                            ('python-version', ['python3', '--version']),
                            ('ndk-clang-version', [LLVM / 'aarch64-linux-android28-clang', '--version']),
                            ('d8-version', [SDK / 'build-tools/37.0.0/d8', '--version']),
                            ('ndk-version', ['cat', NDK / 'source.properties'])]:
            run(label, argv, {'JAVA_HOME': str(JDK)})
        app = source / 'native/android/app/src/dev/mixer/android'
        tests = source / 'verification/android-v2-jni-candidate-bridge'
        classes = out / '.build/production-classes'
        classes.mkdir()
        run('production-java17', [JDK / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror',
                                 '-d', classes, app / 'NativeBridge.java', app / 'UiPacket.java', app / 'Json.java',
                                 tests / 'BridgeTests.java'])

        # Fault authority exists only in these exact derived copies, retained in
        # artifacts and bound to their unchanged production input by digest.
        raw_c = (source / 'native/android/bridge/jni.c').read_text()
        prefix, preparation = raw_c.split('JNIEXPORT jobject JNICALL Java_dev_mixer_android_NativeBridge_prepareV2', 1)
        replacements = {'malloc(': 'test_malloc(', '(*env)->GetByteArrayRegion(env,': 'test_input(env,',
                        '(*env)->NewByteArray(env,': 'test_array(env,', '(*env)->SetByteArrayRegion(env,': 'test_output(env,',
                        '(*env)->FindClass(env,': 'test_class(env,', '(*env)->GetMethodID(env,': 'test_method(env,',
                        '(*env)->NewObject(env,': 'test_object(env,'}
        counts = {}
        for before, after in replacements.items():
            counts[before] = preparation.count(before)
            assert counts[before] >= 1, before
            preparation = preparation.replace(before, after)
        derived = prefix + 'JNIEXPORT jobject JNICALL Java_dev_mixer_android_NativeBridge_prepareV2' + preparation
        for before, after in [('mixer_android_prepare_v2(', 'test_prepare('),
                              ('mixer_android_abort_v2(', 'test_abort('), ('mixer_android_destroy(', 'test_destroy(')]:
            counts[before] = derived.count(before)
            derived = derived.replace(before, after)
        shim = (tests / 'fault-shim.c').read_text()
        insertion = '#include "mixer_android_v2.h"\n'
        assert derived.count(insertion) == 1
        derived = derived.replace(insertion, insertion + '#define MIXER_FAULT_DECLARATIONS\n' + shim + '\n#undef MIXER_FAULT_DECLARATIONS\n')
        derived += '\n' + shim
        fault_dir = out / 'artifacts/derived'
        fault_dir.mkdir(parents=True)
        fault_c = fault_dir / 'jni.c'
        fault_c.write_text(derived)
        fault_java = fault_dir / 'NativeBridge.java'
        raw_java = (app / 'NativeBridge.java').read_text()
        assert raw_java.count('this.packet=packet.clone();') == 1
        fault_java.write_text(raw_java.replace('this.packet=packet.clone();', 'this.packet=FaultControl.clonePacket(packet);'))
        derivation = {'productionC': sha(source / 'native/android/bridge/jni.c'),
                      'productionJava': sha(app / 'NativeBridge.java'), 'derivedC': sha(fault_c),
                      'derivedJava': sha(fault_java), 'shim': sha(tests / 'fault-shim.c'),
                      'prepareOnlyReplacements': replacements, 'replacementCounts': counts,
                      'scope': 'Test-only substitutions; Swift library and engine contracts unchanged. No production allocation flag.'}
        (fault_dir / 'derivation.json').write_text(json.dumps(derivation, indent=2) + '\n')
        fault_classes = out / '.build/fault-classes'
        fault_classes.mkdir()
        run('derived-java17', [JDK / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror', '-d', fault_classes,
                              fault_java, app / 'UiPacket.java', app / 'Json.java', tests / 'FaultControl.java', tests / 'FaultTests.java'])
        for mode in ['debug', 'release']:
            scratch = out / '.build' / mode
            run(mode + '-swift-build', ['swift', 'build', '--package-path', 'native/android/engine', '--scratch-path', scratch,
                                       '--product', 'MixerAndroidEngine', '-c', mode, '-Xswiftc', '-warnings-as-errors'])
            engine = retain(scratch / mode / 'libMixerAndroidEngine.dylib', mode + '/libMixerAndroidEngine.dylib')
            common = ['-std=c11', '-shared', '-fPIC', '-O2', '-Wall', '-Wextra', '-Werror', '-pedantic',
                      '-I', source / 'native/android/bridge', '-I', JDK / 'include', '-I', JDK / 'include/darwin',
                      '-L', engine.parent, '-lMixerAndroidEngine', '-Wl,-rpath,' + str(engine.parent)]
            for kind, c, cp, name in [('production', source / 'native/android/bridge/jni.c', classes, 'BridgeTests'),
                                      ('derived', fault_c, fault_classes, 'FaultTests')]:
                libdir = out / 'artifacts' / mode / kind
                libdir.mkdir()
                jni = libdir / 'libmixer_android_jni.dylib'
                run(mode + '-' + kind + '-jni-compile', ['clang', *common, c, '-o', jni])
                for jvm, flags in [('normal', []), ('interpreted', ['-Xint'])]:
                    label = mode + '-' + kind + '-' + jvm
                    log = run(label, [JDK / 'bin/java', '--enable-native-access=ALL-UNNAMED', '-Xcheck:jni', *flags,
                                      '-Djava.library.path=' + str(libdir), '-cp', cp, 'dev.mixer.android.' + name])
                    assertions(label, log, 'production JNI' if kind == 'production' else 'derived JNI fault')
                symbols = run(mode + '-' + kind + '-symbols', ['nm', '-gU', jni]).read_text()
                for name in EXPORTS:
                    assert re.search(r'\bT _Java_dev_mixer_android_NativeBridge_' + name + r'$', symbols, re.M), name
        android_env = {'DEVELOPER_DIR': '/Applications/Xcode_26.6.app/Contents/Developer', 'JAVA_HOME': str(JDK)}
        run('android-swift-version', [SWIFT, '--version'], android_env)
        scratch = out / '.build/android'
        run('android-swift-build', [SWIFT, 'build', '--package-path', 'native/android/engine', '--scratch-path', scratch,
                                   '--swift-sdks-path', SDKS, '--swift-sdk', 'aarch64-unknown-linux-android28',
                                   '--product', 'MixerAndroidEngine', '-c', 'release', '-Xswiftc', '-warnings-as-errors'], android_env)
        engine = retain(scratch / 'aarch64-unknown-linux-android28/release/libMixerAndroidEngine.so', 'android/libMixerAndroidEngine.so')
        jni = engine.parent / 'libmixer_android_jni.so'
        run('android-production-jni-link', [LLVM / 'aarch64-linux-android28-clang', '-std=c11', '-shared', '-fPIC', '-O2',
                                          '-Wall', '-Wextra', '-Werror', '-pedantic', '-I', source / 'native/android/bridge',
                                          source / 'native/android/bridge/jni.c', '-L', engine.parent, '-lMixerAndroidEngine',
                                          '-Wl,--no-undefined', '-Wl,-z,max-page-size=16384', '-o', jni])
        symbols = run('android-production-jni-symbols', [LLVM / 'llvm-nm', '--defined-only', '--dynamic', jni]).read_text()
        for name in EXPORTS:
            assert re.search(r'\bT Java_dev_mixer_android_NativeBridge_' + name + r'$', symbols, re.M), name
        run('android-production-jni-needed', [LLVM / 'llvm-readelf', '-d', jni])
        all_classes = out / '.build/android-classes'
        all_classes.mkdir()
        run('android-all-java17', [JDK / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror', '-classpath', JAR,
                                   '-d', all_classes, *sorted(app.glob('*.java'))])
        dex = out / 'artifacts/android/dex'
        dex.mkdir()
        run('android-d8-min28', [SDK / 'build-tools/37.0.0/d8', '--min-api', '28', '--lib', JAR, '--output', dex,
                               *sorted(all_classes.rglob('*.class'))], android_env)
        receipt['unchangedLiveInputs'] = all(sha(ROOT / name) == value for name, value in manifest.items())
        assert receipt['unchangedLiveInputs']
        receipt['status'] = 'passed'
    except Exception as error:
        receipt['status'] = 'failed'
        receipt['failure'] = repr(error)
        raise
    finally:
        for artifact in sorted((out / 'artifacts').rglob('*')) if (out / 'artifacts').exists() else []:
            if artifact.is_file():
                receipt['artifacts'][str(artifact.relative_to(ROOT))] = sha(artifact)
        receipt['finishedUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save()


if __name__ == '__main__':
    main()
