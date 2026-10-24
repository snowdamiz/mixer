#!/usr/bin/env python3
"""Independent bindings and host-only replay of actual SDK coordinator bytecode."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import traceback

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
LANE = ROOT / 'verification/android-native-v2-coordinator'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'coordinator-review-[0-9]+', args.output)
    out = BASE / args.output
    out.mkdir()
    candidate = LANE / 'candidate-3'
    checks, reads, summary, executed = [], {}, {}, []

    def read(path):
        data = path.read_bytes()
        reads[str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)] = sha(data)
        return data

    def obj(path):
        return json.loads(read(path))

    def bounded(base, name):
        path = (base / name).resolve()
        assert path.is_relative_to(base.resolve()), name
        return path

    def check(value, name):
        assert value, name
        checks.append(name)

    status, error = 'failed', None
    try:
        receipt = obj(candidate / 'receipt.json')
        state = obj(LANE / 'state.json')
        lock = obj(candidate / 'source-lock.json')
        contract = obj(LANE / 'root-contract.json')
        check(receipt['status'] == 'host-decisions-and-actual-sdk-dex-pass-native-runtime-pending', 'producer-scoped-status')
        check(receipt['actualSDKCompilation'] and receipt['hostDecisionAcceptance'], 'producer-sdk-and-host-status')
        check(receipt['nativeAcceptance'] is False and receipt['gaAcceptance'] is False, 'no-native-or-ga-acceptance')
        check(receipt['futureNativeIntegration'] == 'compiled only, NOT RUN', 'integration-execution-pending')
        check(state['receiptSHA256'] == sha(read(candidate / 'receipt.json')), 'state-binds-receipt')
        check(state['artifactSealSHA256'] == sha(read(candidate / 'artifact-seal.json')), 'state-binds-artifact-seal')
        check(state['rootContractSHA256'] == sha(read(LANE / 'root-contract.json')), 'state-binds-contract')
        files = lock['files']
        closure = sha(json.dumps(files, sort_keys=True, separators=(',', ':')).encode())
        check(closure == lock['treeSHA256'] == receipt['sourceTreeSHA256'] == state['sourceTreeSHA256'], 'exact-source-closure')
        for name, expected in files.items():
            data = read(bounded(candidate / 'inputs', name))
            check(sha(data) == expected, 'captured-source:' + name)
            check(sha(read(bounded(ROOT, name))) == expected, 'current-source:' + name)
        for name, expected in contract['bindings'].items():
            check(files[name] == expected, 'frozen-owner-contract:' + name)
        seal = obj(candidate / 'artifact-seal.json')
        for name, metadata in seal['files'].items():
            data = read(bounded(candidate, name))
            check(len(data) == metadata['bytes'] and sha(data) == metadata['sha256'], 'artifact:' + name)
        for command in receipt['commands']:
            check(command['exitCode'] == 0, 'producer-command-success:' + command['log'])
            check(sha(read(bounded(candidate, command['log']))) == command['logSHA256'], 'producer-command-log:' + command['log'])
        commands = {item['log']: item for item in receipt['commands']}
        check(len(commands) == 13, 'complete-thirteen-producer-commands')
        production_command = commands['production-java17-sdk37.log']['argv']
        production_sources = sorted((ROOT / 'native/android/app/src').rglob('*.java'))
        expected_production = {str(candidate / 'inputs' / item.relative_to(ROOT)) for item in production_sources}
        check({item for item in production_command if item.endswith('.java')} == expected_production
              and len(expected_production) == receipt['productionSourceCount'] == 16, 'exact-actual-sdk-sixteen-source-closure')
        check(production_command[production_command.index('--release') + 1] == '17'
              and '-Xlint:all' in production_command and '-Werror' in production_command, 'strict-java17-compilation')
        check(production_command[production_command.index('-classpath') + 1].endswith('/platforms/android-37.0/android.jar'), 'actual-sdk37-compilation')
        class_relative = 'dev/mixer/android/NativeCoordinatorV2.class'
        production_class = read(candidate / 'production-classes' / class_relative)
        host_class = read(candidate / 'host-classes' / class_relative)
        expected_class = '14a1210ca4208b3eb58a5d70db893b5f1729f5d7587c887cd16f37c18b758992'
        check(production_class == host_class and sha(production_class) == expected_class
              == receipt['productionCoordinatorClassSHA256'] == receipt['executedCoordinatorClassSHA256']
              == state['productionCoordinatorClassSHA256'] == state['executedCoordinatorClassSHA256'], 'same-actual-sdk-and-host-coordinator-bytecode')
        check(production_class[:4] == b'\xca\xfe\xba\xbe' and int.from_bytes(production_class[6:8], 'big') == 61, 'actual-java17-classfile')
        check(len(receipt['hostLeafSubstitutes']) == 8 and all('NativeCoordinatorV2HostLeaves/' in name for name in receipt['hostLeafSubstitutes']), 'eight-explicit-test-only-leaves')
        integration_command = commands['future-integration-java17-sdk37-NOT-RUN.log']['argv']
        expected_integration = {str(candidate / 'inputs/native/android/tests' / name) for name in [
            'NativeCoordinatorV2IntegrationActivity.java', 'NativeCoordinatorV2IntegrationInstrumentation.java']}
        check({item for item in integration_command if item.endswith('.java')} == expected_integration,
              'future-integration-compiles-real-two-test-sources-without-host-leaves')
        for label, minimum in [('production-dex-min28.log', '28'), ('future-integration-dex-min36-NOT-RUN.log', '36')]:
            argv = commands[label]['argv']
            check(argv[argv.index('--min-api') + 1] == minimum, 'declared-dex-target:' + label)
            check(all('/host-classes/' not in item for item in argv), 'dex-excludes-host-leaves:' + label)
        for directory in ['production-dex-min28', 'future-integration-dex-min36-NOT-RUN']:
            dex_files = sorted((candidate / directory).glob('*.dex'))
            check(bool(dex_files), 'retained-dex:' + directory)
            for dex in dex_files:
                data = read(dex)
                check(data[:4] == b'dex\n' and data[7] == 0, 'dex-header:' + str(dex.relative_to(candidate)))
        for name, metadata in receipt['toolArtifacts'].items():
            data = read(Path(name))
            check(sha(data) == metadata['sha256'] and len(data) == metadata['bytes'], 'current-tool:' + name)
        # Copy all sealed host leaves and the exact SDK-produced class, never compile them here.
        local_classes = out / 'host-classes'
        shutil.copytree(candidate / 'host-classes', local_classes)
        for source in (candidate / 'host-classes').rglob('*.class'):
            target = local_classes / source.relative_to(candidate / 'host-classes')
            check(sha(read(target)) == sha(read(source)), 'copied-host-class:' + str(source.relative_to(candidate / 'host-classes')))
        java = Path(receipt['environment']['JAVA_HOME']) / 'bin/java'
        argv = [str(java), '-ea', '-Xverify:all', '-Xlog:class+load=info:file=' + str(out / 'class-load.log'),
                '-classpath', str(local_classes), 'dev.mixer.android.NativeCoordinatorV2HostTests']
        environment = os.environ.copy()
        for key in ['JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', '_JAVA_OPTIONS', 'CLASSPATH']:
            environment.pop(key, None)
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        replay = subprocess.run(argv, cwd=ROOT, env=environment, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=30)
        log = out / 'host-replay.log'
        log.write_bytes(replay.stdout)
        executed.append({'argv': argv, 'cwd': str(ROOT), 'startedUTC': started,
                         'finishedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                         'exitCode': replay.returncode, 'log': str(log.relative_to(ROOT)), 'sha256': sha(replay.stdout),
                         'scope': 'Host JVM only; all Android/JNI/renderer leaves are explicitly substituted.'})
        check(replay.returncode == 0, 'independent-host-replay-success')
        check(replay.stdout == read(candidate / 'production-bytecode-host-fault-matrix.log'), 'independent-replay-exact-output')
        output = replay.stdout.decode()
        check('PASS production-coordinator-bytecode decision scenarios=133 checks=2087' in output, 'all-133-scenarios-2087-checks')
        scenario_names = re.findall(r'^PASS (.*?) trace=', output, re.M)
        check(len(scenario_names) == len(set(scenario_names)) == 133, 'unique-explicit-scenario-results')
        loading = read(out / 'class-load.log').decode()
        for name in ['NativeCoordinatorV2', 'NativeBridge', 'NativeRenderer', 'NativeCoordinatorV2HostTests']:
            lines = [line for line in loading.splitlines() if ('dev.mixer.android.' + name + ' source:') in line]
            check(len(lines) == 1 and str(local_classes) in lines[0], 'actual-loaded-class-origin:' + name)
        check(sha(read(local_classes / class_relative)) == expected_class, 'executed-coordinator-stable-after-replay')
        for name, expected in files.items():
            check(sha(read(ROOT / name)) == expected, 'final-source-unchanged:' + name)
        summary = {'candidate': 'candidate-3', 'sourceInputs': len(files), 'sourceClosureSHA256': closure,
                   'productionJavaSources': 16, 'executedCoordinatorClassSHA256': expected_class,
                   'sealedArtifacts': len(seal['files']), 'hostScenarios': 133, 'hostChecks': 2087,
                   'hostOutputIdenticalToProducer': True, 'sourceFindings': []}
        status = 'passed-private-coordinator-source-bindings-and-production-bytecode-host-review-native-pending'
    except Exception as failure:
        error = repr(failure)
        (out / 'failure.log').write_text(traceback.format_exc())
    result = {'status': status, 'error': error, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'command': [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
              'pythonVersion': platform.python_version(), 'reviewerScriptSHA256': sha(Path(__file__).read_bytes()),
              'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'sourceTree': subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=ROOT, text=True).strip(),
              'checks': checks, 'summary': summary, 'commandsExecuted': executed, 'evidenceSHA256': reads,
              'nativeAcceptance': False, 'gaAcceptance': False,
              'scope': 'Independent private coordinator source/contract/test review, offline artifact/source/tool bindings and one copied production-bytecode host JVM fault-matrix replay. No compilation, JNI/Swift/native view execution, GUI, image view, capture, target discovery or publication.',
              'pending': ['Actual JNI/ordinary Swift registry/native renderer joined runtime, draw/input/IME/lifecycle fault matrix.',
                          'Physical final matrix, public Activity/bootstrap, signed release, immutable FieldLog packages, stores and GA.']}
    (out / 'receipt.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': status, 'bindings': len(checks), 'evidenceFiles': len(reads), 'error': error,
                      'receipt': str(out / 'receipt.json')}))
    return 0 if status.startswith('passed-') else 1


if __name__ == '__main__':
    sys.exit(main())
