#!/usr/bin/env python3
"""Run only host source/archive controls and pure unchanged oracle replay."""
import datetime
import json
import platform
import sys
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout

import prepare


def main():
    started = time.monotonic()
    verified = prepare.verify()
    output = prepare.BASE / 'host-tests.stdout.log'
    error = prepare.BASE / 'host-tests.stderr.log'
    prepare.require(not output.exists() and not error.exists(), 'Preserve previous host attempt')
    with output.open('w') as stdout, error.open('w') as stderr, redirect_stdout(stdout), redirect_stderr(stderr):
        import test_reference
        result = unittest.TextTestRunner(stream=stderr, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_reference))
    owned = {name: prepare.row(prepare.BASE / name) for name in ['prepare.py','reference_contract.py','test_reference.py','verify_host.py','build.py']}
    cleanup = {'temporaryOracleAndArchiveDirectoriesAbsent': not any(path.is_dir() and path.name.startswith(('pure-oracle-', 'archive-control-', 'corrupt-control-')) for path in prepare.BASE.iterdir()),
               'nativeInstancesCreatedOrQueried': 0, 'servicesStarted': 0, 'otherProjectsTouched': False}
    receipt = {'schema': 'mixer.apple-focus-reference-host-receipt.1', 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command': [sys.executable, '-B', str(prepare.BASE / 'verify_host.py')], 'cwd': str(prepare.ROOT),
        'python': sys.version, 'pythonExecutable': str(prepare.Path(sys.executable).resolve()), 'platform': platform.platform(),
        'elapsedSeconds': time.monotonic() - started, **verified, 'testsRun': result.testsRun,
        'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped), 'passed': result.wasSuccessful(),
        'ownedSources': owned, 'ownedSourceTreeSHA256': prepare.sha(prepare.stable(owned)),
        'outputs': {path.name: prepare.row(path) for path in [output,error]}, 'sourceArchiveUnchanged': prepare.verify() == verified,
        'sourceRevisionLabel': json.loads((prepare.BASE / 'prepared.json').read_bytes())['sourceRevisionLabel'],
        'scope': 'Host controls and synthetic pure-oracle controls only; not native focus evidence.',
        'originalFailureReplay': 'Complete unchanged verdict; sole false predicate actualNativeFocusTraversal',
        'cleanup': cleanup, 'runtimeSelected': False, 'nativeExecuted': False, 'physicalPhones': 'disconnected-deferred', 'gaAccepted': False}
    (prepare.BASE / 'host-receipt.json').write_bytes(prepare.stable(receipt))
    print(f"{'PASS' if result.wasSuccessful() else 'FAIL'}: {result.testsRun} host controls; {len(result.failures)} failures; {len(result.errors)} errors")
    if not result.wasSuccessful(): raise SystemExit(1)


if __name__ == '__main__': main()
