#!/usr/bin/env python3
"""Seal or verify this narrow review without selected composition/native work."""
import datetime
import json
from pathlib import Path
import sys

import run_review as r


def checks():
    source = r.verify_inputs()
    r.require(source == json.loads((r.BASE / 'source-verification.json').read_bytes()), 'Source review inputs changed')
    host = json.loads((r.BASE / 'host-attempt/receipt.json').read_bytes())
    command = json.loads((r.BASE / 'command-receipt.json').read_bytes())
    cleanup = json.loads((r.BASE / 'cleanup.json').read_bytes())
    baseline = json.loads((r.BASE / 'baseline-reconciliation.json').read_bytes())
    r.require(host['passed'] and host['testsRun'] == 19 and host['skipped'] == 0
              and host['errors'] == host['failures'] == 0 and host['acceptedInputsAndPacketUnchanged'],
              'Independent host result differs')
    r.require(command['reviewSource'] == r.row(r.BASE / 'run_review.py'), 'Executed review source changed')
    r.require(command['exitCode'] == 0 and not command['timedOut'] and not command['signals']
              and command['ownedProcessGroup']['state'] == 'absent', 'Review command not terminal clean')
    for name, stream in command['streams'].items():
        raw = (r.BASE / (name + '.log')).read_bytes()
        r.require(stream['eof'] and not stream['readerFailed'] and len(raw) == stream['bytes']
                  and r.sha(raw) == stream['sha256'], 'Complete review stream differs')
    r.require(cleanup['ownedScratchAbsent'] and cleanup['ownedProcessGroupAbsent']
              and cleanup['producerAndDirectInputBindingsUnchanged']
              and not Path(cleanup['ownedScratch']).exists(), 'Review cleanup incomplete')
    for name, row in baseline['inputBindings'].items():
        r.require(r.row(r.ROOT / name) == row, 'Reconciled baseline input changed')
    for name, row in baseline['actualV5RetainedApplication'].items():
        r.require(r.row(r.ROOT / name) == row, 'Actual V5 retained app changed')
    r.require(baseline['script'] == r.row(r.BASE / 'verify_baseline.py')
              and baseline['supportScript'] == r.row(r.BASE / 'run_review.py')
              and baseline['actualV5AndFreshV6All13ApplicationRowsMatch']
              and baseline['originalV1AndFreshV6All13ApplicationRowsMatch']
              and baseline['applicationAndLibrarySourceFilesUnchangedFromOriginalV1'] == 34,
              'Baseline reconciliation incomplete')
    r.require(not list(r.BASE.glob('review-owned-*')), 'Owned scratch remains')
    return source, host, baseline


def inventory():
    paths = [r.ROOT / 'docs/apple-settings-instrumented-runtime-review.md',
             *sorted(r.BASE.rglob('*'))]
    return {str(p.relative_to(r.ROOT)): r.row(p) for p in paths
            if p.is_file() and p.name not in {'handoff.json', 'handoff.sha256'}}


def main(action):
    source, host, baseline = checks()
    target = r.BASE / 'handoff.json'
    if action == 'seal':
        r.require(not target.exists(), 'Preserve first review seal')
        review = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'status': 'source-and-host-packaging-accepted', 'blockingFindings': [],
                  'producerHandoffSHA256': r.EXPECTED_HANDOFF, 'producerMembersVerified': 61,
                  'packetSHA256': r.EXPECTED_PACKET, 'buildHandoffSHA256': r.EXPECTED_BUILD,
                  'sourceTreeSHA256': source['sourceTreeSHA256'],
                  'runtimeSourceTreeSHA256': source['runtimeSourceTreeSHA256'],
                  'productArchiveSHA256': source['productArchiveSHA256'],
                  'hostTests': {'original': 14, 'additionalIndependent': 5, 'passed': 19,
                                'failures': 0, 'errors': 0, 'skipped': 0},
                  'exactSyntheticDispatchRecorderCalls': len(host['syntheticDispatchRecorderCalls']),
                  'strictImporterOracleDeadlinesCleanupUnchanged': True,
                  'actualV5AndFreshV6All13ApplicationRowsMatch': True,
                  'applicationAndLibrarySourceFilesUnchangedFromOriginalV1': 34,
                  'staleTemplateObservation': {'resolved': True,
                      'differentProductPaths': list(baseline['staleTemplateNineApplicationProductDifferences']),
                      'meaning': 'Template-build source prefers toggle, but actual V5 dispatch overrides its products with original V1 referenceButton app. Fresh V6 reuses the exact actual V5 application.',
                      'receipt': 'baseline-reconciliation.json'},
                  'oneLaterRootSelectedBoundedAttemptMayBePrepared': True,
                  'nativeSelectionStillRequired': True,
                  'rootSelectionConditions': ['Exact reviewed packet and out-of-band selection hash',
                      'Fresh schema-6 root selection within five minutes, pinned Xcode and exact argv',
                      'Pre-creation baseline and one owned V6 simulator; no reuse of an attempt marker',
                      'Unchanged strict official importer/oracle and all five independent cleanup checks'],
                  'nativeExecuted': False, 'nativeSelected': False, 'compilerExecuted': False,
                  'deviceQueries': 0, 'listenersStarted': 0, 'uiOrCaptureExecuted': False,
                  'gitOrLiveServiceStateUsed': False, 'excludedFrozenLanesReadImportedOrExecuted': False,
                  'physicalPhones': 'disconnected-deferred', 'settingsPreconditionPassed': False,
                  'nativeKeyboardQualified': False, 'fieldLogDogfoodQualified': False, 'gaAccepted': False,
                  'ownedScratchAbsent': True, 'ownedProcessGroupAbsent': True,
                  'limitations': ['Prior V5 Settings failure and skipped Tab remain failed native evidence',
                      'Host controls do not qualify future simulator behavior, physical devices, full matrix, signed delivery, store, customer or operational gates']}
        (r.BASE / 'review.json').write_bytes(r.stable(review))
        members = inventory()
        handoff = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   'status': review['status'], 'packetSHA256': r.EXPECTED_PACKET,
                   'members': members, 'memberTreeSHA256': r.sha(r.stable(members)),
                   'nativeSelected': False, 'nativeExecuted': False, 'gaAccepted': False}
        target.write_bytes(r.stable(handoff))
        (r.BASE / 'handoff.sha256').write_text(r.sha(target.read_bytes()) + '  handoff.json\n')
    else:
        handoff = json.loads(target.read_bytes())
        r.require(handoff['members'] == inventory()
                  and handoff['memberTreeSHA256'] == r.sha(r.stable(handoff['members'])), 'Review inventory changed')
    print(json.dumps({'handoffSHA256': r.sha(target.read_bytes()), 'members': len(handoff['members']),
                      'packetSHA256': r.EXPECTED_PACKET, 'status': handoff['status'], 'nativeSelected': False}))


if __name__ == '__main__':
    r.require(len(sys.argv) == 2 and sys.argv[1] in {'seal', 'verify'}, 'seal or verify required')
    main(sys.argv[1])
