#!/usr/bin/env python3
"""Record and seal host verification of the private test-only derivative."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import sys
import run as adapter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if (len(sys.argv) != 3 or not re.fullmatch(r'host-review-[0-9]+', sys.argv[1])
            or not re.fullmatch(r'host-tests-[0-9]+', sys.argv[2])):
        raise SystemExit('usage: python3 -B collect_host.py host-review-N host-tests-N (fresh outputs)')
    review, tests = HERE / sys.argv[1], HERE / sys.argv[2]
    review.mkdir()
    runner, source, diff = adapter.load_runner()
    paths = [HERE / name for name in ('build.py', 'prepare_runner.py', 'run.py', 'runner-contract.json',
        'verify_candidate.py', 'test_runner.py', 'collect_host.py', 'check_packet.py')]
    paths.append(ROOT / 'docs/android-coordinator-click-fixture.md')
    sources = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    commands = []
    receipt = {'schema': 1, 'status': 'running', 'commands': commands,
        'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'sourceLock': sources, 'sourceClosureSHA256': hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
        'pythonVersion': sys.version, 'pythonExecutable': sys.executable, 'pythonExecutableSHA256': sha(sys.executable),
        'platform': platform.platform(), 'nativeCommandsExecuted': 0, 'nativeInstancesStarted': 0,
        'physicalTargetsQueried': False, 'nativeRuntime': 'NOT RUN by derivation lane',
        'runtimeInvocation': [sys.executable, '-B', 'verification/android-coordinator-click-fixture/run.py',
            '--build', 'candidate-1', '--attempt', 'runtime-1', '--execute-native'],
        'scope': 'test-only retained artifact verification and transformed runner host guards; root native dispatch pending',
        'limitations': ['Host tests use synthetic SDK operations and children and do not qualify Android app behavior.',
            'Fresh corrected APK native assertions pending root dispatch; original 27th assertion remains failed.',
            'Physical phones disconnected/deferred; full native matrix/public release/FieldLog/store/customer/operational/GA pending.']}

    def command(name, argv, timeout=30):
        start = datetime.datetime.now(datetime.timezone.utc).isoformat()
        completed = runner.execute(argv, cwd=ROOT, timeout=timeout)
        log = review / (name + '.log'); log.write_bytes(completed.stdout)
        commands.append({'name': name, 'argv': list(map(str, argv)), 'cwd': str(ROOT), 'startedUTC': start,
            'finishedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'exitCode': completed.returncode,
            'output': log.name, 'outputSHA256': sha(log), 'ownedCommandGroupCleanup': completed.groupCleanup})
        if completed.returncode:
            raise RuntimeError('host command failed: ' + name)
        return completed.stdout.decode().strip()

    try:
        receipt['sourceRevision'] = command('source-revision', ['git', 'rev-parse', 'HEAD'])
        receipt['sourceTree'] = command('source-tree', ['git', 'rev-parse', 'HEAD^{tree}'])
        receipt['versions'] = {'python': command('python-version', [sys.executable, '--version']),
            'macOS': command('macos-version', ['/usr/bin/sw_vers']),
            'lsof': command('lsof-version', ['/usr/sbin/lsof', '-v']),
            'git': command('git-version', ['git', '--version'])}
        receipt['hostToolSHA256'] = {name: sha(name) for name in ('/usr/sbin/lsof', '/bin/ps')}
        receipt['artifactVerification'] = json.loads(command('artifact-verification',
            [sys.executable, '-B', str(HERE / 'verify_candidate.py')]))
        command('host-tests', [sys.executable, '-B', str(HERE / 'test_runner.py'), tests.name], timeout=180)
        result = json.loads((tests / 'receipt.json').read_text())
        if result['status'] != 'passed' or result['testsRun'] != 36:
            raise ValueError('36 passing host guards required')
        if {str(p.relative_to(ROOT)): sha(p) for p in paths} != sources:
            raise ValueError('host source drift during collection')
        metadata = runner.bind_candidate(HERE / 'candidate-1')
        receipt['frozenCandidate'] = {'path': 'verification/android-coordinator-click-fixture/candidate-1',
            'apkSHA256': metadata['apkSHA256'], 'archiveSHA256': metadata['builtArchiveSHA256'],
            'sourceClosureSHA256': metadata['sourceClosureSHA256'], 'inputCount': 105, 'artifactCount': 177,
            'sourceDerivation': metadata['sourceDerivation'], 'privateKeyRetained': False,
            'buildScratchCleanup': metadata['buildScratchCleanup']}
        receipt['builderDispatch'] = {'argv': [sys.executable, '-B', 'verification/android-coordinator-click-fixture/build.py',
            '--attempt', 'candidate-1'], 'builderSHA256': sources['verification/android-coordinator-click-fixture/build.py'],
            'receiptSHA256': sha(HERE / 'candidate-1/receipt.json'),
            'toolVersions': metadata['versions'], 'toolBindings': metadata['tools']}
        # Explicitly clean the cache created by the early syntax-only compile.
        cache = HERE / '__pycache__'
        cache_cleanup = {'status': 'not-created'}
        if cache.exists():
            if cache.is_symlink() or not cache.is_dir() or any(p.is_symlink() for p in cache.rglob('*')):
                raise ValueError('unexpected owned cache path')
            checked = runner.execute(['/usr/sbin/lsof', '-nP', '+D', str(cache)], cwd=ROOT, timeout=30)
            log = review / 'owned-cache-open-holders.log'; log.write_bytes(checked.stdout)
            cache_cleanup = {'path': str(cache.relative_to(ROOT)), 'files': len(list(cache.rglob('*'))),
                'holderCheckExitCode': checked.returncode, 'holderOutput': log.name,
                'holderOutputSHA256': sha(log), 'ownedCommandGroupCleanup': checked.groupCleanup}
            if checked.returncode != 1 or checked.stdout:
                raise ValueError('owned cache holder or unavailable check')
            shutil.rmtree(cache)
            cache_cleanup.update({'status': 'removed', 'pathAbsent': not cache.exists()})
        receipt['ownedCacheCleanup'] = cache_cleanup
        remaining = [str(p.relative_to(HERE)) for p in HERE.rglob('.build')]
        if remaining:
            raise ValueError('owned build/extraction scratch remains: ' + repr(remaining))
        if (HERE / 'runner-source/transformed_runner.py').read_text() != source or (HERE / 'runner-source/runner.diff').read_text() != diff:
            raise ValueError('concrete source/diff drift')
        receipt.update({'status': 'passed-host-test-only-derivation', 'testsRun': 36,
            'allOwnedBuildAndExtractionScratchAbsent': True, 'sourceUnchanged': True,
            'transformedRunnerSHA256': hashlib.sha256(source.encode()).hexdigest(),
            'wrapperSHA256': sha(HERE / 'run.py'), 'runnerContractSHA256': sha(adapter.CONTRACT)})
    except BaseException as failure:
        receipt.update({'status': 'failed-host-verification-retained', 'failure': repr(failure)})
        raise
    finally:
        receipt['finishedUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save(review / 'receipt.json', receipt)
    roots = paths + [HERE / 'candidate-1', HERE / 'runner-source', review]
    roots.extend(sorted(p for p in HERE.iterdir() if p.name.startswith('host-tests-')))
    roots.extend(sorted(p for p in HERE.iterdir() if p.name.startswith('host-review-') and p != review))
    files = {}
    for root in roots:
        for p in ([root] if root.is_file() else sorted(p for p in root.rglob('*') if p.is_file())):
            if p.is_symlink():
                raise ValueError('symlink in packet')
            files[str(p.relative_to(ROOT))] = {'bytes': p.stat().st_size, 'sha256': sha(p)}
    save(HERE / 'packet-seal.json', {'schema': 1, 'files': files,
        'membershipRoots': [str(p.relative_to(ROOT)) for p in roots],
        'fileTreeSHA256': hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
        'immutableReferences': adapter.BINDINGS, 'runnerContractSHA256': sha(adapter.CONTRACT),
        'transformedRunnerSHA256': hashlib.sha256(source.encode()).hexdigest(),
        'nativeRuntime': 'NOT RUN by derivation lane', 'physicalTargetsQueried': False,
        'futureRuntimeOutputs': 'root-owned runtime-N directories excluded; retain each independently'})
    print(json.dumps({'status': receipt['status'], 'testsRun': 36, 'files': len(files),
        'transformedRunnerSHA256': receipt['transformedRunnerSHA256'], 'nativeInstancesStarted': 0}, sort_keys=True))


if __name__ == '__main__':
    main()
