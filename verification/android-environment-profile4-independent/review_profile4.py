#!/usr/bin/env python3
"""Independent host review of the sealed profile4 CLI; no native/UI operations."""
from __future__ import annotations

import ast
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import traceback

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PRODUCER = ROOT / 'verification/android-environment-platform-profile4'
EXPECTED = {
    'verification/android-environment-platform-profile4/manifest.json': '046f1a5a4f69dae7dafb529d55caf7fcd475a54614c40103f90be1d7fd6d39b4',
    'verification/android-environment-platform-profile4/source-map.json': '32fbc6369362631d69c66baaeaf1131d04cf697b9d0781f9bfa4e72624f4348c',
    'verification/android-environment-platform-implementation/manifest.json': '161c47daa9c07cd01252327f31b814ed3a3f708587f2ed84adaee81b902cfacf',
    'verification/android-environment-platform-independent/manifest.json': '0912ccdf0ad7b09c5bef249cc4db4cd4d952dd08863de3ffe06435644ce60a9b',
    'verification/android-environment-platform-root-review/selection.json': '55214c11fcf73b9a788421e70a99546f696a72b76183001ad3ed93e3639c6ba7',
    'verification/android-environment-platform-root-review/native-acceptance.json': '0c15ca808c2f5684d768125674cdfc0bf48bff672193f79fcaaee47726bf2478',
}
commands, checks, products = [], [], []
scratch = None
source_map = json.loads((PRODUCER / 'source-map.json').read_text())
profile = json.loads((PRODUCER / 'proposed-profile4.json').read_text())
prior = json.loads((PRODUCER / 'prior-profile3.json').read_text())
extra_sources = {}
sys.dont_write_bytecode = True


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def demand(value, message):
    if not value:
        raise AssertionError(message)


def check(name, **detail):
    checks.append({'name': name, 'passed': True, **detail})
    save('checks.json', checks)


def run(label, args, *, cwd=None, env=None, timeout=600, expected=0):
    args = list(map(str, args))
    started = now()
    process = subprocess.Popen(args, cwd=cwd or ROOT, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
    (HERE / (label + '.stdout')).write_bytes(stdout)
    (HERE / (label + '.stderr')).write_bytes(stderr)
    commands.append({'label': label, 'argv': args, 'cwd': str(cwd or ROOT),
                     'started': started, 'ended': now(), 'exit': process.returncode,
                     'timed_out': timed_out, 'child_reaped': process.poll() is not None,
                     'stdout': identity(stdout), 'stderr': identity(stderr)})
    save('commands.json', commands)
    demand(not timed_out, label + ' timeout')
    if expected is not None:
        demand(process.returncode == expected, label + ' exit: ' + str(process.returncode))
    return process.returncode, stdout, stderr


def custody():
    packets = []
    for relative, expected in EXPECTED.items():
        p = ROOT / relative
        demand(identity(p.read_bytes())['sha256'] == expected, 'Seal changed: ' + relative)
        value = json.loads(p.read_text())
        if relative.endswith('manifest.json'):
            members = value.get('files') or {r['path']: {k: r[k] for k in ('bytes', 'sha256')} for r in value['members']}
            for path, digest in members.items():
                demand(identity((ROOT / path).read_bytes()) == digest, 'Member changed: ' + path)
            count = value.get('member_count', value.get('members', len(members)))
            demand(count == len(members), 'Member count mismatch: ' + relative)
            total = sum(d['bytes'] for d in members.values())
            if 'member_bytes' in value:
                demand(total == value['member_bytes'], 'Member byte total')
            packets.append({'path': relative, 'sha256': expected, 'members_verified': len(members), 'member_bytes': total})
    demand(len(source_map) == 111, 'Expected exact111source map')
    for relative, expected in source_map.items():
        demand(identity((ROOT / relative).read_bytes()) == expected, 'Live source drift: ' + relative)
        demand(identity((PRODUCER / 'source' / relative).read_bytes()) == expected, 'Frozen source drift: ' + relative)
    save('custody.json', {'at': now(), 'packets': packets, 'seals': EXPECTED, 'live_and_frozen_sources': len(source_map),
                         'source_map_identity': identity((PRODUCER / 'source-map.json').read_bytes())})
    check('exact-custody', members=sum(p['members_verified'] for p in packets), sources=len(source_map))


def projection(files):
    return hashlib.sha256(''.join(n + '\0' + files[n]['sha256'] + '\n' for n in sorted(files)).encode()).hexdigest()


def lock_profile(value):
    return {k: value[k] for k in ('id', 'sdk_compatibility_sha256', 'adapter_compatibility_sha256', 'default_descriptor')}


def verify_profile():
    demand(profile['id'] == 'mixer.android-source-pair.4', 'Profile id')
    demand(len(profile['sdk_files']) == 22 and len(profile['adapter_files']) == 23, 'Closed projection counts')
    for kind, prefix in [('sdk', 'sdk/'), ('adapter', 'native/android/')]:
        files = profile[kind + '_files']
        demand(projection(files) == profile[kind + '_compatibility_sha256'], kind + ' projection')
        for relative, ident in files.items():
            source = prefix + ('engine/' if kind == 'adapter' and relative.startswith('Sources/') else '') + relative
            demand(source_map[source] == ident, 'Compiled policy source identity: ' + source)
    demand(prior['sdk_files'] == profile['sdk_files'], 'SDK map changed')
    demand(prior['sdk_compatibility_sha256'] == profile['sdk_compatibility_sha256'], 'SDK hash changed')
    demand(prior['wire'] == profile['wire'], 'Wire changed')
    demand(prior['default_descriptor'] == profile['default_descriptor'], 'Default descriptor changed')
    added = set(profile['adapter_files']) - set(prior['adapter_files'])
    changed = {n for n in prior['adapter_files'] if prior['adapter_files'][n] != profile['adapter_files'].get(n)}
    demand(added == {'app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java'}, 'New adapter closure')
    demand(changed == {'app/src/dev/mixer/android/NativeEnvironmentV2.java'}, 'Changed adapter closure')
    swift = (PRODUCER / 'source/cli/Sources/MixerBuild/AndroidSDKCompatibility.swift').read_text()
    literal = swift.split('from: Data(#"""', 1)[1].split('"""#.utf8)', 1)[0]
    demand(json.loads(literal) == profile, 'Swift embedded policy not equal to reviewed profile')
    native = ROOT / 'verification/android-environment-platform-implementation/final-environment/inputs/native/android'
    for n in added | changed:
        demand(identity((native / n).read_bytes()) == profile['adapter_files'][n], 'Native producer source-pair identity')
    save('projection.json', {'profile': profile['id'], 'sdk': profile['sdk_compatibility_sha256'],
                            'adapter': profile['adapter_compatibility_sha256'], 'sdk_count': 22, 'adapter_count': 23,
                            'added_adapter': sorted(added), 'changed_adapter': sorted(changed),
                            'unchanged_sdk_descriptor_wire': True, 'compiled_swift_literal_exact': True})
    check('projection-native-policy-coherence')


def freeze_build_inputs():
    tree = scratch / 'source'
    for relative, expected in source_map.items():
        target = tree / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PRODUCER / 'source' / relative, target)
        demand(identity(target.read_bytes()) == expected, 'Isolated input differs: ' + relative)
    names = [ROOT / 'updates/Package.swift', ROOT / 'cli/Package.resolved']
    names += sorted(p for p in (ROOT / 'updates/Sources').rglob('*') if p.is_file())
    for source in names:
        relative = str(source.relative_to(ROOT))
        data = source.read_bytes()
        extra_sources[relative] = identity(data)
        target = tree / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    save('build-inputs.json', {'frozen_source_map': EXPECTED['verification/android-environment-platform-profile4/source-map.json'],
                              'frozen_sources': source_map, 'additional_unchanged_build_dependencies': extra_sources,
                              'note': 'Extra local update-verifier dependency inputs are current exact bytes, not part of the profile4 source projection.'})
    return tree


def inventory(path):
    result = {}
    if not path.exists():
        return result
    for p in sorted(path.rglob('*')):
        relative = str(p.relative_to(path))
        if p.is_symlink():
            result[relative] = {'symlink': os.readlink(p)}
        elif p.is_file():
            result[relative] = identity(p.read_bytes())
        elif p.is_dir():
            result[relative] = {'directory': True}
        else:
            result[relative] = {'unsupported': True}
    return result


def source_tree(path):
    # Independently implement the existing unauthenticated whole-source digest.
    # It is a mutation input, never the source compatibility oracle.
    excluded = {'.build', '.git', '.swiftpm', 'node_modules', '.gradle', '.mixer', 'target', '.DS_Store'}
    records = []
    for p in sorted(path.rglob('*')):
        relative = p.relative_to(path)
        if any(part in excluded for part in relative.parts):
            continue
        if p.is_file() and not p.is_symlink():
            name = p.name
            if name == '.env' or (name.startswith('.env.') and name != '.env.example') or p.suffix.lower() in {'.pem', '.key', '.p12', '.pfx', '.mobileprovision', '.keystore', '.jks'}:
                continue
            records.append(str(relative) + '\0' + identity(p.read_bytes())['sha256'] + '\n')
    return hashlib.sha256(''.join(records).encode()).hexdigest()


def load_driver(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_generated(app, module):
    lock = json.loads((app / 'mixer.lock').read_text())
    demand(lock['android']['profile'] == lock_profile(profile), 'Actual generated lock policy')
    for kind, prefix in [('sdk', 'Generated/MixerSDK'), ('adapter', 'Generated/MixerAndroid')]:
        for relative, ident in profile[kind + '_files'].items():
            demand(identity((app / prefix / relative).read_bytes()) == ident, 'Actual generated projection: ' + relative)
    descriptor = (app / 'Generated/MixerAndroid/app/assets/MixerAppearanceV2/descriptor.json').read_bytes()
    demand(identity(descriptor) == profile['default_descriptor'], 'Actual generated default descriptor')
    demand(descriptor == (PRODUCER / 'source/verification/android-default-appearance-packaging/run-2/created-descriptor.json').read_bytes(), 'Frozen default bytes')
    demand(module.source_profile() == profile, 'Rendered driver policy')
    demand(module.admit_source_pair(app, module.source_profile()) == descriptor, 'Actual source pair admission')
    demand(source_tree(app / 'Generated/MixerAndroid') == lock['android']['adapterDigest'], 'Independent adapter full-tree digest')
    demand(source_tree(app / 'Generated/MixerSDK') == lock['sdkDigest'], 'Independent SDK full-tree digest')
    return inventory(app)


def refusals(binary, baseline, module, source):
    tools = scratch / 'tool-sentinels'
    tools.mkdir()
    marker = scratch / 'unexpected-tool-call'
    tool_source = '#!/bin/sh\nprintf "%s\\n" "$0 $*" >> "$MIXER_INDEPENDENT_TOOL_MARKER"\nexit 97\n'
    for name in ['swift', 'python3', 'xcodebuild', 'xcrun', 'java', 'javac', 'adb', 'emulator', 'simctl']:
        p = tools / name
        p.write_text(tool_source)
        p.chmod(0o755)
    negative_env = os.environ.copy()
    negative_env.update(PATH=str(tools), MIXER_INDEPENDENT_TOOL_MARKER=str(marker),
                        MIXER_SWIFT=str(tools / 'swift'), MIXER_JDK=str(tools),
                        ANDROID_HOME=str(tools / 'missing-android'), MIXER_SWIFT_SDKS_PATH=str(tools / 'missing-swift-sdks'),
                        MIXER_ANDROID_ARTIFACT_PATH=str(tools / 'missing-artifact'))
    cases = [('stale-profile3', None, None), ('stale-profile3-id-only', None, None), ('missing-profile', None, None),
             ('missing-android-lock', None, None), ('missing-lock-file', None, None)]
    for target in ['NativeEnvironmentV2.java', 'NativeEnvironmentPlatformV2.java']:
        for action in ['same-size-edit', 'remove', 'case-rename', 'recomputed-profile']:
            cases.append((target.replace('.java', '') + '-' + action, target, action))
    cases += [('descriptor-same-size-edit', 'descriptor', 'same-size-edit'), ('sdk-same-size-edit', 'sdk', 'same-size-edit')]
    rows = []
    for case, target, action in cases:
        project = scratch / 'refusals' / case
        project.parent.mkdir(exist_ok=True)
        shutil.copytree(baseline, project)
        lock = json.loads((project / 'mixer.lock').read_text())
        expected_cli = 'android.sdk-compatibility'
        expected_driver = 'Android SDK source compatibility rejected'
        if case.startswith('stale-profile3'):
            lock['android']['profile'] = lock_profile(prior)
            if case.endswith('id-only'):
                lock['android']['profile']['id'] = profile['id']
            expected_cli = 'android.sdk-profile-mismatch'
            expected_driver = expected_cli
        elif case == 'missing-profile':
            del lock['android']['profile']
            expected_cli = 'android.sdk-profile-required'
            expected_driver = expected_cli
        elif case == 'missing-android-lock':
            del lock['android']
            expected_cli = 'android.sdk-profile-required'
            expected_driver = expected_cli
        elif case == 'missing-lock-file':
            expected_cli = 'android.sdk-profile-required'
            expected_driver = 'mixer.lock'
        else:
            if target == 'descriptor':
                path = project / 'Generated/MixerAndroid/app/assets/MixerAppearanceV2/descriptor.json'
            elif target == 'sdk':
                path = project / 'Generated/MixerSDK/Sources/MixerCore/Lifecycle.swift'
            else:
                path = project / 'Generated/MixerAndroid/app/src/dev/mixer/android' / target
            if action == 'remove':
                path.unlink()
            elif action == 'case-rename':
                path.rename(path.with_name(path.name.replace('Native', 'native', 1)))
            else:
                data = bytearray(path.read_bytes())
                data[len(data) // 2] ^= 1
                path.write_bytes(data)
            lock['android']['adapterDigest'] = source_tree(project / 'Generated/MixerAndroid')
            lock['sdkDigest'] = source_tree(project / 'Generated/MixerSDK')
            if action == 'recomputed-profile':
                modified = json.loads(json.dumps(profile))
                key = 'app/src/dev/mixer/android/' + target
                modified['adapter_files'][key] = identity(path.read_bytes())
                modified['adapter_compatibility_sha256'] = projection(modified['adapter_files'])
                lock['android']['profile'] = lock_profile(modified)
                expected_cli = 'android.sdk-profile-mismatch'
                expected_driver = expected_cli
        (project / 'mixer.lock').write_text(json.dumps(lock, indent=2) + '\n')
        if case == 'missing-lock-file':
            (project / 'mixer.lock').unlink()
        # A malformed package is a second ordering oracle if a compiler ran.
        (project / 'Package.swift').write_text('INDEPENDENT INVALID SWIFTPM ORDERING SENTINEL\n')
        output = project / '.mixer/android-build'
        output.mkdir(parents=True)
        (output / 'build-receipt.json').write_text('retain preexisting receipt\n')
        (output / 'Profile4Consumer-unsigned.apk').write_text('retain preexisting apk\n')
        (output / 'build-input.json').write_text('retain preexisting build input\n')
        before = inventory(project)
        entries = [
            ('host-build', ['build', '--platform', 'host']),
            ('host-test', ['test', '--platform', 'host']),
            ('android-build', ['build', '--platform', 'android']),
            ('ios-build', ['build', '--platform', 'ios']),
            ('release-inspect', ['release', 'inspect']),
            ('export', ['export', str(scratch / ('export-rejected-' + case))]),
        ]
        for entry, args in entries:
            label = 'reject-' + case + '-' + entry
            code, stdout, stderr = run(label, [binary, *args, '--directory', project], env=negative_env, expected=1, timeout=30)
            body = json.loads(stdout)
            demand(body.get('code') == expected_cli, label + ' wrong diagnostic: ' + str(body))
            demand(not stderr, label + ' stderr')
            demand(not marker.exists(), label + ' executed tool')
            demand(inventory(project) == before, label + ' mutated source/output')
            demand(not (scratch / ('export-rejected-' + case)).exists(), label + ' exported output')
            rows.append({'case': case, 'entry': entry, 'code': body['code'], 'tool_sentinel_unreached': True,
                         'full_fixture_inventory_unchanged': True, 'output_absent_or_preserved': True})
        label = 'reject-' + case + '-direct-driver'
        code, stdout, stderr = run(label, [sys.executable, '-B', project / 'Generated/MixerAndroid/android-build.py', 'build', project],
                                   env=negative_env, expected=1, timeout=30)
        demand(expected_driver.encode() in stderr, label + ' wrong diagnostic: ' + stderr.decode())
        demand(not stdout, label + ' stdout')
        demand(not marker.exists(), label + ' executed tool')
        demand(inventory(project) == before, label + ' mutated source/output')
        rows.append({'case': case, 'entry': 'direct-driver', 'diagnostic': stderr.decode().strip(),
                     'tool_sentinel_unreached': True, 'full_fixture_inventory_unchanged': True, 'output_absent_or_preserved': True})
        shutil.rmtree(project)
    save('refusal-results.json', {'fixtures': len(cases), 'commands': len(rows), 'rows': rows,
                                  'fixture_policy': 'All changed snapshots recompute unauthenticated whole-source lock digests; two also forge source-profile projections. Generated driver remains untouched.'})
    check('fresh-cli-and-direct-driver-refusals', fixtures=len(cases), commands=len(rows))
    # Input-side refusal is independent of the generated-project gate.
    for target in ['NativeEnvironmentV2.java', 'NativeEnvironmentPlatformV2.java']:
        adapter = scratch / ('input-' + target)
        shutil.copytree(source / 'native/android', adapter)
        path = adapter / 'app/src/dev/mixer/android' / target
        data = bytearray(path.read_bytes()); data[0] ^= 1; path.write_bytes(data)
        destination = scratch / ('created-rejected-' + target)
        before = inventory(adapter)
        label = 'reject-create-' + target
        code, stdout, stderr = run(label, [binary, 'create', 'Rejected', '--directory', destination,
            '--platform', 'android', '--sdk-path', source / 'sdk', '--android-adapter-path', adapter], env=negative_env, expected=1, timeout=30)
        body = json.loads(stdout)
        demand(body.get('code') == 'create.android-sdk-compatibility', label + ' wrong diagnostic')
        demand(not marker.exists() and not destination.exists(), label + ' side effects')
        demand(not list(scratch.glob('.mixer-create-*')), label + ' staging residue')
        demand(inventory(adapter) == before, label + ' input mutation')
        shutil.rmtree(adapter)
    check('fresh-create-input-refusals', commands=2)


def review():
    global scratch
    demand(not (HERE / 'receipt.json').exists(), 'One-shot review already has a receipt')
    custody()
    verify_profile()
    scratch = Path(tempfile.mkdtemp(prefix='mixer-independent-profile4-', dir='/tmp'))
    save('start.json', {'at': now(), 'argv': sys.argv, 'python': sys.version, 'platform': platform.platform(),
                        'scratch': str(scratch), 'context_revision_inherited_not_live_git': 'fb4c8f074f1a3e5eb2b1b1a45b44f0fa61a7cc62',
                        'native_UI_capture_process_inventory_or_Git': False})
    source = freeze_build_inputs()
    run('swift-version', ['/usr/bin/swift', '--version'])
    run('python-version', [sys.executable, '--version'])
    binaries = {}
    for mode in ['debug', 'release']:
        common = ['--package-path', source / 'cli', '--scratch-path', scratch / ('cli-' + mode),
                  '--disable-automatic-resolution', '--jobs', '2', '-c', mode]
        run(mode + '-build', ['/usr/bin/swift', 'build', *common, '--product', 'mixer'])
        _, output, _ = run(mode + '-binpath', ['/usr/bin/swift', 'build', *common, '--show-bin-path'])
        binary = Path(output.decode().strip()) / 'mixer'
        products.append({'role': mode + '-exact-cli-before-use', 'path': str(binary), **identity(binary.read_bytes())})
        binaries[mode] = binary
    check('fresh-debug-release-builds')
    app, exported = scratch / 'Profile4Consumer', scratch / 'ExportedConsumer'
    run('actual-create', [binaries['debug'], 'create', 'Profile4Consumer', '--directory', app,
                         '--application', 'dev.mixer.independentprofile4', '--platform', 'android',
                         '--sdk-path', source / 'sdk', '--android-adapter-path', source / 'native/android'])
    driver = load_driver(app / 'Generated/MixerAndroid/android-build.py', 'independent_actual_generated_driver')
    created = verify_generated(app, driver)
    # Independently replay a new authored-source variation, outside the pinned framework closure.
    feature = app / 'Sources/AppFeatures/ProjectFeature.swift'
    original = feature.read_text()
    demand('Your project' in original, 'Expected starter title')
    feature.write_text(original.replace('Your project', 'Independent profile4 variation'))
    run('actual-export', [binaries['release'], 'export', exported, '--directory', app])
    export_inventory = verify_generated(exported, driver)
    app_inventory = inventory(app)
    file_inventory = lambda rows: {n: v for n, v in rows.items() if 'directory' not in v}
    save('export-comparison.json', {'source_inventory': app_inventory, 'export_inventory': export_inventory,
        'source_only_directories': sorted(n for n in app_inventory.keys() - export_inventory.keys()),
        'semantics': 'Source export preserves admitted files and their parents. Empty directories are not part of SourceDigest.files.'})
    demand(file_inventory(app_inventory) == file_inventory(export_inventory), 'Actual export did not retain every current authored file')
    demand('Independent profile4 variation' in (exported / 'Sources/AppFeatures/ProjectFeature.swift').read_text(), 'Authored source variation not exported')
    save('actual-consumers.json', {'created_before_authored_variation': created, 'exported_with_authored_variation': export_inventory,
                                  'new_variation': 'Both starter navigation titles changed to Independent profile4 variation; actual Release export preserves source. No prior custom variation credited.'})
    check('actual-debug-create-release-export-and-app-source-variation')
    # A wholly new copied-SDK host test module with the actual exported descriptor.
    consumer = scratch / 'DescriptorConsumer'
    tests = consumer / 'Tests/IndependentTests'
    tests.mkdir(parents=True)
    (consumer / 'Package.swift').write_text('// swift-tools-version: 6.2\nimport PackageDescription\nlet package = Package(name: "IndependentDescriptorConsumer", platforms: [.macOS(.v14)], dependencies: [.package(path: "../ExportedConsumer/Generated/MixerSDK")], targets: [.testTarget(name: "IndependentTests", dependencies: [.product(name: "MixerUI", package: "MixerSDK")], resources: [.copy("descriptor.json")])])\n')
    shutil.copy2(HERE / 'IndependentDescriptorTests.swift', tests / 'IndependentDescriptorTests.swift')
    shutil.copy2(exported / 'Generated/MixerAndroid/app/assets/MixerAppearanceV2/descriptor.json', tests / 'descriptor.json')
    run('independent-copied-sdk-descriptor-tests', ['/usr/bin/swift', 'test', '--package-path', consumer,
        '--scratch-path', scratch / 'descriptor-build', '--disable-automatic-resolution', '--jobs', '2'])
    check('independent-copied-sdk-descriptor-tests', methods=3)
    # Generated user code must remain host-compilable after the new variation.
    run('new-authored-variation-host-tests', ['/usr/bin/swift', 'test', '--package-path', exported,
        '--scratch-path', scratch / 'app-build', '--disable-automatic-resolution', '--jobs', '2'])
    check('new-authored-variation-host-tests', existing_methods=4)
    refusals(binaries['release'], exported, driver, source)
    # Release assessment remains blocked despite exact local source-profile acceptance.
    _, output, _ = run('positive-release-policy', [binaries['release'], 'release', 'inspect', '--directory', exported], expected=2)
    assessment = json.loads(output)
    demand(assessment['technicalEligibility'] == 'blocked' and assessment['publicationAllowed'] is False, 'Local source pair incorrectly authorized publication')
    demand(assessment['policyAssessment'] == 'pending-project-review', 'Policy authority drift')
    check('release-authority-remains-blocked')
    for mode, binary in binaries.items():
        products.append({'role': mode + '-exact-cli-after-use', 'path': str(binary), **identity(binary.read_bytes())})
    for relative, expected in source_map.items():
        demand(identity((ROOT / relative).read_bytes()) == expected, 'Final live source drift: ' + relative)
        demand(identity((source / relative).read_bytes()) == expected, 'Final isolated source drift: ' + relative)
    for relative, expected in extra_sources.items():
        demand(identity((ROOT / relative).read_bytes()) == expected, 'Final dependency input drift: ' + relative)
    custody()
    check('final-source-and-custody-stability')


if __name__ == '__main__':
    status = 'failed'
    error = None
    try:
        review()
        status = 'passed-private-host-source-review'
    except BaseException:
        error = traceback.format_exc()
        (HERE / 'failure.txt').write_text(error)
        print(error, file=sys.stderr)
    finally:
        if scratch and scratch.exists():
            for p in sorted(scratch.rglob('*')):
                if p.is_file() and (p.name == 'mixer' or '.xctest' in p.parts):
                    products.append({'role': 'retired-host-product', 'path': str(p), **identity(p.read_bytes())})
            shutil.rmtree(scratch)
        save('receipt.json', {'schema': 1, 'at': now(), 'status': status, 'python': sys.version, 'argv': sys.argv,
            'commands': len(commands), 'checks': len(checks), 'products': products,
            'candidate_manifest_sha256': EXPECTED['verification/android-environment-platform-profile4/manifest.json'],
            'source_map_sha256': EXPECTED['verification/android-environment-platform-profile4/source-map.json'],
            'owned_children_reaped': all(c['child_reaped'] for c in commands), 'owned_scratch_removed': scratch is None or not scratch.exists(),
            'native_UI_capture_process_inventory_or_Git': False, 'product_or_producer_or_root_metadata_written': False,
            'native_runtime_or_publicV2_or_OTA_or_GA_qualification': False, 'error': error})
    print(json.dumps({'status': status, 'commands': len(commands), 'checks': len(checks), 'scratch_removed': scratch is None or not scratch.exists()}))
    sys.exit(0 if error is None else 1)
