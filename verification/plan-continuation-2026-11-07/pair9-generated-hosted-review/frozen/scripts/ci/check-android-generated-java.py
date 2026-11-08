#!/usr/bin/env python3
"""Actual CLI Debug/Release Android creation and Java/D8 consumer checks.

Requires explicit installed tool paths. Never downloads tools, builds an APK,
signs, installs, launches a runtime, or queries devices. Importing is inert.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
POLICY = 'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift'
DRIVER = 'cli/Sources/MixerBuild/Resources/android-build.py'
MARKER = '__MIXER_ANDROID_SOURCE_PROFILE_HEX__'
DESCRIPTOR = 'app/assets/MixerAppearanceV2/descriptor.json'
MODES = ('debug', 'release')
FORMS = ('original', 'relocated', 'exported')
PRODUCER_JOBS = 2
JAVAP_STDOUT_BYTES = 8_388_608


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def identity(path):
    require(stat.S_ISREG(path.lstat().st_mode), 'Expected regular file: ' + str(path))
    h = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1_048_576), b''):
            size += len(chunk)
            h.update(chunk)
    return {'bytes': size, 'sha256': h.hexdigest()}


def inventory(root):
    """No source filtering: preserve the entire actual emitted consumer graph."""
    require(stat.S_ISDIR(root.lstat().st_mode), 'Expected ordinary directory: ' + str(root))
    result = {}
    for base, dirs, names in os.walk(root, followlinks=False):
        for name in dirs:
            require(not (Path(base) / name).is_symlink(), 'Inventory rejects directory symlinks')
        for name in sorted(names):
            path = Path(base) / name
            result[path.relative_to(root).as_posix()] = identity(path)
            require(len(result) <= 10000, 'Inventory exceeds 10000 files')
    return dict(sorted(result.items()))


def source_digest(files):
    return hashlib.sha256(''.join(p + '\0' + v['sha256'] + '\n'
                                  for p, v in sorted(files.items())).encode()).hexdigest()


def closed_inventory(root, prefix, expected):
    actual = {p.relative_to(root).as_posix() for p in (root / prefix).rglob('*')}
    wanted = set()
    for path in expected:
        if path.startswith(prefix + '/'):
            wanted.add(path)
            wanted.update(p.as_posix() for p in Path(path).parents if str(p) != '.')
    wanted = {p for p in wanted if p.startswith(prefix + '/')}
    require(actual == wanted, 'Consumer closed directory topology differs: ' + prefix)


def unique_json(text):
    def pairs(values):
        result = {}
        for key, value in values:
            require(key not in result, 'Duplicate JSON key: ' + key)
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=pairs)


def load_profile(root=ROOT):
    # Same policy literal as the existing CLI Python admission harness; no
    # independently maintained source-pair map and no synthetic CLI rendering.
    text = (root / POLICY).read_text()
    require(text.count('Data(#"""\n') == 1, 'Ambiguous canonical source policy')
    profile = unique_json(text.split('Data(#"""\n', 1)[1].split('\n        """#.utf8)', 1)[0])
    require(profile['schema'] == 1 and profile['id'] == 'mixer.android-source-pair.9',
            'Unsupported canonical source pair')
    for kind, count in (('sdk', 22), ('adapter', 24)):
        files = profile[kind + '_files']
        require(len(files) == count and source_digest(files) == profile[kind + '_compatibility_sha256'],
                'Canonical projection differs: ' + kind)
    return profile


def java_roster(profile):
    paths = sorted(p for p in profile['adapter_files'] if p.endswith('.java'))
    require(len(paths) == 18 and all(p.startswith('app/src/dev/mixer/android/') for p in paths),
            'Expected all 18 product Java sources')
    return paths


def validate_consumer(root, profile, toolchain, template):
    files = inventory(root)
    lock = unique_json((root / 'mixer.lock').read_text())
    require(lock['schema'] == 1, 'Unsupported consumer lock')
    expected_profile = {k: profile[k] for k in (
        'id', 'sdk_compatibility_sha256', 'adapter_compatibility_sha256', 'default_descriptor')}
    require(lock['android']['profile'] == expected_profile, 'Consumer source-pair lock differs')
    require(lock['android']['toolchain'] == toolchain and lock['swiftVersion'] == toolchain['swift_version'],
            'Consumer toolchain lock differs')
    for kind, directory, field in (('sdk', 'MixerSDK', 'sdkDigest'),
                                   ('adapter', 'MixerAndroid', 'adapterDigest')):
        prefix = 'Generated/' + directory + '/'
        actual = {p[len(prefix):]: v for p, v in files.items() if p.startswith(prefix)}
        expected_digest = lock[field] if kind == 'sdk' else lock['android'][field]
        require(source_digest(actual) == expected_digest, 'Consumer tree lock differs: ' + kind)
        for path, value in profile[kind + '_files'].items():
            require(actual.get(path) == value, 'Consumer pinned source differs: ' + path)
        closed = ('Sources/MixerCore/', 'Sources/MixerUI/') if kind == 'sdk' else (
            'Sources/MixerAndroidRuntime/', 'app/src/', 'bridge/', 'contracts/')
        require({p for p in actual if p.startswith(closed)} ==
                {p for p in profile[kind + '_files'] if p.startswith(closed)},
                'Consumer closed inventory differs: ' + kind)
        for prefix_path in closed:
            closed_inventory(root / 'Generated' / directory, prefix_path.rstrip('/'), profile[kind + '_files'])
        if kind == 'sdk':
            require(all(p.split('/')[0].isascii() and
                        (not p.split('/')[0].lower().startswith('package') or p == 'Package.swift')
                        for p in actual), 'Consumer SDK manifest namespace differs')
    adapter = root / 'Generated/MixerAndroid'
    require(identity(adapter / DESCRIPTOR) == profile['default_descriptor'], 'Consumer descriptor differs')
    require({p for p in files if p.startswith('Generated/MixerAndroid/app/assets/')} ==
            {'Generated/MixerAndroid/' + DESCRIPTOR}, 'Consumer appearance inventory differs')
    rendered = (adapter / 'android-build.py').read_bytes().decode('utf-8')
    assignments = [n for n in ast.parse(rendered).body if isinstance(n, ast.Assign) and
                   any(isinstance(t, ast.Name) and t.id == 'SOURCE_PROFILE_HEX' for t in n.targets)]
    require(len(assignments) == 1, 'Missing rendered driver profile')
    encoded = ast.literal_eval(assignments[0].value)
    require(unique_json(bytes.fromhex(encoded).decode()) == profile, 'Rendered driver profile differs')
    require(template.count(MARKER) == 1 and rendered == template.replace(MARKER, encoded),
            'Rendered driver differs from canonical template')
    java = sorted(p for p in files if p.endswith('.java'))
    require(java == ['Generated/MixerAndroid/' + p for p in java_roster(profile)],
            'Consumer Java inventory differs')
    return files


class Commands:
    """Bounded pipes and only owned process-group cleanup, including failures."""
    def __init__(self, out, env, *, seconds=2400, command_seconds=600,
                 output_bytes=4_194_304, total_output_bytes=67_108_864, cleanup_seconds=5):
        self.out, self.env = out, env
        self.deadline = time.monotonic() + seconds
        self.command_seconds = command_seconds
        self.output_bytes, self.total_output_bytes = output_bytes, total_output_bytes
        self.used_output = 0
        self.records = []
        self.cleanup_seconds = cleanup_seconds

    def custody_terminal(self):
        return bool(self.records) and all(r['terminal_custody'] for r in self.records)

    def run(self, label, argv, *, cwd=ROOT, expected_failure=False, diagnostics=False,
            stdout_bytes=None):
        require(stdout_bytes is None or type(stdout_bytes) is int and 0 < stdout_bytes <= JAVAP_STDOUT_BYTES,
                'Invalid explicit stdout budget')
        stream_limits = {'stdout': self.output_bytes if stdout_bytes is None else stdout_bytes,
                         'stderr': self.output_bytes}
        require(len(self.records) < 160, 'Command count budget exhausted')
        require(time.monotonic() < self.deadline, 'Run time budget exhausted')
        require(not self.records or self.custody_terminal(), 'Prior command custody remains unknown')
        argv = list(map(str, argv))
        number = len(self.records)
        record = {'label': label, 'argv': argv, 'cwd': str(cwd), 'exit_code': None,
                  'stream_output_limits': stream_limits, 'total_output_limit': self.total_output_bytes,
                  'output_bytes_before': self.used_output,
                  'started_utc': datetime.now(timezone.utc).isoformat(), 'stop': None,
                  'pid': None, 'owned_pgid': None, 'direct_child_reaped': False,
                  'stdout_eof': False, 'stderr_eof': False, 'owned_group_absent': False,
                  'signal': {'name': 'SIGKILL', 'attempted': False, 'outcome': 'not-started'},
                  'group_observation': {'outcome': 'not-started', 'attempts': 0},
                  'cleanup_errors': [], 'terminal_custody': False}
        self.records.append(record)
        logs = {k: self.out / f'{number:03}-{label}.{k}' for k in ('stdout', 'stderr')}
        buffers = {k: bytearray() for k in logs}
        child = None
        start = time.monotonic()
        selector = None

        def cleanup_error(operation, error):
            record['cleanup_errors'].append({'operation': operation,
                'type': type(error).__name__, 'message': str(error)})

        def read_stream(name):
            pipe = getattr(child, name)
            try:
                chunk = os.read(pipe.fileno(), 65536)
            except BlockingIOError:
                return
            if not chunk:
                record[name + '_eof'] = True
                if selector is not None and pipe.fileno() in selector.get_map():
                    selector.unregister(pipe)
                return
            room = min(stream_limits[name] - len(buffers[name]),
                       self.total_output_bytes - self.used_output)
            kept = chunk[:max(room, 0)]
            buffers[name].extend(kept)
            self.used_output += len(kept)
            if len(kept) != len(chunk) and record['stop'] is None:
                record['stop'] = 'output-limit'

        try:
            selector = selectors.DefaultSelector()
            child = subprocess.Popen(argv, cwd=cwd, env=self.env, stdin=subprocess.DEVNULL,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            record['pid'] = record['owned_pgid'] = child.pid
            for name in logs:
                pipe = getattr(child, name)
                os.set_blocking(pipe.fileno(), False)
                selector.register(pipe, selectors.EVENT_READ, name)
            while selector.get_map() or child.poll() is None:
                if time.monotonic() >= min(self.deadline, start + self.command_seconds):
                    record['stop'] = 'timeout'
                    break
                for key, _ in selector.select(0.02):
                    read_stream(key.data)
                    if record['stop']:
                        break
                if record['stop']:
                    break
        except BaseException as error:
            record['execution_error'] = {'type': type(error).__name__, 'message': str(error)}
        finally:
            if child is not None:
                cleanup_deadline = time.monotonic() + self.cleanup_seconds
                record['cleanup_seconds_limit'] = self.cleanup_seconds
                record['signal']['attempted'] = True
                try:
                    os.killpg(record['owned_pgid'], signal.SIGKILL)
                    record['signal']['outcome'] = 'sent'
                except ProcessLookupError:
                    record['signal']['outcome'] = 'already-absent'
                except BaseException as error:
                    record['signal']['outcome'] = 'denied' if isinstance(error, PermissionError) else 'error'
                    cleanup_error('signal-owned-group', error)
                try:
                    record['exit_code'] = child.wait(timeout=max(0, cleanup_deadline - time.monotonic()))
                    record['direct_child_reaped'] = True
                except BaseException as error:
                    cleanup_error('reap-direct-child', error)
                readable = set()
                for name in logs:
                    try:
                        os.set_blocking(getattr(child, name).fileno(), False)
                        readable.add(name)
                    except BaseException as error:
                        cleanup_error('nonblocking-' + name, error)
                # Probe only the group created by this Popen. No enumeration,
                # historical-group probing, or escaped-descendant containment.
                while True:
                    observation = record['group_observation']
                    if observation['outcome'] not in ('absent', 'denied', 'error'):
                        observation['attempts'] += 1
                        try:
                            os.killpg(record['owned_pgid'], 0)
                            observation['outcome'] = 'present'
                        except ProcessLookupError:
                            observation['outcome'] = 'absent'
                            record['owned_group_absent'] = True
                        except BaseException as error:
                            observation['outcome'] = 'denied' if isinstance(error, PermissionError) else 'error'
                            cleanup_error('observe-owned-group', error)
                    for name in sorted(readable):
                        if not record[name + '_eof']:
                            try:
                                read_stream(name)
                            except BaseException as error:
                                cleanup_error('drain-' + name, error)
                                readable.remove(name)
                    if (record['owned_group_absent'] and all(record[n + '_eof'] for n in logs)
                            or observation['outcome'] in ('denied', 'error') and all(record[n + '_eof'] for n in logs)
                            or time.monotonic() >= cleanup_deadline):
                        break
                    try:
                        time.sleep(min(0.02, max(0, cleanup_deadline - time.monotonic())))
                    except BaseException as error:
                        cleanup_error('cleanup-wait', error)
                        break
                if observation['outcome'] == 'present':
                    observation['outcome'] = 'present-at-deadline'
                observation['elapsed_seconds'] = round(time.monotonic() - (cleanup_deadline - self.cleanup_seconds), 3)
                for name in logs:
                    try:
                        getattr(child, name).close()
                    except BaseException as error:
                        cleanup_error('close-' + name, error)
            if selector is not None:
                try:
                    selector.close()
                except BaseException as error:
                    cleanup_error('close-selector', error)
            record['elapsed_seconds'] = round(time.monotonic() - start, 3)
            record['logs'] = {}
            for name, path in logs.items():
                try:
                    path.write_bytes(buffers[name])
                    record['logs'][name] = {'path': str(path), **identity(path)}
                except BaseException as error:
                    cleanup_error('persist-' + name, error)
            record['terminal_custody'] = (record['direct_child_reaped'] and record['stdout_eof']
                and record['stderr_eof'] and record['owned_group_absent'] and not record['cleanup_errors'])
            try:
                save(self.out / 'commands.json', self.records)
            except BaseException as error:
                cleanup_error('persist-command-receipt', error)
                record['terminal_custody'] = False
        require('execution_error' not in record, label + ': ' + str(record.get('execution_error')))
        require(record['terminal_custody'], label + ': terminal custody unknown or cleanup failed')
        require(record['stop'] is None, label + ': ' + str(record['stop']))
        require(record['exit_code'] is not None and
                (record['exit_code'] > 0 if expected_failure else record['exit_code'] == 0),
                label + ': unexpected exit ' + str(record['exit_code']))
        data = buffers['stdout'] + buffers['stderr'] if diagnostics else buffers['stdout']
        return bytes(data).decode('utf-8')


def member_references(dump, class_files):
    """Inventory actual javap constant-pool members, retaining their owning class."""
    expected = {str(p.absolute()): p for p in class_files}
    observed, references = set(), []
    current = None
    for line in dump.splitlines():
        if line.startswith('Classfile '):
            current = line.removeprefix('Classfile ').strip()
            require(current in expected and current not in observed, 'Unexpected/duplicate javap class scope')
            observed.add(current)
        left, separator, right = line.strip().partition(' = ')
        parts = right.split()
        if separator and left.startswith('#') and parts and parts[0] in ('Fieldref', 'Methodref', 'InterfaceMethodref'):
            require(current is not None and ' // ' in right, 'Unscoped/unresolved javap member reference')
            references.append({'class_file': str(expected[current]), 'constant_pool_index': left,
                               'kind': parts[0], 'member': right.partition(' // ')[2].strip(),
                               'raw_entry': line})
    require(observed == set(expected), 'Missing emitted class in javap member inventory')
    require(bool(references), 'Missing actual class member references')
    return references


def compile_consumer(consumer, destination, profile, jdk, sdk, run, label):
    destination.mkdir()
    classes, dex = destination / 'classes', destination / 'dex'
    classes.mkdir()
    dex.mkdir()
    jar = sdk / 'platforms/android-37.0/android.jar'
    sources = [consumer / 'Generated/MixerAndroid' / p for p in java_roster(profile)]
    run(label + '-javac', [jdk / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror',
                          '-proc:none', '-sourcepath', '', '-classpath', jar, '-d', classes, *sources])
    class_files = sorted(classes.rglob('*.class'))
    required = {p.removeprefix('app/src/').removesuffix('.java') + '.class' for p in java_roster(profile)}
    require(required <= {p.relative_to(classes).as_posix() for p in class_files},
            'Missing emitted product classes')
    require(all(p.relative_to(classes).as_posix().startswith('dev/mixer/android/') for p in class_files),
            'Unexpected emitted class package')
    javap_argv = [jdk / 'bin/javap', '-v', '-p', '-c', '-s', *class_files]
    member_dump = run(label + '-javap-members', javap_argv, stdout_bytes=JAVAP_STDOUT_BYTES)
    raw = destination / 'member-references.javap.txt'
    raw.write_bytes(member_dump.encode('utf-8'))
    references = member_references(member_dump, class_files)
    member_inventory = {'tool': 'official JDK javap', 'command_label': label + '-javap-members',
        'argv': list(map(str, javap_argv)), 'raw_output': {'path': str(raw), **identity(raw)},
        'class_inputs': inventory(classes), 'references': references,
        'scope': 'All emitted classfile constant-pool Fieldref/Methodref/InterfaceMethodref entries; '
                 'raw verbose disassembly also retained. Includes unused entries; excludes dynamic/reflection '
                 'resolution and post-D8 reference rewriting. No API28 floor/linkage approval.'}
    save(destination / 'member-references.json', member_inventory)
    run(label + '-d8', [sdk / 'build-tools/37.0.0/d8', '--min-api', '28', '--lib', jar,
                       '--output', dex, *class_files])
    require(sorted(p.name for p in dex.iterdir()) == ['classes.dex'], 'Expected one actual DEX')
    require((dex / 'classes.dex').read_bytes()[:8] in (b'dex\n035\0', b'dex\n037\0', b'dex\n038\0', b'dex\n039\0', b'dex\n040\0', b'dex\n041\0'),
            'Missing DEX header')
    dump = run(label + '-dexdump', [sdk / 'build-tools/37.0.0/dexdump', dex / 'classes.dex'])
    descriptors = {line.partition(':')[2].strip().strip("'") for line in dump.splitlines()
                   if line.strip().startswith('Class descriptor')}
    require(all('L' + p.relative_to(classes).as_posix().removesuffix('.class') + ';' in descriptors for p in class_files),
            'Missing product class descriptors in actual DEX')
    result = {'sources': {str(p.relative_to(consumer)): identity(p) for p in sources},
              'classes': inventory(classes), 'dex': inventory(dex),
              'member_references': {'inventory': identity(destination / 'member-references.json'),
                                    'count': len(references), 'raw_output': member_inventory['raw_output'],
                                    'command_label': member_inventory['command_label'],
                                    'scope': member_inventory['scope']},
              'scope': 'Java17 strict compilation; D8 min-api28; no API28 floor/linkage, runtime or APK qualification'}
    save(destination / 'receipt.json', result)
    return result


def tamper_cases(profile):
    return (
        ('sdk', 'Generated/MixerSDK/Sources/MixerCore/Lifecycle.swift', 'android.sdk-compatibility'),
        ('adapter', 'Generated/MixerAndroid/' + java_roster(profile)[0], 'android.sdk-compatibility'),
        ('descriptor', 'Generated/MixerAndroid/' + DESCRIPTOR, 'android.sdk-compatibility'),
        ('extra-java', 'Generated/MixerAndroid/app/src/dev/mixer/android/Extra.java', 'android.sdk-compatibility'),
        ('profile', 'mixer.lock', 'android.sdk-profile-mismatch'),
        ('missing-lock', 'mixer.lock', 'android.sdk-profile-required'),
    )


def tamper_consumers(source, scratch, cli, profile, run, label):
    outcomes = []
    for name, path, code in tamper_cases(profile):
        root = scratch / name
        shutil.copytree(source, root)
        target = root / path
        if name == 'profile':
            lock = unique_json(target.read_text())
            lock['android']['profile']['id'] = 'mixer.android-source-pair.6'
            save(target, lock)
        elif name == 'missing-lock':
            target.unlink()
        else:
            if name == 'extra-java':
                target.write_text('package dev.mixer.android; final class Extra {}\n')
            else:
                content = target.read_bytes()
                target.write_bytes(bytes([content[0] ^ 1]) + content[1:])
            # Recomputed generic locks must not admit changed pinned sources.
            lock = unique_json((root / 'mixer.lock').read_text())
            lock['sdkDigest'] = source_digest(inventory(root / 'Generated/MixerSDK'))
            lock['android']['adapterDigest'] = source_digest(inventory(root / 'Generated/MixerAndroid'))
            save(root / 'mixer.lock', lock)
        report = unique_json(run(label + '-tamper-' + name,
                                 [cli, 'build', '--platform', 'android', '--directory', root],
                                 expected_failure=True))
        require(report.get('status') == 'error' and report.get('code') == code,
                'Unexpected tamper refusal: ' + name)
        require(not (root / '.mixer').exists(), 'Tamper reached build staging: ' + name)
        driver_diagnostic = run(label + '-driver-tamper-' + name,
            [sys.executable, '-B', root / 'Generated/MixerAndroid/android-build.py', 'build', root],
            expected_failure=True, diagnostics=True)
        expected = ('android.sdk-profile-mismatch' if name == 'profile' else
                    'mixer.lock' if name == 'missing-lock' else 'Android SDK source compatibility rejected')
        require('Android local build error:' in driver_diagnostic and expected in driver_diagnostic and
                'Traceback' not in driver_diagnostic, 'Unexpected driver tamper refusal: ' + name)
        require(not (root / '.mixer').exists(), 'Driver tamper reached build staging: ' + name)
        outcomes.append({'case': name, 'refusal': report, 'driver_refusal': driver_diagnostic,
                         'build_staging_created': False})
        shutil.rmtree(root)
    return outcomes


def tool_environment(args):
    paths = {}
    for key in ('swift', 'swift_sdks', 'android_artifact', 'jdk', 'android_sdk'):
        path = getattr(args, key)
        require(path.is_absolute(), 'Tool paths must be absolute: ' + key)
        # Preserve the Swift launcher name (it can be a swift-driver symlink),
        # matching the canonical driver's absolute rather than resolved path.
        paths[key] = path.absolute() if key == 'swift' else path.resolve(strict=True)
    require(paths['swift'].is_file() and os.access(paths['swift'], os.X_OK), 'Missing explicit Swift executable')
    # Canonical driver uses this macOS NDK layout; do not suggest a Linux job.
    required = [paths['android_artifact'] / 'android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64/bin/aarch64-linux-android28-clang',
                paths['android_artifact'] / 'swift-sdk.json', paths['jdk'] / 'bin/javac',
                paths['jdk'] / 'bin/javap',
                paths['android_sdk'] / 'platforms/android-37.0/android.jar',
                paths['android_sdk'] / 'build-tools/37.0.0/d8',
                paths['android_sdk'] / 'build-tools/37.0.0/dexdump']
    require(all(p.is_file() for p in required), 'Missing complete installed Android toolchain prerequisite')
    env = os.environ.copy()
    env.update({'MIXER_SWIFT': str(paths['swift']), 'MIXER_SWIFT_SDKS_PATH': str(paths['swift_sdks']),
                'MIXER_ANDROID_ARTIFACT_PATH': str(paths['android_artifact']), 'MIXER_JDK': str(paths['jdk']),
                'ANDROID_HOME': str(paths['android_sdk']), 'ANDROID_SDK_ROOT': str(paths['android_sdk']),
                'JAVA_HOME': str(paths['jdk']), 'PYTHONDONTWRITEBYTECODE': '1',
                'PATH': os.pathsep.join([str(paths['swift'].parent), str(paths['jdk'] / 'bin'),
                                        str(Path(sys.executable).parent), env.get('PATH', '')])})
    return paths, env


def apple_producer_provenance(env):
    selection = {k: env.get(k) for k in ('DEVELOPER_DIR', 'SDKROOT')}
    require(all(isinstance(v, str) and v and Path(v).is_absolute() for v in selection.values()),
            'Explicit per-command DEVELOPER_DIR and SDKROOT required for the Apple producer')
    developer, sdk = (Path(selection[k]).resolve(strict=True) for k in ('DEVELOPER_DIR', 'SDKROOT'))
    require(developer.is_dir() and sdk.is_dir() and
            sdk.is_relative_to(developer / 'Platforms/MacOSX.platform/Developer/SDKs'),
            'Apple producer SDK must belong to the selected developer directory')
    version_file, settings_file = developer.parent / 'version.plist', sdk / 'SDKSettings.json'
    version, settings = plistlib.loads(version_file.read_bytes()), unique_json(settings_file.read_text())
    require(settings['CanonicalName'].startswith('macosx'), 'Apple producer requires a macOS SDK')
    return {'selection': selection, 'resolved_developer_dir': str(developer), 'resolved_sdkroot': str(sdk),
            'xcode_version': version['CFBundleShortVersionString'], 'xcode_build': version['ProductBuildVersion'],
            'sdk_version': settings['Version'], 'sdk_canonical_name': settings['CanonicalName'],
            'xcode_version_plist': identity(version_file), 'sdk_settings': identity(settings_file),
            'selection_scope': 'Child process environment only; no global xcode-select change'}


def source_inputs(profile):
    paths = {Path(__file__).relative_to(ROOT).as_posix(), POLICY, DRIVER,
             'scripts/ci/check-android-binding.py'}
    for package in ('cli', 'sdk', 'updates'):
        paths.update(str(p.relative_to(ROOT)) for p in (ROOT / package / 'Sources').rglob('*') if p.is_file())
        paths.update(str(p.relative_to(ROOT)) for p in (ROOT / package).glob('Package.*') if p.is_file())
    for p in profile['adapter_files']:
        paths.add('native/android/' + ('engine/' if p.startswith('Sources/') else '') + p)
    return {p: identity(ROOT / p) for p in sorted(paths)}


def execute(args):
    out = args.output.absolute()
    out.mkdir(parents=True, exist_ok=False)
    commands_dir = out / 'commands'
    commands_dir.mkdir()
    receipt = {'schema': 1, 'status': 'failed', 'argv': sys.argv, 'python': sys.version,
               'observed_utc': datetime.now(timezone.utc).isoformat(),
               'scope': 'Actual CLI Debug/Release producers and original/relocated/exported Java/D8 consumers',
               'apk_build': 'not run; shipped Android driver is Release-only',
               'runtime_device_signing_published_package_GA': 'pending', 'consumers': {}}
    scratch = None
    commands = None
    try:
        require(args.execute_toolchains, 'Explicit --execute-toolchains required; parent selects execution environment')
        require(sys.platform == 'darwin', 'Canonical Android inspection requires a macOS toolchain host')
        paths, env = tool_environment(args)
        receipt['selected_paths'] = {k: str(v) for k, v in paths.items()}
        receipt['apple_producer'] = apple_producer_provenance(env)
        commands = Commands(commands_dir, env)
        run = commands.run
        receipt['revision'] = run('revision', ['git', 'rev-parse', 'HEAD']).strip()
        receipt['git_tree'] = run('git-tree', ['git', 'rev-parse', 'HEAD^{tree}']).strip()
        profile = load_profile()
        receipt['source_inputs'] = initial = source_inputs(profile)
        receipt['source_inputs_sha256'] = source_digest(initial)
        save(out / 'receipt.json', receipt)
        # Reuse the canonical installed official distribution inspection. No fake
        # inventory and no platform-only stand-in for create's prerequisites.
        inspection = unique_json(run('official-inspect', [sys.executable, '-B', ROOT / DRIVER, 'inspect']))
        require(inspection['schema'] == 1 and inspection['sdk_id'] == 'aarch64-unknown-linux-android28' and
                inspection['min_api'] == 28 and inspection['target_api'] == 37 and
                inspection['javac_version'].startswith('javac 25.'), 'Unexpected canonical tool identity')
        require(inspection['tools']['swift']['path'] == str(paths['swift']) and
                inspection['tools']['javac']['path'] == str(paths['jdk'] / 'bin/javac') and
                inspection['distributions']['android_platform']['path'] ==
                str(paths['android_sdk'] / 'platforms/android-37.0'), 'Inspection selected different tool paths')
        receipt['official_toolchain'] = inspection
        receipt['d8_version'] = run('d8-version', [paths['android_sdk'] / 'build-tools/37.0.0/d8', '--version']).strip()
        receipt['javap_tool'] = {'path': str(paths['jdk'] / 'bin/javap'),
            **identity(paths['jdk'] / 'bin/javap'),
            'version': run('javap-version', [paths['jdk'] / 'bin/javap', '-version']).strip()}
        require(receipt['javap_tool']['version'].startswith('25.'), 'Unexpected javap version')
        receipt['android_jar'] = identity(paths['android_sdk'] / 'platforms/android-37.0/android.jar')
        template = (ROOT / DRIVER).read_bytes().decode('utf-8')
        scratch = Path(tempfile.mkdtemp(prefix='generated-java-owned-', dir=out))
        # Keep all child temporary state inside the one removable owned directory.
        (scratch / 'tmp').mkdir()
        env['TMPDIR'] = str(scratch / 'tmp')
        spec = importlib.util.spec_from_file_location('generated_java_dependencies', ROOT / 'scripts/ci/check-android-binding.py')
        dependencies = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dependencies)
        baseline = None
        receipt['producer_jobs'] = PRODUCER_JOBS
        for mode in MODES:
            build = scratch / ('producer-' + mode)
            flags = [paths['swift'], 'build', '--package-path', ROOT / 'cli', '--scratch-path', build,
                     '--disable-automatic-resolution', '-j', str(PRODUCER_JOBS), '-c', mode]
            run(mode + '-producer-build', [*flags, '--product', 'mixer'])
            bin_path = Path(run(mode + '-producer-bin', [*flags, '--show-bin-path']).strip()).resolve(strict=True)
            require(bin_path.is_relative_to(build.resolve()), 'Producer escaped its owned scratch')
            cli = bin_path / 'mixer'
            receipt.setdefault('producers', {})[mode] = {'binary': identity(cli), 'configuration': mode,
                'jobs': PRODUCER_JOBS, 'build_argv': list(map(str, [*flags, '--product', 'mixer'])),
                'dependencies': dependencies.dependency_checkouts(ROOT / 'cli', build, run, mode + '-dependency')}
            mode_root = scratch / mode
            mode_root.mkdir()
            original = mode_root / 'original'
            run(mode + '-create', [cli, 'create', 'GeneratedJavaApp', '--platform', 'android',
                '--directory', original, '--application', 'dev.mixer.generatedjava',
                '--sdk-path', ROOT / 'sdk', '--android-adapter-path', ROOT / 'native/android'])
            original_files = validate_consumer(original, profile, inspection, template)
            if baseline is None:
                baseline = original_files
            require(original_files == baseline, 'Debug/Release emitted consumer identity differs')
            exported, relocated = mode_root / 'exported', mode_root / 'relocated'
            run(mode + '-export', [cli, 'export', exported, '--directory', original])
            # Move the actual original after its compilation, so relocation has
            # no surviving original path to fall back on.
            for form in FORMS:
                consumer = mode_root / form
                if form == 'relocated':
                    original.rename(relocated)
                    require(not original.exists(), 'Original survives relocation')
                before = validate_consumer(consumer, profile, inspection, template)
                require(before == original_files, 'Relocated/exported inventory differs')
                artifact = out / (mode + '-' + form)
                result = compile_consumer(consumer, artifact, profile, paths['jdk'], paths['android_sdk'], run, mode + '-' + form)
                require(inventory(consumer) == before, 'Consumer changed during Java compilation')
                save(artifact / 'consumer-inventory.json', before)
                save(artifact / 'consumer-directories.json', sorted(
                    p.relative_to(consumer).as_posix() for p in consumer.rglob('*') if p.is_dir()))
                shutil.copyfile(consumer / 'mixer.lock', artifact / 'mixer.lock')
                shutil.copyfile(consumer / 'Generated/MixerAndroid' / DESCRIPTOR, artifact / 'descriptor.json')
                receipt['consumers'][mode + '-' + form] = {'java_count': len(result['sources']),
                    'classes': len(result['classes']), 'inventory_sha256': source_digest(before),
                    'member_references': result['member_references']}
                save(out / 'receipt.json', receipt)
            negative = mode_root / 'tamper'
            negative.mkdir()
            receipt.setdefault('tamper', {})[mode] = tamper_consumers(exported, negative, cli, profile, run, mode)
            receipt['producers'][mode]['dependencies_postflight'] = dependencies.dependency_checkouts(
                ROOT / 'cli', build, run, mode + '-post-dependency')
        require(source_inputs(profile) == initial, 'Owning source changed during integration')
        require(apple_producer_provenance(env) == receipt['apple_producer'],
                'Selected Apple producer SDK changed during integration')
        require(unique_json(run('official-inspect-postflight', [sys.executable, '-B', ROOT / DRIVER, 'inspect'])) == inspection,
                'Installed official distributions changed during integration')
        require(identity(paths['jdk'] / 'bin/javap') == {k: receipt['javap_tool'][k] for k in ('bytes', 'sha256')} and
                run('javap-version-postflight', [paths['jdk'] / 'bin/javap', '-version']).strip() == receipt['javap_tool']['version'],
                'Installed javap changed during integration')
        require(set(receipt['consumers']) == {m + '-' + f for m in MODES for f in FORMS}, 'Incomplete consumer matrix')
        require(commands.custody_terminal(), 'Command custody remains unknown')
        receipt['status'] = 'passed-java-crosscompile-only'
    except Exception as error:
        receipt['error'] = str(error)
    finally:
        terminal = commands is not None and commands.custody_terminal()
        receipt['command_records'] = commands.records if commands is not None else []
        receipt['cleanup'] = {'owned_scratch_started': scratch is not None,
            'command_custody_terminal': terminal, 'owned_scratch_removed': False}
        if scratch is not None:
            receipt['cleanup']['owned_scratch_path'] = str(scratch)
            if not terminal:
                receipt['status'] = 'failed'
                receipt['cleanup']['retention_reason'] = 'Terminal command custody not positively observed or cleanup denied/failed'
            else:
                try:
                    shutil.rmtree(scratch)
                    receipt['cleanup']['owned_scratch_removed'] = not scratch.exists()
                    require(receipt['cleanup']['owned_scratch_removed'], 'Scratch remains after deletion')
                except Exception as error:
                    receipt['status'] = 'failed'
                    receipt['cleanup']['error'] = str(error)
        if commands is not None and not terminal:
            receipt['status'] = 'failed'
            receipt.setdefault('error', 'Terminal command custody not positively observed or cleanup denied/failed')
        save(out / 'receipt.json', receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('swift', 'swift-sdks', 'android-artifact', 'jdk', 'android-sdk', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--execute-toolchains', action='store_true')
    receipt = execute(parser.parse_args())
    print(json.dumps({'status': receipt['status'], 'error': receipt.get('error')}))
    return 0 if receipt['status'] == 'passed-java-crosscompile-only' else 1


if __name__ == '__main__':
    sys.exit(main())
