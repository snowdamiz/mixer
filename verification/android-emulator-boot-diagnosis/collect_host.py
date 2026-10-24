#!/usr/bin/env python3
"""Collect host-only probe guard evidence; never pass the native dispatch flag."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = HERE / 'host-review-1'
    out.mkdir()
    names = ('boot_probe.py', 'test_boot_probe.py', 'probe-contract.json', 'official-sources.json', 'collect_host.py')
    bindings = {name: sha(HERE / name) for name in names}
    commands = []
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    for name, argv in (
        ('source-revision', ['git', 'rev-parse', 'HEAD']),
        ('python-version', [sys.executable, '--version']),
        ('git-version', ['git', '--version']),
        ('host-guards', [sys.executable, '-m', 'unittest', 'discover', '-s',
                         'verification/android-emulator-boot-diagnosis', '-p', 'test_boot_probe.py', '-v']),
        ('probe-help', [sys.executable, 'verification/android-emulator-boot-diagnosis/boot_probe.py', '--help']),
    ):
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        result = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, timeout=30)
        data = result.stdout + result.stderr
        path = out / (name + '.log')
        path.write_bytes(data)
        commands.append({'argv': argv, 'cwd': str(ROOT), 'startedUTC': started,
                         'finishedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                         'exitCode': result.returncode, 'output': path.name, 'outputSHA256': sha(path)})
        assert result.returncode == 0, name
    assert bindings == {name: sha(HERE / name) for name in names}
    result = {'schema': 1, 'status': 'passed-host-only-guards', 'tests': 15,
              'bindings': bindings, 'commands': commands, 'nativeLaunches': 0,
              'targetDiscovery': False, 'physicalTargetsQueried': False,
              'scope': 'Injected host lifecycle/identity/cleanup guard fixtures; no boot or app acceptance'}
    (out / 'receipt.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': result['status'], 'tests': 15, 'runnerSHA256': bindings['boot_probe.py'],
                      'contractSHA256': bindings['probe-contract.json'], 'receipt': str(out / 'receipt.json')}))


if __name__ == '__main__':
    main()
