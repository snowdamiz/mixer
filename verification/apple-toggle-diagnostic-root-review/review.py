"""Bind the completed diagnostic observations; this never accepts the carrier."""
import collections
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RUN = ROOT / 'verification/apple-toggle-diagnostic-runtime-retry/runtime'
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
life = read(RUN / 'lifecycle.json')
assert life['cleanedUp'] and life['ownedDeviceAbsent']
assert life['preservedExistingDeviceIDsAndStates'] and not life['cleanupErrors']
assert life['frontend']['ownedFrontendAbsent'] and not life['frontend']['unattributedNewPIDsPreserved']
assert not life['physicalDevicesQueried']
assert set(life['apps']) == {'comparator', 'diagnostic'}
for app in life['apps'].values():
    installed = app['installedApp']
    assert installed['exactManifest'] and installed['permissionScope'] == 'finite-installed-role-policy'
    modes = {x['path']: x['permissionOctal'] for x in installed['observedPermissions']['entries']}
    assert modes['Frameworks/libMixerCore.dylib'] == modes['Frameworks/libMixerUI.dylib'] == '0644'
    assert modes[app['identity']['executable']] == '0755'
comp = read(RUN / 'captures/comparator-final.json')['observations']
assert len(comp['checks']) == 12 and sum(x['pass'] for x in comp['checks']) == 10
command = read(OUT / 'commands/diagnostic-programmatic.json')
assert command['exitCode'] == 0
diag = json.loads(command['stdout'])
assert diag['checksPassed'] is False and len(diag['checks']) == 19
assert sum(x['pass'] for x in diag['checks']) == 11
assert diag['after']['diagnosticSuiteState'] == 'complete'
assert diag['after']['diagnosticTraceDropped'] == 0
ref = read(RUN / 'captures/standalone-reference-drag.json')['observations']
carrier = read(RUN / 'captures/carrier-drag.json')['observations']
scroll = read(RUN / 'captures/native-scroll-control.json')['observations']
final = read(RUN / 'captures/final-accessibility-activation.json')['observations']
refs = [x for x in ref['diagnosticTrace'] if x['kind'].startswith('referenceTouches')]
assert [x['kind'] for x in refs] == ['referenceTouchesBegan', 'referenceTouchesEnded']
assert not any(x['kind'] == 'referencePan' for x in ref['diagnosticTrace'])
touches = [x for x in carrier['diagnosticTrace'] if x['kind'].startswith('carrierTouches')]
assert [x['kind'] for x in touches] == ['carrierTouchesBegan', 'carrierTouchesEnded']
assert any(x['kind'] == 'recognizerReceiveDecision' and x['result'] is True for x in carrier['diagnosticTrace'])
assert carrier['state']['panAcceptedCount'] == carrier['state']['continueCount'] == 0
assert carrier['state']['eventCount'] == 3 and carrier['state']['isOn']
assert scroll['diagnosticTrace'] == carrier['diagnosticTrace'] and scroll['state']['scrollOffsetY'] == 0
assert final['state']['eventCount'] == 4 and final['state']['primaryCount'] == 6
assert final['state']['accessibilityActivationCount'] == 4 and not final['state']['isOn']
assert final['reference']['primaryCount'] == 3 and not final['reference']['selected']
assert all(x['diagnosticTraceDropped'] == 0 for x in [ref, carrier, scroll, final])
for log in (OUT / 'commands').glob('*.json'):
    row = read(log)
    assert row['exitCode'] == 0
result = {
    'schema': 1,
    'status': 'diagnostic-comparison-complete-carrier-not-accepted',
    'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'sourceRevisionContext': 'bbed074d3bd2453bbcc0807f05219d042cedd738',
    'environment': 'Owned iPhone17Pro iOS26.5(23F77), Xcode26.6/SDK26.5, minimum26.0',
    'comparator': 'Exact original26sourcefiles built with matched SDK still yield10true2false of12; second deselection pass remains vacuous. Initial probe collected4checks before completion; settled capture is authoritative.',
    'diagnostic': '19 strict settled checks:11true8false. Both authored carrier and plain UIKit button fail direct primary/AX off-to-on and on-to-off expectations. This is observed behavior, not a passing direct-activation contract.',
    'movement': {
        'standaloneKinds': [x['kind'] for x in refs],
        'standaloneTimestampDeltaSeconds': refs[1]['timestamp'] - refs[0]['timestamp'],
        'carrierKinds': [x['kind'] for x in touches],
        'carrierTimestampDeltaSeconds': touches[1]['timestamp'] - touches[0]['timestamp'],
        'conclusion': 'CUA drag attempts delivered only begin/end, no moved events even to standalone unfiltered native pan. Authored receive admitted touch but did not pan. Blank-list scroll tool produced no new trace/offset. These attempts do not qualify native movement/arbitration.',
    },
    'activation': 'Actual simulator exposed-element clicks changed plain UIButton true-to-false once and authored toggle true-to-false with one primary/value event. Two CUA pipe interruptions retained; affected authored call showed no mutation before retry.',
    'paint': 'Inline screenshots observed only; no local pixelhash, pressed compositor or numerical parity acceptance.',
    'cleanup': 'Owned A0AD1F39-04CC-4412-B560-C8119AFED560 and frontend1858 absent; all baseline IDs/states preserved.',
    'carrierAccepted': False,
    'liveProductChanged': False,
    'physicalPhones': 'deferred disconnected',
    'gaAccepted': False,
    'bindings': {str(p.relative_to(ROOT)): sha(p) for p in sorted(RUN.rglob('*')) if p.is_file()},
}
for p in sorted(OUT.rglob('*')):
    if p.is_file() and p.name != 'runtime-review.json':
        result['bindings'][str(p.relative_to(ROOT))] = sha(p)
(OUT / 'runtime-review.json').write_text(json.dumps(result, indent=2) + '\n')
print('Diagnostic comparison retained; native movement and direct activation unqualified; owned cleanup verified')
