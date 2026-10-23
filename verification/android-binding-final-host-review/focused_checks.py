#!/usr/bin/env python3
"""Focused real-checkout provenance and receipt-bound host replays."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUNNER = ROOT / 'scripts/ci/check-android-binding.py'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
SPEC = importlib.util.spec_from_file_location('android_binding_runner_independent', RUNNER)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
commands = []
checks = []

def run(name, argv, cwd=ROOT, timeout=120):
    result = subprocess.run([str(v) for v in argv], cwd=cwd, capture_output=True, timeout=timeout)
    log = HERE / (name + '.log')
    log.write_bytes(result.stdout + result.stderr)
    commands.append({'name': name, 'argv': [str(v) for v in argv], 'cwd': str(cwd),
                     'exit': result.returncode, 'log': str(log.relative_to(ROOT)), 'sha256': sha(log)})
    if result.returncode:
        raise RuntimeError(f'{name}: exit {result.returncode}')
    return result.stdout.decode()

def actual_git(label, argv):
    result = subprocess.run([str(v) for v in argv], capture_output=True, check=True, text=True)
    return result.stdout

def rejects(name, action, contains):
    try:
        action()
    except RuntimeError as error:
        if contains not in str(error):
            raise
        checks.append({'name': name, 'result': 'rejected', 'reason': str(error)})
    else:
        raise RuntimeError('Accepted invalid input: ' + name)

def main():
    run('python-version', [sys.executable, '--version'])
    run('swift-version', ['xcrun', 'swift', '--version'])
    run('clang-version', ['xcrun', 'clang', '--version'])
    run('ci-tests', [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'scripts/ci/tests', '-v'])
    run('optimized-ci-tests', [sys.executable, '-B', '-O', '-m', 'unittest', 'discover', '-s', 'scripts/ci/tests', '-v'])
    with tempfile.TemporaryDirectory(prefix='real-git-', dir=HERE) as temp:
        temporary = Path(temp)
        checkout = temporary / 'build/checkouts/example'
        checkout.mkdir(parents=True)
        source = temporary / 'source'
        source.mkdir()
        for argv in [
            ['git', 'init', '-q', checkout],
            ['git', '-C', checkout, 'config', 'user.name', 'Independent fixture'],
            ['git', '-C', checkout, 'config', 'user.email', 'independent@example.invalid'],
        ]:
            subprocess.run([str(v) for v in argv], check=True, capture_output=True)
        tracked = checkout / 'Owned.swift'
        tracked.write_text('let fixture = 1\n')
        subprocess.run(['git', '-C', str(checkout), 'add', 'Owned.swift'], check=True)
        subprocess.run(['git', '-C', str(checkout), 'commit', '-qm', 'Independent provenance fixture'], check=True)
        revision = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip()
        pin = {'identity': 'example', 'kind': 'remoteSourceControl',
               'location': 'https://example.invalid/independent.git',
               'state': {'revision': revision, 'version': '1.0.0'}}
        dep = {'packageRef': {k: pin[k] for k in ['identity', 'kind', 'location']},
               'state': {'checkoutState': pin['state']}, 'subpath': 'example'}
        (source / 'Package.resolved').write_text(json.dumps({'pins': [pin]}))
        (temporary / 'build/workspace-state.json').write_text(json.dumps({'object': {'dependencies': [dep]}}))
        action = lambda: MODULE.dependency_checkouts(source, temporary / 'build', actual_git)
        checks.append({'name': 'actual_clean_pinned_git_checkout', 'result': action()})
        tracked.write_text('let fixture = 2\n')
        rejects('actual_tracked_modification', action, 'checkout is dirty')
        tracked.write_text('let fixture = 1\n')
        untracked = checkout / 'Extra.swift'
        untracked.write_text('let added = 3\n')
        rejects('actual_untracked_source', action, 'checkout is dirty')
        untracked.unlink()
        subprocess.run(['git', '-C', str(checkout), 'commit', '--allow-empty', '-qm', 'Wrong actual HEAD'], check=True)
        rejects('actual_HEAD_disagrees_with_locked_workspace_metadata', action, 'checkout revision changed')
    executions = []
    for mode in ['debug', 'release', 'tsan']:
        parent = ROOT / f'verification/android-binding-ci/qualified-1/{mode}/receipt.json'
        receipt = json.loads(parent.read_text())
        executable = Path(receipt['executable']['path'])
        if sha(executable) != receipt['executable']['sha256']:
            raise RuntimeError('Changed receipt-bound host executable')
        for scenario in ['single-join', 'late-progress-fault', 'cleanup-wrong-lifetime']:
            name = mode + '-' + scenario
            output = run(name, [executable, scenario], timeout=180)
            if 'HOST_PASS ' + scenario not in output.splitlines():
                raise RuntimeError('Missing exact host marker: ' + name)
            executions.append({'mode': mode, 'scenario': scenario, 'parent_receipt': str(parent.relative_to(ROOT)),
                               'parent_receipt_sha256': sha(parent), 'executable_sha256': sha(executable)})
    result = {'observed_utc': datetime.now(timezone.utc).isoformat(), 'status': 'passed',
              'python': platform.python_version(), 'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'script_sha256': sha(__file__), 'runner_sha256': sha(RUNNER), 'commands': commands,
              'provenance_checks': checks, 'executions': executions,
              'scope': 'Nine new executions of already receipt-bound fresh host binaries, existing CI tests under normal/optimized Python, and independent real temporary Git checkout failure probes. No new full matrix, device execution, or build qualification inferred.'}
    (HERE / 'focused-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': 'passed', 'provenance_checks': len(checks), 'host_replays': len(executions), 'commands': len(commands)}))

if __name__ == '__main__':
    main()
