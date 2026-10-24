#!/usr/bin/env python3
"""Collect and freeze host evidence only; root separately owns native dispatch."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import sys
import run as adapter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def files_under(paths):
    found = []
    for path in paths:
        found.extend([path] if path.is_file() else [p for p in path.rglob('*') if p.is_file()])
    return sorted(set(found))


def main():
    import re
    if (len(sys.argv) != 3 or not re.fullmatch(r'host-review-[0-9]+', sys.argv[1])
            or not re.fullmatch(r'host-tests-[0-9]+', sys.argv[2])):
        raise SystemExit('usage: python3 -B collect_host.py host-review-N host-tests-N (fresh outputs)')
    review, tests = HERE / sys.argv[1], HERE / sys.argv[2]
    review.mkdir()
    runner, source, diff = adapter.load_runner()
    helper = adapter.load_module('wifi_collection_helper', adapter.HELPER)
    sources = [HERE / name for name in ('run.py', 'runner-contract.json', 'test_runner.py', 'collect_host.py', 'check_packet.py')]
    sources.append(ROOT / 'docs/android-coordinator-wifi-runner.md')
    lock = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    commands = []
    receipt = {'schema': 1, 'status': 'running', 'startedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'commands': commands, 'sourceLock': lock,
        'sourceClosureSHA256': hashlib.sha256(json.dumps(lock, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
        'pythonVersion': sys.version, 'pythonExecutable': sys.executable, 'pythonExecutableSHA256': sha(sys.executable),
        'platform': platform.platform(), 'baseRunnerSHA256': sha(adapter.BASE),
        'transformedRunnerSHA256': hashlib.sha256(source.encode()).hexdigest(), 'contractSHA256': sha(adapter.CONTRACT),
        'boundEvidenceReferences': adapter.BINDINGS, 'installedExecutableBindings': adapter.EXECUTABLES,
        'nativeCommandsExecuted': 0, 'nativeInstancesStarted': 0, 'nativeTargetsDiscovered': 0,
        'physicalTargetsQueried': False, 'nativeRuntime': 'NOT RUN by adaptation lane; root dispatch pending',
        'scope': 'actual transformed runner main with injected host SDK/child objects; accepted real host extraction/process guards',
        'knownLimitation': json.loads(adapter.CONTRACT.read_text())['knownLimitation'],
        'limitations': ['Host fixtures never qualify APK/app/emulator runtime acceptance.',
            'Physical phone, full native fault/IME/lifecycle, public/signed, FieldLog, store, customer and GA gates remain pending.',
            'Root alone dispatches fresh runtime-N; accepted boot receipt is boot-only.',
            'Extraction cleanup protects cooperating local verification, not an adversarial concurrent filesystem attacker.']}

    def command(name, argv, timeout=30):
        start = datetime.datetime.now(datetime.timezone.utc).isoformat()
        result = helper.execute(argv, cwd=ROOT, timeout=timeout)
        log = review / (name + '.log'); log.write_bytes(result.stdout)
        commands.append({'name': name, 'argv': list(map(str, argv)), 'cwd': str(ROOT), 'startedUTC': start,
            'finishedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'exitCode': result.returncode,
            'output': str(log.relative_to(HERE)), 'outputSHA256': sha(log),
            'ownedCommandGroupCleanup': result.groupCleanup})
        if result.returncode:
            raise RuntimeError('host command failed: ' + name)
        return result.stdout.decode().strip()

    try:
        receipt['sourceRevision'] = command('source-revision', ['git', 'rev-parse', 'HEAD'])
        receipt['sourceTree'] = command('source-tree', ['git', 'rev-parse', 'HEAD^{tree}'])
        receipt['versions'] = {'python': command('python-version', [sys.executable, '--version']),
            'macOS': command('macos-version', ['/usr/bin/sw_vers']),
            'lsof': command('lsof-version', ['/usr/sbin/lsof', '-v']),
            'git': command('git-version', ['git', '--version'])}
        receipt['hostToolSHA256'] = {p: sha(p) for p in ('/usr/sbin/lsof', '/bin/ps')}
        metadata = runner.bind_candidate(runner.BUILDS / 'candidate-2')
        locked = json.loads((runner.BUILDS / 'candidate-2/source-lock.json').read_text())['files']
        artifacts = json.loads((runner.BUILDS / 'candidate-2/built-artifacts.json').read_text())
        receipt['frozenCandidate'] = {'path': 'verification/android-coordinator-join/candidate-2',
            'sourceInputs': len(locked), 'artifacts': len(artifacts), 'apkSHA256': metadata['apkSHA256'],
            'sourceRevision': metadata['sourceRevision'], 'sourceClosureSHA256': metadata['sourceClosureSHA256'],
            'archiveSHA256': runner.ARCHIVE_SHA256, 'bindings': runner.BUILD_BINDINGS,
            'candidateSourceInputsBound': True, 'appAssertions': 'unchanged; eight prepared actual operations NOT RUN by this lane'}
        (review / 'transformed_runner.py').write_text(source)
        (review / 'runner.diff').write_text(diff)
        save(review / 'source-deltas.json', json.loads(adapter.CONTRACT.read_text())['sourceDeltas'])
        command('host-tests', [sys.executable, '-B', str(HERE / 'test_runner.py'), tests.name], timeout=180)
        summary = json.loads((tests / 'receipt.json').read_text())
        if summary['status'] != 'passed' or summary['testsRun'] != 32:
            raise RuntimeError('expected 32 passing host tests')
        if {str(p.relative_to(ROOT)): sha(p) for p in sources} != lock:
            raise RuntimeError('source changed during collection')
        adapter.load_runner()
        runner.bind_candidate(runner.BUILDS / 'candidate-2')
        remaining = [str(p.relative_to(HERE)) for p in HERE.rglob('.build')]
        if remaining:
            raise RuntimeError('owned host extraction remains: ' + repr(remaining))
        receipt.update({'status': 'passed-host-adaptation-guards-only', 'testsRun': 32,
            'unchangedAcceptedGuardsReused': 21, 'allOwnedHostExtractionsAbsent': True,
            'sourceUnchanged': True, 'transformedSource': str((review / 'transformed_runner.py').relative_to(ROOT)),
            'diff': str((review / 'runner.diff').relative_to(ROOT)),
            'runtimeInvocation': [sys.executable, '-B', 'verification/android-coordinator-wifi-runner/run.py',
                '--build', 'candidate-2', '--attempt', 'runtime-1', '--execute-native']})
    except BaseException as failure:
        receipt.update({'status': 'failed-host-adaptation-verification', 'failure': repr(failure)})
        raise
    finally:
        receipt['finishedUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save(review / 'receipt.json', receipt)
    roots = sources + [review, tests]
    # Preserve initial failed host attempts without duplicating accepted APK archives.
    for p in sorted(HERE.iterdir()):
        if p.name.startswith('host-tests-') and p not in roots:
            roots.append(p)
    files = {str(p.relative_to(ROOT)): {'bytes': p.stat().st_size, 'sha256': sha(p)} for p in files_under(roots)}
    save(HERE / 'packet-seal.json', {'schema': 1, 'status': 'frozen-host-adaptation-only',
        'files': files, 'membershipRoots': [str(p.relative_to(ROOT)) for p in roots],
        'fileTreeSHA256': hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
        'immutableReferences': adapter.BINDINGS, 'contractSHA256': sha(adapter.CONTRACT),
        'transformedRunnerSHA256': hashlib.sha256(source.encode()).hexdigest(),
        'nativeRuntime': 'NOT RUN by adaptation lane', 'physicalTargetsQueried': False,
        'futureRuntimeOutputs': 'root-owned runtime-N directories excluded from host packet; retain each runtime receipt/seal independently'})
    print(json.dumps({'status': receipt['status'], 'testsRun': 32,
                      'transformedRunnerSHA256': receipt['transformedRunnerSHA256'], 'nativeInstancesStarted': 0}, sort_keys=True))


if __name__ == '__main__':
    main()
