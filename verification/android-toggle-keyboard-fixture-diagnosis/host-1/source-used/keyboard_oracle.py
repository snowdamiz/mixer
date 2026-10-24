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

KEYBOARD_FIELDS={'schema','scope','status','failure','apkSHA256','sourceClosureSHA256','cases','observations','assertions','events','durationMilliseconds','rawCheckedListenerCallbacks','authoritativeCommits','physicalPhones','TalkBackServiceWorkflow','addedSetupAssertions','originalAssertionCounter','addedScrollSetupAssertions','addedKeyboardSetupAssertions','keyboardSetupEvents','keyboardSetup'}
STAGES=['keyboard.control.install.before','keyboard.before','keyboard.navigation.after','keyboard.control.focus.after','keyboard.control.removed','keyboard.toggle.focus.after','keyboard.toggle.focus.settled','keyboard.cleanup']
VIEW_FIELDS={'frame','size','measured','screen','window','globalVisible','globalVisibleRect','shown','attached','windowFocused','focused','enabled','layoutRequested','class','identity','id','focusable','focusableInTouchMode','inTouchMode','hasFocus','visibility','windowVisibility'}
VIEW_BOOL={'globalVisible','shown','attached','windowFocused','focused','enabled','layoutRequested','focusable','focusableInTouchMode','inTouchMode','hasFocus'}
STATE_FIELDS={'toggle','control','ancestors','ancestorChainComplete','ancestorFocusBlocked','toggleOwnedVisible','controlOwnedVisible','controlPresent','decorFocusOwner','activityFocusOwner','toggleIsFocusOwner','controlIsFocusOwner','geometry'}
GEOMETRY_FIELDS={'decor','root','scroll','content','toggle','windowVisibleFrame','systemBarInsets','contentLayoutHeight','viewportHeight','contentHeight','positiveContentExtent','computedRange','computedExtent','computedOffset','canScrollUp','canScrollDown','density'}
OBSERVATION_FIELDS={'case','stage','uptime','requestReturned','state','inputOpen','permit','proposals','fixtureAcknowledgements','nativeChecked','boundChecked','pressed','stableToggle','quiet','addedKeyboardSetupAssertionsBefore','addedSetupAssertionsBefore'}
REQUEST_FIELDS={'case','action','keyCode','source','repeat','downTime','eventTime','dispatched'}
TRACE_FIELDS={'stage','case','uptime','returned','action','keyCode','source','repeat','canceled','downTime','eventTime','deviceId'}

def _view(value,nullable=False):
    if value is None:
        need(nullable,'non-null focus view required');return
    need(type(value) is dict and (set(value)==VIEW_FIELDS or set(value)==VIEW_FIELDS|{'descendantFocusability'}),'focus view exact schema')
    need(all(type(value[k]) is bool for k in VIEW_BOOL),'focus view boolean fields')
    for key,size in [('frame',4),('size',2),('measured',2),('screen',2),('window',2),('globalVisibleRect',4)]:
        need(type(value[key]) is list and len(value[key])==size and all(type(v) is int for v in value[key]),'focus integer geometry '+key)
    need(type(value['class']) is str and 0<len(value['class'])<=256,'focus class name')
    need(all(type(value[k]) is int for k in ('identity','id','visibility','windowVisibility')),'focus integer identity/visibility')
    need(value['visibility'] in (0,4,8) and value['windowVisibility'] in (0,4,8),'focus visibility values')
    if 'descendantFocusability' in value:need(type(value['descendantFocusability']) is int and value['descendantFocusability'] in (131072,262144,393216),'ancestor descendant focusability')

def _keyboard(native):
    setup=native['keyboardSetup'];need(type(setup) is dict and set(setup)=={'schema','requests','observations','nativeKeyTrace','dropped','observerFailures'} and type(setup['schema']) is int and setup['schema']==1,'keyboard setup exact schema')
    need(type(setup['dropped']) is int and setup['dropped']==0 and type(setup['observerFailures']) is int and setup['observerFailures']==0,'keyboard trace loss/failure')
    requests=setup['requests'];trace=setup['nativeKeyTrace'];rows=setup['observations']
    need(type(requests) is list and len(requests)==8 and type(trace) is list and len(trace)==16 and type(rows) is list and len(rows)==32,'complete bounded keyboard setup evidence')
    for index,request in enumerate(requests):
        case=40+index//2;action=index%2
        need(type(request) is dict and set(request)==REQUEST_FIELDS,'keyboard request exact schema')
        need(all(type(request[k]) is int for k in ('case','action','keyCode','source','repeat','downTime','eventTime')),'keyboard request integer fields')
        need(request['case']==case and request['action']==action and request['keyCode']==20 and request['source']==257 and request['repeat']==0 and request['dispatched'] is True,'exact dispatched keyboard navigation pair')
        need(0<request['downTime']<=request['eventTime'] and (action==0 or request['downTime']==requests[index-1]['downTime'] and request['eventTime']>=requests[index-1]['eventTime']),'keyboard request time order')
        for half in range(2):
            event=trace[2*index+half]
            need(type(event) is dict and set(event)==TRACE_FIELDS,'native key trace exact schema')
            need(all(type(event[k]) is int for k in ('case','uptime','action','keyCode','source','repeat','downTime','eventTime','deviceId')),'native key integer fields')
            need(event['stage']==('activity.key.before' if half==0 else 'activity.key.after') and event['canceled'] is False and (event['returned'] is None if half==0 else type(event['returned']) is bool),'native key hook route')
            need(all(event[k]==request[k] for k in ('case','action','keyCode','source','repeat','downTime','eventTime')),'actual native key delivery equals request')
    for index,row in enumerate(rows):
        helper=index//8;stage=index%8;case=40+helper;before=5*helper+[0,0,1,2,3,4,4,5][stage]
        need(type(row) is dict and set(row)==OBSERVATION_FIELDS,'keyboard focus observation exact schema')
        need(type(row['case']) is int and row['case']==case and row['stage']==STAGES[stage] and type(row['uptime']) is int and row['uptime']>0,'keyboard observation case/stage/time')
        if stage:need(row['uptime']>=rows[index-1]['uptime'],'keyboard observation time order')
        need(type(row['addedKeyboardSetupAssertionsBefore']) is int and row['addedKeyboardSetupAssertionsBefore']==before and type(row['addedSetupAssertionsBefore']) is int and row['addedSetupAssertionsBefore']==6+before,'keyboard observation assertion classification')
        need(all(type(row[k]) is bool for k in ('inputOpen','permit','nativeChecked','boundChecked','pressed','stableToggle','quiet')),'keyboard observation boolean fields')
        need(row['inputOpen'] and row['permit'] and not row['nativeChecked'] and not row['boundChecked'] and not row['pressed'] and row['stableToggle'] and row['quiet'],'keyboard setup must preserve toggle and input state')
        need(all(type(row[k]) is int and row[k]==0 for k in ('proposals','fixtureAcknowledgements')),'keyboard setup cannot activate toggle')
        need(row['requestReturned'] is True if stage in (3,5) else row['requestReturned'] is None,'one native control/toggle focus request outcome')
        state=row['state'];need(type(state) is dict and set(state)==STATE_FIELDS,'focus state exact schema')
        for key in ('toggle','control','decorFocusOwner','activityFocusOwner'):_view(state[key],key!='toggle')
        need(all(type(state[k]) is bool for k in ('ancestorChainComplete','ancestorFocusBlocked','toggleOwnedVisible','controlOwnedVisible','controlPresent','toggleIsFocusOwner','controlIsFocusOwner')),'focus state boolean fields')
        need(type(state['ancestors']) is list and 1<=len(state['ancestors'])<=16 and state['ancestorChainComplete'] and not state['ancestorFocusBlocked'],'complete unblocked native ancestor chain')
        for ancestor in state['ancestors']:
            _view(ancestor);need('descendantFocusability' in ancestor and ancestor['descendantFocusability']!=393216,'native ancestor does not block descendants')
        toggle=state['toggle'];need(state['toggleOwnedVisible'] and toggle['attached'] and toggle['shown'] and toggle['enabled'] and toggle['windowFocused'] and toggle['focusable'],'owned visible enabled focusable toggle')
        if stage>=2:need(toggle['inTouchMode'] is False,'observed keyboard mode required')
        control=state['control']
        if stage==0:need(control is None and not state['controlPresent'],'control absent before installation')
        else:need(control['class']=='android.widget.Button','ordinary platform Button positive control')
        if stage in (1,2,3):need(state['controlPresent'] and state['controlOwnedVisible'] and control['focusable'] and control['attached'] and control['enabled'],'positive control owned visible focusable')
        if stage>=4:need(not state['controlPresent'] and not control['attached'],'owned control removed before original toggle assertion')
        if stage==3:need(state['controlIsFocusOwner'] and control['focused'],'native Button focus positive control')
        if stage in (5,6,7):need(state['toggleIsFocusOwner'] and toggle['focused'],'original toggle is native focus owner')
        for key,flag,target in [('decorFocusOwner','toggleIsFocusOwner',toggle),('activityFocusOwner','toggleIsFocusOwner',toggle),('decorFocusOwner','controlIsFocusOwner',control),('activityFocusOwner','controlIsFocusOwner',control)]:
            if state[flag]:need(state[key] is not None and state[key]['identity']==target['identity'],'native focus owner identity')
        geometry=state['geometry'];need(type(geometry) is dict and set(geometry)==GEOMETRY_FIELDS,'focus geometry exact schema')
        need(all(geometry['toggle'][key]==toggle[key] for key in ('frame','size','measured','screen','window','attached','shown','windowFocused','focused','enabled')),'public geometry and focus snapshot agree')
        if stage:
            original=rows[helper*8]['state']['toggle']
            need(all(toggle[k]==original[k] for k in ('identity','class','frame','size','measured','screen','window','focusable','focusableInTouchMode','enabled')),'actual original toggle geometry and focus policy unchanged')
    return {'focusHelpers':4,'keyboardSetupEvents':8,'nativeKeyTraceRows':16,'focusObservationRows':32,'platformButtonPositiveControls':4}

def validate(native,out,metadata):
    need(type(native) is dict and set(native)==KEYBOARD_FIELDS,'keyboard supplement exact schema')
    for key,maximum in [('assertions',512),('addedSetupAssertions',26),('originalAssertionCounter',512),('addedScrollSetupAssertions',6),('addedKeyboardSetupAssertions',20),('keyboardSetupEvents',8)]:
        need(type(native[key]) is int and 0<=native[key]<=maximum,'keyboard integer partial counter '+key)
    need(native['addedSetupAssertions']==native['addedScrollSetupAssertions']+native['addedKeyboardSetupAssertions'] and native['assertions']==native['originalAssertionCounter']+native['addedSetupAssertions'],'keyboard exact assertion counter sums')
    original={key:value for key,value in native.items() if key not in KEYBOARD_FIELDS-{'schema','scope','status','failure','apkSHA256','sourceClosureSHA256','cases','observations','assertions','events','durationMilliseconds','rawCheckedListenerCallbacks','authoritativeCommits','physicalPhones','TalkBackServiceWorkflow'}}
    original['assertions']=native['originalAssertionCounter']
    result=_validate_original(original,out,metadata)
    need(native['addedScrollSetupAssertions']==6 and native['addedKeyboardSetupAssertions']==20 and native['addedSetupAssertions']==26 and native['keyboardSetupEvents']==8,'all original scroll and keyboard setup controls required')
    evidence=_keyboard(native)
    result.update(assertions=native['assertions'],originalAssertionCounter=native['originalAssertionCounter'],addedSetupAssertions=native['addedSetupAssertions'],addedScrollSetupAssertions=6,addedKeyboardSetupAssertions=20,keyboardSetup=evidence)
    return result
