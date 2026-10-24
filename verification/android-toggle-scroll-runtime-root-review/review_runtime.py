import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RUN = ROOT / 'verification/android-toggle-scroll-failure-analysis/runtime/runtime-1'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
seal = read(RUN / 'artifact-seal.json')
assert {str(p.relative_to(RUN)) for p in RUN.rglob('*') if p.is_file()} == set(seal) | {'artifact-seal.json'}
for name, entry in seal.items():
    assert sha(RUN / name) == entry['sha256'] and (RUN / name).stat().st_size == entry['bytes']
receipt = read(RUN / 'receipt.json')
native = read(RUN / 'native-results-export.log')
assert receipt['status'] == 'failed-native-attempt-retained'
assert native['status'] == 'failed-retained'
assert native['failure'] == 'java.lang.AssertionError: actual native ScrollView interception and CANCEL'
assert len(native['cases']) == 17 and [x['id'] for x in native['cases']] == list(range(1, 18))
assert all(x['status'] == 'passed-component-native' for x in native['cases'])
assert native['assertions'] == 85 and native['events'] == 64
assert native['authoritativeCommits'] is None and native['rawCheckedListenerCallbacks'] is None
assert native['apkSHA256'] == receipt['apkSHA256'] == 'b272894251149cb62ebb95989756d21ad7532bc6a1d6b79d00be77af879ed441'
assert native['sourceClosureSHA256'] == receipt['sourceClosureSHA256'] == 'e878461ca7f47ca76e90b757fba6dcafabcb2f87e4c32430bd3cfc2fd4b68cf8'
instrument = (RUN / 'actual-native-component.log').read_text()
assert 'exportSHA256=' + sha(RUN / 'native-results-export.log') in instrument
assert receipt['diagnostics']['fixtureDiagnosticBindingVerified']
for row in receipt['commands']:
    assert sha(RUN / row['output']) == row['sha256']
    assert not row['ownedCommandGroupCleanup']['after']
for row in receipt['diagnostics']['captures']:
    assert row['exitCode'] == 0 and not row['truncated']
    assert sha(RUN / row['output']) == row['sha256']
    assert not row['ownedCommandGroupCleanup']['after']
assert 'diagnosticSHA256=' + sha(RUN / 'diagnostic-private-fixture.log') in instrument
assert receipt['cleanup'] == 'stopped' and not receipt['ownedEmulatorGroupCleanup']['after']
clean = receipt['extractionCleanup']
assert clean['status'] == 'removed' and clean['pathAbsentAfterCleanup'] and not Path(clean['path']).exists()
assert clean['files'] == 186 and clean['bytes'] == 173014587
assert clean['openHoldersCheck']['exitCode'] == 1 and not (RUN / 'extraction-open-holders.log').read_bytes()
assert not receipt['physicalTargetsQueried'] and receipt['target']['ro.kernel.qemu'] == '1'
for port in [5586, 5587]:
    assert not (RUN / f'port-after-{port}.log').read_bytes()
assert not receipt['outputBudget']['overflow']
trace = read(OUT / 'trace-summary.json')
assert trace['traceSHA256'] == sha(RUN / 'scroll-private-trace.log')
assert trace['entries'] == 101 and len(trace['cases']) == 1
case = trace['cases'][0]
assert case['case'] == 18
assert case['injectionActions'] == case['activityActions'] == case['childActions'] == [0] + [2]*7 + [1]
assert case['injectionTimestampOffsets'] == list(range(0, 201, 25))
assert case['childCancelCount'] == case['interceptTrueCount'] == 0
geometry = case['initialGeometry']
assert geometry['contentLayoutHeight'] == 6000 and geometry['contentHeight'] == 532
assert geometry['viewportHeight'] == 2622 and not geometry['positiveContentExtent']
assert not geometry['canScrollDown'] and not geometry['canScrollUp']
assert not case['finalConjunctState']['scrollPositive']
assert all(case['finalConjunctState'][x] for x in ['zeroProposals','notPressed','inputOpen'])
result = {
    'schema': 1,
    'status': 'failed-original-scroll-protocol-retained-fixture-extent-defect-observed',
    'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'sourceRevisionContext': '09ee31fff245aa14f89cd4054b7df5a214efbb93',
    'completedComponentCases': 17,
    'assertionCounterIncludingFailure': 85,
    'reportedEvents': 64,
    'failure': native['failure'],
    'full45CaseSuiteAccepted': False,
    'observation': 'All9originalevents delivered to Activity and actual child, no CANCEL/intercept. Requested content layout height6000 measured532 inside2622viewport; canScrollUp/Downfalse. ScrollPositivefalse; other original conjuncts true.',
    'inference': 'The fixture does not provide positive scroll extent. Correct only that setup, then rerun unchanged original45cases and9eventprotocol before drawing product conclusions. Timing is observed but not established as a cause.',
    'cleanup': 'Owned emulator95281 group and ports5586/5587 empty;186extractedfiles173014587bytes removed.',
    'next': 'Fixture-only minimum content extent correction and an explicit positive extent precondition, preserving production159classes18libraries and original assertions/protocol.',
    'scope': 'Actual API37 arm64 private View component fixture. Original429assertion20action baseline remains separate. No live product integration, authoritative engine commit, physical phone, TalkBack or GA acceptance.',
    'bindings': {str(p.relative_to(ROOT)): sha(p) for p in sorted(RUN.rglob('*')) if p.is_file()},
}
result['bindings'][str((OUT / 'trace-summary.json').relative_to(ROOT))] = sha(OUT / 'trace-summary.json')
result['bindings'][str(Path(__file__).relative_to(ROOT))] = sha(Path(__file__))
(OUT / 'runtime-review.json').write_text(json.dumps(result, indent=2) + '\n')
print(result['status'], '17 completed cases; full suite failed; cleanup verified')
