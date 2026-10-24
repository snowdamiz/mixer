#!/usr/bin/env python3
"""Offline root verification of captured generated-app and JNI evidence."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import tarfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(path.read_bytes())


def main():
    if len(sys.argv) != 2 or not re.fullmatch(r'candidate-[1-9][0-9]*', sys.argv[1]):
        raise SystemExit('usage: review.py candidate-N')
    candidate = HERE / sys.argv[1]
    result = {'status': 'running', 'reviewer': 'root', 'bindingsChecked': 0,
              'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat()}

    def check(path, value):
        assert path.is_file() and sha(path) == value, str(path)
        result['bindingsChecked'] += 1

    receipt = json.loads((candidate / 'receipt.json').read_text())
    assert receipt['status'] == 'passed' and receipt['unchangedLiveInputs']
    check(candidate / 'source-manifest.json', receipt['sourceManifestSHA256'])
    check(candidate / 'source.tar.gz', receipt['sourceArchiveSHA256'])
    manifest = json.loads((candidate / 'source-manifest.json').read_text())
    with tarfile.open(candidate / 'source.tar.gz') as archive:
        assert len(archive.getmembers()) == len(manifest)
        assert {m.name for m in archive.getmembers()} == set(manifest)
        for member in archive.getmembers():
            assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
            assert digest(archive.extractfile(member).read()) == manifest[member.name]
            result['bindingsChecked'] += 1
            check(ROOT / member.name, manifest[member.name])
    commands = {c['label']: c for c in receipt['commands']}
    assert len(commands) == 10
    for label, command in commands.items():
        check(ROOT / command['log'], command['sha256'])
        assert (command['exitCode'] == 0) == command['expectedSuccess']
        assert command['expectedSuccess'] == (label != 'missing-export-build-rejected')
    for name, value in receipt['artifacts'].items():
        check(ROOT / name, value)
    assert receipt['missingExportRejectsAtLink'] and receipt['staleSuccessArtifactsRemoved']
    generated = {}
    with tarfile.open(candidate / 'generated-consumer.tar.gz') as archive:
        for member in archive.getmembers():
            assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
            assert member.name not in generated
            generated[member.name] = archive.extractfile(member).read()
    for name in ['bridge/jni.c', 'bridge/mixer_android.h', 'bridge/mixer_android_v2.h']:
        assert digest(generated['Generated/MixerAndroid/' + name]) == manifest['native/android/' + name]
        result['bindingsChecked'] += 1
    lock = json.loads(generated['mixer.lock'])
    app = json.loads((candidate / 'baseline/build-receipt.json').read_text())
    assert app['qualification'] == 'local-unsigned-cross-build-only'
    assert app['adapter_digest'] == lock['android']['adapterDigest'] and app['sdk_digest'] == lock['sdkDigest']
    assert app['toolchain'] == lock['android']['toolchain']
    assert app['source_tree_sha256'] == app['source_tree_after_sha256']
    assert all(c['exit_code'] == 0 for c in app['commands'])
    assert any('-Wl,--no-undefined' in c['command'] for c in app['commands'])
    check(candidate / 'baseline/StagedApp-unsigned.apk', app['apk_sha256'])
    with zipfile.ZipFile(candidate / 'baseline/StagedApp-unsigned.apk') as archive:
        assert len(archive.namelist()) == len(set(archive.namelist()))
        assert {n: digest(archive.read(n)) for n in archive.namelist()} == app['apk_entries']
        assert all('META-INF/' not in n for n in archive.namelist())
        for name, value in app['native_libraries'].items():
            assert digest(archive.read('lib/arm64-v8a/' + name)) == value
            result['bindingsChecked'] += 1
    jni = ROOT / 'verification/android-v2-jni-candidate-bridge'
    replay = json.loads((jni / 'root-replay-1/receipt.json').read_text())
    original = json.loads((jni / 'candidate-1/receipt.json').read_text())
    assert replay['status'] == original['status'] == 'passed'
    check(jni / 'candidate-1/receipt.json', replay['candidateReceiptSHA256'])
    jm = json.loads((jni / 'candidate-1/source-manifest.json').read_text())
    # GUI consumer files may evolve independently; bind every actual JNI/Swift
    # engine dependency and the host replay's exact source separately.
    for name, value in jm.items():
        if name.startswith(('native/android/bridge/', 'native/android/engine/', 'sdk/')) or name == 'native/android/app/src/dev/mixer/android/NativeBridge.java':
            check(ROOT / name, value)
    for r in [original, replay]:
        for command in r['commands']:
            check(ROOT / command['log'], command['sha256']); assert command['exitCode'] == 0
        for name, value in r['artifacts'].items(): check(ROOT / name, value)
    assert len(replay['assertions']) == 8
    assert all(value == (585 if key.startswith('production-') else 199) for key, value in replay['assertions'].items())
    independent_path = ROOT / 'verification/native-v2-transaction-independent-review/jni-cli-source-review-1/receipt.json'
    independent = json.loads(independent_path.read_text())
    assert independent['findings'] == [] and len(independent['sourceManifest']) == 6
    for name, value in independent['sourceManifest'].items(): check(ROOT / name, value['sha256'])
    for name, value in independent['evidenceSHA256'].items(): check(ROOT / name, value)
    result.update(status='accepted-private-jni-and-generated-cross-build',
                  sourceRevision=receipt['sourceRevision'], candidate=sys.argv[1],
                  candidateReceiptSHA256=sha(candidate / 'receipt.json'),
                  generatedSourceCount=len(manifest),
                  jniReplayReceiptSHA256=sha(jni / 'root-replay-1/receipt.json'),
                  jniAssertions=replay['assertions'],
                  independentSourceReviewReceiptSHA256=sha(independent_path),
                  reviewSourceSHA256=sha(Path(__file__)),
                  scope='Actual host JNI execution, generated app Swift host session tests, official arm64 API28 unsigned APK link/package and missing-export rejection.',
                  limitations=['Native appearance current revisions have only headless compile evidence; GUI acceptance remains pending.',
                               'No native coordinator or V2 Activity opt-in.',
                               'No Android runtime claim for this JNI/generated integration.',
                               'Computer use, screenshots and native runtime testing paused by user.',
                               'Full target support, signed presentation, final phones, published FieldLog and GA remain open.'])
    (HERE / 'acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'bindingsChecked': result['bindingsChecked']}))


if __name__ == '__main__': main()
