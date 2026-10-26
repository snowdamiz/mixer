#!/usr/bin/env python3
"""Collect bounded source/data evidence only; no product code or native tools execute."""
import datetime
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
FROZEN = ROOT / 'verification/android-default-appearance-packaging'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def identity(data):
    return {'bytes': len(data), 'sha256': sha(data)}


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def command(key, argv):
    started = time.monotonic()
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=20)
    (OUT / (key + '.stdout')).write_bytes(result.stdout)
    (OUT / (key + '.stderr')).write_bytes(result.stderr)
    commands.append({'key': key, 'argv': argv, 'cwd': str(ROOT),
                     'exit': result.returncode, 'seconds': time.monotonic() - started,
                     'stdout': {'path': key + '.stdout', **identity(result.stdout)},
                     'stderr': {'path': key + '.stderr', **identity(result.stderr)}})
    if result.returncode:
        raise RuntimeError('Command failed: ' + key)
    return result.stdout.decode()


commands = []
revision = command('revision', ['git', 'rev-parse', 'HEAD']).strip()
python = command('python-version', [sys.executable, '--version']).strip()
git = command('git-version', ['git', '--version']).strip()
sdk_paths = ['sdk/Package.swift']
for module in ['MixerCore', 'MixerUI']:
    sdk_paths += [str(p.relative_to(ROOT)) for p in sorted((ROOT / 'sdk/Sources' / module).rglob('*.swift'))]
java_names = ['Json', 'UiPacket', 'NativeRenderer', 'NativeBridge', 'MixerActivity',
              'NativeCoordinatorV2', 'AppearanceDescriptorV2', 'AppearanceGeometryV2',
              'AppearanceResolverV2', 'AppearanceNativePathsV2', 'InstalledAppearanceV2',
              'NativeEnvironmentV2', 'AuthoredToggleInputV2', 'NativeAppearanceViewsV2']
adapter_paths = ['native/android/bridge/jni.c', 'native/android/bridge/mixer_android.h',
                 'native/android/bridge/mixer_android_v2.h', 'native/android/contracts/android-profile-v1.json']
adapter_paths += ['native/android/app/src/dev/mixer/android/' + name + '.java' for name in java_names]
adapter_paths += [str(p.relative_to(ROOT)) for p in sorted((ROOT / 'native/android/engine/Sources/MixerAndroidRuntime').rglob('*.swift'))]
other_paths = ['AGENTS.md', 'PLAN.md', 'mixer-product-plan.md',
               'docs/android-default-appearance-packaging.md',
               'docs/android-public-appearance-routing-proposal.md',
               'cli/Package.swift', 'cli/Sources/MixerCLI/main.swift',
               'cli/Sources/MixerBuild/ProjectGenerator.swift',
               'cli/Sources/MixerBuild/Configuration.swift',
               'cli/Sources/MixerBuild/AndroidProject.swift',
               'cli/Sources/MixerBuild/Resources/android-build.py',
               'cli/Tests/MixerBuildTests/AndroidProjectTests.swift',
               'cli/build-tests/test_android_appearance.py',
               'sdk/Tests/MixerUITests/AppearanceDescriptorV2Tests.swift',
               'native/android/engine/Tests/MixerAndroidRuntimeTests/RuntimeTests.swift',
               'native/android/engine/Tests/MixerAndroidRuntimeTests/TransactionTests.swift',
               'verification/android-default-appearance-packaging-root-review/implementation-selection.json',
               'verification/android-default-appearance-packaging/handoff.json',
               'verification/android-default-appearance-packaging/seal.json',
               'verification/android-default-appearance-packaging/run-2/product-before.json',
               'verification/android-default-appearance-packaging/run-2/final-descriptor.json',
               'verification/android-default-appearance-packaging/run-2/swift-final-codec-probe.stdout',
               'verification/android-default-appearance-packaging/run-2/java-final-codec-probe.stdout']
paths = sorted(set(sdk_paths + adapter_paths + other_paths))
manifest = {}
for relative in paths:
    source = ROOT / relative
    if source.is_symlink() or not source.is_file():
        raise RuntimeError('Source is not ordinary file: ' + relative)
    data = source.read_bytes()
    manifest[relative] = identity(data)
    target = OUT / 'source-inputs' / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
write('source-manifest.json', {'revision': revision, 'files': manifest,
      'sha256': sha(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()),
      'sdk_projection': sorted(sdk_paths), 'adapter_projection': sorted(adapter_paths)})
command('contract-search', ['rg', '-n', 'sdk-path|sdkDigest|sdkDistribution|defaultAppearanceData|canonicalData|verifyLock|source_tree|schemaVersion|FORMAT|private ordinary|stable public ABI',
    'cli/Sources/MixerCLI/main.swift', 'cli/Sources/MixerBuild/ProjectGenerator.swift',
    'cli/Sources/MixerBuild/Configuration.swift', 'cli/Sources/MixerBuild/AndroidProject.swift',
    'cli/Sources/MixerBuild/Resources/android-build.py', 'native/android/app/src/dev/mixer/android/UiPacket.java',
    'native/android/app/src/dev/mixer/android/AppearanceDescriptorV2.java',
    'native/android/bridge/mixer_android_v2.h'])
probe = command('contract-probe', [sys.executable, '-B', str(OUT / 'probe.py')])
after = {p: identity((ROOT / p).read_bytes()) for p in paths}
unchanged = after == manifest
write('source-after.json', {'files': after, 'unchanged': unchanged})
write('commands.json', commands)
write('receipt.json', {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'revision': revision, 'status': 'source-contract-proposal-only',
      'collector_command': ['python3', '-B', 'verification/android-copied-sdk-appearance-contract/collect.py'],
      'implementation_selected': False, 'implementation_accepted': False, 'GA_qualified': False,
      'source_manifest_sha256': sha((OUT / 'source-manifest.json').read_bytes()),
      'source_unchanged_during_collection': unchanged, 'tool_versions': {'python': python, 'git': git},
      'commands': 'commands.json', 'probe': json.loads(probe),
      'scope': 'Named first-party source inspection, selected frozen-packet member binding and synthetic data-profile vectors only; no product implementation or compiler execution.',
      'native_runtime_or_capture_started': False, 'process_discovery': False,
      'product_code_imported_or_executed': False, 'whole_builds_or_apks_created': False,
      'committed_or_pushed': False,
      'cleanup': {'scratch_created': False, 'owned_native_instances_started': [], 'owned_background_processes_started': []},
      'pending': ['Root contract selection and bounded implementation', 'Independent implementation review',
                  'Native ABI/runtime/OS/environment/lifecycle qualification', 'Public V2 routing',
                  'Immutable published SDK and external FieldLog consumption', 'Physical matrix', 'Release/store/operational/GA gates']})
if not unchanged:
    raise RuntimeError('Named source inputs changed during collection; packet cannot be frozen.')
print(json.dumps({'status': 'source-contract-proposal-only', 'source_files': len(paths),
                  'sdk_projection_files': len(sdk_paths), 'adapter_projection_files': len(adapter_paths),
                  'source_unchanged_during_collection': unchanged, 'probe': json.loads(probe)}, indent=2))
