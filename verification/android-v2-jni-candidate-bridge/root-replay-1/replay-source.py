#!/usr/bin/env python3
"""Verify retained bindings, then freshly compile/replay the retained JNI inputs."""
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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
JDK = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate')
    parser.add_argument('output')
    args = parser.parse_args()
    for name in [args.candidate, args.output]:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', name):
            parser.error('one bounded directory name required')
    candidate, out = HERE / args.candidate, HERE / args.output
    out.mkdir(exist_ok=False)
    receipt = {'status': 'running', 'startedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'commands': [], 'assertions': {}, 'artifacts': {}, 'bindingsChecked': 0,
               'scope': 'Independent binding checks and fresh host production/derived JNI compilation against retained real Swift libraries, then JVM execution. No Android runtime or hardware.'}

    def save():
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')

    def check(path, expected):
        assert path.is_file() and sha(path) == expected, path
        receipt['bindingsChecked'] += 1

    def run(label, argv):
        argv = [str(x) for x in argv]
        log = out / (label + '.log')
        started = time.monotonic()
        with log.open('wb') as stream:
            result = subprocess.run(argv, cwd=ROOT, env=dict(os.environ, JAVA_HOME=str(JDK)),
                                    stdout=stream, stderr=subprocess.STDOUT, timeout=120)
        receipt['commands'].append({'label': label, 'argv': argv, 'cwd': str(ROOT),
                                    'environment': {'JAVA_HOME': str(JDK)}, 'exitCode': result.returncode,
                                    'seconds': time.monotonic() - started, 'log': str(log.relative_to(ROOT)),
                                    'sha256': sha(log)})
        save()
        print(label, result.returncode, flush=True)
        assert result.returncode == 0, log.read_text()[-4000:]
        return log.read_text()

    try:
        original = json.loads((candidate / 'receipt.json').read_text())
        assert original['status'] == 'passed'
        receipt['candidateReceiptSHA256'] = sha(candidate / 'receipt.json')
        receipt['sourceRevision'] = original['sourceRevision']
        receipt['sourceTreeDigestSHA256'] = original['sourceTreeDigestSHA256']
        check(candidate / 'source-manifest.json', original['sourceManifestSHA256'])
        check(candidate / 'source.tar.gz', original['sourceArchiveSHA256'])
        manifest = json.loads((candidate / 'source-manifest.json').read_text())
        tree = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        assert tree == original['sourceTreeDigestSHA256']
        for command in original['commands']:
            check(ROOT / command['log'], command['sha256'])
            assert command['exitCode'] == 0
        for name, digest in original['artifacts'].items():
            check(ROOT / name, digest)
        source = out / '.build/source'
        source.mkdir(parents=True)
        with tarfile.open(candidate / 'source.tar.gz', 'r:gz') as archive:
            assert len(archive.getmembers()) == len(manifest)
            assert {m.name for m in archive.getmembers()} == set(manifest)
            for member in archive.getmembers():
                assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
                path = source / member.name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.extractfile(member).read())
                check(path, manifest[member.name])
        for name in ['native/android/bridge/jni.c', 'native/android/app/src/dev/mixer/android/NativeBridge.java']:
            check(ROOT / name, manifest[name])
        check(HERE / 'replay.py', sha(Path(__file__)))
        shutil.copyfile(__file__, out / 'replay-source.py')
        run('java-version', [JDK / 'bin/java', '--version'])
        run('clang-version', ['clang', '--version'])
        app = source / 'native/android/app/src/dev/mixer/android'
        tests = source / 'verification/android-v2-jni-candidate-bridge'
        derivation = json.loads((candidate / 'artifacts/derived/derivation.json').read_text())
        check(source / 'native/android/bridge/jni.c', derivation['productionC'])
        check(app / 'NativeBridge.java', derivation['productionJava'])
        check(candidate / 'artifacts/derived/jni.c', derivation['derivedC'])
        check(candidate / 'artifacts/derived/NativeBridge.java', derivation['derivedJava'])
        for kind in ['production', 'derived']:
            classes = out / 'artifacts' / kind / 'classes'
            classes.mkdir(parents=True)
            java = app / 'NativeBridge.java' if kind == 'production' else candidate / 'artifacts/derived/NativeBridge.java'
            extra = [tests / 'BridgeTests.java'] if kind == 'production' else [tests / 'FaultControl.java', tests / 'FaultTests.java']
            run(kind + '-fresh-java17', [JDK / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror', '-d', classes,
                                        java, app / 'UiPacket.java', app / 'Json.java', *extra])
            c = source / 'native/android/bridge/jni.c' if kind == 'production' else candidate / 'artifacts/derived/jni.c'
            for mode in ['debug', 'release']:
                libdir = out / 'artifacts' / kind / mode
                libdir.mkdir()
                engine = candidate / 'artifacts' / mode
                run(kind + '-' + mode + '-fresh-jni', ['clang', '-std=c11', '-shared', '-fPIC', '-O2', '-Wall',
                                                      '-Wextra', '-Werror', '-pedantic', '-I', source / 'native/android/bridge',
                                                      '-I', JDK / 'include', '-I', JDK / 'include/darwin', c,
                                                      '-L', engine, '-lMixerAndroidEngine', '-Wl,-rpath,' + str(engine),
                                                      '-o', libdir / 'libmixer_android_jni.dylib'])
                for jvm, flags in [('normal', []), ('interpreted', ['-Xint'])]:
                    label = kind + '-' + mode + '-' + jvm
                    name = 'BridgeTests' if kind == 'production' else 'FaultTests'
                    text = run(label, [JDK / 'bin/java', '--enable-native-access=ALL-UNNAMED', '-Xcheck:jni', *flags,
                                       '-Djava.library.path=' + str(libdir), '-cp', classes, 'dev.mixer.android.' + name])
                    match = re.fullmatch(r'PASS ([0-9]+) (production JNI|derived JNI fault) assertions\n', text)
                    assert match and int(match.group(1)) == original['assertions'][mode + '-' + kind + '-' + jvm]
                    receipt['assertions'][label] = int(match.group(1))
        receipt['status'] = 'passed'
    except Exception as error:
        receipt['status'] = 'failed'
        receipt['failure'] = repr(error)
        raise
    finally:
        if (out / 'artifacts').exists():
            receipt['artifacts'] = {str(p.relative_to(ROOT)): sha(p) for p in sorted((out / 'artifacts').rglob('*')) if p.is_file()}
        if (out / 'replay-source.py').exists():
            receipt['artifacts'][str((out / 'replay-source.py').relative_to(ROOT))] = sha(out / 'replay-source.py')
        receipt['finishedUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save()


if __name__ == '__main__':
    main()
