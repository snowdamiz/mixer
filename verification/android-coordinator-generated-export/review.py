#!/usr/bin/env python3
"""Offline artifact-closure checks; this is not native or root acceptance."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(path.read_bytes())


def archive_files(path):
    files = {}
    with tarfile.open(path) as archive:
        for member in archive.getmembers():
            assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
            assert member.name not in files
            files[member.name] = archive.extractfile(member).read()
    return files


def tree(files):
    return digest(''.join(name + '\0' + digest(value) + '\n' for name, value in sorted(files.items())).encode())


def main():
    if len(sys.argv) != 2 or not re.fullmatch(r'candidate-[1-9][0-9]*', sys.argv[1]):
        raise SystemExit('usage: review.py candidate-N')
    candidate = HERE / sys.argv[1]
    bindings = {}

    def check(path, expected):
        assert sha(path) == expected, str(path)
        bindings[str(path.relative_to(ROOT))] = expected

    receipt = json.loads((candidate / 'receipt.json').read_text())
    assert receipt['status'] == 'passed'
    check(candidate / 'receipt.json', sha(candidate / 'receipt.json'))
    check(candidate / 'source-manifest.json', receipt['sourceManifestSHA256'])
    check(candidate / 'source.tar.gz', receipt['sourceArchiveSHA256'])
    manifest = json.loads((candidate / 'source-manifest.json').read_text())
    source = archive_files(candidate / 'source.tar.gz')
    assert {name: digest(value) for name, value in source.items()} == manifest
    assert tree(source) == receipt['sourceTreeSHA256'] and len(source) == receipt['sourceInputs']
    accepted = json.loads(source['verification/android-native-v2-coordinator-root-review/acceptance.json'])
    generated = archive_files(candidate / 'generated-consumer.tar.gz')
    for name, value in receipt['exportedNativeSources'].items():
        assert digest(generated['Generated/MixerAndroid/' + name]) == value == manifest['native/android/' + name]
        if name != 'contracts/android-profile-v1.json':
            assert value == accepted['bindings']['native/android/' + name]
    # This independent comparison establishes unchanged V1/bootstrap source
    # using the previously accepted generated consumer, rather than matching
    # source spellings or claiming a native execution result.
    prior_receipt = ROOT / 'verification/android-generated-v2-bridge/candidate-3/receipt.json'
    previous_receipt = json.loads(prior_receipt.read_text())
    assert previous_receipt['status'] == 'passed'
    prior = ROOT / 'verification/android-generated-v2-bridge/candidate-3/generated-consumer.tar.gz'
    check(prior_receipt, sha(prior_receipt))
    check(prior, previous_receipt['artifacts'][str(prior.relative_to(ROOT))])
    previous = archive_files(prior)
    unchanged = ['Platforms/Android/Sources/AppAndroid/NativeEntry.swift',
                 'Generated/MixerAndroid/app/src/dev/mixer/android/MixerActivity.java']
    for name in unchanged:
        assert generated[name] == previous[name], name
    android_manifest = 'Platforms/Android/AndroidManifest.xml'
    assert generated[android_manifest] == previous[android_manifest].replace(
        b'dev.mixer.staged', b'dev.mixer.coordinatorexport').replace(b'StagedApp', b'CoordinatorApp')
    for command in receipt['commands']:
        check(ROOT / command['log'], command['sha256'])
        assert (command['exitCode'] == 0) == command['expectedSuccess']
    commands = {c['label']: c for c in receipt['commands']}
    assert len(commands) == 13
    for negative in ['coordinator-tamper-cli-rejected', 'coordinator-tamper-driver-rejected']:
        assert commands[negative]['expectedSuccess'] is False
    tests = (ROOT / commands['cli-export-snapshot-lock-tests']['log']).read_text()
    assert 'with 3 test cases passed' in tests and 'Test run with 2 tests in 0 suites passed' in tests
    for name, value in receipt['artifacts'].items():
        check(ROOT / name, value)
    app = json.loads((candidate / 'baseline/build-receipt.json').read_text())
    lock = json.loads(generated['mixer.lock'])
    assert app['qualification'] == 'local-unsigned-cross-build-only'
    assert app['adapter_digest'] == lock['android']['adapterDigest']
    assert app['sdk_digest'] == lock['sdkDigest'] and app['toolchain'] == lock['android']['toolchain']
    def subtree(prefix):
        return {name[len(prefix):]: value for name, value in generated.items() if name.startswith(prefix)}
    assert tree(subtree('Generated/MixerSDK/')) == lock['sdkDigest']
    assert tree(subtree('Generated/MixerAndroid/')) == lock['android']['adapterDigest']
    assert subtree('Generated/MixerSDK/') == {name[len('sdk/'):]: value for name, value in source.items() if name.startswith('sdk/')}
    for name, value in source.items():
        runtime = 'native/android/engine/Sources/MixerAndroidRuntime/'
        if name.startswith(runtime):
            assert generated['Generated/MixerAndroid/Sources/MixerAndroidRuntime/' + name[len(runtime):]] == value
    assert generated['Generated/MixerAndroid/android-build.py'] == source['cli/Sources/MixerBuild/Resources/android-build.py']
    assert app['source_tree_sha256'] == app['source_tree_after_sha256'] == tree(generated)
    assert app['toolchain']['min_api'] == 28 and app['toolchain']['target_api'] == 37
    assert all(c['exit_code'] == 0 for c in app['commands'])
    assert any('-Wl,--no-undefined' in c['command'] for c in app['commands'])
    with zipfile.ZipFile(candidate / 'baseline/CoordinatorApp-unsigned.apk') as archive:
        assert len(archive.namelist()) == len(set(archive.namelist()))
        assert {name: digest(archive.read(name)) for name in archive.namelist()} == app['apk_entries']
        assert not any(name.startswith('META-INF/') for name in archive.namelist())
        for name, value in app['native_libraries'].items():
            assert digest(archive.read('lib/arm64-v8a/' + name)) == value
    check(candidate / 'baseline/CoordinatorApp-unsigned.apk', app['apk_sha256'])
    for name in ['NativeCoordinatorV2', 'NativeRenderer', 'NativeBridge', 'MixerActivity']:
        leaf = 'dev/mixer/android/' + name + '.class'
        check(candidate / 'classes' / leaf, accepted['bindings'][
            'verification/android-native-v2-coordinator/candidate-3/production-classes/' + leaf])
    assert receipt['compiledCoordinatorClassSHA256'] == accepted['executedCoordinatorClassSHA256']
    assert receipt['coordinatorDEXPresent'] and receipt['publicV1ActivityClassUnchanged']
    assert receipt['coordinatorTamperRejectedBeforeBuildOutput'] and receipt['unchangedNativeInputs']
    assert not receipt['nativeRuntimeRun'] and not receipt['physicalRun'] and not receipt['nativeAcceptance']
    assert not receipt['publicActivityOptIn'] and not receipt['signedPresentation'] and not receipt['gaAcceptance']
    result = {'status': 'passed-offline-closure-checks', 'reviewer': 'export lane artifact checker; root acceptance separate',
              'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'candidate': sys.argv[1], 'sourceInputs': len(source), 'commandCount': len(commands),
              'unchangedBootstrapInputs': unchanged + [android_manifest + ' (application identity substitution only)'],
              'bindings': bindings, 'reviewScriptSHA256': sha(Path(__file__).resolve()),
              'nativeAcceptance': False, 'physicalAcceptance': False, 'gaAcceptance': False,
              'scope': 'Offline captured source, bootstrap, command, class, APK/DEX/native hash closure only. No runtime execution or release acceptance.'}
    (candidate / 'offline-review.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'bindings'}, indent=2))


if __name__ == '__main__':
    main()
