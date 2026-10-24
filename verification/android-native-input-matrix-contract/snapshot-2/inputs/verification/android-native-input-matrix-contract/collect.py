#!/usr/bin/env python3
"""Freeze a contract review and compile-only SDK witness; never query native targets."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
JDK = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
SDK = Path('/opt/homebrew/share/android-commandlinetools')
JAR = SDK / 'platforms/android-37.0/android.jar'
BASE = 'verification/android-coordinator-apk-packaging/candidate-1'
ACCEPTANCE = 'verification/android-coordinator-join-root-review/native-join-acceptance.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'snapshot-[1-9][0-9]*', args.attempt):
        parser.error('fresh snapshot-N required')
    out = HERE / args.attempt
    out.mkdir()  # Exclusive new evidence directory; never rewrite an earlier attempt.
    commands = []
    receipt = {
        'schema': 1, 'status': 'collecting', 'commands': commands,
        'collectorSHA256': sha(Path(__file__)),
        'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Source/receipt identity review and Java17 SDK37 public-API linkage only',
        'fixtureImplemented': False, 'productionSourcesModified': False,
        'nativeInstancesStarted': 0, 'nativeTargetsQueried': False,
        'nativeAssertionsExecutedByThisLane': 0, 'nativeAcceptance': False,
        'physicalAcceptance': False, 'gaAcceptance': False,
    }

    def run(name, argv):
        argv = [str(value) for value in argv]
        start = datetime.datetime.now(datetime.timezone.utc).isoformat()
        result = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=30, check=False)
        log = out / (name + '.log')
        log.write_bytes(result.stdout)
        commands.append({'name': name, 'argv': argv, 'cwd': str(ROOT),
                         'startedUTC': start,
                         'finishedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                         'exitCode': result.returncode, 'output': log.name,
                         'outputSHA256': sha(log)})
        if result.returncode:
            raise RuntimeError(name + ' failed; full output retained')
        return result.stdout.decode().strip()

    try:
        receipt['sourceRevision'] = run('source-revision', ['git', 'rev-parse', 'HEAD'])
        receipt['sourceTree'] = run('source-tree', ['git', 'rev-parse', 'HEAD^{tree}'])
        receipt['pythonVersion'] = run('python-version', [sys.executable, '--version'])
        receipt['javaVersion'] = run('java-version', [JDK / 'bin/java', '--version'])
        receipt['javacVersion'] = run('javac-version', [JDK / 'bin/javac', '--version'])
        receipt['javapVersion'] = run('javap-version', [JDK / 'bin/javap', '-version'])
        receipt['gitVersion'] = run('git-version', ['git', '--version'])
        lock = json.loads((ROOT / BASE / 'source-lock.json').read_text())
        declared = hashlib.sha256(json.dumps(lock['files'], sort_keys=True,
                                             separators=(',', ':')).encode()).hexdigest()
        assert declared == lock['sourceClosureSHA256']
        policy = json.loads((HERE / 'contract.json').read_text())
        assert declared == policy['predecessor']['sourceClosureSHA256']
        comparisons = {}
        for name, expected in lock['files'].items():
            actual = sha(ROOT / name)
            comparisons[name] = {'expectedSHA256': expected, 'currentSHA256': actual,
                                 'matches': expected == actual,
                                 'nativeOrSDKInput': name.startswith(('native/', 'sdk/'))}
        product_inputs = {name: item for name, item in comparisons.items()
                          if item['nativeOrSDKInput']}
        assert len(product_inputs) == 88
        assert all(item['matches'] for item in product_inputs.values())
        save(out / 'predecessor-input-comparison.json', comparisons)
        receipt['predecessorComparison'] = {
            'frozenInputs': len(comparisons), 'nativeAndSDKInputs': len(product_inputs),
            'nativeAndSDKTestInputs': sum('/Tests/' in name for name in product_inputs),
            'nativeAndSDKInputsAllMatch': True,
            'otherCurrentDrift': [name for name, item in comparisons.items() if not item['matches']],
            'sourceClosureSHA256': declared,
        }
        accepted = json.loads((ROOT / ACCEPTANCE).read_text())
        assert accepted['nativeDevelopmentSubsetAccepted'] is True
        assert accepted['fullNativeAccepted'] is False
        assert accepted['nativeChecks'] == 64 and accepted['nativeOperations'] == 8
        assert accepted['apkSHA256'] == policy['predecessor']['apkSHA256']
        assert accepted['sourceClosureSHA256'] == declared
        for name, expected in accepted['bindings'].items():
            assert sha(ROOT / name) == expected, 'acceptance binding drift: ' + name
        receipt['predecessorRootAcceptance'] = {
            'path': ACCEPTANCE, 'sha256': sha(ROOT / ACCEPTANCE),
            'bindingsRechecked': len(accepted['bindings']),
            'status': accepted['status'], 'nativeChecks': accepted['nativeChecks'],
            'nativeOperations': accepted['nativeOperations'],
            'actualPacketsIndependentlyDecodedByRoot': accepted['actualPacketsIndependentlyDecoded'],
            'scope': accepted['scope'],
        }
        bounds = policy['firstSlice']['bounds']
        actions = len(policy['firstSlice']['cycle']) * policy['firstSlice']['cycleRepetitions']
        actions += len(policy['firstSlice']['singleActions'])
        assert actions == bounds['gestureActions'] == 20
        assert bounds['injectedMotionEvents'] == actions * bounds['eventsPerAction'] == 320
        assert bounds['setupOrdinaryDispatches'] == 2 * bounds['setupAdditionalTasks'] == 36
        assert policy['fixtureImplemented'] is False
        receipt['contractBudgetConsistency'] = 'passed; metadata arithmetic only'

        names = [
            'AGENTS.md', 'mixer-product-plan.md', 'THIRD_PARTY.yml',
            'docs/android-native-v2-coordinator-contract.md', 'docs/android-native-v2-coordinator.md',
            'docs/android-coordinator-join.md', 'docs/android-coordinator-join-runtime-status.md',
            'docs/android-coordinator-join-acceptance.md',
            'docs/android-native-input-matrix-contract.md',
            'native/android/app/src/dev/mixer/android/NativeRenderer.java',
            'native/android/app/src/dev/mixer/android/NativeAppearanceViewsV2.java',
            'native/android/app/src/dev/mixer/android/NativeCoordinatorV2.java',
            'native/android/app/src/dev/mixer/android/NativeEnvironmentV2.java',
            'native/android/app/src/dev/mixer/android/AppearanceGeometryV2.java',
            'native/android/app/src/dev/mixer/android/NativeBridge.java',
            'native/android/app/src/dev/mixer/android/UiPacket.java',
            'native/android/engine/Sources/MixerAndroidEngine/Engine.swift',
            'native/android/engine/Sources/MixerAndroidEngine/Bridge.swift',
            'native/android/engine/Sources/MixerAndroidRuntime/SessionRegistry.swift',
            'native/android/bridge/jni.c',
            'verification/android-coordinator-join/CoordinatorJoinActivity.java',
            'verification/android-coordinator-join/CoordinatorJoinInstrumentation.java',
            'verification/android-coordinator-join/operations.json',
            'verification/android-coordinator-join/run.py',
            'verification/android-coordinator-wifi-runner/run.py',
            'verification/android-native-appearance-v2/emulator-session.json',
            'verification/native-testing-resume-2026-10-24/receipt.json',
            'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json',
            BASE + '/receipt.json', BASE + '/source-lock.json',
            ACCEPTANCE, 'verification/android-coordinator-apk-packaging/runtime-1/native-results.json',
            'verification/android-native-input-matrix-contract/PlatformInputApiProbe.java',
            'verification/android-native-input-matrix-contract/contract.json',
            'verification/android-native-input-matrix-contract/collect.py',
        ]
        hashes = {}
        for name in names:
            target = out / 'inputs' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
            hashes[name] = sha(target)
        receipt['sourceSnapshotSHA256'] = hashlib.sha256(json.dumps(
            hashes, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        save(out / 'source-lock.json', {'sourceRevision': receipt['sourceRevision'],
             'sourceSnapshotSHA256': receipt['sourceSnapshotSHA256'], 'files': hashes})

        tools = [Path(sys.executable), JDK / 'bin/java', JDK / 'bin/javac', JDK / 'bin/javap',
                 Path(shutil.which('git')), JAR, SDK / 'platforms/android-37.0/source.properties',
                 SDK / 'system-images/android-37.0/google_apis/arm64-v8a/source.properties']
        receipt['tools'] = {str(path): {'resolvedPath': str(path.resolve()),
            'bytes': path.stat().st_size, 'sha256': sha(path)} for path in tools}
        receipt['installedSDKSourceAvailability'] = {
            'sourcesDirectoryPresent': (SDK / 'sources').is_dir(),
            'semanticsSource': 'Official Android developer API references cited in contract; installed android.jar declaration linkage only',
        }
        classes = out / 'classes'
        classes.mkdir()
        probe = out / 'inputs/verification/android-native-input-matrix-contract/PlatformInputApiProbe.java'
        run('public-sdk-java17-linkage', [JDK / 'bin/javac', '--release', '17', '-Xlint:all',
            '-Werror', '-classpath', JAR, '-d', classes, probe])
        run('compiled-api-witness-signature', [JDK / 'bin/javap', '-classpath', classes,
            '-p', 'PlatformInputApiProbe'])
        run('installed-sdk-api-signatures', [JDK / 'bin/javap', '-classpath', JAR,
            'android.app.Instrumentation', 'android.app.UiAutomation', 'android.view.MotionEvent',
            'android.view.KeyEvent', 'android.view.ViewConfiguration', 'android.view.View',
            'android.view.inputmethod.InputConnection'])
        receipt['compileWitness'] = {
            'status': 'passed', 'executed': False, 'packaged': False,
            'classSHA256': sha(classes / 'PlatformInputApiProbe.class'),
            'scope': 'Public API declaration linkage only; not a native fixture, Android execution, source behavior proof, production compilation or release authorization',
        }
        receipt['status'] = 'contract-snapshot-and-public-api-linkage-passed-no-native-execution'
    except BaseException as failure:
        receipt['status'] = 'failed-contract-snapshot-retained'
        receipt['failure'] = repr(failure)
        raise
    finally:
        receipt['finishedUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save(out / 'receipt.json', receipt)
        files = {str(path.relative_to(out)): {'bytes': path.stat().st_size, 'sha256': sha(path)}
                 for path in sorted(out.rglob('*')) if path.is_file() and path.name != 'artifact-seal.json'}
        save(out / 'artifact-seal.json', {'schema': 1, 'files': files,
            'scope': 'Immutable retained files; seal is an integrity manifest, not a digital signature'})
        print(json.dumps({'status': receipt['status'], 'receipt': str(out / 'receipt.json'),
                          'retainedFiles': len(files)}, indent=2))


if __name__ == '__main__':
    main()
