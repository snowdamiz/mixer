import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RUNTIME = ROOT / 'verification/apple-authored-toggle-runtime-preflight/runtime'

def read(name):
    return json.loads((RUNTIME / 'captures' / (name + '.json')).read_text())['observations']

def state(name):
    return read(name)['state']

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

initial = state('self-tests')
checks = read('self-tests')['checks']
assert len(checks) == 12 and sum(x['pass'] is True for x in checks) == 10
assert initial['eventValues'] == [False, False]
assert [x['name'] for x in checks if not x['pass']] == [
    'UIKit primary activation selects and emits once',
    'UIButton accessibility activation selects and emits once']
previous = initial
for name, expected in [('native-tap-on', True), ('native-tap-off', False), ('native-element-click', True)]:
    current = state(name)
    assert current['eventCount'] == previous['eventCount'] + 1
    assert current['primaryCount'] == previous['primaryCount'] + 1
    assert current['acceptedCount'] == previous['acceptedCount'] + 1
    assert current['isOn'] is expected and current['retainedOn'] is expected
    assert current['eventValues'][-1] is expected
    assert not current['tracking'] and not current['highlighted']
    previous = current
assert state('native-element-click')['accessibilityActivationCount'] == state('native-tap-off')['accessibilityActivationCount'] + 1
drag = state('ltr-forward')
assert drag['panAcceptedCount'] == 0 and drag['primaryCount'] == previous['primaryCount'] + 1
assert state('vertical-probe')['scrollOffsetY'] == 0
held = state('native-held-press-held')
released = state('native-held-release')
assert all(held[key] for key in ['tracking', 'highlighted', 'authoredPressed'])
assert not held['isOn'] and released['isOn']
assert released['eventCount'] == held['eventCount'] + 1
for label, after, final in [('disable', 'disable', 'disabled-tap'), ('stale', 'stale', 'stale-tap'), ('cancel', 'cancel', 'cancelled-release-tab')]:
    held = state('native-' + label + '-held-held')
    cancelled = state('native-' + label + '-held-' + after)
    released = state(final)
    assert held['tracking'] and held['highlighted'] and held['authoredPressed']
    for current in [cancelled, released]:
        assert current['eventCount'] == held['eventCount']
        assert current['acceptedCount'] == held['acceptedCount']
        assert not current['isOn'] and not current['tracking'] and not current['highlighted']
assert not state('disabled-tap')['enabled']
assert not state('stale-tap')['allowed']
assert not state('cancelled-release-tab')['focused']
dark = state('dark-rtl-authored-tap')
assert dark['rtl'] and dark['isOn'] and dark['selectedTrait']
assert dark['value'] == 'Authored sync status' and dark['eventCount'] == 8
life = json.loads((RUNTIME / 'lifecycle.json').read_text())
assert life['cleanedUp'] and life['ownedDeviceAbsent'] and life['preservedExistingDeviceIDsAndStates']
assert life['frontend']['ownedFrontendAbsent'] and not life['physicalDevicesQueried']
files = [p for p in RUNTIME.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
files += [ROOT / 'verification/apple-authored-toggle-runtime-preflight/packet-seal.json', Path(__file__).resolve()]
receipt = {
    'schema': 1,
    'status': 'partial-native-observations-retained-not-carrier-acceptance',
    'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'sourceRevisionContext': '2f715b10e707de26b89c9bef44831a43c7aa3c62',
    'sourceClosureSHA256': '04f91d8abf20e3401a916b8ab03c6d638eefd53f2e8aa8fcded31ef9706e5b9d',
    'runtime': 'iOS26.5(23F77) simulator; Xcode26.6; exact archived candidate built using Xcode27.1 SDK27.1 path with binary SDK27.0/minimum26.0',
    'observedPassed': ['two opposite coordinate taps', 'simulator accessibility-element activation', 'native held touch state and once-only release', 'cancel/disable/stale during held touch with no release event', 'disabled and stale fresh taps rejected', 'dark RTL activation preserves authored accessibility value and selected trait', 'owned simulator/frontend removed and four baseline states preserved'],
    'failedOrUnqualified': ['two direct programmatic activation checks failed; second deselection assertion is vacuous after first activation failure', 'horizontal drag intent followed primary path with no pan acceptance', 'vertical probe at top gave no positive scroll evidence', 'Tab did not establish native focus', 'CUA screenshot serialized after held release; pressed compositor pixels unavailable', 'screenshots inspected in conversation only, no local pixel comparison', 'production reconciliation, complete Apple adapter, physical VoiceOver and phones, immutable FieldLog, stores, operations and GA remain pending'],
    'cleanupFirstAttempt': 'Post-SIGTERM frontend identity poll rejected transitional process identity. Failure preserved. Original-wrapper retry verified absence without changing frozen code.',
    'bindings': {str(p.relative_to(ROOT)): digest(p) for p in sorted(files)},
}
(OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(receipt['status'], len(files), 'bound files; no full carrier acceptance')
