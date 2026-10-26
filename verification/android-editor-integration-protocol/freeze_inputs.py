#!/usr/bin/env python3
"""Freeze only named canonical inputs and the root-released historical B packet.

This is preparation, never corrected-source admission or OTA authorization.
"""
import datetime
import hashlib
import json
import platform
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREP = ROOT / 'verification/android-editor-integration-preparation'
EXPECTED_PREP = '937686d9fa756776e0ff2e238277eae79287e7ec4c6dd2d2bf4352ff8ecfd242'
EXPECTED_OLD = '4c906824fe5e2e925c3ad5ca7c4ae94ba3b1e7dd6c58e77805dd3862c165c9a3'

def ident(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def projection(files):
    return hashlib.sha256(''.join(p + '\0' + files[p]['sha256'] + '\n' for p in sorted(files)).encode()).hexdigest()

def main():
    manifest = {}
    def copy(source, relative, expected=None):
        data = source.read_bytes()
        identity = ident(data)
        if expected is not None and identity != expected:
            raise RuntimeError('Frozen input identity mismatch: ' + str(source))
        dest = HERE / 'inputs' / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            if dest.read_bytes() != data:
                raise RuntimeError('Refusing to replace changed frozen input: ' + str(dest))
        else:
            dest.write_bytes(data)
        manifest[relative] = {'source': str(source.relative_to(ROOT)), **identity}
        return data

    profile_path = ROOT / 'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift'
    profile_source = profile_path.read_text()
    profile = json.loads(profile_source.split('Data(#"""\n', 1)[1].split('\n        """#.utf8)', 1)[0])
    assert profile['id'] == 'mixer.android-source-pair.4'
    assert len(profile['sdk_files']) == 22 and len(profile['adapter_files']) == 23
    for kind, prefix in (('sdk', 'sdk/'), ('adapter', 'native/android/')):
        files = profile[kind + '_files']
        assert projection(files) == profile[kind + '_compatibility_sha256']
        for path, identity in files.items():
            actual = prefix + ('engine/' if kind == 'adapter' and path.startswith('Sources/') else '') + path
            copy(ROOT / actual, 'repo/' + actual, identity)

    named = [
        'AGENTS.md', 'PLAN.md', 'mixer-product-plan.md',
        'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift',
        'cli/Sources/MixerBuild/AndroidProject.swift',
        'cli/Sources/MixerBuild/Configuration.swift',
        'cli/Sources/MixerBuild/ProjectGenerator.swift',
        'cli/Sources/MixerBuild/Resources/android-build.py',
        'cli/Tests/MixerBuildTests/AndroidSDKCompatibilityTests.swift',
        'cli/Tests/MixerBuildTests/AndroidProjectTests.swift',
        'native/android/tests/run-private-owner-host.py',
        'native/android/tests/run-private-owner-crosscompile.py',
        'native/android/tests/NativeOwnerV2HostTests.java',
        'native/android/tests/NativeOwnerV2ConcreteHostTests.java',
        'native/android/tests/NativeOwnerV2HostLeaves/dev/mixer/android/NativeRenderer.java',
        'native/android/tests/NativeOwnerV2HostLeaves/dev/mixer/android/OwnerHostProbe.java',
        'native/android/tests/NativeOwnerV2ConcreteHostLeaves/dev/mixer/android/ConcreteHostProbe.java',
        'scripts/ci/check-android-binding.py',
        'scripts/ci/tests/test_android_binding_runner.py',
        '.github/workflows/verify.yml',
        'verification/android-private-owner-effect-roster-amendment/required-host-roster.json',
        'verification/android-private-owner-integration-implementation/barrier-map.json',
        'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json',
        'verification/android-editor-boundary-root-review/focus-history-amendment.md',
        'verification/android-editor-boundary-root-review/focus-history-internal-protocol.md',
        'verification/android-editor-boundary-root-review/focus-history-event-reentry-amendment.md',
    ]
    for path in named:
        copy(ROOT / path, 'repo/' + path)
    old_seal = ROOT / 'verification/android-editor-replacement-implementation/seal.json'
    assert ident(old_seal.read_bytes())['sha256'] == EXPECTED_OLD
    copy(old_seal, 'historical-candidate-seal.json')
    prep_bytes = (PREP / 'seal.json').read_bytes()
    assert ident(prep_bytes)['sha256'] == EXPECTED_PREP
    copy(PREP / 'seal.json', 'historical-preparation-seal.json')
    prep = json.loads(prep_bytes)
    selected = [member for member in prep['members'] if member['path'].startswith((
        'closure-B-directprobe/inputs/', 'closure-B-directprobe/classes/')) or member['path'] in (
        'README.md', 'prospective-product-map.json', 'barrier-map-migration-inventory.json',
        'check_existing_closures.py', 'closure-B-directprobe/class-map.json',
        'closure-B-directprobe/source-map.json', 'closure-B-directprobe/source-origins.json',
        'closure-B-directprobe/receipt.json', 'closure-B-directprobe/commands.json',
        'closure-B-directprobe/host.stdout', 'closure-B-directprobe/host.stderr')]
    for member in selected:
        copy(PREP / member['path'], 'historical-preparation/' + member['path'],
             {k: member[k] for k in ('bytes', 'sha256')})
    write_json(HERE / 'input-manifest.json', manifest)
    write_json(HERE / 'current-profile4.json', profile)

    roster = json.loads((ROOT / named[20]).read_text())
    closures = {}
    for label, closure in roster['closures'].items():
        current = closure['actual_production_sources'] + ['native/android/app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java']
        proposed = current + (['native/android/app/src/dev/mixer/android/NativeEditorConnectionV2.java'] if label.startswith('B-') else [])
        closures[label] = {'current_explicit_product_sources': current, 'proposed_explicit_product_sources': proposed,
            'substitutes': closure['substitutes'], 'test_support_sources': closure['test_support_sources'],
            'test_source': closure['test_source'], 'status': 'proposal-only; leaf roster requires fresh exact accepted-source compatibility review'}
    current_cross_java = closures['B-concrete-renderer-views']['current_explicit_product_sources'] + [
        'native/android/app/src/dev/mixer/android/' + n + '.java' for n in ('NativeBridge', 'MixerActivity', 'AdapterInstrumentation')] + [
        'native/android/tests/' + n + '.java' for n in ('NativeAppearanceV2Activity', 'NativeAppearanceV2Instrumentation',
        'AppearanceNativePathsV2Instrumentation', 'NativeCoordinatorV2IntegrationActivity', 'NativeCoordinatorV2IntegrationInstrumentation')]
    tracked = subprocess.check_output(['git', 'ls-files', '-z', '--', 'native/android/engine', 'sdk', 'native/android/bridge'], cwd=ROOT).decode().split('\0')
    cross_other = sorted(p for p in tracked if p and Path(p).suffix in ('.swift', '.c', '.h'))
    for path in cross_other + current_cross_java:
        if 'repo/' + path not in manifest:
            copy(ROOT / path, 'repo/' + path)
    write_json(HERE / 'input-manifest.json', manifest)
    write_json(HERE / 'source-lists.json', {'closures': closures, 'crosscompile': {
        'current_java': current_cross_java,
        'proposed_java': current_cross_java + ['native/android/app/src/dev/mixer/android/NativeEditorConnectionV2.java'],
        'current_swift_c_h': cross_other, 'new_swift_c_h': [],
        'note': 'Current cross runner discovers tracked Swift/C/header files; future evidence must freeze exactly this expanded list plus Package.swift manifests before tools.'}})
    new_adapter = dict(profile['adapter_files'])
    changed = ['NativeAppearanceViewsV2.java', 'NativeCoordinatorV2.java', 'NativeRenderer.java', 'NativeEditorConnectionV2.java']
    for name in changed:
        new_adapter['app/src/dev/mixer/android/' + name] = None
    write_json(HERE / 'proposed-profile5.json', {
        'status': 'unselected proposal; deliberately not an executable admission profile',
        'candidate_binding': None, 'root_acceptance': None, 'id': 'mixer.android-source-pair.5',
        'schema': 1, 'sdk_files': profile['sdk_files'], 'adapter_files': new_adapter,
        'sdk_compatibility_sha256': profile['sdk_compatibility_sha256'], 'adapter_compatibility_sha256': None,
        'default_descriptor': profile['default_descriptor'], 'wire': profile['wire'],
        'fresh_source_comparison_required_for_every_adapter': True,
        'expected_counts': {'sdk': 22, 'adapter': 24, 'exported_java': 18},
        'prior_candidate_is_unaccepted': EXPECTED_OLD})
    commands = [
        {'argv': ['git', 'rev-parse', 'HEAD'], 'exit': 0,
         'stdout': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()},
        {'argv': ['git', 'ls-files', '-z', '--', 'native/android/engine', 'sdk', 'native/android/bridge'],
         'exit': 0, 'expanded_sources': cross_other}]
    write_json(HERE / 'freeze-receipt.json', {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'offline integration proposal and historical host inputs only; no corrected candidate read or accepted',
        'python': platform.python_version(), 'commands': commands, 'input_projection_sha256': projection(manifest),
        'historical_prep_members_checked': len(selected),
        'native_ui_capture_processes_queried_or_started': False, 'git_mutations': False,
        'cleanup': 'No native instances or capture processes queried or created; no scratch created.'})
    print('PASS frozen inputs:', len(manifest), 'historical selected:', len(selected), 'SDK22/adapter23 verified; proposed adapter24 remains unbound')

if __name__ == '__main__':
    main()
