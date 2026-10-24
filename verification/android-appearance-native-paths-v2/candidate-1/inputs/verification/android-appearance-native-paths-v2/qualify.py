#!/usr/bin/env python3
"""Bounded Android Path compile/native checks; only explicit emulator targeting."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
JDK = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
SDK = Path('/opt/homebrew/share/android-commandlinetools')
BT = SDK / 'build-tools/37.0.0'
JAR = SDK / 'platforms/android-37.0/android.jar'
PACKAGE = 'dev.mixer.android.appearancepathsv2'
JAVA = [
    'native/android/app/src/dev/mixer/android/AppearanceGeometryV2.java',
    'native/android/app/src/dev/mixer/android/AppearanceNativePathsV2.java',
    'native/android/tests/AppearanceNativePathsV2Instrumentation.java',
]
INPUTS = JAVA + [
    'AGENTS.md', 'docs/ui-measured-appearance-v2-contract.md',
    'docs/android-appearance-native-paths-v2.md',
    'verification/ui-measured-appearance-v2-contract/shape-definitions.json',
    'verification/android-appearance-native-paths-v2/qualify.py',
    'verification/android-appearance-native-paths-v2/AndroidManifest.xml',
]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='new bounded receipt directory name')
    parser.add_argument('--emulator', help='explicit emulator-N serial; no device discovery')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}', args.output):
        parser.error('output must be one bounded directory name')
    if args.emulator and not re.fullmatch(r'emulator-[0-9]{4,5}', args.emulator):
        parser.error('only an explicit emulator-N serial is permitted')
    out = HERE / args.output
    out.mkdir(exist_ok=False)
    build = HERE / 'build' / args.output
    build.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, JAVA_HOME=str(JDK), PATH=str(JDK / 'bin') + os.pathsep + os.environ['PATH'])
    commands = []
    manifest = {}
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    tree = subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=ROOT, text=True).strip()
    initial_status = subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True)
    for name in INPUTS:
        src = ROOT / name
        destination = out / 'inputs' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, destination)
        manifest[name] = sha(destination)
    closure = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

    def run(name, argv, binary=False, timeout=120):
        command = list(map(str, argv))
        completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=timeout)
        log = out / (name + ('.png' if binary else '.log'))
        log.write_bytes(completed.stdout if binary else completed.stdout + completed.stderr)
        commands.append(dict(name=name, argv=command, cwd=str(ROOT), exitCode=completed.returncode,
                             output=str(log.relative_to(ROOT)), sha256=sha(log)))
        print(name, completed.returncode, flush=True)
        if completed.returncode:
            raise RuntimeError(name + ': ' + (completed.stdout + completed.stderr).decode(errors='replace')[-6000:])
        return completed.stdout if binary else completed.stdout.decode()

    status = 'failed'
    target = None
    native = dict(status='pending', reason='no explicit emulator serial supplied')
    error = None
    try:
        run('python-version', [sys.executable, '--version'])
        run('java-version', [JDK / 'bin/java', '--version'])
        run('javac-version', [JDK / 'bin/javac', '--version'])
        run('d8-version', [BT / 'd8', '--version'])
        run('aapt2-version', [BT / 'aapt2', 'version'])
        run('apksigner-version', [BT / 'apksigner', 'version'])
        run('adb-version', [SDK / 'platform-tools/adb', 'version'])
        run('emulator-version', [SDK / 'emulator/emulator', '-version'])
        source = [out / 'inputs' / name for name in JAVA]
        production = build / 'production-classes'; production.mkdir()
        run('production-java-compile', [JDK / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror',
                                       '-classpath', JAR, '-d', production, *source[:2]])
        production_dex = build / 'production-dex'; production_dex.mkdir()
        run('production-dex-min28', [BT / 'd8', '--min-api', '28', '--lib', JAR, '--output', production_dex,
                                      *sorted(production.rglob('*.class'))])
        classes = build / 'test-classes'; classes.mkdir()
        run('instrumentation-java-compile', [JDK / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror',
                                            '-classpath', JAR, '-d', classes, *source])
        dex = build / 'test-dex'; dex.mkdir()
        run('instrumentation-dex-min34', [BT / 'd8', '--min-api', '34', '--lib', JAR, '--output', dex,
                                         *sorted(classes.rglob('*.class'))])
        unsigned = build / 'unsigned.apk'
        run('package-test-manifest', [BT / 'aapt2', 'link', '-I', JAR, '--manifest',
                                      out / 'inputs/verification/android-appearance-native-paths-v2/AndroidManifest.xml',
                                      '--min-sdk-version', '34', '--target-sdk-version', '37', '-o', unsigned])
        with zipfile.ZipFile(unsigned, 'a', compression=zipfile.ZIP_DEFLATED) as apk:
            for path in sorted(dex.glob('*.dex')):
                apk.write(path, path.name)
        aligned = build / 'aligned.apk'
        run('align-test-apk', [BT / 'zipalign', '-f', '-p', '4', unsigned, aligned])
        key = HERE / 'build/test-only.keystore'
        if not key.exists():
            run('generate-test-only-key', [JDK / 'bin/keytool', '-genkeypair', '-keystore', key,
                 '-storepass', 'android', '-keypass', 'android', '-alias', 'test', '-keyalg', 'RSA',
                 '-keysize', '2048', '-validity', '365', '-dname', 'CN=Mixer Native Path Local Test'])
        apk = build / 'mixer-native-paths-v2-test.apk'
        run('sign-test-apk', [BT / 'apksigner', 'sign', '--ks', key, '--ks-pass', 'pass:android',
                              '--key-pass', 'pass:android', '--out', apk, aligned])
        run('verify-test-signature', [BT / 'apksigner', 'verify', '--verbose', apk])
        if args.emulator:
            adb = [SDK / 'platform-tools/adb', '-s', args.emulator]
            qemu = run('target-emulator-property', adb + ['shell', 'getprop', 'ro.kernel.qemu']).strip()
            if qemu != '1':
                raise RuntimeError('explicit serial is not an emulator; refusing target operations')
            target = {'serial': args.emulator, 'kind': 'emulator', 'ro.kernel.qemu': qemu}
            for prop in ['ro.product.model', 'ro.build.version.sdk', 'ro.build.version.release',
                         'ro.build.fingerprint', 'ro.boot.qemu.avd_name', 'sys.boot_completed']:
                target[prop] = run('target-' + prop.replace('.', '-'), adb + ['shell', 'getprop', prop]).strip()
            if int(target['ro.build.version.sdk']) < 34 or target['sys.boot_completed'] != '1':
                raise RuntimeError('API34+ and boot-complete emulator required for native iterator tests')
            run('install-standalone-test-package', adb + ['install', '-r', '--no-incremental', apk])
            package_path = run('installed-test-package-path', adb + ['shell', 'pm', 'path', PACKAGE]).strip()
            if not package_path.startswith('package:/data/app/') or not package_path.endswith('/base.apk'):
                raise RuntimeError('unexpected installed test package path')
            installed_hash = run('installed-apk-sha256', adb + ['shell', 'sha256sum', package_path[8:]]).split()[0]
            if installed_hash != sha(apk):
                raise RuntimeError('installed standalone test package hash differs')
            target['installedAPK_SHA256'] = installed_hash
            result = run('native-instrumentation', adb + ['shell', 'am', 'instrument', '-w',
                PACKAGE + '/dev.mixer.android.AppearanceNativePathsV2Instrumentation'])
            if 'INSTRUMENTATION_RESULT: status=passed' not in result or 'INSTRUMENTATION_CODE: 0' not in result:
                raise RuntimeError('instrumentation did not report explicit native pass')
            counts = {}
            for field in ['checks', 'native_paths', 'native_verbs']:
                match = re.search(r'INSTRUMENTATION_RESULT: ' + field + r'=(\d+)', result)
                if not match or int(match[1]) <= 0:
                    raise RuntimeError('missing native test count ' + field)
                counts[field] = int(match[1])
            run('native-path-fill', adb + ['exec-out', 'run-as', PACKAGE, 'cat', 'files/native-path-fill.png'], binary=True)
            native = dict(status='passed', **counts, scope='API37 emulator native Path/PathIterator/PathMeasure and software Canvas bitmap fill/clip')
        status = 'passed-compile-and-native-emulator' if args.emulator else 'passed-compile-native-pending'
    except Exception as failure:
        error = repr(failure)
        raise
    finally:
        unchanged = all(sha(ROOT / name) == digest for name, digest in manifest.items())
        artifacts = {str(p.relative_to(HERE)): sha(p) for suffix in ['*.class', '*.dex', '*.apk']
                     for p in build.rglob(suffix)}
        tools = {str(path): sha(path) for path in [JAR, BT / 'lib/d8.jar', BT / 'aapt2', BT / 'zipalign',
            BT / 'lib/apksigner.jar', JDK / 'bin/java', JDK / 'bin/javac', SDK / 'platform-tools/adb',
            SDK / 'emulator/emulator'] if path.exists()}
        receipt = dict(status=status if unchanged else 'failed-source-changed', observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            sourceRevision=revision, sourceTree=tree, sourceClosureSHA256=closure, sourceManifest=manifest,
            sourceUnchanged=unchanged, workingTreeStatusAtStart=initial_status, commands=commands,
            toolSHA256=tools, artifacts=artifacts, target=target, native=native, error=error,
            scope='Closed V2 geometry to fresh Android Path only. Production minimum-API28 D8 compile and standalone API34+ tests. No NativeRenderer integration, physical device, screen/hardware raster, signing authority, OTA release, FieldLog or GA proof.')
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
        if not unchanged and error is None:
            raise RuntimeError('bounded source closure changed during verification')
    print(status, flush=True)


if __name__ == '__main__':
    main()
