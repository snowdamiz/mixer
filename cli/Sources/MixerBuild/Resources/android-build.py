#!/usr/bin/env python3
"""Owned local Android consumer builder. Uses installed official tools; never signs or installs."""
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import uuid
import zipfile

SDK_ID = 'aarch64-unknown-linux-android28'
ENV = os.environ.copy()
HOME_DIR = pathlib.Path.home()
SDK = pathlib.Path(ENV.get('ANDROID_HOME', ENV.get('ANDROID_SDK_ROOT', '/opt/homebrew/share/android-commandlinetools'))).resolve()
JDK = pathlib.Path(ENV.get('MIXER_JDK', '/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')).resolve()
SWIFT = pathlib.Path(ENV.get('MIXER_SWIFT', str(HOME_DIR / 'Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift'))).absolute()
SWIFT_SDKS = pathlib.Path(ENV.get('MIXER_SWIFT_SDKS_PATH', str(HOME_DIR / '.swiftpm/swift-sdks'))).resolve()
ART = pathlib.Path(ENV.get('MIXER_ANDROID_ARTIFACT_PATH', str(SWIFT_SDKS / 'swift-6.3.3-RELEASE_android.artifactbundle/swift-android'))).resolve()
NDK = ART / 'android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64'
RUNTIME = ART / 'swift-resources/usr/lib/swift-aarch64/android'
BT = SDK / 'build-tools/37.0.0'
JAR = SDK / 'platforms/android-37.0/android.jar'
ENV['JAVA_HOME'] = str(JDK)
ENV['PATH'] = str(JDK / 'bin') + os.pathsep + ENV.get('PATH', '')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def tree(path):
    """Hash installed tool distributions, including symlink text and target file bytes."""
    path = path.resolve(strict=True)
    if not path.is_dir():
        raise RuntimeError('Missing installed tool distribution: ' + str(path))
    h = hashlib.sha256()
    for base, dirs, names in os.walk(path, followlinks=False):
        dirs.sort()
        for name in sorted(names + [d for d in dirs if (pathlib.Path(base) / d).is_symlink()]):
            item = pathlib.Path(base) / name
            relative = item.relative_to(path).as_posix()
            if item.is_symlink():
                resolved = item.resolve(strict=True)
                if item.is_dir() and not resolved.is_relative_to(path):
                    raise RuntimeError('Installed distribution directory symlink escapes hashed root: ' + str(item))
                value = 'symlink:' + os.readlink(item)
                if item.is_file():
                    value += ':' + digest(item)
            elif item.is_file():
                value = digest(item)
            else:
                raise RuntimeError('Unsupported installed tool file: ' + str(item))
            h.update((relative + '\0' + value + '\n').encode())
    return h.hexdigest()


def source_tree(path):
    h = hashlib.sha256()
    skip = {'.build', '.git', '.swiftpm', 'node_modules', '.gradle', '.mixer', 'target', '.DS_Store'}
    files = []
    for base, dirs, names in os.walk(path, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in skip)
        for name in names:
            item = pathlib.Path(base) / name
            if name in skip or (name == '.env' or (name.startswith('.env.') and name != '.env.example')) or item.suffix.lower() in {'.pem', '.key', '.p12', '.pfx', '.mobileprovision', '.keystore', '.jks'}:
                continue
            if item.is_symlink():
                raise RuntimeError('Source snapshots reject symlinks: ' + str(item))
            files.append(item)
        for name in dirs:
            if (pathlib.Path(base) / name).is_symlink():
                raise RuntimeError('Source snapshots reject symlinks')
    for item in sorted(files):
        h.update((item.relative_to(path).as_posix() + '\0' + digest(item) + '\n').encode())
    return h.hexdigest()


def probe(args):
    return subprocess.check_output(list(map(str, args)), env=ENV, stderr=subprocess.STDOUT, text=True).strip()


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise RuntimeError('Duplicate JSON key in local build input: ' + key)
            result[key] = value
        return result
    data = path.read_bytes()
    if len(data) > 1024 * 1024:
        raise RuntimeError('Local build JSON input exceeds 1MiB: ' + str(path))
    return json.loads(data, object_pairs_hook=unique)


def configuration(value):
    known = {'schema', 'name', 'application', 'language', 'targets', 'toolchainLock', 'capabilities', 'updates'}
    if not isinstance(value, dict) or set(value) != known or type(value.get('schema')) is not int or value['schema'] != 1 or value['language'] != 'swift' or value['toolchainLock'] != 'mixer.lock':
        raise RuntimeError('Unsupported Android local configuration schema/fields.')
    if not isinstance(value['name'], str) or re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}', value['name']) is None:
        raise RuntimeError('Invalid Android application name; expected a bounded Swift identifier without path components.')
    if not isinstance(value['application'], str) or re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+', value['application']) is None:
        raise RuntimeError('Invalid Android application identifier; expected reverse-DNS components.')
    targets = value['targets']
    if not isinstance(targets, list) or not all(isinstance(t, str) for t in targets) or len(set(targets)) != len(targets) or not set(targets).issubset({'ios', 'android'}) or 'android' not in targets:
        raise RuntimeError('Android local targets must be unique ios/android entries including android.')
    if value['capabilities'] != []:
        raise RuntimeError('Android host supports an empty capability list only in this slice.')
    expected_updates = {'activation': 'cold-start', 'compatibility': 'exact-runtime-fingerprint', 'requireArtifactSignature': True, 'requireAssignmentSignature': True}
    if value['updates'] != expected_updates or type(value['updates'].get('requireArtifactSignature')) is not bool or type(value['updates'].get('requireAssignmentSignature')) is not bool:
        raise RuntimeError('Unsupported Android update policy configuration.')
    return value


def inspect():
    swift_version = probe([SWIFT, '--version'])
    if 'Swift version 6.3.3 ' not in swift_version:
        raise RuntimeError('Supported Android compiler is official Swift 6.3.3; set MIXER_SWIFT.')
    metadata = {
        'ndk': ART / 'android-ndk-r27d/source.properties',
        'platform': JAR.parent / 'source.properties',
        'build_tools': BT / 'source.properties',
        'jdk': JDK / 'release',
        'swift_sdk': ART / 'swift-sdk.json',
        'swift_toolset': ART / 'swift-toolset.json',
    }
    texts = {key: path.read_text() for key, path in metadata.items()}
    if '27.3.13750724' not in texts['ndk'] or 'Pkg.Revision=37.0.0' not in texts['build_tools'] or 'AndroidVersion.ApiLevel=37.0' not in texts['platform'] or 'JAVA_VERSION="25.' not in texts['jdk']:
        raise RuntimeError('Supported tools require NDK r27d, build-tools37.0.0, Android37.0 platform and JDK25.')
    tools = {
        'python': pathlib.Path(sys.executable).resolve(),
        'swift': SWIFT, 'clang': NDK / 'bin/aarch64-linux-android28-clang',
        'readelf': NDK / 'bin/llvm-readelf', 'nm': NDK / 'bin/llvm-nm',
        'java': JDK / 'bin/java', 'javac': JDK / 'bin/javac',
        'd8': BT / 'd8', 'aapt2': BT / 'aapt2', 'zipalign': BT / 'zipalign', 'dexdump': BT / 'dexdump',
    }
    for name, path in tools.items():
        if not path.is_file() or not os.access(path, os.X_OK):
            raise RuntimeError('Missing executable ' + name + ': ' + str(path))
    return {
        'schema': 1, 'sdk_id': SDK_ID, 'abi': 'arm64-v8a', 'min_api': 28, 'target_api': 37,
        'swift_version': swift_version, 'javac_version': probe([JDK / 'bin/javac', '--version']),
        'java_version': probe([JDK / 'bin/java', '--version']),
        'python_version': sys.version,
        'tools': {key: {'path': str(path), 'sha256': digest(path)} for key, path in tools.items()},
        'metadata': {key: {'path': str(path), 'sha256': digest(path)} for key, path in metadata.items()},
        'distributions': {
            'swift_toolchain': {'path': str(SWIFT.parent.parent.parent), 'sha256': tree(SWIFT.parent.parent.parent)},
            'swift_android_sdk': {'path': str(ART.parent), 'sha256': tree(ART.parent)},
            'android_platform': {'path': str(JAR.parent), 'sha256': tree(JAR.parent)},
            'android_build_tools': {'path': str(BT), 'sha256': tree(BT)},
            'jdk': {'path': str(JDK), 'sha256': tree(JDK)},
        },
        'sdk_search_path': str(SWIFT_SDKS),
    }


def build(root):
    lock = read_json(root / 'mixer.lock')
    if not isinstance(lock, dict) or type(lock.get('schema')) is not int or lock['schema'] != 1:
        raise RuntimeError('Unsupported local toolchain lock schema.')
    android = lock.get('android')
    if not android:
        raise RuntimeError('Android host is not generated. Create a new project with --platform android.')
    adapter = root / 'Generated/MixerAndroid'
    if source_tree(adapter) != android['adapterDigest'] or source_tree(root / 'Generated/MixerSDK') != lock['sdkDigest']:
        raise RuntimeError('Bundled SDK or Android adapter source differs from mixer.lock.')
    config = configuration(read_json(root / 'mixer.yml'))
    if any(p.is_file() for p in (root / 'Resources').rglob('*')):
        raise RuntimeError('Android resource packaging is not integrated; resources cannot be omitted.')
    output = root / '.mixer/android-build'
    output.mkdir(parents=True, exist_ok=True)
    receipt_path = output / 'build-receipt.json'
    receipt_path.unlink(missing_ok=True)
    apk_path = output / (config['name'] + '-unsigned.apk')
    apk_path.unlink(missing_ok=True)
    source_before = source_tree(root)
    build_input = {'run_id': uuid.uuid4().hex, 'source_tree_sha256': source_before,
                   'scope': 'Local observed mutation detection; not an immutable build sandbox or attestation.'}
    temporary_input = output / 'build-input.json.tmp'
    temporary_input.write_text(json.dumps(build_input, indent=2) + '\n')
    temporary_input.replace(output / 'build-input.json')
    identity = inspect()
    if identity != android['toolchain']:
        raise RuntimeError('Android toolchain differs from mixer.lock. Restore the exact installed tool distributions.')
    commands = []
    def run(args):
        args = list(map(str, args))
        p = subprocess.run(args, cwd=root, env=ENV, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        commands.append({'command': args, 'exit_code': p.returncode, 'output': p.stdout})
        print(p.stdout, end='', flush=True)
        if p.returncode:
            raise RuntimeError('Android build failed: ' + repr(args))
        return p.stdout
    package = root / 'Platforms/Android'
    swift_args = [SWIFT, 'build', '--package-path', package, '--scratch-path', output / 'swift', '--swift-sdks-path', SWIFT_SDKS, '--swift-sdk', SDK_ID, '-c', 'release', '--product', 'AppAndroid', '-Xlinker', '-z', '-Xlinker', 'max-page-size=16384']
    run(swift_args)
    bin_path = pathlib.Path(run(swift_args + ['--show-bin-path']).strip())
    engine = bin_path / 'libAppAndroid.so'
    if not engine.is_file():
        raise RuntimeError('Actual app Swift library missing: ' + str(engine))
    for path in [output / 'apk', output / 'classes', output / 'dex']:
        if path.exists():
            shutil.rmtree(path)
        path.mkdir()
    libdir = output / 'apk/lib/arm64-v8a'
    libdir.mkdir(parents=True)
    run([NDK / 'bin/aarch64-linux-android28-clang', '-shared', '-fPIC', '-O2', '-Wall', '-Wextra', '-Werror', '-I', adapter / 'bridge', adapter / 'bridge/jni.c', '-L', bin_path, '-lAppAndroid', '-Wl,-z,max-page-size=16384', '-o', libdir / 'libmixer_android_jni.so'])
    shutil.copy2(engine, libdir / engine.name)
    system = {'libc.so', 'libdl.so', 'libm.so', 'liblog.so', 'libandroid.so'}
    pending = list(libdir.glob('*.so'))
    dependencies = {}
    while pending:
        lib = pending.pop()
        header = run([NDK / 'bin/llvm-readelf', '-h', lib])
        if 'ELF64' not in header or 'AArch64' not in header:
            raise RuntimeError('Native APK library is not arm64 ELF64: ' + lib.name)
        dynamic = run([NDK / 'bin/llvm-readelf', '-d', lib])
        needed = re.findall(r'\(NEEDED\).*\[([^\]]+)\]', dynamic)
        dependencies[lib.name] = needed
        for name in needed:
            if name in system or (libdir / name).exists():
                continue
            candidates = [RUNTIME / name, NDK / 'sysroot/usr/lib/aarch64-linux-android' / name]
            found = next((p for p in candidates if p.is_file()), None)
            if found is None:
                raise RuntimeError('Unresolved native runtime dependency: ' + name)
            shutil.copy2(found, libdir / name)
            pending.append(libdir / name)
    classes, dex = output / 'classes', output / 'dex'
    sources = sorted((adapter / 'app/src').rglob('*.java')) + sorted((package / 'Java').rglob('*.java'))
    run([JDK / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror', '-classpath', JAR, '-d', classes, *sources])
    run([BT / 'd8', '--min-api', '28', '--lib', JAR, '--output', dex, *sorted(classes.rglob('*.class'))])
    unsigned = output / 'unaligned.apk'
    run([BT / 'aapt2', 'link', '-I', JAR, '--manifest', package / 'AndroidManifest.xml', '--min-sdk-version', '28', '--target-sdk-version', '37', '-o', unsigned])
    with zipfile.ZipFile(unsigned, 'a', compression=zipfile.ZIP_DEFLATED) as archive:
        for item in sorted((output / 'apk').rglob('*')):
            if item.is_file():
                archive.write(item, item.relative_to(output / 'apk'))
        for item in dex.glob('*.dex'):
            archive.write(item, item.name)
    run([BT / 'zipalign', '-f', '-P', '16', '4', unsigned, apk_path])
    run([BT / 'zipalign', '-c', '-P', '16', '4', apk_path])
    badging = run([BT / 'aapt2', 'dump', 'badging', apk_path])
    if "package: name='" + config['application'] + "'" not in badging or 'dev.mixer.android.MixerActivity' not in badging or "native-code: 'arm64-v8a'" not in badging:
        raise RuntimeError('APK identity, native activity or ABI does not match generated app.')
    dex_dump = run([BT / 'dexdump', '-f', dex / 'classes.dex'])
    for descriptor in ['Ldev/mixer/android/MixerActivity;', 'Ldev/mixer/android/NativeBridge;', 'Ldev/mixer/android/NativeRenderer;']:
        if descriptor not in dex_dump:
            raise RuntimeError('Required owned Android class absent from dex: ' + descriptor)
    symbols = run([NDK / 'bin/llvm-nm', '-D', '--defined-only', engine])
    for symbol in ['mixer_android_create', 'mixer_android_exchange', 'mixer_android_destroy', 'AppFeatures', 'AppModels']:
        if symbol not in symbols:
            raise RuntimeError('App shared feature/model or ABI symbol missing: ' + symbol)
    with zipfile.ZipFile(apk_path) as archive:
        names = archive.namelist()
        if any(n.startswith('META-INF/') for n in names) or any('ChecklistEngine' in n for n in names):
            raise RuntimeError('Unexpected signing/example content in unsigned consumer.')
        content = {n: hashlib.sha256(archive.read(n)).hexdigest() for n in sorted(names)}
    normalized = hashlib.sha256(json.dumps(content, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    source_after = source_tree(root)
    if source_before != source_after or source_tree(adapter) != android['adapterDigest'] or source_tree(root / 'Generated/MixerSDK') != lock['sdkDigest']:
        apk_path.unlink(missing_ok=True)
        raise RuntimeError('Application/SDK/adapter source changed during the Android build; result rejected. Restore stable inputs and rebuild.')
    receipt = {
        'schema_version': 1, 'qualification': 'local-unsigned-cross-build-only',
        'application': config['application'], 'apk': str(apk_path), 'apk_sha256': digest(apk_path), 'apk_bytes': apk_path.stat().st_size,
        'apk_content_sha256': normalized, 'apk_entries': content,
        'source_tree_sha256': source_before, 'source_tree_after_sha256': source_after,
        'source_observation_scope': 'Before/after local mutation detection only; inputs are not isolated or immutably captured.',
        'sdk_digest': lock['sdkDigest'], 'adapter_digest': android['adapterDigest'],
        'toolchain': identity, 'native_dependencies': dependencies,
        'native_libraries': {p.name: digest(p) for p in sorted(libdir.glob('*.so'))}, 'commands': commands,
        'scope': 'Actual generated AppModels/AppFeatures Swift, owned JNI/native widgets, arm64 Android APK inspected. Unsigned; no install, device interaction, lifecycle, accessibility, performance, published SDK, store or FieldLog qualification.',
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    print('UNSIGNED APK:', apk_path, 'SHA256:', receipt['apk_sha256'], flush=True)
    print('RECEIPT:', receipt_path, flush=True)


if __name__ == '__main__':
    try:
        if len(sys.argv) == 2 and sys.argv[1] == 'inspect':
            print(json.dumps(inspect(), sort_keys=True))
        elif len(sys.argv) == 3 and sys.argv[1] == 'build':
            build(pathlib.Path(sys.argv[2]).resolve())
        else:
            raise RuntimeError('Usage: android-build.py inspect | build PROJECT')
    except Exception as error:
        print('Android local build error: ' + str(error), file=sys.stderr)
        sys.exit(1)
