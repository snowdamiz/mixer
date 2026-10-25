#!/usr/bin/env python3
"""Record only host controls; no native process, inventory, service, UI or capture."""
import datetime
import io
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
    require = prepare.require
    require(not output.exists() and not error.exists() and not (prepare.BASE / 'host-cases').exists(), 'Preserve previous host evidence')
    with output.open('w') as stdout, error.open('w') as stderr, redirect_stdout(stdout), redirect_stderr(stderr):
        import test_join
        result = unittest.TextTestRunner(stream=stderr, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_join))
    receipt = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command': [sys.executable, '-B', str(prepare.BASE / 'verify_host.py')], 'cwd': str(prepare.ROOT),
        'python': sys.version, 'pythonExecutable': str(prepare.Path(sys.executable).resolve()), 'platform': platform.platform(),
        'elapsedSeconds': time.monotonic() - started, 'packetSHA256': verified['packetSHA256'],
        'testsRun': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped),
        'passed': result.wasSuccessful(), 'outputs': {p.name: prepare.file_row(p) for p in [output, error]},
        'hostCaseEvidence': prepare.tree(prepare.BASE / 'host-cases', strict_directories=False),
        'sourceAndCompiledProductsUnchanged': prepare.verify() == verified,
        'nativeExecuted': False, 'nativeInstancesQueried': False, 'serviceStarted': False,
        'scope': 'Executable selected-module imports, mocked native argv/lifecycle boundaries, exact archive controls and one harmless owned Python subprocess timeout; no simulator/device calls.',
        'runtimeSelected': False, 'physicalPhones': 'disconnected-deferred', 'gaAccepted': False,
        'limitations': ['No simulator or XCTest runtime behavior qualified.', 'Historical first-Tab and Xcode finalization failures remain unresolved.',
                        'Full six-case, comparator, carrier, signing, store, FieldLog, operational and GA acceptance remain pending.']}
    prepare.save(prepare.BASE / 'host-receipt.json', receipt)
    print(f"{'PASS' if result.wasSuccessful() else 'FAIL'}: {result.testsRun} host controls; {len(result.failures)} failures, {len(result.errors)} errors; zero native commands")
    if not result.wasSuccessful(): raise SystemExit(1)


if __name__ == '__main__': main()
