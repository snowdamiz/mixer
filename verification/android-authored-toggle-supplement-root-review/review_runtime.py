import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RUN = ROOT / 'verification/android-authored-toggle-supplement-repair/runtime/runtime-1'
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
assert native['apkSHA256'] == receipt['apkSHA256'] == '919a819e42e9b3d5d530a85837b8e00bf986aab47ae01eaa99a1adde3b47d980'
assert native['sourceClosureSHA256'] == receipt['sourceClosureSHA256'] == '8ead95069a3538043749cf4574185c6271c8e900be02b65daee312b34f3c68e9'
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
assert clean['files'] == 184 and clean['bytes'] == 172984832
assert clean['openHoldersCheck']['exitCode'] == 1 and not (RUN / 'extraction-open-holders.log').read_bytes()
assert not receipt['physicalTargetsQueried'] and receipt['target']['ro.kernel.qemu'] == '1'
for port in [5586, 5587]:
    assert not (RUN / f'port-after-{port}.log').read_bytes()
assert not receipt['outputBudget']['overflow']
result = {
    'schema': 1,
    'status': 'failed-component-retained-with-bound-original-assertion-and-cleanup',
    'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'sourceRevisionContext': '2f715b10e707de26b89c9bef44831a43c7aa3c62',
    'completedComponentCases': 17,
    'assertionCounterIncludingFailure': 85,
    'reportedEvents': 64,
    'failure': native['failure'],
    'full45CaseSuiteAccepted': False,
    'diagnosticPlumbingObserved': 'Main-thread assertion reached worker, original stack exported and hash-bound; crash buffer empty. No inferred cause for old runtime3.',
    'visualObservation': 'Root viewed preview-false-false.png and preview-true-true.png; both show authored intermediate thumb. Four PNG exports retained; no numerical or complete visual acceptance.',
    'cleanup': 'Owned emulator90516 group and ports5586/5587 empty;184 extractedfiles172984832bytes removed.',
    'next': 'Diagnose actual ScrollView input delivery, scroll extent, timing and intercept/CANCEL path without weakening original assertion or changing product prematurely.',
    'scope': 'Actual API37 arm64 private View component fixture. Original429assertion20action baseline remains separate. No live product integration, authoritative engine commit, physical phone, TalkBack or GA acceptance.',
    'bindings': {str(p.relative_to(ROOT)): sha(p) for p in sorted(RUN.rglob('*')) if p.is_file()},
}
result['bindings'][str(Path(__file__).relative_to(ROOT))] = sha(Path(__file__))
(OUT / 'runtime-review.json').write_text(json.dumps(result, indent=2) + '\n')
print(result['status'], '17 completed cases; full suite failed; cleanup verified')
