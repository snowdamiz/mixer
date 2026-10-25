#!/usr/bin/env python3
"""Run only local diagnostic controls and retain a compact honest receipt."""
import datetime
import hashlib
import io
import json
import pathlib
import sys
import unittest

import prepare
import test_diagnostic


class Results(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passed_names = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.passed_names.append(test.id())


def main():
    # Deterministic preparation first; original sources are never written.
    patch, manifest_bytes = prepare.artifacts()
    (prepare.BASE / 'source.patch').write_bytes(patch)
    (prepare.BASE / 'prepared.json').write_bytes(manifest_bytes)
    output = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromModule(test_diagnostic)
    result = unittest.TextTestRunner(stream=output, verbosity=2, resultclass=Results).run(suite)
    transcript = output.getvalue()
    (prepare.BASE / 'host-tests.stdout.txt').write_text(transcript)
    (prepare.BASE / 'host-tests.stderr.txt').write_text('')
    manifest = json.loads(manifest_bytes)
    retained = ['prepare.py', 'focus_diagnostic.py', 'test_diagnostic.py', 'run_host_controls.py',
                'snippets/focus-context.swift', 'snippets/ax.swift', 'source.patch', 'prepared.json',
                'host-tests.stdout.txt', 'host-tests.stderr.txt']
    file_rows = {name: {'sha256': hashlib.sha256((prepare.BASE / name).read_bytes()).hexdigest(),
                        'bytes': (prepare.BASE / name).stat().st_size} for name in retained}
    receipt = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'status': 'passed-host-controls-only' if result.wasSuccessful() else 'failed-host-controls',
               'command': '/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-toggle-keyboard-focus-diagnostic-v1/run_host_controls.py',
               'argv': sys.argv, 'tool': {'pythonVersion': sys.version, 'executable': sys.executable},
               'cwd': str(pathlib.Path.cwd()), 'testsRun': result.testsRun,
               'passed': result.passed_names, 'failureCount': len(result.failures), 'errorCount': len(result.errors),
               'skippedCount': len(result.skipped), 'inheritedSourceRevisionLabel': prepare.INHERITED_REVIEW_REVISION,
               'sourceRevisionQueried': False, 'inputTreeSHA256': manifest['inputTreeSHA256'],
               'preparedSourceTreeSHA256': manifest['preparedSourceTreeSHA256'],
               'retainedFileTreeSHA256': hashlib.sha256(prepare.stable_json(file_rows)).hexdigest(),
               'files': file_rows, 'sourceBindings': manifest['immutableInputs'],
               'evidenceKind': 'offline data verification, diagnostic adapter tests, independent host models and in-memory patch application',
               'selectedRuntimeOrAuthorityImported': False, 'compilerOrNativeExecuted': False,
               'commandFinalizationInstrumentation': 'pending-separate-slice',
               'originalV3EvidenceWritten': False, 'diagnosticsGrantAcceptance': False,
               'limitations': manifest['limitations']}
    (prepare.BASE / 'receipt.json').write_bytes(prepare.stable_json(receipt))
    print(transcript, end='')
    print('Receipt: ' + str(prepare.BASE / 'receipt.json'))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
