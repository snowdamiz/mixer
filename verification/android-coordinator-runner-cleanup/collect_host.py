#!/usr/bin/env python3
"""Seal and execute only controlled host guards for the separately bound runner."""
import datetime
import difflib
import hashlib
import json
from pathlib import Path
import platform
import sys
from owned_process import execute
import run as runner

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def main():
    if len(sys.argv) != 3 or not sys.argv[1].startswith('host-review-') or not sys.argv[1][12:].isdigit() or not sys.argv[2].startswith('host-tests-') or not sys.argv[2][11:].isdigit():
        raise SystemExit('usage: python3 -B collect_host.py host-review-N host-tests-N (fresh directories)')
    review = HERE / sys.argv[1]
    review.mkdir()
    test_attempt = sys.argv[2]
    sources = [HERE / name for name in ['run.py', 'owned_process.py', 'test_cleanup.py', 'test_runner_guards.py', 'collect_host.py']]
    sources.append(ROOT / 'docs/android-coordinator-runner-cleanup.md')
    source_lock = {str(path.relative_to(ROOT)): sha(path) for path in sources}
    closure = hashlib.sha256(json.dumps(source_lock, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    commands = []
    receipt = {'schema': 1, 'status': 'running', 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'commands': commands, 'sourceLock': source_lock, 'runnerClosureSHA256': closure,
        'pythonVersion': sys.version, 'platform': platform.platform(),
        'pythonExecutable': sys.executable, 'pythonExecutableSHA256': sha(Path(sys.executable)),
        'nativeRuntime': 'NOT RUN', 'nativeCommandsExecuted': 0, 'nativeInstancesStarted': 0,
        'nativeTargetsDiscovered': 0, 'physicalTargetsQueried': False,
        'scope': 'controlled host file/process guards and candidate2 identity only; no Android execution or native acceptance',
        'limitations': ['No native success/failure runtime receipt; root dispatch remains pending.',
            'Synthetic main() fixtures stop before every native command and cannot qualify the APK.',
            'Physical phone matrix, full native matrix, public/signed/FieldLog/store/customer/GA gates remain pending.',
            'Cleanup is intended for the cooperating local verification process, not an adversarial concurrent filesystem attacker.']}
    def command(name, argv, timeout=30):
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        result = execute(argv, cwd=ROOT, timeout=timeout)
        log = review / (name + '.log')
        log.write_bytes(result.stdout)
        commands.append({'name': name, 'argv': list(map(str, argv)), 'cwd': str(ROOT),
            'startedUTC': started, 'finishedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'exitCode': result.returncode, 'output': str(log.relative_to(HERE)), 'outputSHA256': sha(log),
            'ownedCommandGroupCleanup': result.groupCleanup})
        if result.returncode:
            raise RuntimeError(name + ' failed; inspect ' + str(log))
        return result.stdout.decode().strip()
    try:
        receipt['sourceRevision'] = command('source-revision', ['git', 'rev-parse', 'HEAD'])
        receipt['sourceTree'] = command('source-tree', ['git', 'rev-parse', 'HEAD^{tree}'])
        receipt['toolVersions'] = {
            'python': command('python-version', [sys.executable, '--version']),
            'lsof': command('lsof-version', ['/usr/sbin/lsof', '-v']),
            'git': command('git-version', ['git', '--version']),
            'macOS': command('macos-version', ['/usr/bin/sw_vers']),
        }
        receipt['hostToolSHA256'] = {str(path): sha(path) for path in [Path('/usr/sbin/lsof'), Path('/bin/ps')]}
        metadata = runner.bind_candidate(runner.BUILDS / 'candidate-2')
        frozen_files = json.loads((runner.BUILDS / 'candidate-2/source-lock.json').read_text())['files']
        live_mismatches = [name for name, expected in frozen_files.items() if sha(ROOT / name) != expected]
        if live_mismatches:
            raise RuntimeError('frozen live input changed ' + repr(live_mismatches))
        receipt['frozenCandidate2'] = {'sourceInputs': len(frozen_files), 'sourceClosureSHA256': metadata['sourceClosureSHA256'],
            'archiveSHA256': sha(runner.BUILDS / 'candidate-2/built-artifacts.tar.gz'), 'apkSHA256': metadata['apkSHA256'],
            'bindings': runner.BUILD_BINDINGS, 'frozenInputsMatch': True, 'liveInputsMatch': True}
        original = (runner.BUILDS / 'run.py').read_text()
        (review / 'runner.diff').write_text(''.join(difflib.unified_diff(original.splitlines(keepends=True),
            (HERE / 'run.py').read_text().splitlines(keepends=True),
            fromfile='verification/android-coordinator-join/run.py', tofile='verification/android-coordinator-runner-cleanup/run.py')))
        command('extraction-host-tests', [sys.executable, '-B', str(HERE / 'test_cleanup.py'), test_attempt], timeout=90)
        command('preserved-runner-guards', [sys.executable, '-B', str(HERE / 'test_runner_guards.py')], timeout=30)
        tests = json.loads((HERE / test_attempt / 'unittest-result.json').read_text())
        if tests['status'] != 'passed' or tests['testsRun'] != 20:
            raise RuntimeError('host extraction test summary mismatch')
        if 'Ran 4 tests' not in (review / 'preserved-runner-guards.log').read_text():
            raise RuntimeError('preserved runner guard count mismatch')
        if {str(path.relative_to(ROOT)): sha(path) for path in sources} != source_lock:
            raise RuntimeError('runner source changed during host verification')
        runner.bind_candidate(runner.BUILDS / 'candidate-2')
        if any(sha(ROOT / name) != expected for name, expected in frozen_files.items()):
            raise RuntimeError('frozen live inputs changed during host verification')
        if any(path.name == '.build' for path in HERE.rglob('*')):
            raise RuntimeError('owned extraction remains in cleanup lane')
        receipt.update({'status': 'passed-host-cleanup-and-preserved-guards-only', 'hostExtractionTestsPassed': 20,
            'preservedRunnerGuardTestsPassed': 4, 'allOwnedExtractionsAbsent': True, 'sourceUnchanged': True,
            'correctedRunnerSHA256': sha(HERE / 'run.py'), 'originalFrozenRunnerSHA256': runner.ORIGINAL_RUNNER_SHA256,
            'testedCheckerReferenceSHA256': '20f00f2fe8c0d1936c7ec2aec771970fed28e1657d8085cc12eae1ced624f679',
            'runtimeInvocation': ['python3', '-B', 'verification/android-coordinator-runner-cleanup/run.py',
                '--build', 'candidate-2', '--attempt', 'runtime-1', '--execute-native']})
    except BaseException as failure:
        receipt['status'] = 'failed-host-verification'
        receipt['failure'] = repr(failure)
        raise
    finally:
        receipt['finishedUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save(review / 'receipt.json', receipt)
    print(json.dumps({'status': receipt['status'], 'runnerSHA256': receipt['correctedRunnerSHA256'],
        'hostTestsPassed': 24, 'nativeRuntime': 'NOT RUN'}, sort_keys=True))


if __name__ == '__main__':
    main()
