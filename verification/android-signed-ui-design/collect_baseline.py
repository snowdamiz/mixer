#!/usr/bin/env python3
"""Record a bounded, device-free baseline for the Android signed-UI design.

This checks existing host contracts only. It never calls adb, downloads tools,
builds a signed guest host, changes a source file, or claims Android execution.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
JDK = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
SWIFT_ANDROID = Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift')
NDK = Path('/Users/andreyyurlov/.swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android/android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64')
ENV = os.environ.copy()
ENV['DEVELOPER_DIR'] = '/Applications/Xcode_26.6.app/Contents/Developer'
commands = []


def run(name, command):
    result = subprocess.run([str(value) for value in command], cwd=ROOT,
                            env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    path = OUT / (name + '.log')
    path.write_bytes(result.stdout)
    commands.append({'name': name, 'argv': [str(value) for value in command],
                     'exit_code': result.returncode,
                     'output': str(path.relative_to(ROOT))})
    return result.returncode, result.stdout.decode(errors='replace')


sources = [
    'AGENTS.md', 'mixer-product-plan.md', 'PLAN.md',
    'contracts/ui-v1.json', 'contracts/guest-ui-event-v1.json',
    'docs/guest-ui-event-integration-design.md',
    'sdk/Sources/MixerGuest/GuestUIExchangeV1.swift',
    'sdk/Sources/MixerGuest/GuestUIWakeV1.swift',
    'sdk/Sources/MixerUI/Reconciliation.swift',
    'sdk/Sources/MixerApple/MixerNativeView.swift',
    'capability-activation/Package.swift',
    'capability-activation/Sources/MixerCapabilityActivation/CapabilityGuestUIRuntime.swift',
    'capability-activation/Sources/MixerCapabilityActivation/CapabilityGuestUIPresentation.swift',
    'capability-activation/Sources/MixerCapabilityActivation/CapabilityGuestUIApple.swift',
    'capability-activation/Sources/MixerCapabilityActivation/CapabilityInstalledExecutionMode.swift',
    'capability-activation/Sources/MixerCapabilityActivation/CapabilityColdStartControl.swift',
    'capability-activation/Sources/MixerCapabilityActivation/CapabilityColdStartWorker.swift',
    'native/android/README.md', 'native/android/build.py', 'native/android/verify.py',
    'native/android/bridge/mixer_android.h', 'native/android/bridge/jni.c',
    'native/android/engine/Package.swift',
    'native/android/engine/Sources/MixerAndroidRuntime/DocumentSession.swift',
    'native/android/engine/Sources/MixerAndroidRuntime/SessionRegistry.swift',
    'native/android/app/src/dev/mixer/android/NativeBridge.java',
    'native/android/app/src/dev/mixer/android/MixerActivity.java',
    'native/android/app/src/dev/mixer/android/NativeRenderer.java',
    'native/android/app/src/dev/mixer/android/UiPacket.java',
    'native/android/app/src/dev/mixer/android/Json.java',
    'native/android/tests/ContractTests.java',
    'native/android/contracts/android-profile-v1.json',
    'cli/Sources/MixerBuild/AndroidProject.swift',
    'cli/Sources/MixerBuild/Resources/android-build.py', 'THIRD_PARTY.yml',
]


def manifest():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sources}


before = manifest()
_, revision = run('source-revision', ['git', 'rev-parse', 'HEAD'])
run('source-status', ['git', 'status', '--short'])
versions = {}
for name, command in [
    ('python', [sys.executable, '--version']),
    ('swift-host', ['/usr/bin/swift', '--version']),
    ('swift-android', [SWIFT_ANDROID, '--version']),
    ('javac', [JDK / 'bin/javac', '--version']),
    ('java', [JDK / 'bin/java', '--version']),
    ('ndk-clang', [NDK / 'bin/aarch64-linux-android28-clang', '--version']),
]:
    code, output = run('version-' + name, command)
    versions[name] = {'exit_code': code, 'output': output.strip()}

classes = OUT / 'host-java-classes'
classes.mkdir(exist_ok=True)
java_sources = [ROOT / 'native/android/app/src/dev/mixer/android' / name
                for name in ['Json.java', 'UiPacket.java']]
java_sources.append(ROOT / 'native/android/tests/ContractTests.java')
java_build, _ = run('java-contract-build', [JDK / 'bin/javac', '--release', '17',
    '-Xlint:all', '-Werror', '-d', classes, *java_sources])
java_code, java_output = run('java-contract-tests', [JDK / 'bin/java', '-cp', classes,
    'dev.mixer.android.ContractTests']) if java_build == 0 else (-1, 'compile failed')
swift_code, swift_output = run('swift-android-engine-host-tests', ['/usr/bin/swift', 'test',
    '--package-path', ROOT / 'native/android/engine', '--scratch-path', OUT / 'host-swift-build',
    '--disable-automatic-resolution'])
after = manifest()
manifest_text = ''.join(f'{digest}  {name}\n' for name, digest in before.items())
(OUT / 'source-manifest.sha256').write_text(manifest_text)
receipt = {
    'schema_version': 1,
    'observed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'executor': 'Android signed UI design lane',
    'source_revision': revision.strip(),
    'source_tree_digest': hashlib.sha256(manifest_text.encode()).hexdigest(),
    'source_manifest': str((OUT / 'source-manifest.sha256').relative_to(ROOT)),
    'selected_inputs_unchanged_during_checks': before == after,
    'tool_versions': versions,
    'commands': commands,
    'observations': {
        'java_contract_tests_exit_code': java_code,
        'java_contract_marker': next((line for line in java_output.splitlines()
                                      if line.startswith('Android wire contract checks passed:')), None),
        'swift_android_engine_host_tests_exit_code': swift_code,
        'swift_host_test_summary': [line for line in swift_output.splitlines()
                                    if 'Test run with ' in line or 'Executed ' in line],
    },
    'scope': 'Existing development Android adapter host contracts only; design evidence.',
    'not_executed': ['Android signed runtime', 'Android JNI runtime', 'Android native widgets',
                     'Android layout/display/health', 'device or emulator queries or execution',
                     'APK build/signing/publication', 'FieldLog or GA qualification'],
}
(OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'source_revision': receipt['source_revision'],
                  'selected_inputs_unchanged_during_checks': before == after,
                  'observations': receipt['observations']}, indent=2))
sys.exit(0 if java_code == 0 and swift_code == 0 and before == after else 1)
