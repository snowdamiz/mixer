#!/usr/bin/env python3
"""Independent bounded consumer controls and signature compilation of admitted bytes."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
PRODUCER = ROOT / 'verification/android-environment-observer-lifecycle'
SOURCE = PRODUCER / 'profile-qualification-2/source'
OUT = PACKET / 'profile-signature-controls-3'
EXPECTED_PROPOSAL = '80eed4b279283d073f745061eb071aff7daa7b4369cbabd9e4b97fab6ff98b8a'
EXPECTED_MANIFEST = '12ff1a93d3ea3bfcbac663745759514a72c9db78e7ef43729f697030dc393060'
EXPECTED_OBSERVER = '814b00b91b458c1287cb9c924c099fc2e647e42501b09e09acd711fbe5b54dac'
STRIP = ('CLASSPATH', 'JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS', 'JDK_JAVAC_OPTIONS')


def ident(data): return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
def load(path): return json.loads(path.read_text())
def save(path, value): path.write_text(json.dumps(value, indent=2) + '\n')
def literal(path): return json.loads(path.read_text().split('Data(#"""\n', 1)[1].split('"""#.utf8)', 1)[0])
def project(files): return hashlib.sha256(''.join(p + '\0' + files[p]['sha256'] + '\n' for p in sorted(files)).encode()).hexdigest()
def require(path, expected):
    actual = ident(path.read_bytes())
    assert actual == expected, (str(path), actual, expected)
    return actual


def main():
    OUT.mkdir(exist_ok=False)
    receipt = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'argv': [sys.executable, *sys.argv], 'python_version': sys.version,
               'script': ident(Path(__file__).read_bytes()), 'commands': [], 'cases': [], 'status': 'failed',
               'native_capture_ui_or_process_discovery': False,
               'scope': 'Independent actual CLI/rendered-driver admission, ordinary app-owned factory/reducer host tests and actual adapter Java/D8 signature controls; no Android runtime or release authority.'}
    scratch = None
    env = {k: v for k, v in os.environ.items() if k not in STRIP}
    env['PATH'] = '/usr/bin:' + env.get('PATH', '')
    env['MIXER_SWIFT'] = '/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift'
    env['PYTHONDONTWRITEBYTECODE'] = '1'

    def run(label, argv, expected=0, run_env=None, timeout=60):
        argv = list(map(str, argv))
        child = subprocess.Popen(argv, cwd=ROOT, env=run_env or env, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        timed = False
        try: stdout, stderr = child.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed = True; os.killpg(child.pid, signal.SIGKILL); stdout, stderr = child.communicate()
        (OUT / (label + '.stdout')).write_bytes(stdout); (OUT / (label + '.stderr')).write_bytes(stderr)
        receipt['commands'].append({'label': label, 'argv': argv, 'cwd': str(ROOT), 'exit': child.returncode,
            'expected_exit': expected, 'timed_out': timed, 'child_reaped': True,
            'stdout': ident(stdout), 'stderr': ident(stderr)})
        save(OUT / 'receipt.json', receipt)
        print(label, child.returncode, flush=True)
        assert child.returncode == expected and not timed, label
        return stdout, stderr

    try:
        assert ident((PRODUCER / 'manifest.json').read_bytes())['sha256'] == EXPECTED_MANIFEST
        assert ident((PRODUCER / 'candidate-proposal.json').read_bytes())['sha256'] == EXPECTED_PROPOSAL
        proposal = load(PRODUCER / 'candidate-proposal.json')
        for relative, expected in proposal['files'].items(): require(PRODUCER / 'candidate-inputs' / relative, expected)
        old = literal(ROOT / 'verification/android-owner-effect-contract/inputs/cli/Sources/MixerBuild/AndroidSDKCompatibility.swift')
        profile = literal(PRODUCER / 'candidate-inputs/cli/Sources/MixerBuild/AndroidSDKCompatibility.swift')
        assert profile == load(PRODUCER / 'candidate-profile-2.json')
        assert profile['schema'] == 1 and profile['id'] == 'mixer.android-source-pair.2'
        assert profile['default_descriptor'] == old['default_descriptor'] and profile['wire'] == old['wire']
        assert profile['sdk_files'] == old['sdk_files'] and len(profile['sdk_files']) == 22
        assert set(profile['adapter_files']) == set(old['adapter_files']) and len(profile['adapter_files']) == 20
        changed = [p for p in old['adapter_files'] if old['adapter_files'][p] != profile['adapter_files'][p]]
        assert changed == ['app/src/dev/mixer/android/NativeEnvironmentV2.java'], changed
        assert profile['adapter_files'][changed[0]]['sha256'] == EXPECTED_OBSERVER
        for kind in ('sdk', 'adapter'):
            assert project(profile[kind + '_files']) == profile[kind + '_compatibility_sha256']
        receipt['fixed_map'] = {'sdk': 22, 'adapter': 20, 'changed': changed,
            'sdk_sha256': profile['sdk_compatibility_sha256'], 'adapter_sha256': profile['adapter_compatibility_sha256']}
        receipt['cases'].append('independent-old-to-new-exact42-map-only-observer-diff')
        audited = []
        for folder in ('profile-qualification-2', 'cross-compilation-1'):
            prior = load(PRODUCER / folder / 'receipt.json')
            for cmd in load(PRODUCER / folder / 'commands.json'):
                assert cmd['exit'] == cmd.get('expected_exit', 0) and not cmd['timed_out'] and cmd['child_reaped']
                for stream in ('stdout', 'stderr'):
                    require(PRODUCER / folder / (cmd['label'] + '.' + stream), cmd[stream])
            audited.append({'folder': folder, 'receipt': ident((PRODUCER / folder / 'receipt.json').read_bytes()),
                            'commands': ident((PRODUCER / folder / 'commands.json').read_bytes()), 'status': prior['status']})
        receipt['producer_command_stream_audit'] = audited
        receipt['cases'].append('producer-actual-cli-and-swift-jni-crosscompile-command-stream-identities-audited')
        scratch = Path(tempfile.mkdtemp(prefix='consumer-signature-', dir=OUT))
        run('swift-version', ['/usr/bin/swift', '--version'])
        receipt['host_swift_launcher'] = {'path': '/usr/bin/swift', **ident(Path('/usr/bin/swift').read_bytes())}
        cli_build = scratch / 'cli-build'
        run('actual-cli-build', ['/usr/bin/swift', 'build', '--package-path', SOURCE / 'cli', '--scratch-path', cli_build,
                                '--disable-automatic-resolution', '--product', 'mixer'])
        cli = cli_build / 'debug/mixer'; receipt['compiled_cli'] = ident(cli.read_bytes())
        app = OUT / 'IndependentConsumer'
        run('actual-cli-create', [cli, 'create', 'IndependentConsumer', '--directory', app,
            '--application', 'dev.mixer.independentobserver', '--platform', 'android', '--sdk-path', SOURCE / 'sdk',
            '--android-adapter-path', SOURCE / 'native/android'])
        driver = app / 'Generated/MixerAndroid/android-build.py'
        spec = importlib.util.spec_from_file_location('independently_audited_actual_rendered_driver', driver)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        assert module.source_profile() == profile
        assert module.profile_lock(profile) == load(app / 'mixer.lock')['android']['profile']
        require(app / 'Generated/MixerAndroid/app/assets/MixerAppearanceV2/descriptor.json', profile['default_descriptor'])
        assert ident(module.admit_source_pair(app, profile)) == profile['default_descriptor']
        receipt['rendered_driver'] = ident(driver.read_bytes())
        receipt['cases'].append('fresh-actual-cli-created-app-and-actual-rendered-driver-positive-admission')
        run('ordinary-preset-session-tests', ['/usr/bin/swift', 'test', '--package-path', app / 'Platforms/Android',
                                             '--scratch-path', scratch / 'app-tests'])
        entry = app / 'Platforms/Android/Sources/AppAndroid/NativeEntry.swift'
        data = entry.read_text(); assert 'ProjectFeatureState()' in data
        entry.write_text(data.replace('ProjectFeatureState()', 'ProjectFeatureState(draft: "Independent factory seed")'))
        reducer = app / 'Sources/AppFeatures/ProjectFeature.swift'
        data = reducer.read_text(); assert 'state.draft = value' in data
        reducer.write_text(data.replace('state.draft = value', 'state.draft = value.uppercased()'))
        custom = app / 'Platforms/Android/Tests/AppAndroidTests/IndependentFactoryTests.swift'
        custom.write_text('''import Foundation
import Testing
import MixerUI
@_spi(MixerNativeAppearanceV2) @testable import AppAndroid
@Test func independentFactoryReducer() throws {
    let helper = ApplicationSessionTests()
    let handle = mixerAndroidCreate(); #expect(handle != 0)
    defer { #expect(mixerAndroidDestroy(handle) == 0) }
    let initial = helper.exchange(handle); #expect(initial.0 == 0)
    #expect(String(decoding: initial.1, as: UTF8.self).contains("Independent factory seed"))
    let event = try helper.event(initial.1, id: "draft", kind: .textChange, value: .string("custom lower"))
    let changed = helper.exchange(handle, event); #expect(changed.0 == 0)
    #expect(String(decoding: changed.1, as: UTF8.self).contains("CUSTOM LOWER"))
    func revision(_ data: Data) throws -> UInt64 {
        let object = try #require(JSONSerialization.jsonObject(with: data) as? [String: Any])
        return try UIDocument.decode(JSONSerialization.data(withJSONObject: object["document"]!)).revision
    }
    #expect(try revision(initial.1) == 1)
    #expect(try revision(changed.1) == 2)
}
''')
        receipt['app_owned_variation'] = {str(p.relative_to(app)): ident(p.read_bytes()) for p in (entry, reducer, custom)}
        run('independent-factory-reducer-test', ['/usr/bin/swift', 'test', '--package-path', app / 'Platforms/Android',
            '--scratch-path', scratch / 'app-tests', '--filter', 'independentFactoryReducer'])
        receipt['cases'].append('ordinary-app-owned-preset-and-distinct-factory-reducer-revision-controls')
        for name in ('old-profile', 'profile-id-only', 'missing-profile', 'wrong-profile-type', 'edited-observer',
                     'recomputed-lock', 'edited-sdk-recomputed-lock', 'edited-descriptor-recomputed-lock',
                     'edited-profile-projection', 'unknown-profile-field', 'extra-sdk-source'):
            fixture = OUT / name
            shutil.copytree(app, fixture, ignore=shutil.ignore_patterns('.build', '.swiftpm'))
            lock = load(fixture / 'mixer.lock')
            expected = 'android.sdk-compatibility'
            if name == 'old-profile':
                lock['android']['profile'] = module.profile_lock(old); shutil.rmtree(fixture / 'Generated'); expected = 'android.sdk-profile-mismatch'
            elif name == 'profile-id-only':
                lock['android']['profile']['id'] = old['id']; expected = 'android.sdk-profile-mismatch'
            elif name == 'missing-profile':
                del lock['android']['profile']; expected = 'android.sdk-profile-required'
            elif name == 'wrong-profile-type':
                lock['android']['profile'] = 'unselected record type'; expected = 'android.sdk-profile-mismatch'
            elif name == 'unknown-profile-field':
                lock['android']['profile']['unselected'] = True; expected = 'android.sdk-profile-mismatch'
            elif name == 'extra-sdk-source':
                (fixture / 'Generated/MixerSDK/Sources/MixerCore/Unselected.swift').write_text('unselected source must never be generic-hashed')
            elif name == 'edited-sdk-recomputed-lock':
                changed_source = fixture / 'Generated/MixerSDK/Sources/MixerCore/Lifecycle.swift'
                before = changed_source.read_bytes(); changed_source.write_bytes(b'!' + before[1:])
                lock['sdkDigest'] = module.source_tree(fixture / 'Generated/MixerSDK')
            elif name == 'edited-descriptor-recomputed-lock':
                changed_source = fixture / 'Generated/MixerAndroid/app/assets/MixerAppearanceV2/descriptor.json'
                before = changed_source.read_bytes(); changed_source.write_bytes(b'!' + before[1:])
                lock['android']['adapterDigest'] = module.source_tree(fixture / 'Generated/MixerAndroid')
            else:
                observer = fixture / 'Generated/MixerAndroid/app/src/dev/mixer/android/NativeEnvironmentV2.java'
                before = observer.read_bytes(); observer.write_bytes(before.replace(b'private long generation = 1;', b'private long generation = 2;'))
                assert len(observer.read_bytes()) == len(before) and observer.read_bytes() != before
                if name in ('recomputed-lock', 'edited-profile-projection'):
                    lock['android']['adapterDigest'] = module.source_tree(fixture / 'Generated/MixerAndroid')
                if name == 'edited-profile-projection':
                    edited_map = dict(profile['adapter_files'])
                    edited_map['app/src/dev/mixer/android/NativeEnvironmentV2.java'] = ident(observer.read_bytes())
                    lock['android']['profile']['adapter_compatibility_sha256'] = project(edited_map)
                    expected = 'android.sdk-profile-mismatch'
            save(fixture / 'mixer.lock', lock)
            expected_driver = ('profile-required' if name in ('missing-profile', 'wrong-profile-type') else
                'profile-mismatch' if expected.endswith('profile-mismatch') else 'source compatibility rejected')
            for function in ('source_tree', 'inspect', 'checked_output'):
                original = getattr(module, function)
                def trap(*args, _function=function, **kwargs): raise AssertionError('preaccess violation: ' + _function)
                setattr(module, function, trap)
                try:
                    try: module.build(fixture)
                    except RuntimeError as rejected:
                        assert expected_driver in str(rejected)
                    else: raise AssertionError('negative profile fixture admitted')
                finally: setattr(module, function, original)
            stdout, _ = run(name + '-actual-cli', [cli, 'build', '--platform', 'android', '--directory', fixture], expected=1)
            assert json.loads(stdout)['code'] == expected, stdout
            _, stderr = run(name + '-actual-driver', [sys.executable, '-B', driver, 'build', fixture], expected=1)
            assert expected_driver in stderr.decode()
            assert not (fixture / '.mixer').exists()
            receipt['cases'].append(name + '-actual-cli-driver-reject-with-preaccess-traps-no-output')
        literal_original = module.SOURCE_PROFILE_HEX
        read_original = module.read_json
        bad_policy = dict(profile); bad_policy['unknown'] = True
        wrong_schema = dict(profile); wrong_schema['schema'] = True
        wrong_id = dict(profile); wrong_id['id'] = old['id']
        short_map = dict(profile); short_map['sdk_files'] = dict(profile['sdk_files']); short_map['sdk_files'].pop('Package.swift')
        for label, encoded in (
            ('unknown-policy-field', json.dumps(bad_policy)), ('wrong-schema-type', json.dumps(wrong_schema)),
            ('old-policy-id', json.dumps(wrong_id)), ('wrong-map-count', json.dumps(short_map)),
            ('duplicate-policy-key', json.dumps(profile)[:-1] + ',"id":"mixer.android-source-pair.2"}'),
            ('unrendered-policy', '__MIXER_ANDROID_SOURCE_PROFILE_HEX__')):
            module.SOURCE_PROFILE_HEX = encoded.encode().hex() if label != 'unrendered-policy' else encoded
            def trap_lock(*args, **kwargs): raise AssertionError('lock read before policy decode rejection')
            module.read_json = trap_lock
            try:
                try: module.build(OUT / 'absent-root')
                except RuntimeError as rejected: assert 'not rendered or supported' in str(rejected)
                else: raise AssertionError('invalid rendered policy admitted')
            finally:
                module.SOURCE_PROFILE_HEX = literal_original; module.read_json = read_original
            receipt['cases'].append(label + '-rendered-driver-pre-lock-rejection')
        admission = load(ROOT / 'verification/android-environment-observer-root-review/independent-candidate-admission.json')
        javac = Path(admission['tools']['javac']['resolved'])
        require(javac, {'bytes': admission['tools']['javac']['bytes'], 'sha256': admission['tools']['javac']['sha256']})
        jar = Path('/opt/homebrew/share/android-commandlinetools/platforms/android-37.0/android.jar')
        expected_jar = load(PRODUCER / 'cross-compilation-1/receipt.json')['android_sdk_jar']
        require(jar, {k: expected_jar[k] for k in ('bytes', 'sha256')})
        d8 = Path('/opt/homebrew/share/android-commandlinetools/build-tools/37.0.0/d8')
        d8jar = d8.parent / 'lib/d8.jar'
        receipt['signature_tools'] = {'javac': {'path': str(javac), **ident(javac.read_bytes())},
            'android_jar': {'path': str(jar), **ident(jar.read_bytes())}, 'd8': {'path': str(d8), **ident(d8.read_bytes())},
            'd8_jar': {'path': str(d8jar), **ident(d8jar.read_bytes())}}
        env['JAVA_HOME'] = str(javac.parent.parent)
        run('d8-version', [d8, '--version'])
        classes = scratch / 'classes'; empty = scratch / 'empty'; dex = scratch / 'dex'
        classes.mkdir(); empty.mkdir(); dex.mkdir()
        java_sources = [PRODUCER / 'candidate-inputs/native/android' / p for p in sorted(profile['adapter_files']) if p.startswith('app/src/') and p.endswith('.java')]
        assert len(java_sources) == 14
        run('independent-javac-sdk', [javac, '--release', '17', '-Xlint:all', '-Werror', '-proc:none', '-classpath', jar,
                                    '-sourcepath', empty, '-d', classes, *java_sources])
        compiled = sorted(classes.rglob('*.class'))
        receipt['classes'] = {str(p.relative_to(classes)): ident(p.read_bytes()) for p in compiled}
        run('independent-d8-min28', [d8, '--min-api', '28', '--lib', jar, '--output', dex, *compiled])
        receipt['dex'] = {p.name: ident(p.read_bytes()) for p in sorted(dex.glob('*.dex'))}
        assert len(compiled) == 160 and receipt['dex']
        receipt['cases'].append('independent-complete14java-adapter-pinned-sdk-java17-and-d8-min28')
        for relative, expected in proposal['files'].items(): require(PRODUCER / 'candidate-inputs' / relative, expected)
        receipt['status'] = 'passed-independent-consumer-and-signature-controls'
    except BaseException as error:
        receipt['failure'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        if scratch is not None: shutil.rmtree(scratch)
        receipt['cleanup'] = {'owned_scratch_removed': scratch is None or not scratch.exists(),
            'owned_children_reaped': all(c['child_reaped'] for c in receipt['commands']), 'native_instances_created': False}
        save(OUT / 'receipt.json', receipt)


if __name__ == '__main__': main()
