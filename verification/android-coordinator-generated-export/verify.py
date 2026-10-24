#!/usr/bin/env python3
"""Export-only proof: frozen CLI inputs, host source-lock tests, unsigned APK.

Uses installed official compilers and offline artifact inspection. Never queries,
starts, installs onto or executes an Android/Apple runtime.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
JDK = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
SDK = Path('/opt/homebrew/share/android-commandlinetools')
SDKS = Path('/Users/andreyyurlov/Library/org.swift.swiftpm/swift-sdks')
COORDINATOR = 'native/android/app/src/dev/mixer/android/NativeCoordinatorV2.java'
CLASS = 'dev/mixer/android/NativeCoordinatorV2.class'
ACCEPTANCE = 'verification/android-native-v2-coordinator-root-review/acceptance.json'
EXPORTS = ['mixer_android_create', 'mixer_android_destroy', 'mixer_android_exchange',
           'mixer_android_prepare_v2', 'mixer_android_commit_v2', 'mixer_android_abort_v2']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(manifest):
    value = ''.join(name + '\0' + digest + '\n' for name, digest in sorted(manifest.items()))
    return hashlib.sha256(value.encode()).hexdigest()


def main():
    if len(sys.argv) != 2 or not re.fullmatch(r'candidate-[1-9][0-9]*', sys.argv[1]):
        raise SystemExit('usage: verify.py candidate-N')
    out = HERE / sys.argv[1]
    out.mkdir(exist_ok=False)
    scratch = out / '.build'
    source = scratch / 'source'
    source.mkdir(parents=True)
    # Capture the actual CLI dependency closure once. Build and source-lock tests
    # use this isolated copy even if unrelated root work advances HEAD.
    paths = set(subprocess.check_output(['git', 'ls-files', '-z', '--', 'cli', 'sdk', 'updates'],
                                        cwd=ROOT).decode().strip('\0').split('\0'))
    paths.update(str(p.relative_to(ROOT)) for p in (ROOT / 'native/android/app/src').rglob('*.java'))
    paths.update(str(p.relative_to(ROOT)) for p in (ROOT / 'native/android/engine/Sources/MixerAndroidRuntime').rglob('*.swift'))
    paths.update(['native/android/bridge/jni.c', 'native/android/bridge/mixer_android.h',
                  'native/android/bridge/mixer_android_v2.h', 'native/android/contracts/android-profile-v1.json',
                  'AGENTS.md', 'THIRD_PARTY.yml', ACCEPTANCE,
                  'verification/android-native-v2-coordinator/candidate-3/source-lock.json',
                  'verification/android-generated-v2-bridge/candidate-3/source-manifest.json',
                  'verification/computer-use-pause-2026-10-24/receipt.json',
                  'verification/android-coordinator-generated-export/verify.py'])
    manifest = {}
    for name in sorted(paths):
        src, dst = ROOT / name, source / name
        assert src.is_file() and not src.is_symlink(), name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        manifest[name] = sha(dst)
    accepted = json.loads((source / ACCEPTANCE).read_text())
    assert accepted['nativeAcceptance'] is False and accepted['publicActivityOptIn'] is False
    assert accepted['privateNativeAPIFloor'] == 36 and accepted['productionDEXMinAPI'] == 28
    native = {name: digest for name, digest in manifest.items() if name.startswith('native/android/')}
    prior_export = json.loads((source / 'verification/android-generated-v2-bridge/candidate-3/source-manifest.json').read_text())
    for name, digest in native.items():
        if name == 'native/android/contracts/android-profile-v1.json':
            assert prior_export[name] == digest, 'changed V1 compile profile'
        else:
            assert accepted['bindings'][name] == digest, 'unaccepted native input: ' + name
    (out / 'source-manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    with tarfile.open(out / 'source.tar.gz', 'w:gz') as archive:
        for name in sorted(paths):
            archive.add(source / name, arcname=name, recursive=False)
    receipt = {
        'schema': 1, 'status': 'running', 'startedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'sourceTreeSHA256': tree(manifest), 'sourceInputs': len(manifest),
        'sourceManifestSHA256': sha(out / 'source-manifest.json'), 'sourceArchiveSHA256': sha(out / 'source.tar.gz'),
        'coordinatorSourceSHA256': manifest[COORDINATOR],
        'acceptedCoordinatorClassSHA256': accepted['executedCoordinatorClassSHA256'],
        'commands': [], 'artifacts': {}, 'nativeRuntimeRun': False, 'physicalRun': False,
        'publicActivityOptIn': False, 'privateNativeAPIFloor': 36,
        'nativeAcceptance': False, 'signedPresentation': False, 'gaAcceptance': False,
        'scope': 'Fresh generated source export, host CLI snapshot/lock tests, official unsigned arm64 API28 cross-build, exact class and DEX/ELF inspection. No Android/native/UI execution, signing, publication, store or FieldLog qualification.'}
    env = dict(os.environ, JAVA_HOME=str(JDK), PATH=str(JDK / 'bin') + os.pathsep + os.environ['PATH'],
               MIXER_SWIFT_SDKS_PATH=str(SDKS), ANDROID_HOME=str(SDK), MIXER_JDK=str(JDK))

    def save():
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')

    def run(label, argv, cwd=source, success=True):
        argv = list(map(str, argv))
        log = out / (label + '.log')
        started = time.monotonic()
        with log.open('wb') as stream:
            result = subprocess.run(argv, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=1200)
        receipt['commands'].append({'label': label, 'argv': argv, 'cwd': str(cwd), 'exitCode': result.returncode,
                                    'expectedSuccess': success, 'seconds': time.monotonic() - started,
                                    'log': str(log.relative_to(ROOT)), 'sha256': sha(log)})
        save()
        print(label, result.returncode, flush=True)
        if (result.returncode == 0) != success:
            print(log.read_text(errors='replace')[-4000:], flush=True)
            raise RuntimeError(label)
        return log

    def retain(src, name):
        dst = out / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        receipt['artifacts'][str(dst.relative_to(ROOT))] = sha(dst)

    try:
        for label, argv in [('host-swift-version', ['swift', '--version']),
                            ('javac-version', [JDK / 'bin/javac', '--version']),
                            ('javap-version', [JDK / 'bin/javap', '-version']),
                            ('d8-version', [SDK / 'build-tools/37.0.0/d8', '--version']),
                            ('python-version', [sys.executable, '--version'])]:
            run(label, argv)
        cli = scratch / 'cli'
        run('cli-export-snapshot-lock-tests', ['swift', 'test', '--package-path', 'cli', '--scratch-path', cli,
            '--filter', 'androidSnapshotOwnsOnlyRuntimeRendererCoordinator|androidCoordinatorSnapshotChanges'])
        mixer = cli / 'debug/mixer'
        assert mixer.is_file()
        receipt['cliBinarySHA256'] = sha(mixer)
        app = scratch / 'CoordinatorApp'
        run('create-consumer', [mixer, 'create', 'CoordinatorApp', '--directory', app,
            '--application', 'dev.mixer.coordinatorexport', '--sdk-path', source / 'sdk', '--platform', 'android',
            '--android-adapter-path', source / 'native/android'])
        adapter = app / 'Generated/MixerAndroid'
        generated_native = {}
        for path in sorted(adapter.rglob('*')):
            if path.is_file() and path.suffix in {'.java', '.c', '.h'}:
                relative = str(path.relative_to(adapter))
                assert sha(path) == manifest['native/android/' + relative]
                generated_native[relative] = sha(path)
        receipt['exportedNativeSources'] = generated_native
        assert 'app/src/dev/mixer/android/NativeCoordinatorV2.java' in generated_native
        assert not any('Instrumentation' in name or '/tests/' in name for name in generated_native)
        # A real generated project must reject changes to the newly exported
        # source before either CLI or direct driver creates build output.
        coordinator = adapter / 'app/src/dev/mixer/android/NativeCoordinatorV2.java'
        original = coordinator.read_bytes()
        coordinator.write_bytes(original + b'\n// deliberate locked source tamper\n')
        rejected = run('coordinator-tamper-cli-rejected', [mixer, 'build', '--platform', 'android'], cwd=app, success=False)
        assert 'lock.android-drift' in rejected.read_text()
        rejected = run('coordinator-tamper-driver-rejected',
                       [sys.executable, adapter / 'android-build.py', 'build', app], cwd=app, success=False)
        assert 'source differs from mixer.lock' in rejected.read_text()
        assert not (app / '.mixer').exists()
        coordinator.write_bytes(original)
        receipt['coordinatorTamperRejectedBeforeBuildOutput'] = True
        with tarfile.open(out / 'generated-consumer.tar.gz', 'w:gz') as archive:
            for path in sorted(app.rglob('*')):
                if path.is_file(): archive.add(path, arcname=path.relative_to(app), recursive=False)
        receipt['artifacts'][str((out / 'generated-consumer.tar.gz').relative_to(ROOT))] = sha(out / 'generated-consumer.tar.gz')
        run('generated-android-cross-build', [mixer, 'build', '--platform', 'android'], cwd=app)
        build = app / '.mixer/android-build'
        built = json.loads((build / 'build-receipt.json').read_text())
        assert built['qualification'] == 'local-unsigned-cross-build-only'
        assert built['source_tree_sha256'] == built['source_tree_after_sha256']
        assert built['toolchain']['min_api'] == 28 and built['toolchain']['abi'] == 'arm64-v8a'
        assert all(c['exit_code'] == 0 for c in built['commands'])
        assert any('-Wl,--no-undefined' in c['command'] for c in built['commands'])
        lock = json.loads((app / 'mixer.lock').read_text())
        assert built['adapter_digest'] == lock['android']['adapterDigest']
        assert built['sdk_digest'] == lock['sdkDigest'] and built['toolchain'] == lock['android']['toolchain']
        apk = build / 'CoordinatorApp-unsigned.apk'
        assert sha(apk) == built['apk_sha256']
        with zipfile.ZipFile(apk) as archive:
            assert len(archive.namelist()) == len(set(archive.namelist()))
            assert {name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()} == built['apk_entries']
            assert not any(name.startswith('META-INF/') for name in archive.namelist())
            assert archive.read('classes.dex') == (build / 'dex/classes.dex').read_bytes()
            assert archive.read('lib/arm64-v8a/libAppAndroid.so') == (build / 'apk/lib/arm64-v8a/libAppAndroid.so').read_bytes()
        for name in ['build-input.json', 'build-receipt.json', 'CoordinatorApp-unsigned.apk']:
            retain(build / name, 'baseline/' + name)
        for name in [CLASS, 'dev/mixer/android/NativeRenderer.class', 'dev/mixer/android/NativeBridge.class',
                     'dev/mixer/android/MixerActivity.class']:
            compiled = build / 'classes' / name
            previous = 'verification/android-native-v2-coordinator/candidate-3/production-classes/' + name
            assert sha(compiled) == accepted['bindings'][previous], name
            retain(compiled, 'classes/' + name)
        receipt['compiledCoordinatorClassSHA256'] = sha(build / 'classes' / CLASS)
        bytecode = run('activity-bytecode', [JDK / 'bin/javap', '-p', '-c', '-classpath', build / 'classes',
                                           'dev.mixer.android.MixerActivity']).read_text()
        assert 'NativeBridge.exchange:' in bytecode and 'NativeCoordinatorV2' not in bytecode
        dex = run('generated-dex-inspection', [SDK / 'build-tools/37.0.0/dexdump', '-d', build / 'dex/classes.dex']).read_text()
        assert "Class descriptor  : 'Ldev/mixer/android/NativeCoordinatorV2;'" in dex
        assert not any(name in dex for name in ['NativeCoordinatorV2HostTests', 'NativeCoordinatorV2IntegrationActivity',
                                               'NativeCoordinatorV2IntegrationInstrumentation', 'AdapterInstrumentation'])
        nm = Path(built['toolchain']['tools']['nm']['path'])
        symbols = run('app-native-export-inspection', [nm, '-D', '--defined-only',
                      build / 'apk/lib/arm64-v8a/libAppAndroid.so']).read_text()
        defined = {line.split()[-1] for line in symbols.splitlines() if line.split()}
        assert all(symbol in defined for symbol in EXPORTS)
        receipt['ordinaryCExports'] = EXPORTS
        receipt['publicV1ActivityClassUnchanged'] = True
        receipt['coordinatorDEXPresent'] = True
        receipt['unchangedNativeInputs'] = all(sha(ROOT / name) == value for name, value in native.items())
        assert receipt['unchangedNativeInputs']
        receipt['liveCapturedInputChanges'] = [name for name, value in manifest.items() if sha(ROOT / name) != value]
        assert not any(name in receipt['liveCapturedInputChanges'] for name in [
            'cli/Sources/MixerBuild/AndroidProject.swift', 'cli/Tests/MixerBuildTests/AndroidProjectTests.swift'])
        receipt['endingRevision'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        receipt['status'] = 'passed'
    except Exception as failure:
        receipt['status'] = 'failed'
        receipt['failure'] = repr(failure)
        raise
    finally:
        # Retained source archives, APK, exact class bytes, commands and logs are
        # sufficient for offline review; disposable compiler output is bounded.
        if scratch.exists():
            shutil.rmtree(scratch)
            receipt['cleanup'] = 'Removed owned .build source/compiler/generated-app scratch after recording source archives and available evidence; no runtime instance was started.'
        receipt['finishedUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save()


if __name__ == '__main__':
    main()
