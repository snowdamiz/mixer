"""Strict selected-execution import. Inputs are captured by the root-owned runtime adapter.

This module never invokes a tool. Host fixtures can exercise consistency only;
native provenance starts in adapter.capture_official(), not in evidence fields.
"""
import copy
import datetime
from decimal import Decimal, Context, InvalidOperation, MAX_EMAX, MIN_ETINY
import hashlib
import json
import math
import re
from pathlib import Path
import uuid

METHODS = ('test000PublicSettingsFullKeyboardAccess', 'test010ReferenceFirstTab')
CASE = 'keyboard-enabled-off'
SOURCE = 'f402eba7b6fa8abf2671e3a95441351dace37f291a9d55024232c9112b2720fb'
PRODUCT = '495f83c4702f7b229be495756f0a524c700f07159c5e21975dea471d118a8904'
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



def root_datetime(value):
    """Validate exact schema 5 ISO lexemes before any ordering use.

    The emitter is datetime.now(UTC).isoformat(). Coordinated root choice also
    retains canonical whole-minute offsets. Fractions have exactly six digits
    when present; unsupported precision and offset seconds fail closed.
    """
    require(type(value) is str and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{6})?[+-][0-9]{2}:[0-9]{2}',value) is not None,
            'Canonical exactly representable root ISO timestamp required')
    try:
        stamp=datetime.datetime.fromisoformat(value)
    except (ValueError,OverflowError) as error:
        raise ValueError('Valid canonical root calendar/time/offset required') from error
    precision='microseconds' if value[19:20]=='.' else 'seconds'
    require(stamp.isoformat(timespec=precision)==value,'Canonical exact root timestamp roundtrip differs')
    return stamp


def datetime_ns(value):
    stamp=root_datetime(value)
    delta=stamp.astimezone(datetime.timezone.utc)-datetime.datetime(1970,1,1,tzinfo=datetime.timezone.utc)
    return ((delta.days*86400+delta.seconds)*1_000_000_000+delta.microseconds*1000)


MAX_TIMESTAMP_TOKEN_BYTES = 1024
# The ordinary JSON pass already rejects numbers outside finite binary64 range.
# Its largest accepted second value has at most 309 integer digits, hence at
# most 318 nanosecond digits. Check before any power or integer construction.
MAX_TIMESTAMP_NS_DIGITS = 318


def decimal_timestamp_ns(value):
    """Exact tuple conversion; no Decimal arithmetic or ambient context reads.

    A genuine sub-nanosecond endpoint remains incomplete evidence. Trailing
    decimal zeroes and exponent notation are accepted when exactly integral.
    Work is bounded by the token/coefficient and result lengths, never by an
    attacker-controlled exponent. Even extreme zero exponents need no power.
    """
    require(type(value) is Decimal and value.is_finite(),'Original finite decimal wall-time token required')
    sign,digits,exponent=value.as_tuple()
    require(len(digits)<=MAX_TIMESTAMP_TOKEN_BYTES,'Timestamp coefficient exceeds importer bound')
    nonzero=any(digits)
    require(not sign or not nonzero,'Original nonnegative decimal wall-time token required')
    if not nonzero:return 0
    power=exponent+9
    if power<0:
        cut=-power
        require(cut<len(digits) and not any(digits[-cut:]),'Official timestamp exceeds nanosecond representation; ordering is incomplete')
        digits=digits[:-cut]
        power=0
    require(len(digits)+power<=MAX_TIMESTAMP_NS_DIGITS,'Timestamp nanosecond range exceeds importer bound')
    coefficient=0
    for digit in digits:coefficient=coefficient*10+digit
    return coefficient*10**power


def decimal_document(raw):
    # parse() first validates duplicates, raw syntax, depth and finiteness. The
    # second pass retains original decimal lexemes exclusively for wall ordering.
    parse(raw)
    def exact_number(token):
        require(len(token)<=MAX_TIMESTAMP_TOKEN_BYTES,'Timestamp decimal token exceeds importer bound')
        # JSON syntax is already checked. Bound effective exponent before exact
        # construction. The private context only receives invalid-conversion
        # signals; caller flags, traps, precision and rounding are never used.
        parts=re.fullmatch(r'-?(0|[1-9][0-9]*)(?:\.([0-9]+))?(?:[eE]([+-]?[0-9]+))?',token)
        require(parts is not None,'Bounded exact JSON numeric token required')
        fraction=parts[2] or ''
        exponent=int(parts[3] or '0')-len(fraction)
        require(MIN_ETINY<=exponent<=MAX_EMAX,'Unrepresentable exact decimal exponent')
        try:return Decimal(token,context=Context(traps=[InvalidOperation]))
        except InvalidOperation as error:raise ValueError('Unrepresentable exact decimal token') from error
    return json.loads(raw.decode('utf-8'),parse_float=exact_number,parse_int=exact_number)


def signature(value):
    require(type(value) is list and len(value)==4,'Closed native file signature required')
    inode,mtime,size,digest_value=value
    require(type(inode) is int and inode>0 and type(mtime) is int and mtime>=0 and type(size) is int and 0<size<=16_000_000,'Exact native inode/nanosecond mtime/byte length required')
    require(type(digest_value) is str and len(digest_value)==64 and all(c in '0123456789abcdef' for c in digest_value),'Original native file SHA256 shape required')
    return value


def validate_root(value, packet_sha=None, fresh=False):
    require(type(value) is dict and set(value) == {'schema','runID','packetSHA256','selectedAtUTC','ownedSimulatorIdentity','sourceTreeSHA256','productArchiveSHA256','developerDirectory','baselineDevices','baselineFrontends'}, 'Closed root selection required')
    require(value['schema'] == 'mixer.apple-focus-reference-root-selection.9', 'Root selection schema differs')
    require(str(uuid.UUID(value['runID'])) == value['runID'], 'Canonical fresh run UUID required')
    require(type(value['packetSHA256']) is str and len(value['packetSHA256']) == 64 and (packet_sha is None or value['packetSHA256'] == packet_sha), 'Root selected packet differs')
    require(value['sourceTreeSHA256'] == SOURCE and value['productArchiveSHA256'] == PRODUCT, 'Root source/product identity differs')
    identity = value['ownedSimulatorIdentity']
    require(type(identity) is dict and set(identity) == {'udid','name','runtime','build'}, 'Closed owned simulator identity required')
    require(str(uuid.UUID(identity['udid'])).upper() == identity['udid'] and type(identity['name']) is str and identity['name'].startswith('MixerFocusReferenceV9-'), 'Root-owned canonical simulator identity required')
    require(identity['runtime'] == 'com.apple.CoreSimulator.SimRuntime.iOS-26-5' and identity['build'] == '23F77', 'Pinned runtime/build required')
    require(value['developerDirectory'] == '/Applications/Xcode_26.6.app/Contents/Developer', 'Pinned compiler tools directory required')
    require(type(value['baselineDevices']) is dict and type(value['baselineDevices'].get('devices')) is dict and type(value['baselineFrontends']) is list, 'Root pre-creation baseline required')
    require(all(type(rows) is list and all(type(item) is dict and item.get('udid') != identity['udid'] for item in rows) for rows in value['baselineDevices']['devices'].values()), 'Owned simulator already in root pre-creation baseline')
    selected = root_datetime(value['selectedAtUTC']).astimezone(datetime.timezone.utc)
    if fresh:
        age = datetime.datetime.now(datetime.timezone.utc) - selected
        require(datetime.timedelta(0) <= age <= datetime.timedelta(seconds=300), 'Root selection is stale or future-dated')
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


def official_methods(summary, tests, root, code, exact_summary=None):
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
    require(number(summary.get('startTime')) and number(summary.get('finishTime')), 'Official run time range missing')
    start = datetime_ns(root['selectedAtUTC'])
    # Native callers always pass the original decimal document. The fallback is
    # used only by legacy synthetic fixture helpers before final exact import.
    exact_summary=exact_summary if exact_summary is not None else {key:Decimal(str(summary[key])) for key in ['startTime','finishTime']}
    summary_start=decimal_timestamp_ns(exact_summary['startTime'])
    summary_finish=decimal_timestamp_ns(exact_summary['finishTime'])
    require(start <= summary_start < summary_finish <= start + 660_000_000_000, 'Official run predates/exceeds fresh root selection')
    return rows


def attachments(manifest, payloads, summary, root, exact_manifest, exact_summary):
    require(type(manifest) is list and len(manifest) == 2, 'Exact selected attachment groups required')
    require(type(payloads) is dict, 'Captured file byte mapping required')
    groups, names, digests, selected = set(), set(), set(), {}
    for group_index, group in enumerate(manifest):
        require(type(group) is dict and set(group) == {'attachments','testIdentifier','testIdentifierURL'}, 'Closed official attachment group required')
        method = next((m for m in METHODS if group['testIdentifier'] == 'ToggleUITests/' + m + '()' and group['testIdentifierURL'] == PREFIX + m), None)
        require(method is not None and method not in groups, 'Foreign/duplicate official attachment owner')
        groups.add(method)
        require(type(group['attachments']) is list, 'Official attachment list required')
        for item_index,item in enumerate(group['attachments']):
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
                token=exact_manifest[group_index]['attachments'][item_index].get('timestamp')
                timestamp_ns=decimal_timestamp_ns(token)
                require(decimal_timestamp_ns(exact_summary['startTime']) <= timestamp_ns <= decimal_timestamp_ns(exact_summary['finishTime']), 'Stale/replayed authoritative attachment timestamp')
                digests.add(digest(raw)); selected[role] = {'value':data,'timestamp':item['timestamp'],'timestampNS':timestamp_ns,'file':name,'sha256':digest(raw)}
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
    result = {'schema':'mixer.apple-focus-reference-runtime-import.9','diagnosticOnly':True,'diagnosticOutcome':'unknown','provenanceAccepted':False,'keyInjectionCount':None,'singleTabDiagnosticEvidencePassed':False,'runPassed':False,'completeCaseSet':False,'cursorCompletionCredit':False,'fullSixCaseQualification':False,'nativeKeyboardQualification':False,'carrierAccepted':False,'gaAccepted':False,'physicalPhones':'disconnected-deferred'}
    try:
        root = validate_root(root)
        code = observer_terminal(observer, root, session, streams)
        require(type(cleanup) is list and {x.get('resource') for x in cleanup} == {'loopback-server-shutdown','loopback-server-close','loopback-thread-join','ephemeral-capability-workspace-removal','owned-simulator-and-baseline-reconciliation'} and len(cleanup) == 5 and all(x.get('passed') is True for x in cleanup), 'All five owned cleanup operations must be observed passing')
        require(type(official) is CapturedOfficial and official.rootSHA256 == digest(stable(root)) and official.session == str(session) and type(official.code) is int and official.code == code, 'Official capture belongs to another root-selected run/session/outcome')
        require(type(payloads) is dict and all(type(value) is bytes for value in payloads.values()) and tuple(sorted((name,digest(value)) for name,value in payloads.items())) == official._payloadSHA256, 'Attachment bytes differ from actual selected export capture')
        require(type(captures) is dict and all(type(value) is bytes for value in captures.values()) and tuple(sorted((name,digest(value)) for name,value in captures.items())) == official._captureSHA256, 'Application observation bytes differ from actual selected capture')
        official = dict(official._raw)
        summary, tests, manifest = (parse(official[key]) for key in ('summary','tests','manifest'))
        exact_summary=decimal_document(official['summary']);exact_manifest=decimal_document(official['manifest'])
        methods=official_methods(summary,tests,root,code,exact_summary)
        joined = attachments(manifest,payloads,summary,root,exact_manifest,exact_summary)
        result.update(provenanceAccepted=True,runID=root['runID'],packetSHA256=root['packetSHA256'],ownedSimulatorIdentity=root['ownedSimulatorIdentity'],sourceTreeSHA256=SOURCE,productArchiveSHA256=PRODUCT,officialMethodResults=methods,officialSHA256={k:digest(v) for k,v in official.items()},authoritativeAttachments={key:{k:v for k,v in row.items() if k!='value'} for key,row in joined.items()})
        require(type(captures) is dict, 'Immutable runtime capture mapping required')
        require(set(captures) <= {'begin','before','after','witness'}, 'Unrelated application captures rejected')
        if 'premise' not in joined: return result
        # A unique attachment proves a premise only after authoritative execution joins.
        require('begin' in captures and 'before' in captures, 'Application begin/baseline missing')
        begin, before = parse(captures['begin']), parse(captures['before'])
        require(begin.get('ownedSimulatorIdentity') == root['ownedSimulatorIdentity'] and begin.get('candidate') == 'diagnostic' and begin.get('case') == CASE and type(begin.get('generation')) is int and begin['generation'] == 1 and type(begin.get('actionIndex')) is int and begin['actionIndex'] == 0, 'Application begin belongs to another selected generation/device')
        start_ns=datetime_ns(root['selectedAtUTC'])
        finish_ns=decimal_timestamp_ns(exact_summary['finishTime'])
        require(type(begin.get('begunWallNS')) is int and start_ns <= begin['begunWallNS'] <= finish_ns, 'Application generation predates selected run')
        signature(before.get('signature'))
        require(begin['begunWallNS'] <= before['signature'][1] <= joined['premise']['timestampNS'], 'Before sample ordering beyond original decimal premise endpoint is incomplete/stale')
        p = joined['premise']['value']
        require(type(before.get('generation')) is int and before['generation'] == begin['generation'] and before.get('action') == 'native-keyboard' and type(before.get('commandGeneration')) is int and before['commandGeneration'] == 2 and p.get('generation') == begin['generation'] and type(p.get('actionIndex')) is int and p['actionIndex'] == 1, 'Generation/action ordering differs')
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
            require(joined['premise']['timestampNS'] <= joined['before']['timestampNS'] <= joined['witness']['timestampNS'] <= joined['verdict']['timestampNS'], 'Official attachment ordering contradicts key action')
            after, retained = parse(captures['after']), parse(captures['witness'])
            signature(after.get('signature'))
            require(before['signature'][1] <= after['signature'][1] <= joined['witness']['timestampNS'], 'Changed/unchanged after sample ordering beyond original decimal witness endpoint is incomplete/stale')
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
