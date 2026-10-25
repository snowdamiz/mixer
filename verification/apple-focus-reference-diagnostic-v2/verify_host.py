#!/usr/bin/env python3
"""Preserve v1; run retained host controls and eight v2 classifier regressions only."""
import argparse
import datetime
import json
import platform
import sys
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout

import prepare


def main(attempt):
    started = time.monotonic()
    history_before = prepare.verify_history()
    verified = prepare.verify()
    prepare.require(type(attempt) is int and attempt > 0, 'Positive host attempt required')
    base = prepare.BASE / f'host-attempt-{attempt}'
    prepare.require(not base.exists(), 'Preserve previous host attempt')
    base.mkdir()
    old_tests = (prepare.SOURCES_BASE / 'test_reference.py').read_text().split("\n\nif __name__ == '__main__': unittest.main()", 1)[0]
    adapted_tests = (prepare.BASE / 'test_reference.py').read_text().split('\n    def reject_frozen_counterexample', 1)[0]
    prepare.require(adapted_tests.rstrip() == old_tests.replace("prepare.BASE / 'accepted-sources.tar.gz'", "prepare.SOURCES_BASE / 'accepted-sources.tar.gz'").rstrip(),
                    'Retained 26 controls changed beyond read-only archive path adaptation')
    output, error = base / 'stdout.log', base / 'stderr.log'
    with output.open('w') as stdout, error.open('w') as stderr, redirect_stdout(stdout), redirect_stderr(stderr):
        import test_reference
        result = unittest.TextTestRunner(stream=stderr, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_reference))
    regressions = getattr(test_reference.ReferenceControls, 'regression_outcomes', [])
    regression_path = base / 'regression-outcomes.json'
    regression_path.write_bytes(prepare.stable({'schema': 'mixer.apple-focus-reference-v2-regressions.1',
        'syntheticOnly': True, 'counterexampleSource': prepare.row(prepare.REVIEW / 'counterexamples.json'), 'outcomes': regressions}))
    history_after = prepare.verify_history()
    source_after = prepare.verify()
    owned = {name: prepare.row(prepare.BASE / name) for name in ['prepare.py','reference_contract.py','test_reference.py','verify_host.py','freeze.py']}
    cleanup = {'temporaryOracleAndArchiveDirectoriesAbsent': not any(path.is_dir() and path.name.startswith(('pure-oracle-', 'archive-control-', 'corrupt-control-')) for path in prepare.BASE.iterdir()),
               'v1AndReviewFrozenMembersUnchanged': history_before == history_after,
               'nativeInstancesCreatedOrQueried': 0, 'servicesStarted': 0, 'otherProjectsTouched': False}
    compile_base = prepare.SOURCES_BASE / 'compile-attempt-1'
    compiled = json.loads((compile_base / 'receipt.json').read_bytes())
    receipt = {'schema': 'mixer.apple-focus-reference-v2-host-receipt.1', 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command': [sys.executable, '-B', str(prepare.BASE / 'verify_host.py'), '--attempt', str(attempt)],
        'cwd': str(prepare.ROOT), 'python': sys.version, 'pythonExecutable': str(prepare.Path(sys.executable).resolve()), 'platform': platform.platform(),
        'elapsedSeconds': time.monotonic() - started, 'history': history_after, 'reusedSource': verified,
        'sourceRevisionLabel': compiled['sourceRevisionLabel'], 'sourceRevisionMeaning': 'Inherited frozen label; no Git query.',
        'testsRun': result.testsRun, 'retainedV1Controls': 26, 'newRegressionControls': 8,
        'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped),
        'passed': result.wasSuccessful() and result.testsRun == 34 and len(regressions) == 8,
        'ownedSources': owned, 'ownedSourceTreeSHA256': prepare.sha(prepare.stable(owned)),
        'outputs': {path.name: prepare.row(path) for path in [output,error,regression_path]},
        'sourceAndProductReuse': {'prepared': prepare.row(prepare.SOURCES_BASE / 'prepared.json'),
            'derivativeSourceArchive': prepare.row(prepare.SOURCES_BASE / 'accepted-sources.tar.gz'),
            'productArchive': prepare.row(compile_base / 'products.tar.gz'), 'compileReceipt': prepare.row(compile_base / 'receipt.json'),
            'derivative39SourceTreeSHA256': compiled['sourceTreeSHA256'], 'productTreeSHA256': compiled['productTreeSHA256'],
            'sourceOverlayChanged': False, 'compileRerun': False, 'sourceUnchanged': source_after == verified},
        'originalFailureReplay': 'Complete unchanged authored-first verdict; sole false predicate actualNativeFocusTraversal',
        'scope': 'Pure classifier internal consistency only; selected-run provenance importer remains a separate prerequisite.',
        'selectedRunProvenanceImporterPresent': False, 'cleanup': cleanup,
        'nativeExecuted': False, 'runtimeSelected': False, 'compileRerun': False, 'servicesStarted': 0,
        'completeCaseSet': False, 'runPassed': False, 'fullSixCaseQualification': False, 'carrierAccepted': False,
        'physicalPhones': 'disconnected-deferred', 'gaAccepted': False}
    (base / 'receipt.json').write_bytes(prepare.stable(receipt))
    print(f"{'PASS' if receipt['passed'] else 'FAIL'}: {result.testsRun} host controls; {len(result.failures)} failures; {len(result.errors)} errors; {len(regressions)} regressions retained")
    if not receipt['passed']: raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', type=int, default=1)
    main(parser.parse_args().attempt)
