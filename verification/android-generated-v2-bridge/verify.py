#!/usr/bin/env python3
"""Fresh CLI consumer: generated Swift staging ABI, JNI link and unsigned APK."""
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


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if len(sys.argv) != 2 or not re.fullmatch(r'candidate-[1-9][0-9]*', sys.argv[1]):
        raise SystemExit('usage: verify.py candidate-N')
    out = HERE / sys.argv[1]
    out.mkdir(exist_ok=False)
    source = out / '.build/source'
    source.mkdir(parents=True)
    # CLI/Android compilation does not depend on the parallel unpublished UIKit
    # consumer. Capture tracked SDK sources plus the complete Java/runtime closure.
    paths = set(subprocess.check_output(['git', 'ls-files', '-z', '--', 'cli', 'sdk', 'updates'], cwd=ROOT).decode().strip('\0').split('\0'))
    paths.update(str(p.relative_to(ROOT)) for p in (ROOT / 'native/android/app/src').rglob('*.java'))
    paths.update(str(p.relative_to(ROOT)) for p in (ROOT / 'native/android/engine/Sources/MixerAndroidRuntime').glob('*.swift'))
    paths.update(['native/android/bridge/jni.c', 'native/android/bridge/mixer_android.h',
                  'native/android/bridge/mixer_android_v2.h', 'native/android/contracts/android-profile-v1.json',
                  'AGENTS.md', 'verification/android-generated-v2-bridge/verify.py'])
    manifest = {}
    for name in sorted(paths):
        src, dst = ROOT / name, source / name
        assert src.is_file() and not src.is_symlink(), name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        manifest[name] = sha(dst)
    (out / 'source-manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    with tarfile.open(out / 'source.tar.gz', 'w:gz') as archive:
        for name in sorted(paths):
            archive.add(source / name, arcname=name, recursive=False)
    receipt = {'status': 'running', 'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'startedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'commands': [], 'artifacts': {},
               'sourceManifestSHA256': sha(out / 'source-manifest.json'), 'sourceArchiveSHA256': sha(out / 'source.tar.gz'),
               'scope': 'Fresh CLI create, generated application host tests Debug/Release, official arm64 API28 unsigned APK build and missing-export link rejection. No emulator, device, V2 Activity opt-in or release qualification.'}
    env = dict(os.environ, JAVA_HOME=str(JDK), PATH=str(JDK / 'bin') + os.pathsep + os.environ['PATH'], MIXER_SWIFT_SDKS_PATH=str(SDKS))

    def save():
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')

    def run(label, argv, cwd=source, success=True):
        argv = list(map(str, argv)); log = out / (label + '.log'); start = time.monotonic()
        with log.open('wb') as stream:
            result = subprocess.run(argv, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=1200)
        receipt['commands'].append({'label': label, 'argv': argv, 'cwd': str(cwd), 'exitCode': result.returncode,
                                    'expectedSuccess': success, 'seconds': time.monotonic() - start,
                                    'log': str(log.relative_to(ROOT)), 'sha256': sha(log)})
        save(); print(label, result.returncode, flush=True)
        if (result.returncode == 0) != success:
            print(log.read_text(errors='replace')[-4000:], flush=True)
            raise RuntimeError(label)
        return log

    def retain(src, name):
        dst = out / name; dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        receipt['artifacts'][str(dst.relative_to(ROOT))] = sha(dst)

    try:
        for label, argv in [('swift-version', ['swift', '--version']), ('javac-version', [JDK / 'bin/javac', '--version']),
                            ('d8-version', [SDK / 'build-tools/37.0.0/d8', '--version']), ('python-version', [sys.executable, '--version'])]:
            run(label, argv)
        scratch = out / '.build/cli'
        run('cli-android-regressions', ['swift', 'test', '--package-path', 'cli', '--scratch-path', scratch,
                                       '--filter', 'Android|android'])
        mixer = scratch / 'debug/mixer'; assert mixer.is_file()
        receipt['cliBinarySHA256'] = sha(mixer)
        app = out / '.build/StagedApp'
        run('create-consumer', [mixer, 'create', 'StagedApp', '--directory', app,
                               '--application', 'dev.mixer.staged', '--sdk-path', source / 'sdk', '--platform', 'android',
                               '--android-adapter-path', source / 'native/android'])
        adapter = app / 'Generated/MixerAndroid'
        for name in ['bridge/jni.c', 'bridge/mixer_android.h', 'bridge/mixer_android_v2.h']:
            assert sha(adapter / name) == manifest['native/android/' + name]
        for mode in ['debug', 'release']:
            run('generated-session-' + mode, ['swift', 'test', '--package-path', app / 'Platforms/Android',
                                              '--scratch-path', out / '.build' / ('host-' + mode), '-c', mode])
        # Capture only source inputs before the APK builder creates .mixer output.
        with tarfile.open(out / 'generated-consumer.tar.gz', 'w:gz') as archive:
            for path in sorted(app.rglob('*')):
                if path.is_file(): archive.add(path, arcname=path.relative_to(app), recursive=False)
        receipt['artifacts'][str((out / 'generated-consumer.tar.gz').relative_to(ROOT))] = sha(out / 'generated-consumer.tar.gz')
        run('generated-android-build', [mixer, 'build', '--platform', 'android'], cwd=app)
        build = app / '.mixer/android-build'
        qualification = json.loads((build / 'build-receipt.json').read_text())
        assert qualification['qualification'] == 'local-unsigned-cross-build-only'
        assert qualification['source_tree_sha256'] == qualification['source_tree_after_sha256']
        assert all(c['exit_code'] == 0 for c in qualification['commands'])
        assert any('-Wl,--no-undefined' in c['command'] for c in qualification['commands'])
        apk = build / 'StagedApp-unsigned.apk'
        assert sha(apk) == qualification['apk_sha256']
        with zipfile.ZipFile(apk) as archive:
            assert {n: hashlib.sha256(archive.read(n)).hexdigest() for n in archive.namelist()} == qualification['apk_entries']
            assert 'lib/arm64-v8a/libAppAndroid.so' in archive.namelist()
            assert 'lib/arm64-v8a/libmixer_android_jni.so' in archive.namelist()
        for name in ['build-input.json', 'build-receipt.json', 'StagedApp-unsigned.apk']:
            retain(build / name, 'baseline/' + name)
        # A real app-owned edit removes one C symbol. The production driver must
        # reject at JNI linking and remove its old success artifact/receipt.
        entry = app / 'Platforms/Android/Sources/AppAndroid/NativeEntry.swift'
        before = entry.read_text(); declaration = '@_cdecl("mixer_android_commit_v2")'
        assert before.count(declaration) == 1
        entry.write_text(before.replace(declaration, '// deliberate missing C export'))
        retain(entry, 'negative/NativeEntry.swift')
        failure = run('missing-export-build-rejected', [mixer, 'build', '--platform', 'android'], cwd=app, success=False)
        error = failure.read_text(errors='replace')
        assert 'undefined symbol: mixer_android_commit_v2' in error
        assert not apk.exists() and not (build / 'build-receipt.json').exists()
        receipt['missingExportRejectsAtLink'] = True
        receipt['staleSuccessArtifactsRemoved'] = True
        receipt['unchangedLiveInputs'] = all(sha(ROOT / name) == value for name, value in manifest.items())
        assert receipt['unchangedLiveInputs'], 'source changed during qualification'
        receipt['status'] = 'passed'
    except Exception as failure:
        receipt['status'] = 'failed'; receipt['failure'] = repr(failure)
        raise
    finally:
        receipt['finishedUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat(); save()


if __name__ == '__main__': main()
