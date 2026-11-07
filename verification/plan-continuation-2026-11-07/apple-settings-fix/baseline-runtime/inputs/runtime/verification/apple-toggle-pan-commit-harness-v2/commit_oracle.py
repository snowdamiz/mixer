"""Closed evidence rules for a real native release; host controls never qualify UIKit."""
import importlib.util
import json
import math
import pathlib

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

original = load('pan_commit_original_oracle', BASE.parent / 'apple-toggle-pan-origin-correction/oracle.py')
interruption = load('pan_commit_interruption_oracle', BASE.parent / 'apple-toggle-native-interruption/interruption_oracle.py')
semantic = load('pan_commit_semantic_oracle', BASE.parent / 'apple-toggle-semantic-activation/semantic_oracle.py')
SPECS = {x['name']: x for x in json.loads((BASE / 'cases.json').read_bytes())}
ORIGINAL_CASES = original.CASES - {'diagnostic-direct', 'comparator-direct'}
CASES = ORIGINAL_CASES | interruption.CASES | set(SPECS) | {'semantic-components'}
ACTIONS = original.ACTIONS | interruption.ACTIONS | {'native-pan-commit'}
CASE_ACTION = {**{n: original.CASE_ACTION[n] for n in ORIGINAL_CASES}, **interruption.CASE_ACTION,
               **{n: 'native-pan-commit' for n in SPECS}, 'semantic-components': 'direct-suite'}
CASE_COMMAND_SEQUENCE = {**{n: original.CASE_COMMAND_SEQUENCE[n] for n in ORIGINAL_CASES},
                         **interruption.CASE_COMMAND_SEQUENCE,
                         **{n: ['resume', 'reset'] + (['set-on'] if s['initial'] else []) + ['arm-commit-' + s['mode']] for n,s in SPECS.items()},
                         'semantic-components': ['resume', 'reset', 'self-tests']}
COMMANDS = set(sum(CASE_COMMAND_SEQUENCE.values(), []))
geometry_valid = original.geometry_valid
BOOLS = {'isOn','retainedOn','enabled','allowed','highlighted','authoredPressed','tracking','touchInside','focused','firstResponder','panActive','toggleTrait','buttonTrait','selectedTrait','notEnabledTrait','configurationNil','menuNil','nativeToggleSelection','rtl'}
COUNTERS = {'panAcceptedCount','panNoChangeCount','panCancellationCount','primaryCount','acceptedCount','rejectedCount','beginCount','continueCount','endCount','cancellationCount','accessibilityActivationCount','eventCount'}
STATE_KEYS = BOOLS | COUNTERS | {'identity','panState','previewThumbX','eventValues','traits','label','hint','value','buttonType','scrollOffsetY','frameInWindow','bounds','displayScale'}
HOOK_KEYS = {'mode','reason','initial','before','after','nativeGestureAtHook','returned','startedUptime','finishedUptime','traceSequenceAtCompletion'}

def number(x): return type(x) in (int,float) and math.isfinite(x)
def natural(x): return type(x) is int and x >= 0
def point(x): return type(x) is dict and set(x)=={'x','y'} and all(number(v) for v in x.values())
def gesture(g):
    return (type(g) is dict and type(g.get('identity')) is str and bool(g['identity']) and
            g.get('class') == 'UIPanGestureRecognizer' and type(g.get('state')) is int and g['state'] in range(6) and
            natural(g.get('touchCount')) and type(g.get('enabled')) is bool and type(g.get('cancelsTouches')) is bool and
            type(g.get('allowedTouchTypes')) is list and all(natural(x) for x in g['allowedTouchTypes']) and
            point(g.get('translationInWindow')) and point(g.get('velocityInWindow')))
def state_shape(s):
    return (type(s) is dict and set(s)==STATE_KEYS and all(type(s[k]) is bool for k in BOOLS) and
            all(natural(s[k]) for k in COUNTERS) and type(s['identity']) is str and bool(s['identity']) and
            type(s['panState']) is int and s['panState'] in range(6) and natural(s['traits']) and
            natural(s['buttonType']) and type(s['eventValues']) is list and all(type(v) is bool for v in s['eventValues']) and
            s['eventCount']==len(s['eventValues']) and (s['previewThumbX'] is None or number(s['previewThumbX'])) and
            number(s['scrollOffsetY']) and number(s['displayScale']) and s['displayScale'] >= 0 and
            all(type(s[k]) is str for k in ['frameInWindow','bounds','label','hint']) and all(rectangle(s[k], attached=False) for k in ['frameInWindow','bounds']) and (s['value'] is None or type(s['value']) is str) and
            s['isOn'] is s['retainedOn'] is s['selectedTrait'] and s['notEnabledTrait'] is (not s['enabled']) and
            s['buttonTrait'] is True and s['toggleTrait'] is True and s['nativeToggleSelection'] is False and
            s['configurationNil'] is True and s['menuNil'] is True and s['buttonType']==0 and
            s['label']=='Sync entries' and s['hint']=='Updates the sync preference')

def rectangle(text, attached):
    try:
        value=json.loads(text.replace('{','[').replace('}',']'),parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite rectangle')))
        return (type(value) is list and len(value)==2 and all(type(row) is list and len(row)==2 for row in value) and
                all(number(v) and abs(v)<=4096 for row in value for v in row) and
                all(v>0 if attached else v>=0 for v in value[1]))
    except (TypeError,ValueError):return False

def state(s):
    return state_shape(s) and s['displayScale'] > 0 and all(rectangle(s[k], attached=True) for k in ['frameInWindow','bounds'])

def failed(case, action, reason):
    return {'schema':'mixer.apple-toggle.pan-commit-verdict.1','candidate':'diagnostic','case':case,'action':action,
            'passed':False,'predicates':{'wellFormedClosedEvidence':False},'failure':reason,
            'scope':'Private simulator evidence only; no adapter, physical VoiceOver, parity, dogfood or GA acceptance'}

def commit_verdict(candidate, case, action, before, after, file_changed):
    s = SPECS[case]; initial=s['initial']; mode=s['mode']
    accepted=mode in {'nested-primary','nested-accessibility','after-event-rebind'}
    proposed=not initial; final=proposed if accepted and mode!='after-event-rebind' else initial
    b,a=before['state'],after['state']; hooks=after['panCommitRecords']
    assert state(b) and state(a)
    assert type(before['panCommitRecords']) is list and type(hooks) is list
    assert type(before['nativeInterruptions']) is list and type(after['nativeInterruptions']) is list
    trace=after['diagnosticTrace']; prior=before['diagnosticTrace']
    assert type(trace) is list and type(prior) is list and trace[:len(prior)]==prior
    assert all(type(t) is dict and natural(t['sequence']) and number(t['uptime']) and type(t['kind']) is str for t in trace)
    assert natural(after['diagnosticTraceDropped']) and natural(before['diagnosticTraceDropped'])
    assert type(before['events']) is list and type(after['events']) is list
    events=after['events']; assert events[:len(before['events'])]==before['events']
    assert all(type(e) is dict and set(e)=={'sequence','uptime','stage','reason','state'} and natural(e['sequence']) and number(e['uptime']) and type(e['reason']) is str and type(e['stage']) is str and (state_shape(e['state']) if i<len(before['events']) else state(e['state'])) for i,e in enumerate(events))
    delta=trace[len(prior):]; new=events[len(before['events']):]
    callbacks=[t for t in delta if t['kind']=='authoredPanCallback']; assert all(gesture(t) for t in callbacks)
    decisions=[t for t in delta if t['kind']=='shouldBeginDecision' and t.get('isAuthoredPan') is True]
    for t in decisions: assert type(t['result']) is bool and type(t['admissionReason']) is str
    touches=[t for t in delta if t['kind']=='recognizerShouldReceiveTouch']
    for t in touches: assert type(t['phase']) is int
    preview=[e for e in new if e['reason']=='panPreview']; values=[e for e in new if e['reason']=='valueChanged']
    completed=[e for e in new if e['reason']=='panCommitHookComplete']; success=[e for e in new if e['reason']=='panAccepted']; rejected=[e for e in new if e['reason']=='panCommitRejected']
    states=[t['state'] for t in callbacks]; compressed=[v for i,v in enumerate(states) if i==0 or v!=states[i-1]]
    p={
        'closedCandidateAction':candidate=='diagnostic' and action==CASE_ACTION[case],
        'freshObservation':file_changed is True,
        'initialValueAndAdmission':b['isOn'] is initial and b['rtl'] is False and b['enabled'] is True and b['allowed'] is True,
        'initialPanIdle':b['panActive'] is False and b['previewThumbX'] is None,
        'initialHooksEmpty':before['panCommitRecords']==[] and before['nativeInterruptions']==[] and after['nativeInterruptions']==[],
        'sameNativeCarrier':b['identity']==a['identity'],
        'completeMonotonicTrace':after['diagnosticTraceDropped']==before['diagnosticTraceDropped']==0 and [t['sequence'] for t in trace]==list(range(1,len(trace)+1)) and [t['uptime'] for t in trace]==sorted(t['uptime'] for t in trace),
        'completeMonotonicEvents':[e['sequence'] for e in events]==list(range(len(events))) and [e['uptime'] for e in events]==sorted(e['uptime'] for e in events),
        'actualNativeTouch':any(t['phase']==0 for t in touches),
        'nativeBeganChangedEnded':compressed==[1,2,3] and bool(callbacks) and all(t['touchCount']==(0 if t['state']==3 else 1) for t in callbacks),
        'oneNativeRecognizer':bool(callbacks) and len({t['identity'] for t in callbacks})==1,
        'nativeTimeProgressed':bool(callbacks) and callbacks[-1]['uptime']-callbacks[0]['uptime']>=.15 and len({t['uptime'] for t in callbacks})>=3,
        'nativeTranslationProgressed':bool(callbacks) and (max(t['translationInWindow']['x'] for t in callbacks)-min(t['translationInWindow']['x'] for t in callbacks))>=12 and (callbacks[-1]['translationInWindow']['x']<=-12 if initial else callbacks[-1]['translationInWindow']['x']>=12),
        'nativeAdmissionAccepted':bool(decisions) and all(t['result'] is True and t['admissionReason']=='accepted' for t in decisions),
        'previewBeforeCommit':bool(preview) and all(e['state']['isOn'] is initial and e['state']['eventCount']==b['eventCount'] and e['state']['panActive'] is True and number(e['state']['previewThumbX']) for e in preview),
        'latestFinalBinding':a['isOn'] is final,
        'finalGateAndDirection':a['enabled'] is (mode!='disable') and a['allowed'] is (mode!='stale') and a['rtl'] is (mode=='direction'),
        'previewCleared':a['panActive'] is False and a['previewThumbX'] is None,
        'exactSemanticCounters':all(a[k]-b[k]==int(accepted) for k in ['acceptedCount','panAcceptedCount','eventCount']) and a['panNoChangeCount']==b['panNoChangeCount'] and a['panCancellationCount']-b['panCancellationCount']==int(not accepted),
        'exactNestedCounters':a['primaryCount']-b['primaryCount']==int(mode=='nested-primary') and a['rejectedCount']-b['rejectedCount']==int(mode=='nested-primary') and a['accessibilityActivationCount']-b['accessibilityActivationCount']==int(mode=='nested-accessibility'),
        'exactValueHistory':a['eventValues']==b['eventValues']+([proposed] if accepted else []),
        'oneOrZeroValueEvent':len(values)==int(accepted) and all(e['state']['isOn'] is proposed and e['state']['eventValues']==b['eventValues']+[proposed] for e in values),
        'oneCompletionAndDisposition':len(completed)==1 and len(success)==int(accepted) and len(rejected)==int(not accepted),
        'stationaryScroll':abs(a['scrollOffsetY']-b['scrollOffsetY'])<=1,
        'oneHook':len(hooks)==1,
    }
    if len(hooks)==1:
        h=hooks[0];assert type(h) is dict and set(h)==HOOK_KEYS and state(h['before']) and state(h['after']) and gesture(h['nativeGestureAtHook'])
        assert type(h['initial']) is bool and number(h['startedUptime']) and number(h['finishedUptime']) and natural(h['traceSequenceAtCompletion'])
        hb,ha,g=h['before'],h['after'],h['nativeGestureAtHook']; late=mode=='after-event-rebind'; n=int(late)
        expected_hook_final=initial if mode in {'rebind','after-event-rebind'} else proposed
        p.update(
            exactHookModeAndReason=h['mode']=='arm-commit-'+mode and h['initial'] is initial and h['reason']==('panAccepted' if late else 'selection'),
            sameEndedNativeRecognizer=bool(callbacks) and g['identity']==callbacks[0]['identity'] and g['state']==3 and g['touchCount']==0 and hb['panState']==3,
            hookAfterNativeEnd=bool(callbacks) and callbacks[-1]['uptime']<=h['startedUptime']<=h['finishedUptime'] and callbacks[-1]['sequence']<=h['traceSequenceAtCompletion']<=len(trace),
            hookCarrierIdentity=hb['identity']==ha['identity']==a['identity'],
            hookPreviewCleared=all(x['panActive'] is False and x['previewThumbX'] is None for x in [hb,ha]),
            hookProposedValueAndCounters=hb['isOn'] is proposed and all(hb[k]-b[k]==n for k in ['eventCount','acceptedCount','panAcceptedCount']) and hb['eventValues']==b['eventValues']+([proposed] if late else []) and all(hb[k]==b[k] for k in ['primaryCount','rejectedCount','accessibilityActivationCount','panNoChangeCount','panCancellationCount']),
            exactHookNestedCounters=ha['primaryCount']-hb['primaryCount']==int(mode=='nested-primary') and ha['rejectedCount']-hb['rejectedCount']==int(mode=='nested-primary') and ha['accessibilityActivationCount']-hb['accessibilityActivationCount']==int(mode=='nested-accessibility'),
            hookResult=ha['isOn'] is expected_hook_final and ha['enabled'] is (mode!='disable') and ha['allowed'] is (mode!='stale') and ha['rtl'] is (mode=='direction'),
            exactNestedReturn=h['returned'] is (False if mode=='nested-accessibility' else None),
            hookOperationSilent=ha['eventCount']==hb['eventCount'] and ha['eventValues']==hb['eventValues'] and all(ha[k]==hb[k] for k in ['acceptedCount','panAcceptedCount','panNoChangeCount','panCancellationCount']),
        )
        selection=[e for e in new if e['reason']=='selection']; first=selection[0] if selection else None
        p['selectionObservedBeforeHook']=first is not None and first['state']['isOn'] is proposed and first['uptime']<=h['startedUptime'] and bool(preview) and preview[-1]['sequence']<first['sequence']
        p['hookCompletionRecordedAfterOperation']=len(completed)==1 and h['finishedUptime']<=completed[0]['uptime']
        if accepted:
            p['acceptedValuePrecedesInformationalObserver']=len(values)==len(success)==1 and values[0]['sequence']<success[0]['sequence']
            p['hookValueEventOrdering']=(values[0]['sequence']<success[0]['sequence']<completed[0]['sequence'] if late and len(values)==len(success)==len(completed)==1 else completed[0]['sequence']<values[0]['sequence'] if len(values)==len(completed)==1 else False)
            p['noStaleTransitionAfterHook']=all(e['state']['eventCount']==a['eventCount'] and e['state']['eventValues']==a['eventValues'] for e in new if late and e['sequence']>=completed[0]['sequence'])
        else:
            p['rejectionFollowsHook']=len(completed)==len(rejected)==1 and completed[0]['sequence']<rejected[0]['sequence']
            p['rejectedCommitNeverEmits']=all(e['state']['eventCount']==b['eventCount'] and e['state']['eventValues']==b['eventValues'] for e in new)
    return {'schema':'mixer.apple-toggle.pan-commit-verdict.1','candidate':candidate,'case':case,'action':action,'predicates':p,'passed':all(v is True for v in p.values()),'scope':'Real public XCTest release with synchronous fixture callbacks; no physical VoiceOver, production adapter, full parity, dogfood or GA acceptance'}

def semantic_verdict(candidate, case, action, before, after, file_changed):
    # Original strict suite is evaluated unchanged and retained, including failures.
    raw=original.verdict(candidate,'diagnostic-direct',action,before,after,file_changed)
    checked=semantic.verify(after['semanticOperations'])
    checks=after['checks']; assert type(checks) is list and all(type(x) is dict and set(x)=={'name','pass'} and type(x['name']) is str and type(x['pass']) is bool for x in checks)
    failures=[x['name'] for x in checks if x['pass'] is False]
    p={'closedScopedComponent':candidate=='diagnostic' and case=='semantic-components' and action=='direct-suite',
       'freshObservation':file_changed is True,'sameCarrier':before['state']['identity']==after['state']['identity'],
       'completeDiagnosticSuite':after['diagnosticSuiteState']=='complete',
       'selected36SemanticComponents':checked['cases']==36,
       'original19ChecksPreserved':[x['name'] for x in checks]==original.EXPECTED_CHECK_NAMES['diagnostic'],
       'originalFourReferenceFailuresRetained':failures==original.EXPECTED_CHECK_NAMES['diagnostic'][14:18],
       'originalStrictSuiteStillFails':raw['passed'] is False and raw['predicates']['allOriginalStrictChecksTrue'] is False,
       'completeTrace':type(after['diagnosticTraceDropped']) is int and after['diagnosticTraceDropped']==0}
    return {'schema':'mixer.apple-toggle.pan-commit-scoped-semantic-verdict.1','candidate':candidate,'case':case,'action':action,
            'passed':all(v is True for v in p.values()),'predicates':p,'semanticComponents':checked,
            'originalStrictVerdict':raw,'originalChecks':checks,'originalFailures':failures,
            'nativeInteraction':False,'scope':'Only unchanged36direct semantic callback components qualify; original19strict checks preserve four reference failures and remain failed'}

def verdict(candidate, case, action, before, after, file_changed=True):
    try:
        if case not in CASES or action != CASE_ACTION[case]: return failed(case,action,'Unknown closed case/action')
        if case in ORIGINAL_CASES: return original.verdict(candidate,case,action,before,after,file_changed)
        if case in interruption.CASES: return interruption.verdict(candidate,case,action,before,after,file_changed)
        if case=='semantic-components': return semantic_verdict(candidate,case,action,before,after,file_changed)
        return commit_verdict(candidate,case,action,before,after,file_changed)
    except (AssertionError,KeyError,IndexError,TypeError,ValueError,AttributeError,OverflowError) as error:
        return failed(case,action,type(error).__name__+': '+str(error))
