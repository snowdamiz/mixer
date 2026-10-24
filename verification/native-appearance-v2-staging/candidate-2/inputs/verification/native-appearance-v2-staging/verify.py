#!/usr/bin/env python3
"""Retain inspected inputs and compiler-only API declaration feasibility evidence."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
JDK = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
SDK = Path('/opt/homebrew/share/android-commandlinetools')
JAR = SDK / 'platforms/android-37.0/android.jar'
JAVA = [
    'native/android/app/src/dev/mixer/android/Json.java',
    'native/android/app/src/dev/mixer/android/UiPacket.java',
    'native/android/app/src/dev/mixer/android/AppearanceDescriptorV2.java',
    'native/android/app/src/dev/mixer/android/AppearanceGeometryV2.java',
    'native/android/app/src/dev/mixer/android/AppearanceResolverV2.java',
    'native/android/app/src/dev/mixer/android/AppearanceNativePathsV2.java',
    'native/android/app/src/dev/mixer/android/NativeRenderer.java',
    'verification/native-appearance-v2-staging/AndroidAPIDeclarations.java',
]
INPUTS = JAVA + [
    'AGENTS.md', 'mixer-product-plan.md',
    'docs/ui-measured-appearance-v2-contract.md',
    'docs/ui-appearance-resolution-v2.md', 'docs/android-appearance-v2-resolution.md',
    'docs/native-appearance-v2-staging.md',
    'sdk/Sources/MixerUI/Reconciliation.swift',
    'sdk/Sources/MixerUI/AppearanceResolutionV2.swift',
    'sdk/Sources/MixerApple/MixerNativeView.swift',
    'sdk/Sources/MixerApple/AppearanceNativePathsV2.swift',
    'native/android/app/src/dev/mixer/android/MixerActivity.java',
    'native/android/app/src/dev/mixer/android/NativeBridge.java',
    'native/android/bridge/jni.c', 'native/android/bridge/mixer_android.h',
    'native/android/engine/Sources/MixerAndroidRuntime/DocumentSession.swift',
    'native/android/engine/Sources/MixerAndroidRuntime/SessionRegistry.swift',
    'cli/Sources/MixerBuild/Configuration.swift',
    'cli/Sources/MixerBuild/ProjectGenerator.swift',
    'cli/Sources/MixerBuild/AppleProject.swift',
    'cli/Sources/MixerBuild/AndroidProject.swift',
    'cli/Sources/MixerBuild/Resources/android-build.py',
    'verification/native-appearance-v2-staging/AppleAPIDeclarations.swift',
    'verification/native-appearance-v2-staging/verify.py',
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def check(out, live):
    manifest = json.loads((out / 'input-manifest.json').read_text())
    for name, digest in manifest.items():
        assert sha(out / 'inputs' / name) == digest, name
        if live:
            assert sha(ROOT / name) == digest, 'live input differs: ' + name
    seal = json.loads((out / 'artifact-seal.json').read_text())
    actual = {str(path.relative_to(out)): sha(path) for path in sorted(out.rglob('*'))
              if path.is_file() and path.name != 'artifact-seal.json'}
    assert actual == seal, 'retained artifact closure differs'
    print('PASS retained compiler-only evidence' + (' and live inputs' if live else ''))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output')
    group.add_argument('--check')
    parser.add_argument('--check-live', action='store_true')
    args = parser.parse_args()
    name = args.output or args.check
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', name):
        parser.error('output/check is one bounded directory name')
    out = HERE / name
    if args.check:
        check(out, args.check_live)
        return
    out.mkdir(exist_ok=False)
    manifest = {}
    for relative in INPUTS:
        src = ROOT / relative
        assert src.is_file() and not src.is_symlink(), relative
        target = out / 'inputs' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
        manifest[relative] = sha(target)
    (out / 'input-manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    commands = []

    def run(label, argv):
        argv = list(map(str, argv))
        proc = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=120)
        log = out / (label + '.log')
        log.write_bytes(proc.stdout + proc.stderr)
        commands.append({'label': label, 'argv': argv, 'cwd': str(ROOT), 'exitCode': proc.returncode,
                         'output': str(log.relative_to(ROOT)), 'sha256': sha(log)})
        print(label, proc.returncode, flush=True)
        if proc.returncode:
            raise RuntimeError(label + ': ' + (proc.stdout + proc.stderr).decode(errors='replace')[-4000:])
        return proc.stdout.decode().strip()

    status, failure = 'failed', None
    tools = {}
    try:
        revision = run('revision', ['git', 'rev-parse', 'HEAD'])
        tree = run('committed-tree', ['git', 'rev-parse', 'HEAD^{tree}'])
        run('worktree-status', ['git', 'status', '--porcelain'])
        tools['python'] = run('python-version', [sys.executable, '--version'])
        tools['swift'] = run('swift-version', ['xcrun', 'swiftc', '--version'])
        tools['javac'] = run('javac-version', [JDK / 'bin/javac', '--version'])
        tools['xcode'] = run('xcode-version', ['xcodebuild', '-version'])
        iphone_sdk = run('iphone-sdk', ['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'])
        sim_sdk = run('simulator-sdk', ['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-path'])
        for label, sdk_path, triple in [('iphone-declarations', iphone_sdk, 'arm64-apple-ios17.0'),
                                        ('simulator-declarations', sim_sdk, 'arm64-apple-ios17.0-simulator')]:
            run(label, ['xcrun', 'swiftc', '-typecheck', '-sdk', sdk_path, '-target', triple,
                        out / 'inputs/verification/native-appearance-v2-staging/AppleAPIDeclarations.swift'])
        classes = out / 'classes'
        classes.mkdir()
        run('android-declarations', [JDK / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror',
                                    '-classpath', JAR, '-d', classes,
                                    *[out / 'inputs' / relative for relative in JAVA]])
        tools['androidJar'] = {'path': str(JAR), 'sha256': sha(JAR),
                               'scope': 'API37 compile stubs; no API28/API29 execution'}
        headers = Path(iphone_sdk) / 'System/Library/Frameworks/UIKit.framework/Headers'
        tools['selectedUIKitHeaders'] = {name: sha(headers / name) for name in [
            'UITextField.h', 'UITextInput.h', 'UITextSelectionDisplayInteraction.h',
            'UITextSelectionHighlightView.h', 'UITextInteraction.h']}
        status = 'passed-compiler-only'
    except Exception as error:
        failure = str(error)
        revision = locals().get('revision')
        tree = locals().get('tree')
    receipt = {'schema': 1, 'status': status, 'failure': failure,
               'createdAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'revision': revision, 'committedTree': tree,
               'inputClosureSha256': hashlib.sha256(encoded(manifest)).hexdigest(),
               'commands': commands, 'tools': tools,
               'scope': 'Source-backed proposal plus compiler-only selected public toolkit API declarations.',
               'nativeExecution': 'not run', 'physicalDevices': 'not enumerated or run; disconnected',
               'pending': ['all-ten native consumers', 'Apple built-in field selection/caret feasibility',
                           'API28 Android cursor/font implementation', 'native IME/selection retention/rollback',
                           'ordinary engine/JNI transaction', 'installed resource/font consumption',
                           'ordinary bootstrap/public API freeze', 'signed V2', 'physical parity',
                           'immutable published FieldLog qualification', 'all GA gates']}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    seal = {str(path.relative_to(out)): sha(path) for path in sorted(out.rglob('*')) if path.is_file()}
    (out / 'artifact-seal.json').write_text(json.dumps(seal, indent=2, sort_keys=True) + '\n')
    print(status)
    if failure:
        raise SystemExit(failure)


if __name__ == '__main__':
    main()
