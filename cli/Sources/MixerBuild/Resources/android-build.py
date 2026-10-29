#!/usr/bin/env python3
"""Owned local Android consumer builder. Uses installed official tools; never signs or installs."""
import hashlib
import json
import os
import pathlib
import re
import shutil
import stat
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
APPEARANCE_ASSET = 'assets/MixerAppearanceV2/descriptor.json'
SOURCE_PROFILE_HEX = '__MIXER_ANDROID_SOURCE_PROFILE_HEX__'
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


def source_profile():
    """Build-only decode. Raw import/inspect never evaluates the template marker."""
    message = 'Android SDK source profile is not rendered or supported; recreate with the matching CLI.'
    try:
        def unique(pairs):
            value = {}
            for key, item in pairs:
                if key in value:
                    raise ValueError('duplicate profile key')
                value[key] = item
            return value
        value = json.loads(bytes.fromhex(SOURCE_PROFILE_HEX), object_pairs_hook=unique)
        keys = {'schema', 'id', 'sdk_compatibility_sha256', 'adapter_compatibility_sha256',
                'default_descriptor', 'sdk_files', 'adapter_files', 'wire'}
        if not isinstance(value, dict) or set(value) != keys or type(value['schema']) is not int or value['schema'] != 1 or value['id'] != 'mixer.android-source-pair.6':
            raise ValueError('unsupported profile shape/id')
        def identity(item):
            return (isinstance(item, dict) and set(item) == {'bytes', 'sha256'} and
                    type(item['bytes']) is int and 0 < item['bytes'] <= 1_048_576 and
                    isinstance(item['sha256'], str) and re.fullmatch('[0-9a-f]{64}', item['sha256']) is not None)
        if not identity(value['default_descriptor']) or value['default_descriptor']['bytes'] > 65_536:
            raise ValueError('unsupported descriptor identity')
        for kind, count in (('sdk', 22), ('adapter', 23)):
            files = value[kind + '_files']
            if not isinstance(files, dict) or len(files) != count:
                raise ValueError('unsupported source map')
            for path, item in files.items():
                if (not isinstance(path, str) or not path.isascii() or
                    any(part in ('', '.', '..') for part in path.split('/')) or path.startswith('/') or not identity(item)):
                    raise ValueError('unsupported source identity')
            projection = hashlib.sha256(''.join(path + '\0' + files[path]['sha256'] + '\n' for path in sorted(files)).encode()).hexdigest()
            if projection != value[kind + '_compatibility_sha256']:
                raise ValueError('unsupported projection digest')
        wire = value['wire']
        if (not isinstance(wire, dict) or set(wire) != {'android_profile_id', 'appearance_format', 'appearance_recipe', 'document_schema', 'native_packet_schema', 'staged_C_ABI'} or
            type(wire['document_schema']) is not int or type(wire['native_packet_schema']) is not int or
            wire['document_schema'] != 1 or wire['native_packet_schema'] != 1 or
            not all(isinstance(item, str) and item for key, item in wire.items() if key not in ('document_schema', 'native_packet_schema'))):
            raise ValueError('unsupported wire shape')
        return value
    except (ValueError, TypeError, KeyError, UnicodeError) as error:
        raise RuntimeError(message) from error


def profile_lock(profile):
    return {key: profile[key] for key in ('id', 'sdk_compatibility_sha256', 'adapter_compatibility_sha256', 'default_descriptor')}


def profile_required(android, profile):
    if not isinstance(android, dict) or not isinstance(android.get('profile'), dict):
        raise RuntimeError('android.sdk-profile-required: Android project predates source-pair admission; explicitly migrate or recreate with the matching first-party CLI/SDK distribution.')
    if android['profile'] != profile_lock(profile):
        raise RuntimeError('android.sdk-profile-mismatch: recreate with the matching first-party CLI/SDK distribution (' + profile['id'] + ').')


def profile_failure(path):
    return RuntimeError('Android SDK source compatibility rejected (' + str(path) + '); install the matching first-party CLI/SDK distribution. Local locks cannot authorize changed sources.')


def ordinary_directory(path):
    try:
        if not stat.S_ISDIR(path.lstat().st_mode):
            raise profile_failure(path)
    except FileNotFoundError as error:
        raise profile_failure(path) from error


def exact_path(root, relative, directory=False, identity=None):
    current = root
    parts = relative.split('/')
    for index, name in enumerate(parts):
        ordinary_directory(current)
        if name not in [p.name for p in current.iterdir()]:
            raise profile_failure(relative)
        current = current / name
        if index < len(parts) - 1 or directory:
            ordinary_directory(current)
    if identity is not None:
        info = current.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size != identity['bytes']:
            raise profile_failure(relative + ': expected ordinary pinned-size file')
    return current


def closed_sources(root, relative, files):
    directory = exact_path(root, relative, directory=True)
    prefix = relative + '/'
    expected = {p[len(prefix):].split('/')[0] for p in files if p.startswith(prefix)}
    if {p.name for p in directory.iterdir()} != expected:
        raise profile_failure(relative + ': exact directory inventory')
    for name in sorted(expected):
        item = relative + '/' + name
        if item in files:
            exact_path(root, item, identity=files[item])
        else:
            closed_sources(root, item, files)


def sdk_layout(root, profile):
    ordinary_directory(root)
    names = [p.name for p in root.iterdir()]
    # This MUST precede transformation/classification and entry lstat/follow/read.
    if not all(name.isascii() for name in names):
        raise profile_failure('non-ASCII SDK-root entry name')
    for name in names:
        if name.lower().startswith('package') and name != 'Package.swift':
            raise profile_failure('reserved SDK manifest namespace: ' + name)
    exact_path(root, 'Package.swift', identity=profile['sdk_files']['Package.swift'])
    for relative in ('Sources/MixerCore', 'Sources/MixerUI'):
        closed_sources(root, relative, profile['sdk_files'])


def adapter_layout(root, profile):
    for relative, identity in profile['adapter_files'].items():
        exact_path(root, relative, identity=identity)
    for relative in ('Sources/MixerAndroidRuntime', 'app/src', 'bridge', 'contracts'):
        closed_sources(root, relative, profile['adapter_files'])


def pinned_read(path, identity):
    with path.open('rb') as stream:
        data = stream.read(identity['bytes'] + 1)
    if len(data) != identity['bytes'] or hashlib.sha256(data).hexdigest() != identity['sha256']:
        raise profile_failure(path)
    return data


def admit_source_pair(root, profile):
    generated = exact_path(root, 'Generated', directory=True)
    adapter = exact_path(generated, 'MixerAndroid', directory=True)
    # Closed appearance topology/type/size before required-source content reads.
    appearance_layout(adapter)
    sdk = exact_path(generated, 'MixerSDK', directory=True)
    sdk_layout(sdk, profile)
    adapter_layout(adapter, profile)
    appearance = pinned_read(adapter / 'app' / APPEARANCE_ASSET, profile['default_descriptor'])
    for directory, key in ((sdk, 'sdk_files'), (adapter, 'adapter_files')):
        for relative, identity in profile[key].items():
            pinned_read(directory / relative, identity)
    return appearance


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


def appearance_layout(adapter):
    """Admit the complete closed asset layout before source_tree opens any asset.

    This checks local layout/type/size and bytes, not Swift/Java codec semantics.
    A recomputed unauthenticated lock is not default provenance or authority.
    """
    exact_path(adapter.parent.parent, 'Generated/MixerAndroid/app/assets/MixerAppearanceV2', directory=True)
    assets = adapter / 'app/assets'
    descriptor = adapter / 'app' / APPEARANCE_ASSET
    for path in (adapter.parent, adapter, adapter / 'app', assets, descriptor.parent):
        try:
            info = path.lstat()
        except FileNotFoundError as error:
            raise RuntimeError('Missing Android appearance asset directory: ' + str(path)) from error
        if not stat.S_ISDIR(info.st_mode):
            raise RuntimeError('Android appearance asset directories must be ordinary directories: ' + str(path))
    # Inspect every name, including hidden, excluded-extension and skipped names.
    if sorted(p.name for p in assets.iterdir()) != ['MixerAppearanceV2'] or sorted(p.name for p in descriptor.parent.iterdir()) != ['descriptor.json']:
        raise RuntimeError('Android appearance assets must contain only MixerAppearanceV2/descriptor.json.')
    info = descriptor.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise RuntimeError('Android appearance descriptor must be a regular file without symlinks.')
    if not 1 <= info.st_size <= 65_536:
        raise RuntimeError('Android appearance descriptor must contain 1..65536 bytes.')
    return descriptor, info.st_size


def appearance_input(adapter):
    descriptor, size = appearance_layout(adapter)
    with descriptor.open('rb') as stream:
        data = stream.read(65_537)
    if len(data) != size:
        raise RuntimeError('Android appearance descriptor changed during admission.')
    return data


def appearance_archive(archive, expected):
    """Require one exact final asset and reject all duplicate ZIP names."""
    names = archive.namelist()
    if len(names) != len(set(names)):
        raise RuntimeError('Duplicate ZIP entries in unsigned Android APK.')
    if sorted(n for n in names if n == 'assets' or n.startswith('assets/')) != [APPEARANCE_ASSET]:
        raise RuntimeError('APK must contain exactly the admitted Android appearance asset.')
    if archive.getinfo(APPEARANCE_ASSET).file_size != len(expected) or archive.read(APPEARANCE_ASSET) != expected:
        raise RuntimeError('APK Android appearance bytes differ from admitted locked input.')
    return {'asset': APPEARANCE_ASSET, 'bytes': len(expected), 'sha256': hashlib.sha256(expected).hexdigest(),
            'scope': 'Exact local locked-input packaging only; direct-driver layout/size admission does not establish codec semantics, copied-SDK compatibility, installed use or signed authority.'}


def checked_output(root, create=False):
    """Reject redirected local staging before cleanup or writes.

    SwiftPM creates internal directory links (for example release -> triple/release),
    which are allowed only when their existing target stays inside this output.
    This is a local preflight, not isolation from concurrent same-user writers or
    arbitrary code executed by a package's build tools.
    """
    root = root.resolve(strict=True)
    output = root / '.mixer/android-build'
    for path in (root / '.mixer', output):
        try:
            info = path.lstat()
        except FileNotFoundError:
            if create:
                path.mkdir()
            continue
        if not stat.S_ISDIR(info.st_mode):
            raise RuntimeError('Unsafe Android staging directory: ' + str(path))
    if not output.exists():
        return output
    for base, dirs, names in os.walk(output, followlinks=False):
        for name in sorted(dirs + names):
            path = pathlib.Path(base) / name
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                try:
                    target = path.resolve(strict=True)
                except (OSError, RuntimeError) as error:
                    raise RuntimeError('Unsafe Android staging link: ' + str(path)) from error
                if not target.is_relative_to(output):
                    raise RuntimeError('Unsafe Android staging link escapes output: ' + str(path))
                info = target.stat()
            if stat.S_ISREG(info.st_mode):
                if info.st_nlink != 1:
                    raise RuntimeError('Unsafe Android staging hard link: ' + str(path))
            elif not stat.S_ISDIR(info.st_mode):
                raise RuntimeError('Unsafe Android staging special file: ' + str(path))
    return output


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
    profile = source_profile()
    lock = read_json(root / 'mixer.lock')
    if not isinstance(lock, dict) or type(lock.get('schema')) is not int or lock['schema'] != 1:
        raise RuntimeError('Unsupported local toolchain lock schema.')
    android = lock.get('android')
    profile_required(android, profile)
    adapter = root / 'Generated/MixerAndroid'
    appearance = admit_source_pair(root, profile)
    if source_tree(adapter) != android['adapterDigest'] or source_tree(root / 'Generated/MixerSDK') != lock['sdkDigest']:
        raise RuntimeError('Bundled SDK or Android adapter source differs from mixer.lock.')
    config = configuration(read_json(root / 'mixer.yml'))
    if any(p.is_file() for p in (root / 'Resources').rglob('*')):
        raise RuntimeError('Android resource packaging is not integrated; resources cannot be omitted.')
    output = checked_output(root, create=True)
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
        checked_output(root)
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
        checked_output(root)
        if path.exists():
            shutil.rmtree(path)
        path.mkdir()
    libdir = output / 'apk/lib/arm64-v8a'
    libdir.mkdir(parents=True)
    run([NDK / 'bin/aarch64-linux-android28-clang', '-shared', '-fPIC', '-O2', '-Wall', '-Wextra', '-Werror', '-I', adapter / 'bridge', adapter / 'bridge/jni.c', '-L', bin_path, '-lAppAndroid', '-Wl,--no-undefined', '-Wl,-z,max-page-size=16384', '-o', libdir / 'libmixer_android_jni.so'])
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
    if admit_source_pair(root, profile) != appearance or source_tree(adapter) != android['adapterDigest']:
        raise RuntimeError('Android appearance/adapter input changed before packaging.')
    run([BT / 'aapt2', 'link', '-I', JAR, '--manifest', package / 'AndroidManifest.xml', '-A', adapter / 'app/assets', '--min-sdk-version', '28', '--target-sdk-version', '37', '-o', unsigned])
    checked_output(root)
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
    for symbol in ['mixer_android_create', 'mixer_android_exchange', 'mixer_android_destroy', 'mixer_android_prepare_v2', 'mixer_android_commit_v2', 'mixer_android_abort_v2', 'AppFeatures', 'AppModels']:
        if symbol not in symbols:
            raise RuntimeError('App shared feature/model or ABI symbol missing: ' + symbol)
    with zipfile.ZipFile(apk_path) as archive:
        names = archive.namelist()
        appearance_identity = appearance_archive(archive, appearance)
        if any(n.startswith('META-INF/') for n in names) or any('ChecklistEngine' in n for n in names):
            raise RuntimeError('Unexpected signing/example content in unsigned consumer.')
        content = {n: hashlib.sha256(archive.read(n)).hexdigest() for n in sorted(names)}
    normalized = hashlib.sha256(json.dumps(content, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if admit_source_pair(root, profile) != appearance:
        apk_path.unlink(missing_ok=True)
        raise RuntimeError('Android appearance input changed during the build.')
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
        'source_profile': profile_lock(profile), 'source_profile_observation': 'matched-reviewed-source-pair',
        'appearance_descriptor': appearance_identity,
        'toolchain': identity, 'native_dependencies': dependencies,
        'native_libraries': {p.name: digest(p) for p in sorted(libdir.glob('*.so'))}, 'commands': commands,
        'scope': 'Actual generated AppModels/AppFeatures Swift, owned JNI/native widgets, arm64 Android APK inspected. Unsigned; no install, device interaction, lifecycle, accessibility, performance, published SDK, store or FieldLog qualification.',
    }
    checked_output(root)
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
