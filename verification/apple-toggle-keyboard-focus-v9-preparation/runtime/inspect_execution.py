#!/usr/bin/env python3
"""Inspect this one completed diagnostic's retained files; never native operations."""
import datetime
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_bytes())


def inspect():
    command = read(BASE / 'execution-command.json')
    preflight = read(BASE / 'execution-preflight.json')
    verdict = read(HERE / 'runtime-verdict.json')
    life = read(HERE / 'lifecycle.json')
    official = read(HERE / 'xctest-summary.json')
    tests = read(HERE / 'xctest-tests.json')
    commands = read(HERE / 'commands.json')
    settings = verdict['settingsDiagnostic']
    replay = read(HERE / 'offline-replay.stdout')
    assert command['exitCode'] == 1 and command['unchangedRetry'] is False
    assert verdict['xcodebuildExitCode'] == 0 and official['result'] == 'Passed'
    assert official['totalTestCount'] == official['passedTests'] == 1
    assert official['failedTests'] == official['skippedTests'] == 0
    assert tests['testNodes'][0]['result'] == 'Passed'
    assert verdict['diagnosticCompleted'] and verdict['setupEvidenceComplete']
    assert verdict['expectedDiagnosticQualificationBoundary']
    assert verdict['sessionFailureClassification'] == 'expected-diagnostic-only-inherited-qualification-boundary'
    assert verdict['bridgeFailures'] == verdict['persistenceWarnings'] == verdict['ancillaryFailures'] == []
    assert verdict['persistenceUncertainty'] is None
    assert replay['settingsDiagnostic'] == settings
    assert not settings['persistenceUncertain'] and not settings['persistenceRetirementPending']
    assert settings['terminationMarkers'] == ['terminate-before', 'terminate-after']
    assert settings['completionMarkers'] == ['test-case-finished', 'suite-finished', 'bundle-finished']
    assert settings['requests'] == 278 and settings['sequence'] == 277
    assert settings['routeTaps'] == [0, 1, 2] and settings['switchAction'] == 'tap'
    assert verdict['applicationCasesExecuted'] == verdict['actualNativeInputActions'] == 0
    assert not verdict['nativeKeyboardQualification'] and not verdict['carrierAccepted'] and not verdict['gaAccepted']
    assert not verdict['runPassed'] and not verdict['strictNativeVerdictsPassed']
    assert life['cleanedUp'] and life['ownedDeviceAbsent'] and life['ephemeralWorkspaceAbsent']
    assert life['baselineStatesPreserved'] and life['beforeFrontends'] == life['afterFrontends']
    assert all(x['passed'] for x in life['cleanupResults']) and len(life['cleanupResults']) == 5
    assert not pathlib.Path(life['ephemeralWorkspace']['path']).exists()
    flatten = lambda value: {d['udid']: dict(d, runtimeIdentifier=r) for r, group in value['devices'].items() for d in group}
    before, after = flatten(life['before']), flatten(life['after'])
    assert life['ownedSimulator'] not in before and life['ownedSimulator'] not in after
    assert before.keys() == after.keys()
    for key in before:
        for field in ['name', 'state', 'runtimeIdentifier', 'deviceTypeIdentifier']:
            assert before[key].get(field) == after[key].get(field)
    tests_run = [x for x in commands if 'test-without-building' in x.get('argv', [])]
    assert len(tests_run) == 1 and tests_run[0]['exitCode'] == 0
    assert not any(any(x in arg for x in ['build-for-testing', 'devicectl', 'idevice']) for item in commands for arg in item.get('argv', []))
    exports = [x for x in commands if x.get('argv', [])[1:4] == ['xcresulttool', 'export', 'attachments']]
    assert len(exports) == 1 and exports[0]['exitCode'] == 0
    export_failures = [x for x in commands if x['kind'] == 'attachment-export-failure']
    assert len(export_failures) == 1 and export_failures[0]['message'] == 'Fresh fixed attachment output required'
    assert not verdict['attachmentExport']['passed']
    wrapper = read(HERE / 'export-wrapper-inspection.json')
    assert wrapper['exportingCommandWrapperCount'] == 2
    attachments = {}
    for p in sorted((HERE / 'attachments').rglob('*')):
        assert not p.is_symlink()
        if p.is_file():
            attachments[str(p.relative_to(HERE))] = dict(bytes=p.stat().st_size, sha256=sha(p))
    assert len(attachments) == 12 and 'attachments/manifest.json' in attachments
    manifest = read(HERE / 'attachments/manifest.json')
    retained_names = {p.name for p in (HERE / 'attachments').iterdir() if p.is_file()}
    assert {a['exportedFileName'] for row in manifest for a in row['attachments']} == retained_names - {'manifest.json'}
    assert all(a['deviceId'] == life['ownedSimulator'] for row in manifest for a in row['attachments'])
    records = [read(p) for p in sorted((HERE / 'captures').glob('0000-settings-*.json'))]
    assert len(records) == settings['sequence'] + 1
    assert all(x['ownedSimulatorIdentity']['udid'] == life['ownedSimulator'] for x in records)
    start, end = records[0]['receivedUptime'], records[-1]['receivedUptime']
    assert 0 <= end - start <= 29
    uploaded = {}
    for slot, descriptor in settings['uploads'].items():
        p = HERE / 'captures' / (slot + ('.png' if slot.endswith('-png') else '.txt'))
        assert descriptor['complete'] and p.is_file() and not p.is_symlink()
        assert p.stat().st_size == descriptor['bytes'] and sha(p) == descriptor['sha256']
        uploaded[str(p.relative_to(HERE))] = dict(bytes=p.stat().st_size, sha256=sha(p))
    return dict(
        schema='mixer.apple-toggle.keyboard-v9-native-execution-inspection.1',
        observedUTC=datetime.datetime.now(datetime.UTC).isoformat(),
        inspectionCommand=['python3', '-B', str((HERE/'inspect_execution.py').relative_to(ROOT))],
        pythonVersion=sys.version, pythonExecutableSHA256=sha(pathlib.Path(sys.executable)),
        scope='One completed setup-only iOS simulator diagnostic; evidence-only offline inspection.',
        selectionSHA256=command['selectionSHA256'], producerSealSHA256=preflight['producerSealSHA256'],
        independentReviewSealSHA256=preflight['independentReviewSealSHA256'],
        sourceIdentity=preflight['sourceIdentity'], sourceRevisionContextLabelsOnly=command['sourceRevisionContextLabelsOnly'],
        nativeAttempts=1, xcodebuildExitCode=0, selectedCommandExitCode=1,
        selectedCommandExitClassification=verdict['sessionFailureClassification'],
        officialXCTestResult='Passed', officialXCTestPassed=1, officialXCTestFailed=0,
        diagnosticCompleted=True, setupEvidenceComplete=True, journalSummaryReplayExact=True,
        acceptedRequests=settings['requests'], finalCursor=settings['sequence'], journalRecords=len(records),
        hostDiagnosticSeconds=end-start, limitsUnchanged=dict(setupSeconds=29, perHTTPRequestSeconds=2, sessionSeconds=600, requestLimit=2500, eventLimit=100, uploadLimit=32, aggregateDecodedBytes=7000000),
        settingsRoute=['Accessibility', 'Keyboards & Typing', 'Full Keyboard Access'],
        switchAction='tap', enabledSampleSequences=settings['enabledWithinWindowSequences'],
        uploadedAXAndPNGFiles=uploaded, uploadedFileCount=len(uploaded), decodedBytes=settings['decodedBytesDeclared'],
        screenshotVisualInspection=dict(before='captures/settings-0047-png.png',after='captures/settings-0119-png.png',observed='Full Keyboard Access switch visibly off before tap and green/on after tap; after capture also shows focus outline.',scope='Supporting visual inspection only; does not qualify app keyboard behavior.'),
        officialAttachments=attachments, officialAttachmentExportCommandExitCode=0,
        originalAttachmentReceiptPassed=False, originalAttachmentReceiptPreserved=True,
        attachmentReceiptLimitation='Two inherited ExportingCommands wrappers run on the selected __main__ path. The first official export succeeded; the second rejected the existing fresh-only output directory and overwrote the supplementary receipt with failure. Official attachments, summary, tests, and durable AX/PNG are retained. No receipt or source was corrected.',
        rawXCResultBundleRetained=False, rawXCResultScope='The unchanged harness retained official summary/tests/attachments, then removed its ephemeral xcresult workspace during authorized cleanup.',
        cleanupOperations=life['cleanupResults'], ownedSimulator=life['ownedSimulator'], ownedSimulatorAbsent=True,
        capabilityWorkspaceAbsent=True, baselineSimulatorCount=len(before), baselineStatesPreserved=True,
        baselineFrontendIdentitiesPreserved=True, appAndRunnerRebuilt=False, unchangedRetry=False,
        nativeKeyboardQualification=False, applicationCasesExecuted=0, dependentCasesUnrun=verdict['dependentCasesUnrun'],
        carrierAccepted=False, gaAccepted=False, physicalPhones='disconnected-deferred',
        developmentEvidenceOnly=True, rootAcceptancePending=True,
    )


if __name__ == '__main__':
    result = inspect()
    output = HERE / 'execution-inspection.json'
    assert not output.exists(), 'Never overwrite an evidence receipt'
    output.write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps(dict(passed=True, diagnosticCompleted=True, setupEvidenceComplete=True,
                         acceptedRequests=result['acceptedRequests'], finalCursor=result['finalCursor'],
                         journalSummaryReplayExact=True, ownedSimulatorAbsent=True,
                         capabilityWorkspaceAbsent=True, originalAttachmentReceiptPassed=False,
                         nativeKeyboardQualification=False, gaAccepted=False), sort_keys=True))
