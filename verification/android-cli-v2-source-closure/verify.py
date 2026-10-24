#!/usr/bin/env python3
"""Create a real CLI Android consumer and compile its exported Java closure."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
NAMES = ['Json', 'UiPacket', 'NativeRenderer', 'NativeBridge', 'MixerActivity',
         'AppearanceDescriptorV2', 'AppearanceGeometryV2', 'AppearanceResolverV2',
         'AppearanceNativePathsV2', 'InstalledAppearanceV2', 'NativeEnvironmentV2', 'NativeAppearanceViewsV2']
JDK = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
SDK = Path('/opt/homebrew/share/android-commandlinetools')
JAR = SDK / 'platforms/android-37.0/android.jar'
SDKS = Path('/Users/andreyyurlov/Library/org.swift.swiftpm/swift-sdks')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ['candidate-1', 'candidate-2']:
        raise SystemExit('usage: verify.py candidate-1|candidate-2')
    out = HERE / sys.argv[1]
    out.mkdir(exist_ok=False)
    source = out / '.build/source'
    source.mkdir(parents=True)
    # This regression exercises the Java export. Parallel unpublished Apple
    # consumer files are not needed to compile this CLI or its Java snapshot.
    paths = set(subprocess.check_output(['git', 'ls-files', '-z', '--', 'cli', 'sdk', 'updates'], cwd=ROOT).decode().strip('\0').split('\0'))
    paths.update('native/android/app/src/dev/mixer/android/' + name + '.java' for name in NAMES)
    paths.update(['native/android/bridge/jni.c', 'native/android/bridge/mixer_android.h',
                  'native/android/contracts/android-profile-v1.json',
                  'AGENTS.md', 'verification/android-cli-v2-source-closure/verify.py'])
    paths.update(str(p.relative_to(ROOT)) for p in (ROOT / 'native/android/engine/Sources/MixerAndroidRuntime').glob('*.swift'))
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
               'startedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'commands': [],
               'sourceManifestSHA256': sha(out / 'source-manifest.json'), 'sourceArchiveSHA256': sha(out / 'source.tar.gz'),
               'scope': 'Actual fresh CLI create, byte-locked renderer/runtime export, production Java compile and minAPI28 DEX. Generated app still uses legacy V1; no V2 appearance asset/opt-in, APK, native execution or device test.'}
    env = dict(os.environ, JAVA_HOME=str(JDK), PATH=str(JDK / 'bin') + os.pathsep + os.environ['PATH'], MIXER_SWIFT_SDKS_PATH=str(SDKS))

    def run(label, argv, cwd=source):
        argv = list(map(str, argv))
        log = out / (label + '.log')
        start = time.monotonic()
        with log.open('wb') as stream:
            result = subprocess.run(argv, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=900)
        receipt['commands'].append({'label': label, 'argv': argv, 'cwd': str(cwd), 'exitCode': result.returncode,
                                    'seconds': time.monotonic() - start, 'log': str(log.relative_to(ROOT)), 'sha256': sha(log)})
        print(label, result.returncode, flush=True)
        if result.returncode:
            for line in log.read_text(errors='replace').splitlines()[-12:]: print(line[:400], flush=True)
            raise RuntimeError(label)
        return log

    try:
        for label, argv in [('swift-version', ['swift', '--version']), ('javac-version', [JDK / 'bin/javac', '--version']),
                            ('d8-version', [SDK / 'build-tools/37.0.0/d8', '--version']), ('python-version', [sys.executable, '--version'])]:
            run(label, argv)
        scratch = out / '.build/cli'
        run('snapshot-regression', ['swift', 'test', '--package-path', 'cli', '--scratch-path', scratch,
                                    '--filter', 'androidSnapshotOwnsOnlyRuntimeRendererAndBridgeAndLocksExactBytes'])
        mixer = scratch / 'debug/mixer'
        assert mixer.is_file()
        receipt['cliBinarySHA256'] = sha(mixer)
        app = out / '.build/ClosureApp'
        run('create-consumer', [mixer, 'create', 'ClosureApp', '--directory', app,
                                '--application', 'dev.mixer.closure', '--sdk-path', source / 'sdk', '--platform', 'android',
                                '--android-adapter-path', source / 'native/android'])
        adapter = app / 'Generated/MixerAndroid'
        java = sorted((adapter / 'app/src').rglob('*.java'))
        assert {p.stem for p in java} == set(NAMES)
        exported = {}
        for path in java:
            name = str(path.relative_to(adapter))
            assert sha(path) == manifest['native/android/' + name], name
            exported[name] = sha(path)
        receipt['exportedJava'] = exported
        lock = json.loads((app / 'mixer.lock').read_text())
        driver = adapter / 'android-build.py'
        result = run('verify-adapter-lock', [sys.executable, '-c',
            'import runpy,sys,pathlib; print(runpy.run_path(sys.argv[1])["source_tree"](pathlib.Path(sys.argv[2])))', driver, adapter])
        assert result.read_text().strip() == lock['android']['adapterDigest']
        assert 'NativeBridge.exchange' in (adapter / 'app/src/dev/mixer/android/MixerActivity.java').read_text()
        assert not list(app.rglob('descriptor.json'))
        classes = out / '.build/classes'; classes.mkdir()
        run('exported-java-compile', [JDK / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror',
                                     '-classpath', JAR, '-d', classes, *java])
        dex = out / 'dex'; dex.mkdir()
        run('exported-dex-min28', [SDK / 'build-tools/37.0.0/d8', '--min-api', '28', '--lib', JAR,
                                 '--output', dex, *sorted(classes.rglob('*.class'))])
        with zipfile.ZipFile(out / 'classes.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(classes.rglob('*.class')): archive.write(path, path.relative_to(classes))
        with tarfile.open(out / 'generated-consumer.tar.gz', 'w:gz') as archive:
            for path in sorted(app.rglob('*')):
                if path.is_file(): archive.add(path, arcname=path.relative_to(app), recursive=False)
        shutil.copy2(app / 'mixer.lock', out / 'consumer-mixer.lock')
        receipt['generatedConsumerSHA256'] = sha(out / 'generated-consumer.tar.gz')
        receipt['classesSHA256'] = sha(out / 'classes.zip')
        receipt['dexSHA256'] = {p.name: sha(p) for p in dex.glob('*.dex')}
        receipt['toolSHA256'] = {str(p): sha(p) for p in [JAR, JDK / 'bin/javac', SDK / 'build-tools/37.0.0/lib/d8.jar']}
        receipt['unchangedLiveInputs'] = all(sha(ROOT / name) == value for name, value in manifest.items())
        assert receipt['unchangedLiveInputs']
        receipt['status'] = 'passed'
    except Exception as failure:
        receipt['status'] = 'failed'; receipt['failure'] = repr(failure)
        raise
    finally:
        receipt['finishedUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__': main()
