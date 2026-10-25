#!/usr/bin/env python3
"""Freeze the classifier-only repair and verify immutable v1/reviewer history."""
import argparse
import datetime
import difflib
import json
import sys

import prepare


def observed(attempt):
    history = prepare.verify_history()
    verified = prepare.verify()
    base = prepare.BASE / f'host-attempt-{attempt}'
    receipt = json.loads((base / 'receipt.json').read_bytes())
    prepare.require(receipt['passed'] is True and (receipt['testsRun'], receipt['failures'], receipt['errors'], receipt['skipped']) == (34, 0, 0, 0),
                    'All retained and regression host controls must pass')
    prepare.require(receipt['history'] == history and receipt['reusedSource'] == verified, 'Frozen input identities changed')
    prepare.require(all(prepare.row(prepare.BASE / name) == item for name, item in receipt['ownedSources'].items()), 'Tested v2 source changed')
    prepare.require(all(prepare.row(base / name) == item for name, item in receipt['outputs'].items()), 'Host evidence changed')
    regressions = json.loads((base / 'regression-outcomes.json').read_bytes())['outcomes']
    prepare.require(len(regressions) == 8 and len({item['name'] for item in regressions}) == 8
                    and all(item['status'] == 'invalid-or-incomplete-evidence' and item['singleTabDiagnosticEvidencePassed'] is False for item in regressions),
                    'All eight original counterexamples must be rejected')
    for filename, patchname in [('reference_contract.py', 'classifier.patch'), ('test_reference.py', 'tests.patch')]:
        before = (prepare.SOURCES_BASE / filename).read_text()
        after = (prepare.BASE / filename).read_text()
        expected = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
            fromfile='a/verification/apple-focus-reference-diagnostic-v1/' + filename,
            tofile='b/verification/apple-focus-reference-diagnostic-v2/' + filename))
        prepare.require((prepare.BASE / patchname).read_text() == expected, 'Repair diff changed')
    prepare.require(receipt['cleanup']['temporaryOracleAndArchiveDirectoriesAbsent'] is True
                    and not any(path.is_dir() and path.name.startswith(('pure-oracle-', 'archive-control-', 'corrupt-control-')) for path in prepare.BASE.iterdir()),
                    'Unretired host scratch')
    paths = [path for path in sorted(prepare.BASE.rglob('*')) if path.is_file() and path.name != 'handoff.json']
    paths.append(prepare.ROOT / 'docs/apple-focus-reference-diagnostic-v2.md')
    members = {str(path.relative_to(prepare.ROOT)): prepare.row(path) for path in paths}
    return receipt, history, verified, members


def main(action, attempt):
    receipt, history, verified, members = observed(attempt)
    path = prepare.BASE / 'handoff.json'
    if action == 'freeze':
        prepare.require(not path.exists(), 'Preserve frozen v2 handoff')
        handoff = {'schema': 'mixer.apple-focus-reference-v2-frozen-handoff.1',
            'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'command': [sys.executable, '-B', str(prepare.BASE / 'freeze.py'), 'freeze', '--attempt', str(attempt)],
            'cwd': str(prepare.ROOT), 'python': sys.version, 'sourceRevisionLabel': receipt['sourceRevisionLabel'],
            'history': history, 'reusedSource': verified, 'sourceAndProductReuse': receipt['sourceAndProductReuse'],
            'members': members, 'memberTreeSHA256': prepare.sha(prepare.stable(members)),
            'testsRun': 34, 'retainedV1Controls': 26, 'newRegressionControls': 8, 'hostAttempt': attempt,
            'repairedFindings': ['type-preserving-complete-verdict-replay', 'strict-optional-reporting-integers', 'structured-numeric-overflow-rejection'],
            'historicalV1IndependentReviewPassed': False, 'v2IndependentReviewPending': True,
            'scope': 'Classifier consistency repair only; selected-run provenance importer remains a separate prerequisite.',
            'selectedRunProvenanceImporterPresent': False, 'sourceOverlayChanged': False, 'compileRerun': False,
            'nativeExecuted': False, 'runtimeSelected': False, 'runnablePacketAssembled': False,
            'servicesStarted': 0, 'explicitSimulatorOrDeviceCommands': 0, 'uiOrCapturePerformed': False, 'gitMutationPerformed': False,
            'completeCaseSet': False, 'runPassed': False, 'fullSixCaseQualification': False, 'carrierAccepted': False,
            'physicalPhones': 'disconnected-deferred', 'gaAccepted': False, 'cleanup': receipt['cleanup']}
        path.write_bytes(prepare.stable(handoff))
    else:
        handoff = json.loads(path.read_bytes())
        prepare.require(handoff['members'] == members and handoff['memberTreeSHA256'] == prepare.sha(prepare.stable(members)), 'Frozen v2 member changed')
        prepare.require(handoff['history'] == history and handoff['reusedSource'] == verified and handoff['hostAttempt'] == attempt,
                        'Frozen v2 history changed')
    print(json.dumps({'passed': True, 'handoffSHA256': prepare.row(path)['sha256'], 'members': len(members),
        'testsRun': 34, 'regressionsRejected': 8, 'v1AndReviewHistoryUnchanged': True, 'nativeExecuted': False,
        'runtimeSelected': False, 'compileRerun': False}, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['freeze', 'verify'])
    parser.add_argument('--attempt', type=int, default=1)
    args = parser.parse_args()
    main(args.action, args.attempt)
