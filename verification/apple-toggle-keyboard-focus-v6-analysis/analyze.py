#!/usr/bin/env python3
"""Read-only V6 native evidence replay; writes only this new analysis lane.

No native, compiler, UI, process, Git, publication, or existing audit invocation.
The proposed V7 predicates below are review models, not runtime implementation.
"""
import argparse
import copy
import datetime
import hashlib
import importlib.util
import json
import pathlib
import plistlib
import sys
import time
import traceback

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PREP = ROOT / 'verification/apple-toggle-keyboard-focus-v6-preparation'
REVIEW = ROOT / 'verification/apple-toggle-keyboard-focus-v6-independent-review'
ROOT_REVIEW = ROOT / 'verification/apple-toggle-keyboard-focus-v6-root-review'
RUNTIME = PREP / 'runtime'
CAPTURES = RUNTIME / 'captures'
PUBLIC = pathlib.Path('/Applications/Xcode_26.6.app/Contents/Developer/Platforms/iPhoneSimulator.platform/Developer/Library/Frameworks/XCUIAutomation.framework/Headers')
EXPECTED_SELECTION = '37fad53c29f09de16730107e9d8d80cd78ab111a34bbecf2b6a517fa17b1b681'
EXPECTED_PREP = '5b2743fd61dbabc95abc6e50468347efe406953fb1314785b17013922b6438fd'
EXPECTED_REVIEW = '24dfa4e5b4b354447fc03686d8b8732c3387ff019f6305f0dd6fc52fb9bcd1c0'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def write(name, value):
    target = BASE / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


def require(ok, reason):
    if not ok:
        raise AssertionError(reason)


def inventory():
    paths = set()
    seals = [(PREP / 'packet-seal.json', EXPECTED_PREP, 184), (REVIEW / 'review-seal.json', EXPECTED_REVIEW, 158)]
    for seal, expected, count in seals:
        require(sha(seal) == expected, 'Input seal identity changed: ' + str(seal))
        bound = read(seal)['files']
        require(len(bound) == count, 'Input seal count changed')
        for name, digest in bound.items():
            path = ROOT / name
            require(path.is_file() and not path.is_symlink() and sha(path) == digest, 'Sealed file changed: ' + name)
            paths.add(path)
        paths.add(seal)
    require(sha(ROOT_REVIEW / 'selection.json') == EXPECTED_SELECTION, 'Root runtime selection changed')
    paths.update(ROOT_REVIEW / name for name in ['selection.json', 'runtime.stdout', 'runtime.stderr', 'runtime-review.json'])
    paths.add(ROOT / 'AGENTS.md')
    paths.add(ROOT / 'docs/apple-toggle-keyboard-focus-v6-preparation.md')
    paths.add(ROOT / 'docs/apple-toggle-keyboard-focus-v6-independent-review.md')
    # Include every journal, AX, PNG and official export; no restored-app scan is needed.
    paths.update(p for p in RUNTIME.rglob('*') if p.is_file() and 'restored-app' not in p.parts)
    paths.update(PUBLIC / name for name in ['XCUIElement.h', 'XCUIElementQuery.h', 'XCUIElementAttributes.h', 'XCUIElementTypes.h'])
    result = {}
    for path in sorted(paths):
        require(path.is_file() and not path.is_symlink(), 'Input path not immutable regular file: ' + str(path))
        name = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        result[name] = {'sha256': sha(path), 'bytes': path.stat().st_size}
    return result


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def decode_archive(path):
    """Decode data with plistlib only; do not instantiate NSKeyedArchiver classes."""
    raw = plistlib.loads(path.read_bytes())
    require(raw['$archiver'] == 'NSKeyedArchiver', 'Unexpected official attachment encoding')
    objects = raw['$objects']

    def decode(value, depth=0):
        require(depth < 100, 'Archive nesting cap')
        if isinstance(value, plistlib.UID):
            require(0 <= value.data < len(objects), 'Archive UID bounds')
            return None if value.data == 0 else decode(objects[value.data], depth + 1)
        if isinstance(value, list):
            return [decode(x, depth + 1) for x in value]
        if isinstance(value, dict):
            if 'NS.keys' in value and 'NS.objects' in value:
                return dict(zip(decode(value['NS.keys'], depth + 1), decode(value['NS.objects'], depth + 1), strict=True))
            if 'NS.objects' in value:
                return decode(value['NS.objects'], depth + 1)
            return {k: decode(v, depth + 1) for k, v in value.items() if k != '$class'}
        return value

    return decode(raw['$top']['root'])


def inside(point, frame):
    x, y = point
    return frame['x'] < x < frame['x'] + frame['width'] and frame['y'] < y < frame['y'] + frame['height']


def center(frame):
    return [frame['x'] + frame['width'] / 2, frame['y'] + frame['height'] / 2]


def proposed_row(t, container, witness, index):
    """Review model: exact observed route-2 suffixes only, all V6 target checks retained."""
    container = copy.deepcopy(container)
    if (index == 2 and witness['relation'] == 'descendant'
            and container['identifier'] == 'FULL_KEYBOARD_ACCESS'
            and container['label'] in ['Full Keyboard Access, Off', 'Full Keyboard Access, On']):
        container['label'] = 'Full Keyboard Access'
    return t.route_target(container, witness, index)


def proposed_leaf(t, parent, leaf, relation):
    """Review model for a future public-query witness; synthetic flags are not native evidence."""
    try:
        t.snapshot(parent)
        t.snapshot(leaf)
        if not (t.expected_switch(parent) and parent['identifier'] == 'FKAEnabledSwitch'
                and relation == {'relation': 'direct-child', 'parentMatchCount': 1, 'childSwitchCount': 1, 'leafChildSwitchCount': 0}
                and leaf['bundle'] == parent['bundle'] and leaf['identifier'] == leaf['label'] == ''
                and leaf['elementType'] == 40 and leaf['appState'] == 4
                and all(leaf[k] is True for k in ['exists', 'hittable', 'enabled', 'foreground'])
                and parent['valueKind'] == leaf['valueKind'] == 'string'
                and parent['value'] == leaf['value'] and leaf['value'] in ['0', '1']):
            return False
        p, l = parent['frame'], leaf['frame']
        hit = center(l)
        intersection = min(p['x'] + p['width'], l['x'] + l['width']) > max(p['x'], l['x']) and min(p['y'] + p['height'], l['y'] + l['height']) > max(p['y'], l['y'])
        return l['width'] < p['width'] and intersection and inside(hit, p) and inside(hit, l) and inside(hit, {'x': 0, 'y': 0, 'width': 402, 'height': 874})
    except ValueError:
        return False


def controls(t, search, parent, leaf_frame):
    results = []

    def check(name, got, expected):
        require(got == expected, 'Control failed: ' + name)
        results.append({'name': name, 'observed': got, 'expected': expected, 'passed': True})

    c, w = search['snapshot'], search['routeWitness']
    check('V6-actual-route2-Off-retains-false', t.route_target(c, w, 2), False)
    check('proposal-actual-route2-Off', proposed_row(t, c, w, 2), True)
    for label, expected in [('Full Keyboard Access, On', True), ('Full Keyboard Access, Off ', False), ('Full Keyboard Access, Off, Other', False), ('Full Keyboard Accessory, Off', False), ('Full Keyboard Access, Enabled', False)]:
        changed = copy.deepcopy(c); changed['label'] = label
        check('proposal-exact-label-' + label, proposed_row(t, changed, w, 2), expected)
    for field, value in [('identifier', ''), ('identifier', 'OTHER'), ('elementType', 48), ('foreground', False), ('enabled', False)]:
        changed = copy.deepcopy(c); changed[field] = value
        check('proposal-wrong-container-' + field + '-' + str(value), proposed_row(t, changed, w, 2), False)
    changed = copy.deepcopy(w); changed['target']['label'] = 'Off'
    check('proposal-wrong-descendant-label', proposed_row(t, c, changed, 2), False)
    changed = copy.deepcopy(w); changed['target']['frame']['x'] = 500
    check('proposal-disjoint-row-descendant', proposed_row(t, c, changed, 2), False)
    changed = copy.deepcopy(w); changed['relation'] = 'self'
    check('proposal-no-descendant-binding', proposed_row(t, c, changed, 2), False)
    check('proposal-wrong-route-index', proposed_row(t, c, w, 1), False)
    leaf = copy.deepcopy(parent)
    leaf.update(identifier='', label='', frame=leaf_frame)
    relation = {'relation': 'direct-child', 'parentMatchCount': 1, 'childSwitchCount': 1, 'leafChildSwitchCount': 0}
    check('proposal-actual-geometry-synthetic-leaf-metadata', proposed_leaf(t, parent, leaf, relation), True)
    check('proposal-composite-as-leaf', proposed_leaf(t, parent, parent, relation), False)
    for field, value in [('relation', 'descendant'), ('parentMatchCount', 2), ('childSwitchCount', 0), ('childSwitchCount', 2), ('leafChildSwitchCount', 1)]:
        changed = copy.deepcopy(relation); changed[field] = value
        check('proposal-relation-' + field + '-' + str(value), proposed_leaf(t, parent, leaf, changed), False)
    for field, value in [('identifier', 'FKAEnabledSwitch'), ('label', 'Full Keyboard Access'), ('bundle', 'other'), ('elementType', 9), ('value', '1'), ('valueKind', 'unsupported'), ('enabled', False), ('hittable', False), ('foreground', False), ('appState', 3)]:
        changed = copy.deepcopy(leaf); changed[field] = value
        check('proposal-leaf-' + field + '-' + str(value), proposed_leaf(t, parent, changed, relation), False)
    for name, frame in [('disjoint', {'x': 380, 'y': 146.3333282470703, 'width': 15, 'height': 28}), ('zero', {'x': 305, 'y': 146.3333282470703, 'width': 0, 'height': 28}), ('center-on-parent-right-edge', {'x': 335, 'y': 146.3333282470703, 'width': 62, 'height': 28})]:
        changed = copy.deepcopy(leaf); changed['frame'] = frame
        check('proposal-leaf-geometry-' + name, proposed_leaf(t, parent, changed, relation), False)
    changed_parent = copy.deepcopy(parent); changed_parent['identifier'] = 'Full Keyboard Access'
    check('proposal-parent-must-be-exact-identified-composite', proposed_leaf(t, changed_parent, leaf, relation), False)
    return {'schema': 'mixer.apple-toggle.keyboard-v6-analysis-controls.1', 'scope': 'Host review models and actual V6 route predicate. Leaf flags and On fixtures are synthetic; no native selection or V7 runtime pass.', 'controls': results, 'passed': True, 'count': len(results)}


def analyze():
    before = inventory()
    sys.path.insert(0, str(PREP))
    replay = module('v6_analysis_replay', PREP / 'replay.py')
    t = replay.t
    replayed = replay.replay(CAPTURES)
    verdict = read(RUNTIME / 'runtime-verdict.json')
    require(replayed == verdict['settingsDiagnostic'], 'Exact V6 offline replay differs')
    records = [read(p) for p in sorted(CAPTURES.glob('0000-settings-*.json'))]
    require(len(records) == 275 and [x['record'].get('sequence', 0) for x in records] == list(range(275)), 'Journal sequence count/order')
    by_sequence = {x['record'].get('sequence', 0): x['record'] for x in records}
    official = read(RUNTIME / 'xctest-summary.json')
    commands = read(RUNTIME / 'commands.json')
    tests = [c for c in commands if pathlib.Path(c.get('argv', [''])[0]).name == 'xcodebuild']
    require(len(tests) == 1, 'Expected exactly one selected XCTest command')
    command = tests[0]
    require(command['argv'][1] == 'test-without-building' and command['exitCode'] == 65, 'Actual native command/failure differs')
    require([x for x in command['argv'] if x.startswith('-only-testing:')] == ['-only-testing:MixerToggleUITests/ToggleUITests/test000PublicSettingsFullKeyboardAccess'], 'Unexpected app tests')
    require(official['totalTestCount'] == official['failedTests'] == 1 and official['passedTests'] == official['skippedTests'] == 0, 'Official failed test count')
    require(verdict['bridgeFailures'] == [] and verdict['diagnosticCompleted'] and verdict['applicationCasesExecuted'] == 0, 'Runtime status changed')
    require(not verdict['expectedDiagnosticQualificationBoundary'], 'Actual setup failure cannot become expected boundary')
    require(not replayed['setupObservationSatisfied'] and not replayed['settingsReportedEnabled'] and not replayed['selectedRouteEvidenceExpected'], 'Failed setup status')
    require(replayed['requests'] == 275 and replayed['sequence'] == 274 and not replayed['pendingSlots'], 'Telemetry totals')
    require(replayed['claimedRouteTapIndices'] == [0, 1, 2] and replayed['routeTaps'] == [0, 1], 'Route credit distinction changed')
    require(all(x['captureStartedUptime'] >= x['tapFinishedUptime'] and x['tapSequence'] < x['sequence'] and x['destinationMatched'] for x in replayed['routeOpenedBindings']), 'V6 ordering repaired')
    # AX debug output rounds frames to one decimal; do not invent a structured
    # precise leaf snapshot or infer its unqueried hittability.
    leaf_frame = {'x': 305.0, 'y': 146.3, 'width': 63.0, 'height': 28.0}
    parent = by_sequence[47]['snapshot']
    label_frame = {'x': 36.0, 'y': 150.0, 'width': 162.7, 'height': 20.3}
    actual_ax = (CAPTURES / 'settings-0047-ax.txt').read_text()
    require("Switch, 0x113e3a940, {{305.0, 146.3}, {63.0, 28.0}}, value: 0" in actual_ax, 'Observed rounded leaf frame changed')
    require("Button, 0x113e3a800, {{36.0, 150.0}, {162.7, 20.3}}, identifier: 'FKAEnabledSwitch', label: 'Full Keyboard Access'" in actual_ax, 'Observed rounded label frame changed')
    manifest = read(RUNTIME / 'attachments/manifest.json')
    decoded = []
    for group in manifest:
        for item in group['attachments']:
            if not item['suggestedHumanReadableName'].startswith('Synthesized Event'):
                continue
            event = decode_archive(RUNTIME / 'attachments' / item['exportedFileName'])
            decoded.append({'manifest': item, 'decoded': event})
    taps = [x for x in decoded if x['decoded']['name'] == 'tap']
    require(len(taps) == 4, 'Expected three route taps and one conditional switch tap')
    switch = max(taps, key=lambda x: x['manifest']['timestamp'])
    points = [[p['coordinate.x'], p['coordinate.y']] for path in switch['decoded']['eventPaths'] for p in path['pointerEvents']]
    require(points == [center(parent['frame']), center(parent['frame'])], 'Actual switch event differs from composite center')
    require(all(not inside(point, leaf_frame) and not inside(point, label_frame) for point in points), 'Do not overclaim inner or label hit')
    samples = [r['record'] for r in records if r['record'].get('stage') in ['before-switch', 'after-switch', 'poll', 'terminal']]
    require(all(r['snapshot']['valueKind'] == 'string' and r['snapshot']['value'] == '0' for r in samples), 'Actual off samples changed')
    pngs = [CAPTURES / ('settings-' + str(i).zfill(4) + '-png.png') for i in [47, 119, 199]]
    require(len({sha(p) for p in pngs}) == 1, 'Actual before/after/terminal images differ')
    life = read(RUNTIME / 'lifecycle.json')
    require(life['cleanedUp'] and life['ownedDeviceAbsent'] and life['ephemeralWorkspaceAbsent'] and life['baselineStatesPreserved'] and len(life['cleanupResults']) == 5 and all(x['passed'] for x in life['cleanupResults']), 'Recorded cleanup/baseline evidence incomplete')
    inputs_after = inventory()
    require(before == inputs_after, 'Input changed during offline analysis')
    controls_result = controls(t, by_sequence[36], parent, leaf_frame)
    anchor = replayed['anchorUptime']
    summary = {
        'schema': 'mixer.apple-toggle.keyboard-v6-offline-runtime-analysis.1',
        'status': 'sealed-offline-analysis-and-V7-proposal-only',
        'sourceRevisionContext': read(ROOT_REVIEW / 'selection.json')['sourceRevisionContext'],
        'reviewedPreparationSHA256': EXPECTED_PREP, 'reviewedPreparationFiles': 184,
        'reviewedIndependentReviewSHA256': EXPECTED_REVIEW, 'reviewedIndependentReviewFiles': 158,
        'rootRuntimeSelectionSHA256': EXPECTED_SELECTION,
        'inputCount': len(before), 'inputInventorySHA256': hashlib.sha256(json.dumps(before, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
        'exactOfflineReplayMatches': True, 'journalRecords': len(records), 'requests': replayed['requests'], 'lastSequence': replayed['sequence'],
        'officialFailedTests': official['failedTests'], 'xcodebuildExitCode': 65,
        'officialFailureText': official['testFailures'][0]['failureText'],
        'actualEnvironment': official['devicesAndConfigurations'][0]['device'],
        'routeTapBindings': replayed['routeTapBindings'], 'routeOpenedBindings': replayed['routeOpenedBindings'],
        'route2Rejection': {'actualContainerLabel': by_sequence[36]['snapshot']['label'], 'actualContainerIdentifier': by_sequence[36]['snapshot']['identifier'], 'exactTargetMetadataMatched': replayed['routeTapBindings'][2]['samePublicTargetMetadata'], 'V6RowMatched': False, 'cause': 'route_target descendant container label accepts only empty or exact route name; observed exact-ID container adds bounded Off suffix', 'destinationMatched': True},
        'switchEvent': {'attachment': switch['manifest']['exportedFileName'], 'eventName': 'tap', 'points': points, 'parentFrame': parent['frame'], 'leafFrameFromRoundedAXOnly': leaf_frame, 'labelFrameFromRoundedAXOnly': label_frame, 'pointEqualsCompositeCenter': True, 'pointInsideLeaf': False, 'pointInsideLabel': False, 'candidateLeafCenterFromRoundedAX': center(leaf_frame), 'candidateLeafCenterInsideParentAndLeaf': inside(center(leaf_frame), parent['frame']) and inside(center(leaf_frame), leaf_frame), 'leafExtendsBeyondParentRightByPoints': leaf_frame['x'] + leaf_frame['width'] - parent['frame']['x'] - parent['frame']['width'], 'interpretation': 'Actual synthesized tap targeted composite center in gap. No leaf tap was performed; a causal claim that a future leaf tap will enable Settings awaits selected native evidence.'},
        'observation': {'anchorUptime': anchor, 'deadlineUptime': replayed['observationDeadlineUptime'], 'windowSeconds': replayed['observationDeadlineUptime'] - anchor, 'samples': [{'sequence': x['sequence'], 'stage': x['stage'], 'observedOffsetFromAnchor': x['snapshot']['observedUptime'] - anchor, 'value': x['snapshot']['value']} for x in samples], 'pngSHA256': sha(pngs[0]), 'allThreePNGsByteIdentical': True, 'withinWindowEnabled': False},
        'recordedCleanup': {'results': life['cleanupResults'], 'ownedDeviceAbsent': life['ownedDeviceAbsent'], 'ephemeralWorkspaceAbsent': life['ephemeralWorkspaceAbsent'], 'baselineStatesPreserved': life['baselineStatesPreserved'], 'liveRecheckPerformedByAnalysis': False},
        'analysisNativeExecuted': False, 'analysisCompilerExecuted': False, 'analysisNativeInstancesQueried': False,
        'applicationCasesExecuted': 0, 'applicationCasesUnrun': verdict['dependentCasesUnrun'],
        'nativeKeyboardQualification': False, 'carrierAccepted': False, 'gaAccepted': False, 'physicalPhones': 'disconnected-deferred',
        'limitations': ['V6 has no structured leaf snapshot, leaf public query count, leaf hittability query, or explicit switch target metadata in switch-action. AX establishes observed hierarchy only.', 'NSKeyedArchiver data decoded using plistlib without instantiating classes. Event mapping uses manifest timestamps, test log order and exact coordinates.', 'Public XCUIElement debugDescription is debugging-only; no action or authorization can depend on parsing it.', 'Controls for proposed leaf witnesses use synthetic flags/metadata and are not V7 implementation or native validation.', 'Official video inventory bound, but video was not decoded or watched; no claim relies on it.', 'No hardware-keyboard, Mac-lock, physical-device, app input, carrier, or GA outcome inferred.']
    }
    return before, replayed, decoded, command, controls_result, summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    started = time.monotonic()
    if args.check:
        baseline, replayed, decoded, command, controls_result, summary = analyze()
        require(read(BASE / 'review-inputs.json') == baseline, 'Recorded input manifest differs')
        require(read(BASE / 'analysis.json') == summary, 'Recorded analysis differs')
        require(read(BASE / 'replay.json') == replayed, 'Recorded replay differs')
        require(read(BASE / 'decoded-official-events.json') == decoded, 'Recorded official event decoding differs')
        require(read(BASE / 'controls.json') == controls_result, 'Recorded host controls differ')
        print(json.dumps({'passed': True, 'mode': 'read-only-check', 'inputCount': len(baseline), 'controls': controls_result['count'], 'scope': 'offline analysis only; setup and application acceptance remain false'}, sort_keys=True))
        return
    require(not (BASE / 'analysis.json').exists(), 'Analysis already exists; use --check')
    attempt = {'schema': 'mixer.apple-toggle.keyboard-v6-analysis-command.1', 'argv': [sys.executable, '-B', str(pathlib.Path(__file__).relative_to(ROOT))], 'cwd': str(ROOT), 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'tool': {'path': str(pathlib.Path(sys.executable).resolve()), 'version': sys.version, 'sha256': sha(pathlib.Path(sys.executable).resolve())}, 'sourceSHA256': sha(pathlib.Path(__file__)), 'scope': 'Offline Python and file reads only. No existing packet writes or native/compiler/Git operations.'}
    try:
        baseline, replayed, decoded, command, controls_result, summary = analyze()
        write('review-inputs.json', baseline)
        write('replay.json', replayed)
        write('decoded-official-events.json', decoded)
        write('actual-native-command.json', command)
        write('controls.json', controls_result)
        write('analysis.json', summary)
        for name in ['XCUIElement.h', 'XCUIElementQuery.h', 'XCUIElementAttributes.h', 'XCUIElementTypes.h']:
            (BASE / 'official').mkdir(exist_ok=True)
            (BASE / 'official' / name).write_bytes((PUBLIC / name).read_bytes())
        attempt.update(exitCode=0, inputInventorySHA256=summary['inputInventorySHA256'], inputCount=len(baseline), stdout=json.dumps({'passed': True, 'exactReplay': True, 'controls': controls_result['count'], 'setupSatisfied': False}), stderr='')
    except BaseException as error:
        attempt.update(exitCode=1, error={'type': type(error).__name__, 'message': str(error)}, stdout='', stderr=traceback.format_exc())
        raise
    finally:
        attempt['elapsedSeconds'] = time.monotonic() - started
        index = 1
        while (BASE / ('attempt-' + str(index) + '.json')).exists():
            index += 1
        write('attempt-' + str(index) + '.json', attempt)
    print(attempt['stdout'])


if __name__ == '__main__':
    main()
