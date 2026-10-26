#!/usr/bin/env python3
"""Record source-only proposal observations. Never imports or executes product code."""
import datetime
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
FILES = [
    'PLAN.md', 'work-graph.json', 'mixer-product-plan.md',
    'docs/android-authored-toggle-integration.md',
    'verification/android-authored-toggle-integration/acceptance.json',
    'verification/android-authored-toggle-integration/integration.json',
    'verification/android-authored-toggle-integration/host-1/fresh-artifacts.json',
    'docs/android-coordinator-join-acceptance.md',
    'verification/android-coordinator-join-root-review/native-join-acceptance.json',
    'native/android/app/src/dev/mixer/android/MixerActivity.java',
    'native/android/app/src/dev/mixer/android/NativeBridge.java',
    'native/android/app/src/dev/mixer/android/NativeCoordinatorV2.java',
    'native/android/app/src/dev/mixer/android/NativeRenderer.java',
    'native/android/app/src/dev/mixer/android/NativeAppearanceViewsV2.java',
    'native/android/app/src/dev/mixer/android/AuthoredToggleInputV2.java',
    'native/android/app/src/dev/mixer/android/InstalledAppearanceV2.java',
    'native/android/app/src/dev/mixer/android/NativeEnvironmentV2.java',
    'native/android/engine/Sources/MixerAndroidEngine/Engine.swift',
    'native/android/engine/Sources/MixerAndroidEngine/Bridge.swift',
    'native/android/engine/Sources/MixerAndroidRuntime/DocumentSession.swift',
    'native/android/engine/Sources/MixerAndroidRuntime/SessionRegistry.swift',
    'sdk/Sources/MixerUI/NativePacketV1.swift',
    'sdk/Sources/MixerApple/MixerNativeView.swift',
    'sdk/Sources/MixerApple/AppearanceInstalledV2.swift',
    'cli/Sources/MixerBuild/AndroidProject.swift',
    'cli/Sources/MixerBuild/ProjectGenerator.swift',
    'cli/Sources/MixerBuild/Resources/android-build.py',
    'cli/Tests/MixerBuildTests/AndroidProjectTests.swift',
]
EXCERPTS = {
    'cli/Sources/MixerBuild/AndroidProject.swift': [(27, 49), (97, 104), (132, 139)],
    'cli/Tests/MixerBuildTests/AndroidProjectTests.swift': [(7, 25)],
    'native/android/app/src/dev/mixer/android/NativeAppearanceViewsV2.java': [(602, 614)],
    'native/android/app/src/dev/mixer/android/MixerActivity.java': [(8, 16)],
    'native/android/app/src/dev/mixer/android/NativeEnvironmentV2.java': [(69, 74), (125, 128)],
    'mixer-product-plan.md': [(332, 346), (661, 667)],
}


def sha(value):
    return hashlib.sha256(value).hexdigest()


def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def command(argv):
    result = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, check=True)
    return {'argv': argv, 'cwd': str(ROOT), 'exitCode': result.returncode,
            'stdout': result.stdout, 'stderr': result.stderr}


def main():
    commands = [command(['git', 'rev-parse', 'HEAD']), command(['git', '--version']),
                command(['rg', '--version'])]
    contents = {name: (ROOT / name).read_bytes() for name in FILES}
    manifest = {name: sha(value) for name, value in contents.items()}
    tree = sha(''.join(name + '\0' + digest + '\n' for name, digest in sorted(manifest.items())).encode())
    write('source-manifest.json', {'algorithm': 'sha256(path NUL sha256 LF), sorted path UTF-8',
                                   'selectedSourceTreeSHA256': tree, 'files': manifest})
    excerpts = {}
    for name, ranges in EXCERPTS.items():
        lines = contents[name].decode().splitlines()
        excerpts[name] = [{'start': start, 'end': end,
                           'text': '\n'.join(lines[start - 1:end]) + '\n'} for start, end in ranges]
    write('source-excerpts.json', excerpts)
    integration = json.loads(contents['verification/android-authored-toggle-integration/integration.json'])
    authored = 'native/android/app/src/dev/mixer/android/AuthoredToggleInputV2.java'
    matches = {name: manifest[name] == value['afterSHA256'] for name, value in integration['changes'].items()}
    graph = json.loads(contents['work-graph.json'])
    w05 = next(package for package in graph['packages'] if package['id'] == 'W05')
    project = contents['cli/Sources/MixerBuild/AndroidProject.swift'].decode()
    export = project.split('let expected = [', 1)[1].split('\n        ]', 1)[0]
    views = contents['native/android/app/src/dev/mixer/android/NativeAppearanceViewsV2.java'].decode()
    observations = {
        'kind': 'source-only-proposal-observations-no-compiler-reproduction',
        'sourceObservedAuthoredTypeReference': 'implements AuthoredToggleInputV2.CheckedBinding' in views,
        'sourceObservedAuthoredSourceMissingFromExplicitExport': 'AuthoredToggleInputV2.java' not in export,
        'allThreeAcceptedIntegrationSourcesByteIdentical': matches,
        'authoredSourceSHA256': manifest[authored],
        'acceptedAuthoredSourceSHA256': integration['changes'][authored]['afterSHA256'],
        'retainedAcceptedAuthoredClassArtifacts': {
            name: value for name, value in json.loads(contents[
                'verification/android-authored-toggle-integration/host-1/fresh-artifacts.json']).items()
            if name.startswith('production-classes/dev/mixer/android/AuthoredToggleInputV2')
        },
        'W05': {key: w05[key] for key in ['state', 'currentCheckpoint', 'nextImplementation']},
    }
    write('observations.json', observations)
    write('receipt.json', {
        'schema': 1, 'status': 'proposal-only-source-review-complete',
        'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'sourceRevision': commands[0]['stdout'].strip(),
        'sourceTreeScope': 'exact selected source/evidence files, not full worktree',
        'selectedSourceTreeSHA256': tree,
        'invocation': ['python3', 'verification/android-public-appearance-routing-proposal/review_sources.py'],
        'pythonVersion': sys.version, 'hostPlatform': platform.platform(),
        'commands': commands,
        'collectorSHA256': sha(Path(__file__).read_bytes()),
        'bindings': {name: sha((HERE / name).read_bytes()) for name in
                     ['source-manifest.json', 'source-excerpts.json', 'observations.json']},
        'productCodeChanged': False, 'productExecution': False, 'compilerExecution': False,
        'nativeRuntime': False, 'deviceDiscovery': False, 'computerUse': False,
        'capture': False, 'uiAutomation': False, 'processDiscoveryOrMutation': False,
        'implementationAcceptance': False, 'publicRoutingEnabled': False,
        'signedOrHealthAuthorityEnabled': False, 'gaAcceptance': False,
        'scope': 'Offline source hashes, selected exact excerpts and retained acceptance review. '
                 'Source omission finding is not an observed compiler failure. Product tests, '
                 'cross-compilation and all new native checks are unrun in this proposal.',
        'cleanup': 'No native processes, scratch build directories or extracted archives created.',
    })
    print(json.dumps({'status': 'proposal-only-source-review-complete',
                      'selectedSourceTreeSHA256': tree, 'selectedInputs': len(manifest),
                      'authoredSourceMissingFromExport': observations['sourceObservedAuthoredSourceMissingFromExplicitExport'],
                      'allThreeAcceptedSourcesMatch': all(matches.values())}, sort_keys=True))


if __name__ == '__main__':
    main()
