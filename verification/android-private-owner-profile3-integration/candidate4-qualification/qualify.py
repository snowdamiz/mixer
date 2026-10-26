#!/usr/bin/env python3
"""Exact selected profile4 rebinding and bounded actual host-consumer evidence.

This runner never starts an Android/native runtime or uses capture/process discovery.
The immutable selection, producer closure and original profile3 installation are
inputs. New command receipts, source snapshots and failed output remain here.
"""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import time
from unittest import mock

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
CANDIDATE = ROOT / 'verification/android-private-owner-integration-implementation/candidate-4'
SELECTION = ROOT / 'verification/android-private-owner-effect-integration-root-review/candidate-4-profile-selection.json'
PINS = {
    'selection': 'fc0e083821790e12c1c12b709f2a8e7c44a40ff457e4183853ef6adbdd919106',
    'candidate_manifest': '69fcd445119c0ea311c11cf97587d591d87ba1c5bd2d5b3c0a722116f66231c5',
    'profile': 'fa20572d64d0cec8e2bbfd959df6a2993b4e231cca6f3f8009761bd0b2678d62',
    'admission': 'dabbcb66df621c37238d358adb54c89abfce006c399f4ad4eba1373c746eb5ea',
}
OWNED = [
    'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift',
    'cli/Sources/MixerBuild/Resources/android-build.py',
    'cli/Tests/MixerBuildTests/AndroidSDKCompatibilityTests.swift',
    'cli/Tests/MixerBuildTests/AndroidProjectTests.swift',
    'cli/build-tests/test_android_sdk_compatibility.py',
]
SWIFT = Path('/usr/bin/swift')
ANDROID_SWIFT = Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift')
STRIP = ('CLASSPATH', 'JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS',
         'JDK_JAVAC_OPTIONS', 'JAVA_OPTS', 'SWIFT_EXEC', 'SWIFT_DRIVER_SWIFT_FRONTEND_EXEC',
         'DYLD_INSERT_LIBRARIES', 'LD_PRELOAD', 'SDKROOT', 'TOOLCHAINS')
FILTER = 'androidCompatibility|androidSnapshotOwns|androidDefaultAppearance|androidCoordinatorAndAuthoredToggle'


def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def load(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def require(path, expected):
    check(path.is_file() and not path.is_symlink(), 'not ordinary file: ' + str(path))
    actual = identity(path.read_bytes())
    check(actual == expected, 'identity changed: ' + str(path))
    return actual


def pin(path, sha256):
    actual = identity(path.read_bytes())
    check(actual['sha256'] == sha256, 'pin changed: ' + str(path))
    return actual


def projection(files):
    return hashlib.sha256(''.join(p + '\0' + files[p]['sha256'] + '\n'
                                  for p in sorted(files)).encode()).hexdigest()


def regular_files(root):
    excluded = {'.build', '.swiftpm', '.git', '__pycache__', '.mixer'}
    result = {}
    for directory, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in excluded)
        for name in sorted(names):
            path = Path(directory) / name
            if name == '.DS_Store':
                continue
            check(not path.is_symlink(), 'unexpected snapshot symlink: ' + str(path))
            result[path.relative_to(root).as_posix()] = identity(path.read_bytes())
    return result


def literal(path):
    text = path.read_text()
    start = text.index('Data(#"""\n') + len('Data(#"""\n')
    end = text.index('\n        """#.utf8)', start)
    return json.loads(text[start:end]), text, start, end


def read_driver(path, label):
    spec = importlib.util.spec_from_file_location(label, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Qualification:
    def __init__(self):
        self.env = {k: v for k, v in os.environ.items() if k not in STRIP}
        self.env.update(PATH='/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin',
                        MIXER_SWIFT=str(ANDROID_SWIFT), PYTHONDONTWRITEBYTECODE='1')
        self.commands = []
        self.scratch = []
        self.versions = {}
        self.receipt = {
            'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'argv': [sys.executable, *sys.argv], 'cwd': str(ROOT), 'pid': os.getpid(),
            'pgid': os.getpgrp(), 'python_version': sys.version,
            'python_executable': {'path': str(Path(sys.executable).resolve()),
                                  **identity(Path(sys.executable).resolve().read_bytes())},
            'runner': identity(Path(__file__).read_bytes()), 'pins': PINS,
            'status': 'failed', 'scope': 'Exact first-party development source-pair CLI and copied host consumer only',
            'native_runtime_capture_UI_or_process_discovery': False,
            'new_dependencies': [], 'cases': [], 'compiled_products': {},
            'limits': {name: list(resource.getrlimit(getattr(resource, name)))
                       for name in ('RLIMIT_CPU', 'RLIMIT_AS', 'RLIMIT_NOFILE', 'RLIMIT_NPROC')},
        }

    def run(self, label, argv, expected=0, timeout=120, cwd=None, env=None):
        argv = list(map(str, argv))
        cwd = cwd or ROOT
        child_env = env or self.env
        folder = BASE / 'commands' / label
        folder.mkdir(parents=True, exist_ok=False)
        resolved = Path(shutil.which(argv[0], path=child_env['PATH']) or argv[0]).resolve()
        meta = {
            'label': label, 'argv': argv, 'cwd': str(cwd), 'expected_exit': expected,
            'timeout_seconds': timeout, 'start': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'executable': {'path': str(resolved), **identity(resolved.read_bytes())},
            'tool_versions_observed': dict(self.versions),
            'source_binding_sha256': identity((BASE / 'source-binding.json').read_bytes())['sha256']
                                      if (BASE / 'source-binding.json').is_file() else None,
            'environment': {'PATH': child_env['PATH'], 'MIXER_SWIFT': child_env.get('MIXER_SWIFT'),
                            'removed_injection_variable_names': list(STRIP)},
            'resource_limits': self.receipt['limits'],
        }
        save(folder / 'command.json', meta)
        start = time.monotonic()
        timed_out = False
        with (folder / 'stdout').open('wb') as out, (folder / 'stderr').open('wb') as err:
            child = subprocess.Popen(argv, cwd=cwd, env=child_env, stdin=subprocess.DEVNULL,
                                     stdout=out, stderr=err, start_new_session=True)
            meta.update(pid=child.pid, pgid=child.pid)
            save(folder / 'command.json', meta)
            try:
                child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                self.stop_group(child.pid)
                child.wait(timeout=10)
            finally:
                self.stop_group(child.pid)
        stdout = (folder / 'stdout').read_bytes()
        stderr = (folder / 'stderr').read_bytes()
        meta.update(exit=child.returncode, timed_out=timed_out, child_reaped=True,
                    elapsed_seconds=time.monotonic() - start,
                    end=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    stdout=identity(stdout), stderr=identity(stderr),
                    cleanup='only exact owned process group signaled; direct child reaped')
        save(folder / 'result.json', meta)
        self.commands.append(meta)
        save(BASE / 'commands.json', self.commands)
        print(label, child.returncode, 'timeout' if timed_out else '', flush=True)
        check(child.returncode == expected and not timed_out,
              label + ' failed; retained stdout/stderr at ' + str(folder))
        return stdout, stderr

    @staticmethod
    def stop_group(pgid):
        try:
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            return
        until = time.monotonic() + 1
        while time.monotonic() < until:
            try:
                os.killpg(pgid, 0)
            except ProcessLookupError:
                return
            time.sleep(0.02)
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    def preflight_and_rebind(self):
        self.receipt['selection'] = pin(SELECTION, PINS['selection'])
        selected = load(SELECTION)
        check(selected['CLI_validation_authorized'] is True, 'CLI selection absent')
        check(selected['profile_proposal_sha256'] == PINS['profile'] and
              selected['candidate_manifest_sha256'] == PINS['candidate_manifest'], 'selection binding')
        pin(ROOT / selected['candidate_admission'], PINS['admission'])
        pin(CANDIDATE / 'manifest.json', PINS['candidate_manifest'])
        manifest = load(CANDIDATE / 'manifest.json')
        check(len(manifest['files']) == manifest['members'] == 1246, 'candidate inventory count')
        check(sum(x['bytes'] for x in manifest['files'].values()) == manifest['bytes'] == 11884760,
              'candidate inventory bytes')
        check(set(regular_files(CANDIDATE)) == set(manifest['files']) | {'manifest.json'}, 'candidate inventory closure')
        for name, expected in manifest['files'].items():
            require(CANDIDATE / name, expected)
        pin(CANDIDATE / 'profile-proposal.json', PINS['profile'])
        self.profile = load(CANDIDATE / 'profile-proposal.json')
        self.canonical = load(CANDIDATE / 'source-map.json')
        check(len(self.canonical) == 309, 'canonical input count')
        for name, expected in self.canonical.items():
            require(CANDIDATE / 'source' / name, expected)
            require(ROOT / name, expected)
        self.history = {p.relative_to(BASE.parent).as_posix(): identity(p.read_bytes())
                        for p in sorted(BASE.parent.rglob('*'))
                        if p.is_file() and BASE not in p.parents}
        save(BASE / 'historical-inputs-before.json', self.history)
        before = {}
        for name in OWNED:
            data = (ROOT / name).read_bytes()
            before[name] = identity(data)
            target = BASE / 'before' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        old, text, start, end = literal(ROOT / OWNED[0])
        check(old['id'] == self.profile['id'] == 'mixer.android-source-pair.3', 'ID must remain profile3')
        check(old['adapter_compatibility_sha256'] == '72d824927975b54cf0d4dba17c793b07743484f648feab1656a0f42c6accebb4',
              'expected partial candidate3 literal')
        changed = [name for name in old['adapter_files']
                   if old['adapter_files'][name] != self.profile['adapter_files'][name]]
        check(changed == ['app/src/dev/mixer/android/NativeCoordinatorV2.java',
                          'app/src/dev/mixer/android/NativeOwnerV2.java',
                          'app/src/dev/mixer/android/NativeRenderer.java'], 'unexpected candidate4 map diff')
        expected = dict(old)
        expected['adapter_files'] = self.profile['adapter_files']
        expected['adapter_compatibility_sha256'] = self.profile['adapter_compatibility_sha256']
        check(expected == self.profile, 'unselected profile field changed')
        replacement = '\n'.join('        ' + row for row in json.dumps(self.profile, indent=2, sort_keys=True).splitlines())
        (ROOT / OWNED[0]).write_text(text[:start] + replacement + text[end:])
        check(literal(ROOT / OWNED[0])[0] == self.profile, 'post-install exact literal')
        after = {name: identity((ROOT / name).read_bytes()) for name in OWNED}
        check(all(before[name] == after[name] for name in OWNED[1:]), 'rebind touched another owned file')
        save(BASE / 'installation.json', {
            'selection': self.receipt['selection'], 'before': before, 'after': after,
            'changed_profile_entries': changed, 'before_projection': old['adapter_compatibility_sha256'],
            'after_projection': self.profile['adapter_compatibility_sha256'],
            'profile': identity((CANDIDATE / 'profile-proposal.json').read_bytes()),
            'historical_installer_rerun': False, 'native_sources_changed': False,
            'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })
        self.receipt['canonical_inputs_verified'] = len(self.canonical)

    def snapshot(self):
        output, _ = self.run('tracked-input-list', ['/usr/bin/git', 'ls-files', '-z', '--', 'cli', 'sdk', 'updates'])
        names = {x.decode() for x in output.split(b'\0') if x}
        names = {name for name in names if (ROOT / name).is_file()}
        names.update(name for name in self.canonical if name.startswith(('native/android/', 'sdk/')))
        names.update(OWNED)
        names.update(['contracts/ui-v1.json', 'verification/android-default-appearance-packaging/run-2/created-descriptor.json'])
        self.source = BASE / 'source'
        self.source.mkdir(exist_ok=False)
        self.source_binding = {}
        for name in sorted(names):
            original = CANDIDATE / 'source' / name if name in self.canonical else ROOT / name
            data = original.read_bytes()
            require(ROOT / name, identity(data))
            target = self.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            self.source_binding[name] = identity(data)
        save(BASE / 'source-binding.json', {'schema': 1, 'files': self.source_binding,
                                           'projection_sha256': projection(self.source_binding)})
        self.receipt['source_projection_sha256'] = projection(self.source_binding)
        check(literal(self.source / OWNED[0])[0] == self.profile, 'snapshot profile mismatch')

    def tools_and_builds(self):
        for label, argv in [('host-swift', [SWIFT, '--version']), ('python', [sys.executable, '--version']),
                            ('git', ['/usr/bin/git', '--version'])]:
            out, err = self.run(label + '-version', argv)
            self.versions[label] = (out + err).decode().strip()
        out, _ = self.run('source-revision-context', ['/usr/bin/git', 'rev-parse', 'HEAD'])
        self.receipt['revision_context_only'] = out.decode().strip()
        self.clis = {}
        for configuration in ('debug', 'release'):
            build = BASE / ('build-cli-' + configuration)
            self.scratch.append(build)
            common = [SWIFT, '--package-path', self.source / 'cli', '--scratch-path', build,
                      '--disable-automatic-resolution', '--jobs', '2', '-c', configuration]
            self.run(configuration + '-cli-build', [common[0], 'build', *common[1:], '--product', 'mixer'], timeout=600)
            out, _ = self.run(configuration + '-cli-bin-path', [common[0], 'build', *common[1:], '--show-bin-path'])
            cli = Path(out.decode().strip()) / 'mixer'
            self.clis[configuration] = cli
            self.receipt['compiled_products']['cli-' + configuration] = {'path': str(cli), **identity(cli.read_bytes())}
            self.run(configuration + '-cli-version', [cli, 'version'])
            self.run(configuration + '-swift-tests', [common[0], 'test', *common[1:], '--filter', FILTER], timeout=600)
        for mode, flags in [('normal', []), ('optimized', ['-O'])]:
            for name in ('test_android_sdk_compatibility.py', 'test_android_staging.py', 'test_android_appearance.py'):
                self.run('python-' + mode + '-' + name[:-3], [sys.executable, '-B', *flags,
                    self.source / 'cli/build-tests' / name], timeout=120)
        self.receipt['cases'].append('actual-isolated-Debug-Release-CLI-builds-and-focused-tests-plus-three-Python-host-suites-in-both-modes')

    def consumers(self):
        cli = self.clis['debug']
        app = BASE / 'Profile3Consumer'
        self.run('actual-cli-create', [cli, 'create', 'Profile3Consumer', '--directory', app,
                 '--application', 'dev.mixer.privateownerconsumer', '--platform', 'android',
                 '--sdk-path', self.source / 'sdk', '--android-adapter-path', self.source / 'native/android'], timeout=300)
        driver = app / 'Generated/MixerAndroid/android-build.py'
        self.driver = read_driver(driver, 'selected_actual_profile3_driver')
        m = self.driver
        check(m.source_profile() == self.profile, 'actual rendered driver profile')
        check(load(app / 'mixer.lock')['android']['profile'] == m.profile_lock(self.profile), 'actual lock profile')
        require(app / 'Generated/MixerAndroid/app/assets/MixerAppearanceV2/descriptor.json', self.profile['default_descriptor'])
        check(identity(m.admit_source_pair(app, self.profile)) == self.profile['default_descriptor'], 'actual created admission')
        exported = BASE / 'CopiedConsumer'
        self.run('actual-cli-export', [self.clis['release'], 'export', exported, '--directory', app])
        check(m.admit_source_pair(exported, self.profile) == m.admit_source_pair(app, self.profile), 'copied export admission')
        self.exported = exported
        for label, package in [('copied-shared-app', exported), ('copied-native-session', exported / 'Platforms/Android')]:
            scratch = BASE / ('build-' + label)
            self.scratch.append(scratch)
            self.run(label + '-host-tests', [SWIFT, 'test', '--package-path', package, '--scratch-path', scratch,
                     '--disable-automatic-resolution', '--jobs', '2'], timeout=600)
        entry = exported / 'Platforms/Android/Sources/AppAndroid/NativeEntry.swift'
        reducer = exported / 'Sources/AppFeatures/ProjectFeature.swift'
        original_entry = entry.read_text()
        original_reducer = reducer.read_text()
        check('ProjectFeatureState()' in original_entry and 'state.draft = value' in original_reducer,
              'expected app-owned factory/reducer seam')
        entry.write_text(original_entry.replace('ProjectFeatureState()', 'ProjectFeatureState(draft: "Selected owner factory seed")'))
        reducer.write_text(original_reducer.replace('state.draft = value', 'state.draft = value.uppercased()'))
        custom = exported / 'Platforms/Android/Tests/AppAndroidTests/Profile3FactoryTests.swift'
        custom.write_text('''import Foundation
import Testing
import MixerUI
@_spi(MixerNativeAppearanceV2) @testable import AppAndroid
@Test func profile3CopiedFactoryReducer() throws {
    let helper = ApplicationSessionTests()
    let handle = mixerAndroidCreate(); #expect(handle != 0)
    defer { #expect(mixerAndroidDestroy(handle) == 0) }
    let initial = helper.exchange(handle); #expect(initial.0 == 0)
    #expect(String(decoding: initial.1, as: UTF8.self).contains("Selected owner factory seed"))
    let event = try helper.event(initial.1, id: "draft", kind: .textChange, value: .string("selected lower"))
    let changed = helper.exchange(handle, event); #expect(changed.0 == 0)
    #expect(String(decoding: changed.1, as: UTF8.self).contains("SELECTED LOWER"))
    func revision(_ data: Data) throws -> UInt64 {
        let object = try #require(JSONSerialization.jsonObject(with: data) as? [String: Any])
        return try UIDocument.decode(JSONSerialization.data(withJSONObject: object["document"]!)).revision
    }
    #expect(try revision(initial.1) == 1); #expect(try revision(changed.1) == 2)
}
''')
        self.receipt['copied_app_owned_variation'] = {str(p.relative_to(exported)): identity(p.read_bytes())
                                                     for p in (entry, reducer, custom)}
        self.run('copied-custom-factory-reducer-test', [SWIFT, 'test', '--package-path', exported / 'Platforms/Android',
                 '--scratch-path', BASE / 'build-copied-native-session', '--disable-automatic-resolution', '--jobs', '2',
                 '--filter', 'profile3CopiedFactoryReducer'], timeout=600)
        save(BASE / 'consumer-source-binding.json', {
            'created': regular_files(app), 'copied_and_customized': regular_files(exported),
            'created_lock': load(app / 'mixer.lock'), 'copied_lock': load(exported / 'mixer.lock'),
            'rendered_driver': identity(driver.read_bytes()),
        })
        self.receipt['cases'].append('actual-create-Release-export-canonical44-source-admission-and-copied-app-owned-factory-reducer-revision-host-controls')

    def refusals(self):
        m = self.driver
        fixture = BASE / 'preaccess-fixture'
        shutil.copytree(self.exported, fixture)
        self.scratch.append(fixture)
        original_lock = load(fixture / 'mixer.lock')
        trap = BASE / 'trap-tools'
        trap.mkdir()
        marker = trap / 'tool-invoked'
        for name in ('swift', 'python3'):
            path = trap / name
            path.write_text('#!/bin/sh\n/usr/bin/touch "' + str(marker) + '"\necho TOOL-ORDER-SENTINEL >&2\nexit 99\n')
            path.chmod(0o755)
        env = dict(self.env, PATH=str(trap) + ':' + self.env['PATH'], MIXER_SWIFT=str(trap / 'swift'))
        tests = [('profile2', None, None), ('missing-android-lock', None, None)]
        tests += [(name[:-5] + '-' + change, name, change)
                  for name in ('NativeOwnerV2.java', 'OwnerLifecycleV2.java')
                  for change in ('same-size', 'remove', 'rename')]
        reports = []
        for label, filename, change in tests:
            lock = json.loads(json.dumps(original_lock))
            source = fixture / 'Generated/MixerAndroid/app/src/dev/mixer/android' / filename if filename else None
            before = source.read_bytes() if source else None
            renamed = source.with_suffix('.renamed') if source else None
            if label == 'profile2':
                lock['android']['profile']['id'] = 'mixer.android-source-pair.2'
                code, driver_text = 'android.sdk-profile-mismatch', 'profile-mismatch'
            elif label == 'missing-android-lock':
                del lock['android']
                code, driver_text = 'android.sdk-profile-required', 'profile-required'
            else:
                if change == 'same-size':
                    source.write_bytes(b'x' * len(before))
                elif change == 'remove':
                    source.unlink()
                else:
                    source.rename(renamed)
                lock['android']['adapterDigest'] = m.source_tree(fixture / 'Generated/MixerAndroid')
                code, driver_text = 'android.sdk-compatibility', 'source compatibility rejected'
            save(fixture / 'mixer.lock', lock)
            try:
                with (mock.patch.object(m, 'source_tree', side_effect=RuntimeError('PREACCESS-GENERIC-HASH')),
                      mock.patch.object(m, 'inspect', side_effect=RuntimeError('PREACCESS-TOOLS')),
                      mock.patch.object(m, 'checked_output', side_effect=RuntimeError('PREACCESS-OUTPUT'))):
                    try:
                        m.build(fixture)
                    except RuntimeError as rejected:
                        check(driver_text in str(rejected), label + ' trap refusal')
                    else:
                        raise RuntimeError(label + ' admitted by driver')
                for mode, cli in self.clis.items():
                    for platform in ('android', 'host', 'ios'):
                        out, _ = self.run(mode + '-' + label + '-' + platform, [cli, 'build', '--directory', fixture,
                                         '--platform', platform], expected=1, env=env, timeout=20)
                        check(load_json_bytes(out)['code'] == code, label + ' actual CLI refusal')
                    destination = BASE / ('forbidden-' + mode + '-' + label)
                    out, _ = self.run(mode + '-' + label + '-export', [cli, 'export', destination,
                                     '--directory', fixture], expected=1, env=env, timeout=20)
                    check(load_json_bytes(out)['code'] == code and not destination.exists(), label + ' actual export refusal')
                _, err = self.run(label + '-actual-rendered-driver', [sys.executable, '-B',
                                 fixture / 'Generated/MixerAndroid/android-build.py', 'build', fixture],
                                 expected=1, env=env, timeout=20)
                check(driver_text in err.decode(), label + ' direct driver refusal')
                check(not marker.exists() and not (fixture / '.mixer').exists(), label + ' touched tools/output')
                reports.append({'label': label, 'expected_code': code, 'recomputed_generic_adapter_lock': filename is not None,
                                'actual_Debug_Release_common_platforms_and_export': True,
                                'actual_driver_and_preaccess_traps': True, 'tools_output_absent': True})
            finally:
                if source:
                    renamed.unlink(missing_ok=True)
                    source.write_bytes(before)
                save(fixture / 'mixer.lock', original_lock)
        # An old rendered policy refuses before reading a project lock, including absent roots.
        historical = load(BASE.parent / 'before/profile2.json')
        with mock.patch.object(m, 'SOURCE_PROFILE_HEX', json.dumps(historical).encode().hex()), \
             mock.patch.object(m, 'read_json', side_effect=RuntimeError('LOCK-READ-BEFORE-POLICY')):
            try:
                m.build(BASE / 'absent-root')
            except RuntimeError as failure:
                check('not rendered or supported' in str(failure), 'profile2 rendered policy pre-lock refusal')
            else:
                raise RuntimeError('old driver policy admitted')
        save(BASE / 'actual-preaccess-controls.json', {'controls': reports, 'old_policy_prelock_refusal': True,
                                                      'trap_tools': regular_files(trap)})
        self.receipt['cases'].append('profile2-missing-lock-and-six-owner-core-tampers-refuse-before-tools-output-in-actual-Debug-Release-common-CLI-and-driver')

    def final_audit(self):
        for name, expected in self.canonical.items():
            require(ROOT / name, expected)
        for name, expected in self.source_binding.items():
            require(ROOT / name, expected)
            require(self.source / name, expected)
        history = {p.relative_to(BASE.parent).as_posix(): identity(p.read_bytes())
                   for p in sorted(BASE.parent.rglob('*')) if p.is_file() and BASE not in p.parents}
        check(history == self.history, 'preexisting profile history changed')
        save(BASE / 'historical-inputs-after.json', history)
        save(BASE / 'final-owned-sources.json', {name: identity((ROOT / name).read_bytes()) for name in OWNED})
        # These are reused producer compilation observations, not fresh compiler/runtime evidence.
        cross = CANDIDATE / 'evidence/publication-repair-crosscompile-1'
        reused = {p.relative_to(CANDIDATE).as_posix(): identity(p.read_bytes())
                  for p in sorted(cross.rglob('*')) if p.is_file()}
        save(BASE / 'producer-compilation-reuse.json', {
            'scope': 'offline exact-source provenance reuse only; no new Java/D8/Swift-JNI compilation credit',
            'canonical_inputs_reverified': 309, 'root_admitted_Swift_JNI_unchanged_inputs': 76,
            'admission_sha256': PINS['admission'], 'candidate_manifest_sha256': PINS['candidate_manifest'],
            'retained_producer_crosscompile_members': reused,
            'producer_status': load(cross / 'receipt.json')['status'],
        })
        self.receipt['post_source_audit'] = {'snapshot_and_live_sources_match': True, 'canonical309_unchanged': True,
                                            'historical_profile_inputs_unchanged': True}

    def finish(self):
        removed = []
        binary_hashes = {}
        for folder in self.scratch:
            if folder.exists():
                for path in sorted(folder.rglob('*')):
                    if path.is_file() and not path.is_symlink() and (path.name in ('mixer', 'libAppAndroid.dylib')
                        or path.suffix in ('.xctest', '.dylib', '.so') or any(p.endswith('.xctest') for p in path.parts)):
                        binary_hashes[str(path.relative_to(BASE))] = identity(path.read_bytes())
                shutil.rmtree(folder)
                removed.append(str(folder.relative_to(BASE)))
        save(BASE / 'compiled-products-before-cleanup.json', binary_hashes)
        self.receipt.update(commands='commands.json', tool_versions=self.versions,
                            cleanup={'owned_scratch_removed': removed, 'returned_binaries_hashed_before_deletion': True,
                                     'only_owned_child_groups_signaled': True,
                                     'native_capture_UI_instances_started': False},
                            pending=['Independent source/barrier/legacy matrix and implementation acceptance',
                                     'Root review, coherent delivery and CI', 'Native Android runtime and physical phone matrix paused',
                                     'Public V2 routing, immutable published FieldLog packages, signing/store/operational/GA gates'],
                            implementation_accepted=False, GA_qualified=False)
        save(BASE / 'receipt.json', self.receipt)

    def main(self):
        try:
            self.preflight_and_rebind()
            self.snapshot()
            self.tools_and_builds()
            self.consumers()
            self.refusals()
            self.final_audit()
            self.receipt['status'] = 'passed-exact-candidate4-profile3-host-qualification-awaiting-independent-root-review'
        except BaseException as failure:
            self.receipt['failure'] = {'type': type(failure).__name__, 'message': str(failure)}
            raise
        finally:
            self.finish()


def load_json_bytes(data):
    return json.loads(data.decode())


if __name__ == '__main__':
    Qualification().main()
