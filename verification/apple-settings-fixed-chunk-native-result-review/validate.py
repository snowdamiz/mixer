#!/usr/bin/env python3
"""Read-only, offline audit of one frozen V7 diagnostic; never dispatches native work."""
import copy
import hashlib
import importlib.util
import json
import pathlib
import plistlib
import sys
import tarfile

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREP = ROOT / 'verification/apple-settings-fixed-chunk-runtime-preparation'
RUN_ID = 'ddd94f80-4cb3-4a29-8fdd-c6868a343df4'
RUN = PREP / ('native-run-v7-' + RUN_ID)
RT = RUN / 'runtime'
BUILD = ROOT / 'verification/apple-settings-fixed-chunk-native-build/attempt-1'
SELECTION = ROOT / 'verification/apple-settings-fixed-chunk-native-root-selection'
UDID = '8415E228-91B8-4831-887F-BA2A96F056B7'
MANIFEST_SHA = 'ccb7ce47693677fcfc43f68939fdb9eeaa86bdeb6090ee9cfb5a5257a232382c'
SELECTION_SHA = 'abc1d883af3ad8b62e537ee10c7f1d7a925bfc0e6f0422ccfa5819da6d907b27'
HOST_REVIEW_SHA = 'e1c8b2345056742eacbc2b2faa415e760f75ba351b639adb410124322e3f4035'
inputs = {}
checks = []


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def stable(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def read(path):
    path = pathlib.Path(path)
    # Explicit denial also prevents accidental future expansion to unrelated lanes.
    assert not any(word in str(path).lower() for word in ['catalog-inspector', 'authority-driver', 'transportv2'])
    raw = path.read_bytes()
    inputs[str(path.relative_to(ROOT))] = {'bytes': len(raw), 'sha256': digest(raw)}
    return raw


def js(path):
    return json.loads(read(path))


def check(name, condition, detail=None):
    checks.append({'name': name, 'passed': condition is True, 'detail': detail})
    if condition is not True:
        raise AssertionError(name + ': ' + str(detail))


def bindings(label, entries, base=ROOT):
    mismatches = []
    for name, expected in entries.items():
        path = base / name
        if not path.is_file() or path.is_symlink():
            mismatches.append(name + ': absent/not regular')
            continue
        raw = read(path)
        if len(raw) != expected['bytes'] or digest(raw) != expected['sha256']:
            mismatches.append(name)
    check(label, not mismatches, {'members': len(entries), 'mismatches': mismatches})


def archive(label, path, entries, prefix=''):
    raw = read(path)
    import io
    with tarfile.open(fileobj=io.BytesIO(raw)) as package:
        members = {m.name: m for m in package.getmembers() if m.isfile()}
        check(label + ' exact member set', set(members) == {prefix + n for n in entries})
        mismatches = []
        for name, expected in entries.items():
            member = members[prefix + name]
            content = package.extractfile(member).read()
            if digest(content) != expected['sha256'] or len(content) != expected['bytes'] or member.mode != expected['mode']:
                mismatches.append(name)
        check(label + ' payload/hash/mode', not mismatches, {'members': len(entries), 'mismatches': mismatches})


def load_pure(name, path):
    read(path)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def focus(snapshot):
    names = [name for name, row in snapshot['elements'].items() if row['hasFocus']]
    assert len(names) <= 1
    return names[0] if names else None


def device_states(value):
    return {d['udid']: d['state'] for rows in value['devices'].values() for d in rows}


def audit():
    manifest_path = ROOT / 'verification/apple-settings-fixed-chunk-native/result-manifest.json'
    manifest_raw = read(manifest_path)
    check('frozen root manifest anchor', digest(manifest_raw) == MANIFEST_SHA)
    manifest = json.loads(manifest_raw)
    check('frozen root manifest count', len(manifest['files']) == 2428)
    bindings('all root result bindings', manifest['files'])
    selection = js(SELECTION / 'selection.json')
    execution = js(SELECTION / 'execution-selection.json')
    check('exact root selection bytes', digest(read(SELECTION / 'selection.json')) == SELECTION_SHA
          and read(RUN / 'root-selection.json') == read(SELECTION / 'selection.json'))
    check('one selected attempt and host review', execution['attemptsAuthorized'] == 1
          and execution['independentReviewHandoffSHA256'] == HOST_REVIEW_SHA
          and execution['rootSelectionSHA256'] == SELECTION_SHA)
    host_review_path = ROOT / 'verification/apple-settings-fixed-chunk-runtime-review/handoff.json'
    host_review = js(host_review_path)
    check('independent host review exact handoff', digest(read(host_review_path)) == HOST_REVIEW_SHA)
    bindings('independent host review sealed members', host_review['members'])
    producer = js(PREP / 'handoff.json')
    check('producer bound by independent host review', digest(read(PREP / 'handoff.json')) == host_review['producerHandoffSHA256'])
    bindings('producer sealed members', producer['members'])
    packet = js(PREP / 'packet.json')
    check('packet binds selection and review', digest(read(PREP / 'packet.json')) == selection['packetSHA256'] == host_review['packetSHA256'])
    bindings('packet source files', packet['files'], PREP)
    bindings('packet reference files', packet['references'])
    runtime_sources = js(PREP / 'runtime-source-manifest.json')
    check('runtime source tree digest', digest(stable(runtime_sources['files'])) == runtime_sources['treeSHA256'] == packet['runtimeSourceTreeSHA256'])
    check('runtime source archive binding', digest(read(PREP / 'runtime-sources.tar.gz')) == runtime_sources['archive']['sha256'])
    archive('runtime source archive', PREP / 'runtime-sources.tar.gz', runtime_sources['files'], 'selected/')
    source = js(BUILD / 'source-manifest.json')
    products = js(BUILD / 'product-manifest.json')
    for label, base, entries, prefix in [('review runtime source copies', HERE / 'inputs/runtime', runtime_sources['files'], ''),
                                          ('review accepted source copies', HERE / 'inputs/accepted', source['sources'], 'accepted/')]:
        selected_entries = {str(p.relative_to(base)): entries[prefix + str(p.relative_to(base))]
                            for p in base.rglob('*') if p.is_file()}
        bindings(label, selected_entries, base)
    check('compiled source tree binding', len(source['sources']) == 40 and digest(stable(source['sources'])) == source['sourceTreeSHA256'] == selection['sourceTreeSHA256'])
    check('compiled source archive binding', digest(read(BUILD / 'accepted-sources.tar.gz')) == source['archive']['sha256'])
    archive('accepted compile source archive', BUILD / 'accepted-sources.tar.gz', source['sources'])
    check('exact compiled Swift hashes retained', all(next(v['sha256'] for k, v in source['sources'].items() if k.endswith('/' + name)) == sha for name, sha in source['exactFourSwiftFiles'].items()))
    check('product archive binding', digest(read(BUILD / 'products.tar.gz')) == products['archive']['sha256'] == packet['nativeProductArchiveSHA256'] == selection['productArchiveSHA256'])
    check('product tree binding', len(products['products']) == 55 and digest(stable(products['products'])) == products['productTreeSHA256'] and products['sourceTreeSHA256'] == source['sourceTreeSHA256'])
    archive('native product archive', BUILD / 'products.tar.gz', products['products'])
    bindings('restored diagnostic app exact bytes', products['originalApplicationFiles'], RT / 'restored-app/diagnostic')
    commands = js(RT / 'commands.json')
    native_commands = [c for c in commands if c.get('argv', [None])[0] and pathlib.Path(c['argv'][0]).name == 'xcodebuild']
    check('one native command only in selected run', len(native_commands) == 1)
    command = native_commands[0]
    official = js(RT / 'official-capture.json')
    observer = js(RT / 'session/command-observer/observer.json')
    outer = js(ROOT / ('verification/apple-settings-fixed-chunk-native/outer-run-' + RUN_ID + '/receipt.json'))
    check('same native command across captures', command['argv'] == official['argv'] == observer['argv'])
    check('native command is bounded test without building', command['argv'][1] == 'test-without-building'
          and command['argv'].count('-only-testing:MixerToggleUITests/ToggleUITests/test000PublicSettingsFullKeyboardAccess') == 1
          and command['argv'].count('-only-testing:MixerToggleUITests/ToggleUITests/test010ReferenceFirstTab') == 1
          and command['argv'][command['argv'].index('-parallel-testing-enabled') + 1] == 'NO'
          and command['argv'][command['argv'].index('-maximum-concurrent-test-simulator-destinations') + 1] == '1')
    check('original exit statuses distinguished', command['exitCode'] == observer['exitCode'] == 65 and outer['exitCode'] == 0
          and outer['retryAttempted'] is False and outer['signals'] == [] and outer['observationComplete'] is True)
    check('selected source revision label only', outer['sourceRevisionLabel'] == execution['sourceRevision'] == manifest['sourceRevision'] == '4a28261b333c28b4fce386f370a19b93e735c8d2')
    check('outer driver bytes selected', digest(read(ROOT / 'verification/apple-settings-fixed-chunk-native/observe_dispatch.py')) == execution['driverSHA256'] == outer['driverSHA256'])
    for stream in ['stdout', 'stderr']:
        raw = read(RT / ('session/command-observer/' + stream + '.log'))
        check('native ' + stream + ' stream complete', observer['streams'][stream]['eof'] is True
              and observer['streams'][stream]['readerErrors'] == []
              and len(raw) == observer['streams'][stream]['observedBytes'] == observer['streams'][stream]['retainedBytes']
              and digest(raw) == observer['streams'][stream]['retainedSHA256'])
    check('dispatch no retry marker', js(PREP / ('dispatch-attempts/' + RUN_ID + '.json'))['oneAttemptOnly'] is True)
    summary, tests = js(RT / 'xctest-summary.json'), js(RT / 'xctest-tests.json')
    am = js(RT / 'attachments/manifest.json')
    for key, path in [('summary', 'xctest-summary.json'), ('tests', 'xctest-tests.json'), ('manifest', 'attachments/manifest.json')]:
        check('official ' + key + ' binding', digest(read(RT / path)) == official['officialSHA256'][key])
    bindings('official attachment payloads', {name: {'bytes': (RT / 'attachments' / name).stat().st_size, 'sha256': sha} for name, sha in official['payloadSHA256'].items()}, RT / 'attachments')
    methods = {}
    def walk(value):
        if type(value) is dict:
            if value.get('nodeType') == 'Test Case':
                methods[value['name'].split('(')[0]] = value.get('result')
            for v in value.values(): walk(v)
        elif type(value) is list:
            for v in value: walk(v)
    walk(tests)
    check('official exact two method outcomes', methods == {'test000PublicSettingsFullKeyboardAccess': 'Passed', 'test010ReferenceFirstTab': 'Failed'}, methods)
    check('official failed summary counts', summary['totalTestCount'] == 2 and summary['passedTests'] == summary['failedTests'] == 1 and summary['skippedTests'] == 0 and summary['result'] == 'Failed')
    device = summary['devicesAndConfigurations'][0]['device']
    check('actual simulator environment', device['deviceId'] == UDID and device['osVersion'] == '26.5' and device['osBuildNumber'] == '23F77' and device['platform'] == 'iOS Simulator')
    verdict = js(RT / 'runtime-verdict.json')
    check('strict import provenance accepted with failure', verdict['provenanceAccepted'] is True and verdict['runPassed'] is False and verdict['reportingFailures'] == [] and verdict['bridgeFailures'] == [] and verdict['xcodebuildExitCode'] == 65)
    attachments = {role: js(RT / 'attachments' / binding['file']) for role, binding in verdict['authoritativeAttachments'].items()}
    for role, binding in verdict['authoritativeAttachments'].items():
        check('authoritative ' + role + ' exact hash', digest(read(RT / 'attachments' / binding['file'])) == binding['sha256'])
        match = [a for group in am for a in group['attachments'] if a['exportedFileName'] == binding['file']]
        check('authoritative ' + role + ' official timestamp and device', len(match) == 1 and match[0]['timestamp'] == binding['timestamp'] and match[0]['deviceId'] == UDID)
    check('official Settings attachment passed', attachments['settings']['passed'] is True and attachments['settings']['fullKeyboardAccessValue'] == '1' and attachments['settings']['observedEnabledWithinWindow'] is True)
    before = js(RT / 'captures/0001-before-1.json')
    after = js(RT / 'captures/0001-after-1.json')
    retained = js(RT / 'captures/0001-keyboard-witness-1.json')
    original = attachments['verdict']
    check('original verdict unchanged across all result carriers', original == after['verdict'] == verdict['classification']['originalOracleResults'][0] and attachments['witness'] == original['keyboardWitness'] == retained['witness'])
    check('one reference premise and one returned Tab', attachments['premise']['passed'] is True and attachments['premise']['actionInjectionCount'] == 0 and verdict['keyInjectionCount'] == verdict['actualNativeInputActions'] == 1 and original['keyboardWitness']['returned'] is True)
    oracle = load_pure('offline_v2_original', HERE / 'inputs/runtime/inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/keyboard_oracle.py')
    classifier = load_pure('offline_reference_classifier', HERE / 'inputs/runtime/reference_contract.py')
    pair = {'before': before['observation'], 'after': after['observation'], 'fileChanged': before['signature'] != after['signature']}
    replayed = classifier.result([attachments['premise']], [original], oracle, [pair])
    check('unchanged complete oracle and classifier replay', classifier.strict_json_equal(replayed, verdict['classification']), replayed['status'])
    fake_pass = copy.deepcopy(original)
    fake_pass['passed'] = True
    rejected_pass = classifier.result([attachments['premise']], [fake_pass], oracle, [pair])
    check('offline negative control rejects false pass', rejected_pass['status'] == 'invalid-or-incomplete-evidence')
    fake_pair = copy.deepcopy(pair)
    fake_pair['after']['state']['focused'] = True
    rejected_pair = classifier.result([attachments['premise']], [original], oracle, [fake_pair])
    check('offline negative control rejects changed authored focus pair', rejected_pair['status'] == 'invalid-or-incomplete-evidence')
    check('only traversal predicate failed', [k for k, v in original['predicates'].items() if v is False] == ['actualNativeFocusTraversal'])
    w = original['keyboardWitness']
    check('reference to no fixed focused element', focus(w['before']) == 'plain-uibutton-reference' and focus(w['after']) is None)
    check('paired authored focus false without disagreement', before['observation']['state']['focused'] is after['observation']['state']['focused'] is False and original['pairedFocusDisagreement'] is False)
    check('focus signal predicate is satisfied with unchanged authored focus', original['predicates']['appFocusUpdateSignalObserved'] is True and before['observation']['events'] == after['observation']['events'])
    diagnostic = js(RT / 'captures/0001-focus-diagnostic-1.json')
    check('diagnostic cannot replace authoritative sample', diagnostic['authoritative'] is False and diagnostic['atomic'] is False and diagnostic['observationsDropped'] == 0)
    check('bounded focus-only followup agrees', diagnostic['followUp']['captureStatus'] == 'complete' and len(diagnostic['followUp']['rows']) == 3 and all(row['hasFocus'] is False for row in diagnostic['followUp']['rows']))
    b, a = before['observation'], after['observation']
    check('no new authored events or strict traces', b['events'] == a['events'] and b['diagnosticTrace'] == a['diagnosticTrace'] and a['diagnosticTraceDropped'] == 0)
    new_contexts = a['focusContexts'][len(b['focusContexts']):]
    check('three new controller contexts during returned key', len(new_contexts) == 3 and all(row['source'] == 'controller' and row['heading'] == 0 and w['startedUptime'] <= row['uptime'] <= w['finishedUptime'] for row in new_contexts) and a['focusContextDropped'] == 0)
    endpoint_pairs = [(row['previous']['state'], row['next']['state']) for row in new_contexts]
    check('reference clear restore clear sequence', endpoint_pairs == [('item', 'null'), ('null', 'item'), ('item', 'null')])
    reference = b['focusContexts'][0]['next']
    endpoints = [end for row in new_contexts for end in [row['previous'], row['next']] if end['state'] == 'item']
    check('same attached UIButton endpoint identity and frame', all(end == reference for end in endpoints) and reference['class'] == 'UIButton' and reference['attachedToWindow'] is True and reference['frameInWindow'] == w['before']['elements']['plain-uibutton-reference']['frame'] and reference['identifier'] is None)
    check('authored carrier never context endpoint', all(end.get('identity') != b['state']['identity'] for row in a['focusContexts'] for end in [row['previous'], row['next']]))
    local = js(RT / 'session/local-settings-first-failure.json')
    check('historical local marker status preserved distinct from pass', local['supplementalOnly'] is True and local['status'] == 'marker-not-observed' and local['settingsPreconditionPassed'] is False and local['diagnostic'] is None)
    lifecycle = js(RT / 'lifecycle.json')
    baseline, final = device_states(selection['baselineDevices']), device_states(lifecycle['after'])
    check('four baseline simulator states exactly preserved', len(baseline) == 4 and baseline == final and UDID not in final)
    check('all five independent cleanup records passed', len(lifecycle['cleanupResults']) == 5 and all(x['passed'] is True for x in lifecycle['cleanupResults']) and lifecycle['cleanupResults'] == verdict['cleanupResults'] == manifest['cleanupResults'])
    check('cleanup recorded with secret configuration retired', lifecycle['ownedDeviceAbsent'] is True and lifecycle['baselineStatesPreserved'] is True and lifecycle['secretConfigurationAbsent'] is True and not (RT / 'session/session.xctestrun').exists())
    installed = lifecycle['apps']['diagnostic']['installed']
    check('installed diagnostic validated against exact archive', installed['exactManifest'] is True and installed['archiveSHA256'] == selection['productArchiveSHA256'] and installed['observedPermissions']['complete'] is True)
    derivation = js(RT / 'session/configuration-derivation.json')
    check('compiled products unchanged, secret environment retired', derivation['compiledProductsUnchanged'] is True and derivation['retired'] is True and derivation['secretConfigurationAbsent'] is True and derivation['capabilityRetainedInReceipt'] is False)
    failure1, failure2 = js(SELECTION / 'preselection-failure.json'), js(SELECTION / 'preselection-failure-2.json')
    creation_commands = js(SELECTION / 'commands.json')
    check('preselection errors retained without native attempts', failure1['commandsLaunched'] == failure1['simulatorsCreated'] == failure1['nativeAttempts'] == failure2['nativeAttempts'] == 0 and failure2['ownedSimulatorUDID'] == UDID)
    check('one simulator creation in root selection log', sum(c.get('argv', [])[1:3] == ['simctl', 'create'] for c in creation_commands) == 1)
    creation = next(c for c in creation_commands if c.get('argv', [])[1:3] == ['simctl', 'create'])
    intent = js(SELECTION / 'creation-intent.json')
    check('root intent precedes one successful simulator creation', intent['createdUTC'] < creation['startedUTC'] and creation['exitCode'] == 0 and js(SELECTION / 'created-identity.json') == selection['ownedSimulatorIdentity'])
    check('no qualification credit added', all(verdict[key] is False for key in ['runPassed', 'fullSixCaseQualification', 'nativeKeyboardQualification', 'carrierAccepted', 'completeCaseSet', 'cursorCompletionCredit', 'gaAccepted']) and verdict['physicalPhones'] == 'disconnected-deferred')
    # Decode only the saved official binary plist; this never instantiates XCTest objects.
    event = plistlib.loads(read(RT / 'attachments/1FE6FA99-86D8-427A-90F0-FA07BDFA8C4D'))
    check('saved official synthesized-event record includes Tab', '\t' in event['$objects'] and any(type(x) is str and 'XCUIKeyboardKeyTab' in x for x in event['$objects']))
    tools = js(BUILD / 'tools.json')
    api = js(HERE / 'platform-api-contract.json')
    for item in api['sdkSources']:
        raw = pathlib.Path(item['origin']).read_bytes()
        inputs[item['origin']] = {'bytes': len(raw), 'sha256': digest(raw)}
        excerpt = ('\n'.join(raw.decode().splitlines()[item['lineStart']-1:item['lineEnd']]) + '\n').encode()
        check('public API source snapshot ' + item['snapshot'], digest(raw) == item['originSHA256']
              and digest(read(HERE / item['snapshot'])) == item['snapshotSHA256'] and read(HERE / item['snapshot']) == excerpt)
    sdk_settings = api['sdkSettings']
    check('public API inspection uses pinned SDK settings', sdk_settings['sha256'] == tools['bindings'][sdk_settings['path']]['sha256'] == digest(pathlib.Path(sdk_settings['path']).read_bytes()))
    overlay = read(HERE / 'inputs/platform-api/UIKit.swiftinterface').decode()
    check('public environment getter explicitly available', '@available(iOS 15.0' in overlay and '@_Concurrency.MainActor' in overlay and 'public class func focusSystem(for environment: any UIFocusEnvironment) -> UIFocusSystem?' in overlay)
    check('exact app legacy window lifecycle observed', 'let window = UIWindow(frame:' in read(HERE / 'inputs/accepted/source/Prototype/main.swift').decode())
    return {
        'schema': 'mixer.apple-settings-fixed-chunk-native-result-review.1',
        'scope': 'Read-only offline review and unchanged oracle replay; no native query/run/UI/compile/phone/Git/network operation',
        'nativeExecutedByReview': False, 'gaAccepted': False,
        'rootResultManifestSHA256': MANIFEST_SHA, 'rootSelectionSHA256': SELECTION_SHA,
        'sourceRevisionLabel': execution['sourceRevision'], 'compiledSourceTreeSHA256': source['sourceTreeSHA256'],
        'runtimeSourceTreeSHA256': runtime_sources['treeSHA256'], 'productArchiveSHA256': products['archive']['sha256'],
        'officialMethods': methods, 'originalVerdictPassed': original['passed'],
        'originalOracleReplayExact': True, 'failingPredicates': ['actualNativeFocusTraversal'],
        'eventOrdering': {
            'clock': 'ProcessInfo.systemUptime; no inferred conversion to wall clock',
            'baseline': retained['binding']['baselineUptime'],
            'axBefore': diagnostic['observations'][0],
            'keyStart': w['startedUptime'], 'controllerContextsDuringKey': new_contexts,
            'keyReturn': w['finishedUptime'], 'axAfter': diagnostic['observations'][1],
            'focusOnlyFollowUp': diagnostic['followUp'], 'evaluated': retained['binding']['evaluatedUptime'],
            'officialWallAttachmentBindings': verdict['authoritativeAttachments'],
        },
        'observedNativeToolVersionsFromFrozenBuildReceipt': tools,
        'checks': checks, 'passed': True, 'inputs': inputs,
    }


try:
    result = audit()
except Exception as error:
    result = {'schema': 'mixer.apple-settings-fixed-chunk-native-result-review.1', 'passed': False,
              'error': type(error).__name__ + ': ' + str(error), 'checks': checks, 'inputs': inputs,
              'nativeExecutedByReview': False, 'gaAccepted': False}
print(json.dumps(result, indent=2, sort_keys=True))
sys.exit(0 if result['passed'] else 1)
