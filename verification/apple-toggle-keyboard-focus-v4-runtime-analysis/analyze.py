#!/usr/bin/env python3
"""Offline retained-evidence analysis only; no compiler/native/UI operations."""
import datetime
import hashlib
import importlib.util
import json
import pathlib
import plistlib
import subprocess
import sys
import time

B = pathlib.Path(__file__).resolve().parent
ROOT = B.parents[1]
V4 = B.parent / 'apple-toggle-keyboard-focus-v4'
RUNTIME = V4 / 'runtime'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_bytes())
if sys.argv[1:] == ['--check']:
    seal = read(B / 'analysis-seal.json')
    assert all(sha(ROOT / name) == digest for name, digest in seal['files'].items()), 'Analysis seal changed'
    report = read(B / 'analysis.json')
    assert all(sha(ROOT / name) == digest for name, digest in report['inputs'].items()), 'Retained runtime/source input changed'
    result = subprocess.run([sys.executable, '-B', str(V4 / 'replay.py')], cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0 and json.loads(result.stdout)['settingsDiagnostic'] == read(RUNTIME / 'runtime-verdict.json')['settingsDiagnostic']
    print(json.dumps({'status': 'FAILED_DIAGNOSTIC_OFFLINE_ANALYSIS_ONLY', 'analysisSealVerified': True, 'replayMatchesRuntimeExactly': True, 'nativeExecuted': False, 'V5Implemented': False}))
    raise SystemExit(0)
assert not (B / 'analysis-seal.json').exists(), 'Sealed analysis is immutable; use --check'
files = [p for p in RUNTIME.rglob('*') if p.is_file()]
files += [V4 / 'packet-seal.json', B.parent / 'apple-toggle-keyboard-focus-v4-root-review/selection.json', B.parent / 'apple-toggle-keyboard-focus-v4-root-review/runtime-review.json', V4 / 'settings_telemetry.py', V4 / 'harness/UITests/ToggleUITests.swift']
before = {str(p.relative_to(ROOT)): sha(p) for p in sorted(files)}
assert sha(files[-3]) == '8eb08e6e2e3767eeba2cf3191c75385db49813d25615f0ff77c5488323ee5f1b'
assert sha(V4 / 'packet-seal.json') == 'b2b5630c09f3fbe0e0567ff118e88e75ccb5277ea1e1637915c6b3066e9616e3'
verdict = read(RUNTIME / 'runtime-verdict.json')
life = read(RUNTIME / 'lifecycle.json')
argv = [sys.executable, '-B', str(V4 / 'replay.py')]
start = time.monotonic()
p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=60)
commands = [{'argv': argv, 'cwd': str(ROOT), 'pythonVersion': sys.version, 'exitCode': p.returncode, 'elapsedSeconds': time.monotonic() - start, 'stdout': p.stdout, 'stderr': p.stderr}]
assert p.returncode == 0
replayed = json.loads(p.stdout)
assert replayed['settingsDiagnostic'] == verdict['settingsDiagnostic']
(B / 'offline-replay.stdout').write_text(p.stdout)
(B / 'offline-replay.stderr').write_text(p.stderr)
journal = [read(p) for p in sorted((RUNTIME / 'captures').glob('0000-settings-*.json'))]
events = [v for v in journal if v['record']['kind'] != 'chunk']
timeline = [{'sequence': v['record'].get('sequence', 0), 'kind': v['record']['kind'], 'stage': v['record'].get('stage'), 'receivedUptime': v['receivedUptime'], 'receivedElapsedSeconds': v['receivedUptime'] - journal[0]['receivedUptime'], 'runnerUptime': v['record']['uptime'], 'runnerElapsedSeconds': v['record']['uptime'] - journal[0]['record']['uptime'], 'snapshot': v['record'].get('snapshot')} for v in events]
test = next(v for v in read(RUNTIME / 'commands.json') if 'test-without-building' in v.get('argv', []))
summary = read(RUNTIME / 'xctest-summary.json')
trees = {p.name: p.read_text() for p in sorted((RUNTIME / 'captures').glob('*.txt'))}
assert "identifier: 'com.apple.settings.accessibility', label: 'Accessibility'" in trees['settings-0002-ax.txt']
assert "identifier: 'KEYBOARDS', label: 'Keyboards & Typing'" in trees['settings-0010-ax.txt']
assert "StaticText" in trees['settings-0010-ax.txt'] and "{{0.0, 0.0}, {0.0, 0.0}}, label: 'Keyboards & Typing'" in trees['settings-0010-ax.txt']
spec = importlib.util.spec_from_file_location('immutable_v4_telemetry_probe', V4 / 'settings_telemetry.py')
t = importlib.util.module_from_spec(spec); spec.loader.exec_module(t)
search = events[2]['record']['snapshot']
opened = events[4]['record']['snapshot']
assert not t.expected_row(search, 0)
assert not t.absent_opened_row(opened)
candidate = dict(search, identifier='', label='Keyboards & Typing', elementType=48, hittable=False, frame=dict(x=0, y=0, width=0, height=0))
try:
    t.snapshot(candidate)
    raise AssertionError('Expected current strict geometry rejection')
except ValueError as error:
    assert str(error) == 'Attached Settings geometry'
probe = {'nativeObservedAnonymousSearchRowMatchesV4ExpectedRow': False, 'nativeObservedRetainedOldRowIsAbsentException': False, 'reconstructedOffscreenStaticText': candidate, 'reconstructedCandidateCurrentValidatorRejects': 'Attached Settings geometry', 'reconstructedCandidateIsActualRejectedRequest': False}
attachments = read(RUNTIME / 'attachments/manifest.json')
details = []
for item in attachments[0]['attachments']:
    path = RUNTIME / 'attachments' / item['exportedFileName']
    data = path.read_bytes()
    detail = {**item, 'bytes': len(data), 'sha256': sha(path)}
    if data.startswith(b'bplist00'):
        archive = plistlib.loads(data)
        objects = archive.get('$objects', [])
        detail.update(format='binary-plist-NSKeyedArchive', objects=len(objects), archivedClassNames=sorted({v['$classname'] for v in objects if isinstance(v, dict) and '$classname' in v}))
    else:
        detail['format'] = 'QuickTime/MP4 recording; no frame-content inference in this analysis'
    details.append(detail)
outer = pathlib.Path('/tmp/mixer-keyboard-v4-runtime.stderr')
if outer.is_file():
    (B / 'outer-runtime.stderr').write_bytes(outer.read_bytes())
    commands.append({'operation': 'read-existing-root-outer-log', 'path': str(outer), 'sha256': sha(outer), 'bytes': outer.stat().st_size})
report = {'schema': 'mixer.apple-toggle.keyboard-v4-runtime-analysis.1', 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': 'FAILED_DIAGNOSTIC_OFFLINE_ANALYSIS_ONLY', 'runtimeSelectionSourceRevisionContext': read(B.parent / 'apple-toggle-keyboard-focus-v4-root-review/selection.json')['sourceRevisionContext'], 'inputs': before, 'offlineReplayExitCode': p.returncode, 'replayMatchesRuntimeExactly': True, 'durableRecords': len(journal), 'timeline': timeline, 'lastDurableHostElapsedSeconds': journal[-1]['receivedUptime'] - journal[0]['receivedUptime'], 'diagnosticSecondsCap': t.MAX_DURATION, 'durableRequests': verdict['settingsDiagnostic']['requests'], 'requestsCap': t.MAX_REQUESTS, 'AXFiles': len(trees), 'AXBytes': sum(len(s.encode()) for s in trees.values()), 'PNGFiles': len(list((RUNTIME / 'captures').glob('*.png'))), 'officialSummary': summary, 'xcodebuildExitCode': test['exitCode'], 'xcodebuildElapsedSeconds': test['elapsedSeconds'], 'officialAttachmentExportPassed': verdict['attachmentExport']['passed'], 'exportedAttachments': details, 'officialRecordingFramesInspected': False, 'bridgeFailures': verdict['bridgeFailures'], 'probeCurrentValidatorOnly': probe, 'actualRejectedRequestBodyRetained': False, 'actualBudgetCauseIs29SecondExhaustionProven': False, 'windowAnchored': verdict['settingsDiagnostic']['anchorUptime'] is not None, 'applicationCasesExecuted': verdict['applicationCasesExecuted'], 'sixApplicationCasesUnrun': len(verdict['dependentCasesUnrun']) == 6, 'cleanup': {key: life[key] for key in ['cleanedUp', 'cleanupResults', 'ownedDeviceAbsent', 'ephemeralWorkspaceAbsent', 'baselineStatesPreserved']}, 'ownedSimulator': life['ownedSimulator'], 'nativeExecutedByAnalyst': False, 'compilerInvoked': False, 'V5Implemented': False, 'boundsOrQualificationChanged': False, 'gaAccepted': False}
assert len(journal) == 22 and verdict['xcodebuildExitCode'] == 65 and not report['windowAnchored'] and report['sixApplicationCasesUnrun']
assert before == {str(p.relative_to(ROOT)): sha(p) for p in sorted(files)}, 'Runtime evidence changed'
(B / 'analysis.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
(B / 'commands.json').write_text(json.dumps(commands, indent=2, sort_keys=True) + '\n')
print(json.dumps({'status': report['status'], 'replayMatchesRuntimeExactly': True, 'durableRecords': len(journal), 'AXFiles': len(trees), 'PNGFiles': report['PNGFiles'], 'testResult': summary['result'], 'bridgeFailure': verdict['bridgeFailures'][0]['reason'], 'nativeExecutedByAnalyst': False}))
