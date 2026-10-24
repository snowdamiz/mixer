"""Finite component export oracle; no engine/coordinator authority is inferred."""
import hashlib
import math
import re
import struct
from pathlib import Path
import support

SCREENSHOTS = ['preview-' + d + '-' + s + '.png' for d in ('false','true') for s in ('false','true')]
SCOPE = 'actual native View component fixture; fixture Input acknowledgements are not authoritative engine commits'

def expected_cases():
    cases = []
    def add(name, proposals=0, acks=0): cases.append((name, proposals, acks))
    for d in ('false','true'):
        for i in ('false','true'): add('endpoint direction='+d+' initial='+i, 1, 1)
    for d in ('false','true'):
        for s in ('false','true'): add('continuous preview direction='+d+' dark='+s)
    for name in ['crossing displacement and return side', 'exact midpoint tie']: add(name)
    add('horizontal side release outside row',1,1)
    for y in ('-66.0','198.0','-66.01','198.01'): add('corridor boundary y='+y, int(y in ('-66.0','198.0')), int(y in ('-66.0','198.0')))
    add('label held tap no long press commit',1,1)
    for name in ['label horizontal drift cancels','native parent vertical scroll','native parent diagonal vertical dominance','history crossing and return','extra pointer cancels no transfer','active pointer lost','ACTION_OUTSIDE cancellation','disabled mid drag','equal binding replacement','frame change mid drag','parent rebinding mid drag','detach mid drag','visibility loss','window focus loss callback','fixture environment gate closes synchronously','local interaction closes before preview']: add(name)
    add('engine-style rejected fixture proposal restores latest',1)
    add('synchronous newer binding wins',1,1)
    add('synchronous retirement restores old view',1)
    add('synchronous record replacement unaffected by old restoration',1)
    add('native accessibility role checked and click',1,1)
    for name in ['disabled accessibility rejection','stale accessibility and keyboard rejection']: add(name)
    for name in ['native keyboard activation','native key repeat does not multiply']: add(name,1,1)
    add('cancelled native key no activation')
    for name in ['keyboard during held touch then old UP','accessibility during held touch then old UP']: add(name,1,1)
    add('native focus order retained')
    return cases

def need(value, message):
    if not value: raise ValueError(message)

def _validate_original(native, out, metadata):
    need(type(native) is dict and set(native) == {'schema','scope','status','failure','apkSHA256','sourceClosureSHA256','cases','observations','assertions','events','durationMilliseconds','rawCheckedListenerCallbacks','authoritativeCommits','physicalPhones','TalkBackServiceWorkflow'} and native['schema'] == 1 and type(native['schema']) is int, 'supplement schema')
    need(native['status'] == 'passed-component-only' and native['failure'] is None, 'component native fixture failed')
    need(native['scope'] == SCOPE and native['rawCheckedListenerCallbacks'] is None and native['authoritativeCommits'] is None, 'component scope cannot imply engine authority')
    for key in ('apkSHA256', 'sourceClosureSHA256'): need(native[key] == metadata[key], 'component identity ' + key)
    for key, maximum in [('assertions',512), ('events',512), ('durationMilliseconds',120000)]:
        need(type(native[key]) is int and 0 < native[key] <= maximum, 'component counter ' + key)
    need(native['events'] + 1 <= 512, 'one history MotionEvent is outside fixture counter; actual constructed event bound')
    cases = native['cases']; expected = expected_cases()
    need(type(cases) is list and len(cases) == len(expected) <= 64, 'complete exact component case matrix required')
    need(native['assertions'] >= len(cases)*2, 'component assertion minimum')
    for index, (case, (name, proposals, acknowledgements)) in enumerate(zip(cases, expected),1):
        need(set(case) == {'id','name','status','proposals','fixtureAcknowledgements','authoritativeCommits','rawCheckedListenerCallbacks'}, 'component case schema')
        need(type(case['id']) is int and case['id'] == index and case['name'] == name and case['status'] == 'passed-component-native', 'component case order/outcome')
        need(type(case['proposals']) is int and case['proposals'] == proposals and type(case['fixtureAcknowledgements']) is int and case['fixtureAcknowledgements'] == acknowledgements, 'observed proposal/fixture acknowledgement count')
        need(case['authoritativeCommits'] is None and case['rawCheckedListenerCallbacks'] is None, 'component authority must remain null')
    rows = native['observations']
    need(type(rows) is list and 1 <= len(rows) <= 2048, 'component observation bound')
    direct = [r for r in rows if 'action' in r]
    need(len(direct) + 18 == native['events'], 'fixture counter must equal direct touch observations plus eighteen worker requests')
    previous = {}
    for row in direct:
        need(set(row) == {'case','route','action','pointerCount','pointerId','x','y','eventTime','returned','nativeChecked','boundChecked','proposals','fixtureAcknowledgements','pressed'}, 'direct component touch observation schema')
        need(type(row['case']) is int and 1 <= row['case'] <= 45 and row['route'] == 'actual View.onTouchEvent component', 'component direct touch route')
        need(type(row['action']) is int and row['action'] in (0,1,2,3,4,261) and type(row['pointerCount']) is int and row['pointerCount'] in (1,2) and type(row['pointerId']) is int and row['pointerId'] in (7,8), 'component pointer schema')
        need(all(type(row[k]) in (int,float) and math.isfinite(row[k]) for k in ('x','y')), 'component finite coordinates')
        need(type(row['eventTime']) is int and row['eventTime'] > previous.get(row['case'],-1), 'component per-case event timestamp order')
        previous[row['case']] = row['eventTime']
        need(all(type(row[k]) is bool for k in ('returned','nativeChecked','boundChecked','pressed')) and row['nativeChecked'] == row['boundChecked'], 'component state observation schema')
        need(all(type(row[k]) is int and 0 <= row[k] <= 1 for k in ('proposals','fixtureAcknowledgements')) and row['fixtureAcknowledgements'] <= row['proposals'], 'component direct boundary counter schema')
    snapshots = [r for r in rows if 'name' in r]
    need([r['name']+'.png' for r in snapshots] == SCREENSHOTS, 'exact four preview snapshots')
    for row in snapshots:
        need(row['checked'] is False and row['boundChecked'] is False and row['proposals'] == 0 and row['route'] == 'UiAutomation.takeScreenshot after native idle', 'preview committed component state')
        need(set(row['geometry']) == {'offCenter','onCenter','trackX'} and all(type(v) in (int,float) and math.isfinite(v) for v in row['geometry'].values()), 'finite preview geometry')
    final = rows[-1]
    need(final.get('finally') is True and final['pressed'] is False and final['parentAcquired'] == final['parentReleased'], 'component final cleanup observation')
    need(native['physicalPhones'] == 'deferred disconnected' and native['TalkBackServiceWorkflow'] == 'NOT RUN', 'component deferred scope')
    return {'status':'passed-independent-component-export-oracle', 'cases':len(cases), 'assertions':native['assertions'], 'fixtureCountedEvents':native['events'], 'knownUncountedHistoricalMotionEvents':1, 'boundedConstructedMotionEvents':native['events']+1, 'directViewTouchObservations':len(direct), 'workerSendPointerSyncRequests':18, 'eventScope':'direct component calls plus eighteen worker requests; Activity delivery counts not observed by this supplement', 'authoritativeCommits':None, 'rawCheckedListenerCallbacks':None, 'scope':SCOPE, 'screenshotPixelAcceptance':'pending root visual inspection; screenshot export is not a pixel oracle'}

def collect(run, adb, package, out, metadata, code, instrument):
    """Pull only literal finite names. Exported JSON is bound by instrumentation SHA."""
    exported, payload = run('native-results-export', adb + ['exec-out','run-as',package,'cat','files/toggle-supplement-results.json'], allow_failure=True)
    need(exported == 0 and len(payload) <= 8388608, 'bounded component result export unavailable')
    declared = re.findall(rb'INSTRUMENTATION_RESULT: exportSHA256=([0-9a-f]{64})', instrument)
    need(declared == [hashlib.sha256(payload).hexdigest().encode()], 'native component JSON export binding')
    native = support.read_bytes(payload)
    (out / 'toggle-supplement-results.json').write_bytes(payload)
    screenshots = {}; total = len(payload)
    for name in SCREENSHOTS:
        # Failed native attempts may have only a prefix of the four images. Keep available evidence.
        result, image = run('export-'+name, adb + ['exec-out','run-as',package,'cat','files/'+name], allow_failure=True)
        if result: continue
        total += len(image)
        need(33 <= len(image) <= 8388608 and total <= 8388608, 'component total export budget')
        need(image[:8] == b'\x89PNG\r\n\x1a\n' and image[12:16] == b'IHDR' and struct.unpack('>II',image[16:24]) == (1206,2622), 'component PNG viewport')
        (out / name).write_bytes(image); screenshots[name] = support.data_bind(image)
    support.save(out / 'component-screenshot-exports.json', {'files':screenshots,'bindingScope':'host hashes after explicit finite run-as pull; native result export has instrumentation hash; PNG pixel review pending'})
    result = validate(native,out,metadata)
    need(set(screenshots) == set(SCREENSHOTS), 'four actual PNG exports required')
    need(code == 0 and b'INSTRUMENTATION_RESULT: status=passed-component-only' in instrument and b'INSTRUMENTATION_CODE: -1' in instrument, 'component instrumentation failed')
    return result

RESET_FIELDS={'schema','scope','status','failure','apkSHA256','sourceClosureSHA256','cases','observations','assertions','events','durationMilliseconds','rawCheckedListenerCallbacks','authoritativeCommits','physicalPhones','TalkBackServiceWorkflow','addedSetupAssertions','originalAssertionCounter'}
def validate(native,out,metadata):
    need(type(native) is dict and set(native)==RESET_FIELDS,'reset supplement exact schema')
    for key in ('assertions','addedSetupAssertions','originalAssertionCounter'):
        need(type(native[key]) is int and 0<=native[key]<=512,'reset integer counter '+key)
    need(native['assertions']==native['originalAssertionCounter']+native['addedSetupAssertions'] and native['addedSetupAssertions']<=6,'reset assertion counter sum')
    original={key:value for key,value in native.items() if key not in ('addedSetupAssertions','originalAssertionCounter')}
    original['assertions']=native['originalAssertionCounter']
    result=_validate_original(original,out,metadata)
    need(native['addedSetupAssertions']==6,'all six scroll setup assertions required')
    result.update(assertions=native['assertions'],originalAssertionCounter=native['originalAssertionCounter'],addedSetupAssertions=native['addedSetupAssertions'])
    return result
