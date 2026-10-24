#!/usr/bin/env python3
"""Host coordinator decisions + actual SDK37/Java17/DEX only. Never discovers/runs native targets."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / 'verification/android-native-v2-coordinator'
JDK = Path(os.environ.get('MIXER_JDK', '/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home'))
SDK = Path(os.environ.get('ANDROID_HOME', '/opt/homebrew/share/android-commandlinetools'))
JAR = SDK / 'platforms/android-37.0/android.jar'
BT = SDK / 'build-tools/37.0.0'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', required=True, help='new retained evidence directory; never overwritten')
    args = parser.parse_args()
    if Path(args.attempt).name != args.attempt:
        raise ValueError('attempt must be one directory component')
    attempt = HERE / args.attempt
    attempt.mkdir()
    env = os.environ.copy()
    env['JAVA_HOME'] = str(JDK)
    env['PATH'] = str(JDK / 'bin') + os.pathsep + env['PATH']
    commands = []
    receipt = {
        'schema': 1,
        'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'running',
        'scope': 'production coordinator bytecode decision behavior with explicit test-only leaves; actual SDK37 compile/DEX; no native execution',
        'hostDecisionAcceptance': False,
        'actualSDKCompilation': False,
        'productionDEXMinAPI': 28,
        'privateNativeRuntimeFloorAPI': 36,
        'futureNativeIntegration': 'compiled only, NOT RUN',
        'nativeAcceptance': False,
        'gaAcceptance': False,
        'pending': [
            'actual JNI + ordinary Swift registry + native renderer joined runtime test',
            'native draw/input gating, rollback, lifecycle and IME evidence',
            'physical iOS/Android final acceptance matrix',
            'independent accountable acceptance review',
            'public Activity/bootstrap, descriptor opt-in, signed release and GA evidence',
        ],
        'environment': {'JAVA_HOME': str(JDK), 'ANDROID_HOME': str(SDK), 'python': sys.executable},
        'commands': commands,
    }

    def run(name, argv):
        argv = list(map(str, argv))
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        result = subprocess.run(argv, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log = attempt / (name + '.log')
        log.write_bytes(result.stdout)
        commands.append({'argv': argv, 'cwd': str(ROOT), 'environmentOverrides': {'JAVA_HOME': str(JDK), 'PATH_prefix': str(JDK / 'bin')},
                         'startedUTC': started, 'finishedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                         'exitCode': result.returncode, 'log': log.name, 'logSHA256': digest(log)})
        print(f'{name}: exit {result.returncode}', flush=True)
        if result.returncode:
            print(result.stdout.decode(errors='replace'), flush=True)
            raise RuntimeError(f'{name} failed; retained {log}')
        return result.stdout.decode(errors='replace').strip()

    try:
        receipt['sourceRevision'] = run('source-revision', ['git', 'rev-parse', 'HEAD'])
        run('source-status', ['git', 'status', '--short'])
        contract = json.loads((HERE / 'root-contract.json').read_text())
        for relative, expected in contract['bindings'].items():
            if digest(ROOT / relative) != expected:
                raise RuntimeError(f'frozen contract input drifted: {relative}')
        production_sources = sorted((ROOT / 'native/android/app/src').rglob('*.java'))
        host_sources = sorted((ROOT / 'native/android/tests/NativeCoordinatorV2HostLeaves').rglob('*.java'))
        host_sources.append(ROOT / 'native/android/tests/NativeCoordinatorV2HostTests.java')
        integration_sources = sorted((ROOT / 'native/android/tests').glob('NativeCoordinatorV2Integration*.java'))
        closure = set(production_sources + host_sources + integration_sources)
        closure.update(ROOT / path for path in contract['bindings'])
        closure.update(ROOT / path for path in [
            'AGENTS.md', 'mixer-product-plan.md', 'docs/android-native-v2-coordinator.md',
            'native/android/bridge/mixer_android.h', 'native/android/bridge/mixer_android_v2.h',
            'native/android/engine/Package.swift', 'verification/computer-use-pause-2026-10-24/receipt.json',
        ])
        closure.update((ROOT / 'native/android/engine/Sources').rglob('*.swift'))
        closure.update([Path(__file__).resolve(), HERE / 'root-contract.json', HERE / 'AndroidManifest.future-test.xml'])
        source_hashes = {}
        for source in sorted(closure):
            relative = str(source.relative_to(ROOT))
            target = attempt / 'inputs' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            source_hashes[relative] = digest(target)
        source_digest = hashlib.sha256(json.dumps(source_hashes, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        write_json(attempt / 'source-lock.json', {'sourceRevision': receipt['sourceRevision'],
                   'treeSHA256': source_digest, 'files': source_hashes})
        receipt['sourceTreeSHA256'] = source_digest

        def frozen(sources):
            return [attempt / 'inputs' / source.relative_to(ROOT) for source in sources]

        tool_paths = [JDK / 'bin/java', JDK / 'bin/javac', JDK / 'bin/javap', BT / 'd8', BT / 'lib/d8.jar', JAR]
        receipt['toolArtifacts'] = {str(path): {'realPath': str(path.resolve()), 'bytes': path.stat().st_size,
                                                'sha256': digest(path)} for path in tool_paths}
        receipt['versions'] = {
            'java': run('java-version', [JDK / 'bin/java', '--version']),
            'javac': run('javac-version', [JDK / 'bin/javac', '-version']),
            'd8': run('d8-version', [BT / 'd8', '--version']),
            'python': run('python-version', [sys.executable, '--version']),
        }
        classes = attempt / 'production-classes'
        classes.mkdir()
        empty = attempt / 'empty-sourcepath'
        empty.mkdir()
        run('production-java17-sdk37', [JDK / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror',
            '-sourcepath', empty, '-classpath', JAR, '-d', classes, *frozen(production_sources)])
        prod_class = classes / 'dev/mixer/android/NativeCoordinatorV2.class'
        receipt['productionCoordinatorClassSHA256'] = digest(prod_class)
        run('production-coordinator-bytecode', [JDK / 'bin/javap', '-c', '-p', '-classpath', classes,
            'dev.mixer.android.NativeCoordinatorV2'])
        dex = attempt / 'production-dex-min28'
        dex.mkdir()
        run('production-dex-min28', [BT / 'd8', '--min-api', '28', '--lib', JAR, '--output', dex,
            *sorted(classes.rglob('*.class'))])
        receipt['actualSDKCompilation'] = True
        receipt['productionSourceCount'] = len(production_sources)

        host_classes = attempt / 'host-classes'
        host_classes.mkdir()
        run('host-test-leaves-java17', [JDK / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror',
            '-sourcepath', empty, '-classpath', str(classes) + os.pathsep + str(JAR), '-d', host_classes,
            *frozen(host_sources)])
        loaded_class = host_classes / 'dev/mixer/android/NativeCoordinatorV2.class'
        shutil.copy2(prod_class, loaded_class)
        assert digest(loaded_class) == receipt['productionCoordinatorClassSHA256']
        receipt['executedCoordinatorClassSHA256'] = digest(loaded_class)
        receipt['hostLeafSubstitutes'] = [str(source.relative_to(ROOT)) for source in host_sources
                                        if 'NativeCoordinatorV2HostLeaves' in source.parts]
        decision_output = run('production-bytecode-host-fault-matrix', [JDK / 'bin/java', '-ea', '-Xverify:all',
            '-classpath', host_classes, 'dev.mixer.android.NativeCoordinatorV2HostTests'])
        receipt['hostDecisionSummary'] = decision_output.splitlines()[-2:]
        receipt['hostDecisionAcceptance'] = True

        integration_classes = attempt / 'future-integration-classes'
        integration_classes.mkdir()
        run('future-integration-java17-sdk37-NOT-RUN', [JDK / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror',
            '-sourcepath', empty, '-classpath', str(classes) + os.pathsep + str(JAR), '-d', integration_classes,
            *frozen(integration_sources)])
        integration_dex = attempt / 'future-integration-dex-min36-NOT-RUN'
        integration_dex.mkdir()
        run('future-integration-dex-min36-NOT-RUN', [BT / 'd8', '--min-api', '36', '--lib', JAR,
            '--output', integration_dex, *sorted(classes.rglob('*.class')), *sorted(integration_classes.rglob('*.class'))])
        receipt['status'] = 'host-decisions-and-actual-sdk-dex-pass-native-runtime-pending'
        print('\n'.join(receipt['hostDecisionSummary']), flush=True)
    except BaseException as failure:
        receipt['status'] = 'failed-attempt-retained'
        receipt['failure'] = repr(failure)
        raise
    finally:
        receipt['finishedUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        write_json(attempt / 'receipt.json', receipt)
        artifacts = {}
        for path in sorted(attempt.rglob('*')):
            if path.is_file() and path.name != 'artifact-seal.json':
                artifacts[str(path.relative_to(attempt))] = {'bytes': path.stat().st_size, 'sha256': digest(path)}
        write_json(attempt / 'artifact-seal.json', {'schema': 1, 'files': artifacts})


if __name__ == '__main__':
    main()
