#!/usr/bin/env python3
"""Reproduce generated shared Android consumer; no device discovery, signing or install."""
import datetime
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
LOCAL = ROOT / 'verification/local'
LOCAL.mkdir(exist_ok=True)
APP = pathlib.Path(tempfile.mkdtemp(prefix='android-generated-consumer-', dir=LOCAL)) / 'Application'
CLI = ROOT / 'cli/.build/debug/mixer'
commands = []


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest():
    files = []
    for folder in ['cli', 'sdk', 'native/android/engine/Sources', 'native/android/engine/Tests', 'native/android/bridge', 'native/android/app/src', 'native/android/contracts']:
        for path in (ROOT / folder).rglob('*'):
            if path.is_file() and not set(path.relative_to(ROOT).parts) & {'.build', '.swiftpm', '__pycache__'}:
                files.append(path)
    files += [ROOT / 'native/android/engine/Package.swift', ROOT / 'native/android/tests/ContractTests.java', pathlib.Path(__file__)]
    return {str(path.relative_to(ROOT)): sha(path) for path in sorted(set(files))}


def run(name, args, expected=0, contains=None):
    p = subprocess.run(list(map(str, args)), cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = OUT / (name + '.log')
    output.write_text(p.stdout)
    commands.append({'name': name, 'command': list(map(str, args)), 'exit_code': p.returncode, 'expected_exit_code': expected, 'output': str(output.relative_to(ROOT)), 'output_sha256': sha(output)})
    if (expected == 0 and p.returncode != 0) or (expected != 0 and p.returncode == 0):
        raise RuntimeError(name + ' had unexpected result: ' + p.stdout[-12000:])
    if contains and contains not in p.stdout:
        raise RuntimeError(name + ' missing required result: ' + contains + '\n' + p.stdout[-12000:])
    print(name + ': ' + ('passed' if expected == 0 else 'rejected as expected'), flush=True)
    return p.stdout


def build(name):
    run(name, [CLI, 'build', '--platform', 'android', '--directory', APP], contains='UNSIGNED APK:')
    return json.loads((APP / '.mixer/android-build/build-receipt.json').read_text())


def negative_file(name, path, replacement, expected):
    original = path.read_bytes()
    try:
        path.write_bytes(replacement)
        run(name, [CLI, 'build', '--platform', 'android', '--directory', APP], expected=1, contains=expected)
    finally:
        path.write_bytes(original)


initial = manifest()
run('cli-host', ['/usr/bin/swift', 'test', '--package-path', ROOT / 'cli'], contains='19 tests')
run('runtime-host', ['/usr/bin/swift', 'test', '--package-path', ROOT / 'native/android/engine'], contains='5 tests')
run('create', [CLI, 'create', 'GeneratedConsumer', '--directory', APP, '--application', 'dev.mixer.generatedconsumer', '--platform', 'android'], contains='local-development-only')
lock = json.loads((APP / 'mixer.lock').read_text())
JDK = pathlib.Path(lock['android']['toolchain']['distributions']['jdk']['path'])
classes = APP / '.mixer/java-contract-tests'
classes.mkdir(parents=True)
run('java-compile', [JDK / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror', '-d', classes, ROOT / 'native/android/app/src/dev/mixer/android/Json.java', ROOT / 'native/android/app/src/dev/mixer/android/UiPacket.java', ROOT / 'native/android/tests/ContractTests.java'])
run('java-host', [JDK / 'bin/java', '-cp', classes, 'dev.mixer.android.ContractTests'], contains='checks passed: 34')
run('generated-host', ['/usr/bin/swift', 'test', '--package-path', APP], contains='4 tests')
run('generated-session-host', ['/usr/bin/swift', 'test', '--package-path', APP / 'Platforms/Android'], contains='2 tests')
run('ios-build', [CLI, 'build', '--platform', 'ios', '--directory', APP], contains='BUILD SUCCEEDED')
baseline = build('android-build')
(OUT / 'baseline-build-receipt.json').write_text(json.dumps(baseline, indent=2) + '\n')
# The exported consumer contains a byte-exact Java/JNI/header/runtime closure.
for relative in ['bridge/jni.c', 'bridge/mixer_android.h', 'app/src/dev/mixer/android/Json.java', 'app/src/dev/mixer/android/UiPacket.java', 'app/src/dev/mixer/android/NativeBridge.java', 'app/src/dev/mixer/android/NativeRenderer.java', 'app/src/dev/mixer/android/MixerActivity.java']:
    assert (APP / 'Generated/MixerAndroid' / relative).read_bytes() == (ROOT / 'native/android' / relative).read_bytes(), relative
assert not (APP / 'Generated/MixerAndroid/engine/Sources/MixerAndroidEngine').exists()
negative_file('sdk-drift', APP / 'Generated/MixerSDK/Package.swift', b'// changed source\n', 'lock.sdk-drift')
negative_file('adapter-drift', APP / 'Generated/MixerAndroid/bridge/jni.c', b'// changed source\n', 'lock.android-drift')
config_path = APP / 'mixer.yml'
config = json.loads(config_path.read_text())
config['capabilities'] = ['storage.files']
negative_file('unsupported-capability', config_path, json.dumps(config).encode(), 'android.unsupported-capability')
resource = APP / 'Resources/cannot-be-ignored.txt'
try:
    resource.write_text('This file must not silently disappear from an Android app.\n')
    run('unsupported-resource', [CLI, 'build', '--platform', 'android', '--directory', APP], expected=1, contains='android.unsupported-resources')
finally:
    resource.unlink()
modified_lock = json.loads((APP / 'mixer.lock').read_text())
modified_lock['android']['toolchain']['javac_version'] = 'deliberately wrong pinned JDK'
negative_file('toolchain-drift', APP / 'mixer.lock', json.dumps(modified_lock).encode(), 'toolchain differs from mixer.lock')
feature = APP / 'Sources/AppFeatures/ProjectFeature.swift'
manifest_path = APP / 'Platforms/Android/AndroidManifest.xml'
entry = APP / 'Platforms/Android/Sources/AppAndroid/NativeEntry.swift'
original_feature = feature.read_bytes()
feature.write_text(feature.read_text().replace('Your project', 'Edited shared feature proof'))
manifest_path.write_text(manifest_path.read_text() + '<!-- User-owned native manifest edit preserved -->\n')
entry.write_text(entry.read_text() + '// User-owned native entry edit preserved.\n')
owned_hashes = {str(p.relative_to(APP)): sha(p) for p in [feature, manifest_path, entry]}
edited = build('edited-android-build')
assert edited['native_libraries']['libAppAndroid.so'] != baseline['native_libraries']['libAppAndroid.so']
assert edited['apk_content_sha256'] != baseline['apk_content_sha256']
assert owned_hashes == {str(p.relative_to(APP)): sha(p) for p in [feature, manifest_path, entry]}
run('edited-feature-binary', ['/usr/bin/strings', '-a', APP / '.mixer/android-build/apk/lib/arm64-v8a/libAppAndroid.so'], contains='Edited shared feature proof')
(OUT / 'edited-build-receipt.json').write_text(json.dumps(edited, indent=2) + '\n')
# An actual original-source compiler error cannot return a successful Android build.
negative_file('compiler-error', feature, b'this does not compile\n', 'ProjectFeature.swift:')
assert not (APP / '.mixer/android-build/build-receipt.json').exists()
assert not pathlib.Path(edited['apk']).exists()
# A source mutation after the recorded input observation must invalidate a build.
input_marker = APP / '.mixer/android-build/build-input.json'
old_marker = input_marker.read_bytes()
mutation_command = list(map(str, [CLI, 'build', '--platform', 'android', '--directory', APP]))
process = subprocess.Popen(mutation_command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
original = feature.read_bytes()
try:
    deadline = time.monotonic() + 30
    while (not input_marker.exists() or input_marker.read_bytes() == old_marker) and process.poll() is None:
        if time.monotonic() > deadline:
            raise RuntimeError('Build did not record its input observation before mutation probe deadline.')
        time.sleep(0.05)
    assert process.poll() is None, 'Build terminated before source mutation probe.'
    feature.write_bytes(original + b'\n// Concurrent user edit after build input observation.\n')
    mutation_output, _ = process.communicate()
    mutation_log = OUT / 'source-mutation.log'
    mutation_log.write_text(mutation_output)
    commands.append({'name': 'source-mutation', 'command': mutation_command, 'exit_code': process.returncode, 'expected_exit_code': 1, 'output': str(mutation_log.relative_to(ROOT)), 'output_sha256': sha(mutation_log)})
    assert process.returncode != 0 and 'source changed during the Android build' in mutation_output
    assert not (APP / '.mixer/android-build/build-receipt.json').exists()
    assert not pathlib.Path(edited['apk']).exists()
    print('source-mutation: rejected as expected', flush=True)
finally:
    feature.write_bytes(original)
    if process.poll() is None:
        process.terminate()
        process.communicate()
final_build = build('final-android-build')
(OUT / 'build-receipt.json').write_text(json.dumps(final_build, indent=2) + '\n')
export = APP.parent / 'ExportedApplication'
run('export', [CLI, 'export', export, '--directory', APP], contains='Exported source and pinned SDK')
run('exported-host', ['/usr/bin/swift', 'test', '--package-path', export], contains='4 tests')
assert (export / 'Generated/MixerAndroid/bridge/jni.c').read_bytes() == (APP / 'Generated/MixerAndroid/bridge/jni.c').read_bytes()
assert not (export / '.mixer').exists()
final = manifest()
assert initial == final, 'Implementation source changed during verification; rerun from stable inputs.'
source_text = ''.join(value + '  ' + path + '\n' for path, value in final.items())
(OUT / 'source-manifest.sha256').write_text(source_text)
receipt = {
    'schema_version': 1, 'observed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'executor': 'owned reproducible local verification script; independent review pending',
    'source_revision_before_run': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'source_tree_sha256': hashlib.sha256(source_text.encode()).hexdigest(),
    'source_manifest': 'verification/android-generated-consumer/source-manifest.sha256',
    'generated_project': str(APP), 'exported_project': str(export),
    'commands': commands, 'toolchain': final_build['toolchain'],
    'actual_apk': {key: final_build[key] for key in ['apk', 'apk_sha256', 'apk_bytes', 'apk_content_sha256']},
    'baseline_native_sha256': baseline['native_libraries']['libAppAndroid.so'],
    'edited_native_sha256': edited['native_libraries']['libAppAndroid.so'],
    'user_owned_files_preserved': owned_hashes,
    'evidence': {'cli_tests': 19, 'runtime_tests': 3, 'existing_checklist_tests': 5, 'java_wire_checks': 34, 'shared_app_tests': 4, 'generated_app_c_abi_tests': 2, 'ios_simulator_cross_build': 'passed unsigned; no simulator launch', 'android_arm64_cross_build_and_apk_inspection': 'passed unsigned; actual AArch64 ELF64 headers checked; no install or device run', 'lock_drift_capability_resource_original_compiler_errors_and_concurrent_source_mutation': 'rejected', 'source_observation': 'before/after local mutation check only; no immutable sandbox or build attestation', 'user_edits': 'recompiled shared feature and preserved native manifest/entry edits', 'export': 'locked sources exported; host tests passed; independent CI not attempted'},
    'scope': 'Generated application owns its AppModels/AppFeatures reducer/document and native extension entry. Consumes copied owned Java/JNI/runtime through immutable local source locks. Official installed tools only.',
    'pending': ['independent reproduction/review', 'physical Android and iOS (phones disconnected)', 'APK signing/installability', 'FieldLog D2', 'separate-repository published immutable packages', 'clean-machine and independent CI export builds', 'native capability/resource packaging', 'lifecycle/process restoration/persistence', 'accessibility/IME/device/ABI matrix', 'performance', 'store acceptance', 'GA'],
}
(OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'source_tree_sha256': receipt['source_tree_sha256'], 'apk': receipt['actual_apk'], 'pending': receipt['pending']}, indent=2))
