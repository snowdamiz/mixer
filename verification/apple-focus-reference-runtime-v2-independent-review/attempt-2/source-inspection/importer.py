"""Strict selected-execution import. Inputs are captured by the root-owned runtime adapter.

This module never invokes a tool. Host fixtures can exercise consistency only;
native provenance starts in adapter.capture_official(), not in evidence fields.
"""
import copy
import datetime
import hashlib
import json
import math
from pathlib import Path
import uuid

METHODS = ('test000PublicSettingsFullKeyboardAccess', 'test010ReferenceFirstTab')
CASE = 'keyboard-enabled-off'
SOURCE = '696bfdd8a31be7b4d9ba49f57783625c7edbb75c126bb4696e31acc5aa0f238a'
PRODUCT = '0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8'
PREFIX = 'test://com.apple.xcode/MixerToggleUITests/MixerToggleUITests/ToggleUITests/'


def require(value, message):
    if not value: raise ValueError(message)


def digest(data): return hashlib.sha256(data).hexdigest()


def stable(value): return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def parse(raw):
    require(type(raw) is bytes and len(raw) <= 2_000_000, 'Bounded raw JSON bytes required')
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, 'Duplicate JSON object member')
            value[key] = item
        return value
    def constant(value): raise ValueError('Non-finite JSON constant: ' + value)
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
    def finite(item, depth=0):
        require(depth <= 100, 'JSON nesting exceeds importer bound')
        if type(item) is float: require(math.isfinite(item), 'Overflowed JSON number')
        elif type(item) is dict:
            for nested in item.values(): finite(nested, depth + 1)
        elif type(item) is list:
            for nested in item: finite(nested, depth + 1)
    finite(value)
    return value


def read(path):
    require(path.resolve() == path and path.is_file() and not path.is_symlink(), 'Canonical regular evidence required')
    return parse(path.read_bytes())


def number(value): return type(value) in (int, float) and math.isfinite(value) and value >= 0


def validate_root(value, packet_sha=None, fresh=False):
    require(type(value) is dict and set(value) == {'schema','runID','packetSHA256','selectedAtUTC','ownedSimulatorIdentity','sourceTreeSHA256','productArchiveSHA256','developerDirectory','baselineDevices','baselineFrontends'}, 'Closed root selection required')
    require(value['schema'] == 'mixer.apple-focus-reference-root-selection.1', 'Root selection schema differs')
    require(str(uuid.UUID(value['runID'])) == value['runID'], 'Canonical fresh run UUID required')
    require(type(value['packetSHA256']) is str and len(value['packetSHA256']) == 64 and (packet_sha is None or value['packetSHA256'] == packet_sha), 'Root selected packet differs')
    require(value['sourceTreeSHA256'] == SOURCE and value['productArchiveSHA256'] == PRODUCT, 'Root source/product identity differs')
    identity = value['ownedSimulatorIdentity']
    require(type(identity) is dict and set(identity) == {'udid','name','runtime','build'}, 'Closed owned simulator identity required')
    require(str(uuid.UUID(identity['udid'])).upper() == identity['udid'] and type(identity['name']) is str and identity['name'].startswith('MixerFocusReferenceV2-'), 'Root-owned canonical simulator identity required')
    require(identity['runtime'] == 'com.apple.CoreSimulator.SimRuntime.iOS-26-5' and identity['build'] == '23F77', 'Pinned runtime/build required')
    require(value['developerDirectory'] == '/Applications/Xcode_26.6.app/Contents/Developer', 'Pinned compiler tools directory required')
    require(type(value['baselineDevices']) is dict and type(value['baselineDevices'].get('devices')) is dict and type(value['baselineFrontends']) is list, 'Root pre-creation baseline required')
    require(all(type(rows) is list and all(type(item) is dict and item.get('udid') != identity['udid'] for item in rows) for rows in value['baselineDevices']['devices'].values()), 'Owned simulator already in root pre-creation baseline')
    selected = datetime.datetime.fromisoformat(value['selectedAtUTC'])
    require(selected.tzinfo is not None, 'Timezone-aware root selection required')
    if fresh:
        age = (datetime.datetime.now(datetime.timezone.utc) - selected).total_seconds()
        require(0 <= age <= 300, 'Root selection is stale or future-dated')
    return copy.deepcopy(value)


def command_argv(root, session):
    return [root['developerDirectory'] + '/usr/bin/xcodebuild','test-without-building','-xctestrun',str(session / 'session.xctestrun'),'-destination','platform=iOS Simulator,id=' + root['ownedSimulatorIdentity']['udid'],'-parallel-testing-enabled','NO','-maximum-concurrent-test-simulator-destinations','1','-resultBundlePath',str(session / 'session.xcresult')] + ['-only-testing:MixerToggleUITests/ToggleUITests/' + method for method in METHODS]


def observer_terminal(observer, root, session, streams):
    expected = command_argv(root, session)
    require(observer.get('schema') == 'mixer.apple-command-finalization-observer.2' and observer.get('argv') == expected and observer.get('resultBundle') == str(session / 'session.xcresult'), 'Observer selected command/result differs')
    require(type(observer.get('exitCode')) is int and observer['exitCode'] in (0,65), 'Terminal selected XCTest outcome required')
    require(observer.get('startNewSession') is True and observer.get('successInferredFromConsoleOrMarkers') is False, 'Owned observed command required')
    pid, group = observer.get('PID'), observer.get('processGroup')
    require(type(group) is int and group > 0 and type(pid) is int and pid == group, 'Owned process group identity required')
    owned = observer.get('ownedProcessGroup', {})
    require(owned.get('state') == 'absent' and type(owned.get('targetProcessGroup')) is int and owned.get('targetProcessGroup') == group, 'Owned group absence not observed')
    cleanup = observer.get('cleanup', {})
    require((cleanup.get('attempted') is True and cleanup.get('complete') is True) or (cleanup.get('attempted') is False and cleanup.get('complete') is None and cleanup.get('signals') == []), 'Observer cleanup incomplete/unobserved')
    require(set(observer.get('streams', {})) == {'stdout','stderr'} and set(streams) == {'stdout','stderr'}, 'Two observed streams required')
    for name, stream in observer['streams'].items():
        raw = streams[name]
        require(type(raw) is bytes and stream.get('eof') is True and stream.get('readerFailed') is False and stream.get('readerErrors') == [], 'Unobserved/failed stream EOF')
        require(type(stream.get('observedBytes')) is int and type(stream.get('retainedBytes')) is int and stream['observedBytes'] == stream.get('retainedBytes') == len(raw) and stream.get('retainedSHA256') == digest(raw), 'Retained stream bytes differ')
    return observer['exitCode']


def official_methods(summary, tests, root, code):
    """Exact official execution/device identities are established before attachments."""
    identity = root['ownedSimulatorIdentity']
    def device(value):
        require(value.get('deviceId') == identity['udid'] and value.get('deviceName') == identity['name'] and value.get('platform') == 'iOS Simulator' and value.get('osVersion') == '26.5' and value.get('osBuildNumber') == identity['build'] and value.get('architecture') == 'arm64', 'Official selected device differs')
    require(type(tests.get('devices')) is list and len(tests['devices']) == 1, 'Exactly one official device required')
    device(tests['devices'][0])
    configs = summary.get('devicesAndConfigurations')
    require(type(configs) is list and len(configs) == 1, 'Exactly one official configuration required')
    device(configs[0]['device'])
    require(configs[0].get('testPlanConfiguration') == {'configurationId':'1','configurationName':'Test Scheme Action'}, 'Official configuration differs')
    found = []
    def visit(value):
        if type(value) is dict:
            if value.get('nodeType') == 'Test Case': found.append(value)
            for nested in value.values(): visit(nested)
        elif type(value) is list:
            for nested in value: visit(nested)
    visit(tests)
    require(len(found) == 2, 'Exactly two official test executions required; retries/unrelated tests rejected')
    rows = {}
    for node in found:
        method = next((method for method in METHODS if node.get('nodeIdentifier') == 'ToggleUITests/' + method + '()' and node.get('nodeIdentifierURL') == PREFIX + method and node.get('name') == method + '()'), None)
        require(method is not None and method not in rows and node.get('result') in ('Passed','Failed'), 'Foreign/duplicate/incomplete selected test identity')
        require(type(node.get('children',[])) is list and all(type(child) is dict and set(child) == {'name','nodeType'} and child['nodeType'] == 'Failure Message' and type(child['name']) is str for child in node.get('children',[])), 'Repeated/subexecutions beneath selected method rejected')
        rows[method] = node['result']
    require(set(rows) == set(METHODS) and rows[METHODS[0]] == 'Passed', 'Official Settings execution must pass exactly once')
    passed = sum(value == 'Passed' for value in rows.values())
    for key, expected in [('totalTestCount',2),('passedTests',passed),('failedTests',2-passed),('skippedTests',0),('expectedFailures',0)]:
        require(type(summary.get(key)) is int and summary[key] == expected, 'Official summary count differs: ' + key)
        if key != 'totalTestCount': require(type(configs[0].get(key)) is int and configs[0][key] == expected, 'Official configuration count differs')
    require(summary.get('result') == ('Passed' if passed == 2 else 'Failed') and code == (0 if passed == 2 else 65), 'Command outcome contradicts official tests')
    require(number(summary.get('startTime')) and number(summary.get('finishTime')) and summary['startTime'] < summary['finishTime'], 'Official run time range missing')
    start = datetime.datetime.fromisoformat(root['selectedAtUTC']).timestamp()
    require(start <= summary['startTime'] <= summary['finishTime'] <= start + 660, 'Official run predates/exceeds fresh root selection')
    return rows


def attachments(manifest, payloads, summary, root):
    require(type(manifest) is list and len(manifest) == 2, 'Exact selected attachment groups required')
    require(type(payloads) is dict, 'Captured file byte mapping required')
    groups, names, digests, selected = set(), set(), set(), {}
    for group in manifest:
        require(type(group) is dict and set(group) == {'attachments','testIdentifier','testIdentifierURL'}, 'Closed official attachment group required')
        method = next((m for m in METHODS if group['testIdentifier'] == 'ToggleUITests/' + m + '()' and group['testIdentifierURL'] == PREFIX + m), None)
        require(method is not None and method not in groups, 'Foreign/duplicate official attachment owner')
        groups.add(method)
        require(type(group['attachments']) is list, 'Official attachment list required')
        for item in group['attachments']:
            name = item['exportedFileName']
            require(type(name) is str and Path(name).name == name and name not in names and name != 'manifest.json', 'Duplicate/unsafe official attachment file')
            names.add(name)
            require(item.get('deviceId') == root['ownedSimulatorIdentity']['udid'] and item.get('deviceName') == root['ownedSimulatorIdentity']['name'] and item.get('configurationName') == 'Test Scheme Action', 'Foreign attachment device/configuration')
            require(name in payloads and type(payloads[name]) is bytes, 'Official attachment bytes missing')
            raw = payloads[name]
            human = item.get('suggestedHumanReadableName')
            require(type(human) is str, 'Official attachment name missing')
            if name.endswith('.json'):
                data = parse(raw)
                # Every selected JSON attachment is a closed known diagnostic role.
                role = next((role for prefix, role in [('Reference first-Tab precondition_', 'premise'),('Before public key acquire_', 'before'),('Public keyboard acquire_', 'witness'),('Strict keyboard verdict acquire_', 'verdict'),('Public Settings setup-enabled_', 'settings')] if human.startswith(prefix)), None)
                require(role is not None, 'Unrelated JSON attachment rejected')
                require((role == 'settings') is (method == METHODS[0]), 'Attachment joins unrelated selected method')
                require(role not in selected and digest(raw) not in digests, 'Duplicate authoritative attachment role/payload')
                require(number(item.get('timestamp')) and summary['startTime'] <= item['timestamp'] <= summary['finishTime'], 'Stale/replayed authoritative attachment timestamp')
                digests.add(digest(raw)); selected[role] = {'value':data,'timestamp':item['timestamp'],'file':name,'sha256':digest(raw)}
    require(groups == set(METHODS) and names == set(payloads), 'Unmanifested/missing attachment files rejected')
    settings = selected.get('settings', {}).get('value')
    require(type(settings) is dict and settings.get('schema') == 'mixer.apple-toggle.keyboard-settings.1' and settings.get('step') == 'setup-enabled' and settings.get('passed') is True and settings.get('bundle') == 'com.apple.Preferences' and settings.get('route') == ['Accessibility','Keyboards & Typing','Full Keyboard Access'] and settings.get('fullKeyboardAccessValue') == '1', 'Unique official passing Settings attachment required')
    return selected


_CAPTURE_TOKEN = object()


class CapturedOfficial:
    """An in-process capture capability; deliberately has no JSON loader.

    Only the selected runtime tool-call adapter constructs this from official
    return bytes. Host controls use the same boundary with explicit fake tools.
    """
    __slots__ = ('rootSHA256','session','code','_raw','_payloadSHA256','_captureSHA256')
    def __init__(self, token, root, session, code, raw, payloads, captures):
        require(token is _CAPTURE_TOKEN, 'Official capture can only be minted by the trusted adapter')
        object.__setattr__(self,'rootSHA256',digest(stable(root)))
        object.__setattr__(self,'session',str(session))
        object.__setattr__(self,'code',code)
        object.__setattr__(self,'_raw',tuple((key,raw[key]) for key in ('summary','tests','manifest')))
        object.__setattr__(self,'_payloadSHA256',tuple(sorted((name,digest(value)) for name,value in payloads.items())))
        object.__setattr__(self,'_captureSHA256',tuple(sorted((name,digest(value)) for name,value in captures.items())))
    def __setattr__(self, name, value):
        raise TypeError('Official capture is immutable')


def import_selected(root, session, observer, streams, official, payloads, captures, cleanup, oracle, classifier):
    """Called only with adapter-captured official outputs; never mint root context from evidence."""
    result = {'schema':'mixer.apple-focus-reference-runtime-import.2','diagnosticOnly':True,'diagnosticOutcome':'unknown','provenanceAccepted':False,'keyInjectionCount':None,'singleTabDiagnosticEvidencePassed':False,'runPassed':False,'completeCaseSet':False,'cursorCompletionCredit':False,'fullSixCaseQualification':False,'nativeKeyboardQualification':False,'carrierAccepted':False,'gaAccepted':False,'physicalPhones':'disconnected-deferred'}
    try:
        root = validate_root(root)
        code = observer_terminal(observer, root, session, streams)
        require(type(cleanup) is list and {x.get('resource') for x in cleanup} == {'loopback-server-shutdown','loopback-server-close','loopback-thread-join','ephemeral-capability-workspace-removal','owned-simulator-and-baseline-reconciliation'} and len(cleanup) == 5 and all(x.get('passed') is True for x in cleanup), 'All five owned cleanup operations must be observed passing')
        require(type(official) is CapturedOfficial and official.rootSHA256 == digest(stable(root)) and official.session == str(session) and type(official.code) is int and official.code == code, 'Official capture belongs to another root-selected run/session/outcome')
        require(type(payloads) is dict and all(type(value) is bytes for value in payloads.values()) and tuple(sorted((name,digest(value)) for name,value in payloads.items())) == official._payloadSHA256, 'Attachment bytes differ from actual selected export capture')
        require(type(captures) is dict and all(type(value) is bytes for value in captures.values()) and tuple(sorted((name,digest(value)) for name,value in captures.items())) == official._captureSHA256, 'Application observation bytes differ from actual selected capture')
        official = dict(official._raw)
        summary, tests, manifest = (parse(official[key]) for key in ('summary','tests','manifest'))
        methods = official_methods(summary, tests, root, code)
        joined = attachments(manifest, payloads, summary, root)
        result.update(provenanceAccepted=True,runID=root['runID'],packetSHA256=root['packetSHA256'],ownedSimulatorIdentity=root['ownedSimulatorIdentity'],sourceTreeSHA256=SOURCE,productArchiveSHA256=PRODUCT,officialMethodResults=methods,officialSHA256={k:digest(v) for k,v in official.items()},authoritativeAttachments={key:{k:v for k,v in row.items() if k!='value'} for key,row in joined.items()})
        require(type(captures) is dict, 'Immutable runtime capture mapping required')
        require(set(captures) <= {'begin','before','after','witness'}, 'Unrelated application captures rejected')
        if 'premise' not in joined: return result
        # A unique attachment proves a premise only after authoritative execution joins.
        require('begin' in captures and 'before' in captures, 'Application begin/baseline missing')
        begin, before = parse(captures['begin']), parse(captures['before'])
        require(begin.get('ownedSimulatorIdentity') == root['ownedSimulatorIdentity'] and begin.get('candidate') == 'diagnostic' and begin.get('case') == CASE and type(begin.get('generation')) is int and begin['generation'] == 1 and type(begin.get('actionIndex')) is int and begin['actionIndex'] == 0, 'Application begin belongs to another selected generation/device')
        start_ns = int(datetime.datetime.fromisoformat(root['selectedAtUTC']).timestamp() * 1_000_000_000)
        finish_ns = int(summary['finishTime'] * 1_000_000_000)
        require(type(begin.get('begunWallNS')) is int and start_ns <= begin['begunWallNS'] <= finish_ns, 'Application generation predates selected run')
        require(type(before.get('signature')) is list and len(before['signature']) == 4 and type(before['signature'][1]) is int and begin['begunWallNS'] <= before['signature'][1] <= finish_ns, 'Before sample is stale/replayed')
        p = joined['premise']['value']
        require(type(before.get('generation')) is int and before['generation'] == begin['generation'] and before.get('action') == 'native-keyboard' and before.get('commandGeneration') == 2 and p.get('generation') == begin['generation'] and type(p.get('actionIndex')) is int and p['actionIndex'] == 1, 'Generation/action ordering differs')
        require(type(before.get('observation')) is dict and type(before.get('signature')) is list and len(before['signature']) == 4, 'Immutable before observation/signature required')
        before_app = before['observation']
        # The authoritative native focus sample must agree with the app carrier sample.
        oracle.ax(p['before'])
        require(type(before_app['state']['focused']) is bool and p['before']['elements']['authored-toggle']['hasFocus'] is before_app['state']['focused'], 'Before AX/application carrier focus contradicts')
        if p.get('passed') is False:
            require(not ({'before','witness','verdict'} & set(joined)) and not ({'after','witness'} & set(captures)), 'Returned key evidence contradicts failed reference premise')
            classified = classifier.result([p], [], oracle)
        else:
            if not {'before','witness','verdict'} <= set(joined) or not {'after','witness'} <= set(captures):
                return result
            b, w, v = (joined[key]['value'] for key in ('before','witness','verdict'))
            require(set(b) == {'case','phase','key','generation','actionIndex','before'} and b['case'] == CASE and b['phase'] == 'acquire' and b['key'] == 'tab' and type(b['generation']) is int and b['generation'] == 1 and type(b['actionIndex']) is int and b['actionIndex'] == 1 and classifier.strict_json_equal(b['before'], p['before']), 'Before-public-key sample differs from unique premise')
            require(joined['premise']['timestamp'] <= joined['before']['timestamp'] <= joined['witness']['timestamp'] <= joined['verdict']['timestamp'], 'Official attachment ordering contradicts key action')
            after, retained = parse(captures['after']), parse(captures['witness'])
            require(type(after.get('signature')) is list and len(after['signature']) == 4 and type(after['signature'][1]) is int and before['signature'][1] <= after['signature'][1] <= finish_ns, 'After sample is stale/replayed')
            require(type(after.get('observation')) is dict and type(after.get('signature')) is list and len(after['signature']) == 4, 'Immutable after observation/signature required')
            require(classifier.strict_json_equal(w, v.get('keyboardWitness')) and classifier.strict_json_equal(retained, {'binding':v.get('keyboardBinding'),'witness':w}) and classifier.strict_json_equal(after.get('verdict'),v), 'Returned/retained witness/verdict contradicts official attachment')
            require(v.get('ownedSimulatorIdentity') == root['ownedSimulatorIdentity'] and type(v.get('generation')) is int and v['generation'] == 1 and type(v.get('actionIndex')) is int and v['actionIndex'] == 1, 'Original verdict runtime identity differs')
            changed = not classifier.strict_json_equal(before['signature'],after['signature'])
            classified = classifier.result([p],[v],oracle,[{'before':before_app,'after':after['observation'],'fileChanged':changed}])
        result['classification'] = classified
        result['keyInjectionCount'] = classified['keyInjectionCount']
        status = classified['status']
        if status == 'failed-reference-precondition':
            require(methods[METHODS[1]] == 'Failed', 'Failed premise contradicts official test pass')
            result['diagnosticOutcome'] = 'failed-reference-precondition-zero-injection'
        elif status == 'one-original-oracle-result':
            passed = classified['singleTabDiagnosticEvidencePassed']
            require(methods[METHODS[1]] == ('Passed' if passed else 'Failed'), 'Original verdict contradicts official test outcome')
            result.update(diagnosticOutcome='one-strict-original-verdict-passed' if passed else 'one-strict-original-verdict-failed',singleTabDiagnosticEvidencePassed=passed)
        elif status == 'invalid-or-incomplete-evidence': raise ValueError(classified.get('failure','Classifier rejected incomplete evidence'))
    except (KeyError,ValueError,TypeError,IndexError,AttributeError,OverflowError,RecursionError,UnicodeError) as error:
        result.update(diagnosticOutcome='invalid-or-incomplete-evidence',provenanceAccepted=False,keyInjectionCount=None,singleTabDiagnosticEvidencePassed=False,failure=type(error).__name__+': '+str(error))
    return result
