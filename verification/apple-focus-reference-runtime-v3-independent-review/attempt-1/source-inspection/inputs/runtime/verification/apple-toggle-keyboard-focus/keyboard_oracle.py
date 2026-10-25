"""Closed keyboard phases and independent native AX/application evidence rules."""
import importlib.util
import json
import math
import pathlib
BASE=pathlib.Path(__file__).resolve().parent;ROOT=BASE.parents[1]
spec=importlib.util.spec_from_file_location('reviewed_pan_state',BASE.parent/'apple-toggle-pan-commit-harness-v2/commit_oracle.py')
state_contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(state_contract)
SPECS={x['name']:x for x in json.loads((BASE/'cases.json').read_bytes())}
CASES=set(SPECS);ACTIONS={'native-keyboard'};CASE_ACTION={n:'native-keyboard' for n in CASES}
COMMANDS={'resume','reset','set-on','stale','disable'}
CASE_COMMAND_SEQUENCE={n:['resume','reset']+(['set-on'] if s['initial'] else []) for n,s in SPECS.items()}
IDS=('authored-toggle','plain-uibutton-reference','next-focus')
API='XCUIElement.typeKey(_:modifierFlags:)'
ENABLED_PHASES=['space-first','space-reverse','tab-reference','tab-next','reverse-reference','reverse-toggle']
STALE_PHASES=['stale-space','resumed-space']
DISABLED_PHASES=['disabled-navigation','disabled-space','disabled-reverse']
PHASE_KEYS={'acquire':'tab','space-first':'space','space-reverse':'space','tab-reference':'tab','tab-next':'tab','reverse-reference':'shift-tab','reverse-toggle':'shift-tab','stale-space':'space','resumed-space':'space','disabled-held-space':'space','disabled-navigation':'tab','disabled-space':'space','disabled-reverse':'shift-tab'}

def require(ok,reason):
    if not ok:raise ValueError(reason)
def number(x):return type(x) in (int,float) and math.isfinite(x) and x>=0
def natural(x):return type(x) is int and x>=0

def geometry_valid(g):
    return state_contract.original.geometry_valid(g) and set(g)=={'app','target'}

def focused(snapshot):
    names=[name for name,row in snapshot['elements'].items() if row['hasFocus']]
    require(len(names)<=1,'Multiple fixed native elements claim focus')
    return names[0] if names else None

def ax(snapshot):
    require(type(snapshot) is dict and set(snapshot)=={'uptime','appForeground','elements'},'Closed AX snapshot shape required')
    require(number(snapshot['uptime']) and snapshot['appForeground'] is True,'Fresh foreground native AX snapshot required')
    rows=snapshot['elements'];require(type(rows) is dict and set(rows)==set(IDS),'Fixed native identifiers required')
    for name,row in rows.items():
        require(type(row) is dict and set(row)=={'identifier','exists','hittable','enabled','selected','hasFocus','label','frame'},'Closed native element shape required')
        require(row['identifier']==name and type(row['identifier']) is str and type(row['label']) is str,'Native identity/label malformed')
        require(all(type(row[k]) is bool for k in ['exists','hittable','enabled','selected','hasFocus']),'Strict native AX booleans required')
        require(row['exists'] is True and (row['hittable'] is True or row['enabled'] is False),'Native element absent or inaccessible')
        frame=row['frame'];require(type(frame) is dict and set(frame)=={'x','y','width','height'} and all(type(v) in (int,float) and math.isfinite(v) and abs(v)<=4096 for v in frame.values()) and frame['width']>0 and frame['height']>0,'Attached native AX frame required')
    focused(snapshot)
    return snapshot

def witness(w,binding):
    require(type(binding) is dict and set(binding)=={'case','generation','actionIndex','baselineUptime','evaluatedUptime'} and type(binding['case']) is str and binding['case'] in CASES and type(binding['generation']) is int and binding['generation']>0 and type(binding['actionIndex']) is int and binding['actionIndex']>0 and number(binding['baselineUptime']) and number(binding['evaluatedUptime']) and binding['evaluatedUptime']>=binding['baselineUptime'],'Strict current bridge binding required')
    require(type(w) is dict and set(w)=={'case','generation','actionIndex','phase','key','publicAPI','returned','before','startedUptime','finishedUptime','after'},'Closed keyboard witness required')
    require(w['case'] in CASES and type(w['phase']) is str and w['phase'] in PHASE_KEYS,'Unsupported keyboard case/phase')
    require(type(w['generation']) is int and w['generation']>0 and type(w['actionIndex']) is int and w['actionIndex']>0,'Exact generation/action types required')
    require(w['case']==binding['case'] and w['generation']==binding['generation'] and w['actionIndex']==binding['actionIndex'],'Keyboard generation/case/action mismatch')
    require(w['publicAPI']==API and w['key']==PHASE_KEYS[w['phase']] and w['returned'] is True,'Real public typeKey delivery required')
    ax(w['before']);ax(w['after'])
    require(all(number(w[k]) for k in ['startedUptime','finishedUptime']),'Native keyboard times malformed')
    require(binding['baselineUptime']<=w['before']['uptime']<=w['startedUptime']<w['finishedUptime']<=w['after']['uptime']<=binding['evaluatedUptime'],'Stale/reordered native keyboard snapshot')
    require(w['after']['uptime']-w['before']['uptime']<=12,'Keyboard observation window exceeded')
    return w

class Cursor:
    """Finite per-case ordering: setup, bounded Tab acquisition, fixed actions/commands."""
    def __init__(self,name):
        self.name=name;self.spec=SPECS[name];self.setup=CASE_COMMAND_SEQUENCE[name];self.done_commands=[]
        self.acquired=False;self.acquisitions=0;self.phase_index=0;self.held_space=False;self.complete=False;self.failed=False;self.last_after=None
    @property
    def phases(self):return ENABLED_PHASES if self.spec['mode']=='enabled' else STALE_PHASES if self.spec['mode']=='stale' else DISABLED_PHASES
    def next_command(self):
        if len(self.done_commands)<len(self.setup):return self.setup[len(self.done_commands)]
        mid={'stale':{0:'stale',1:'resume'},'disabled':{0:'disable'}}.get(self.spec['mode'],{})
        expected=mid.get(self.phase_index) if self.acquired else None
        if expected is not None and self.done_commands.count(expected)<(2 if expected=='resume' else 1):return expected
        return None
    def command(self,value):
        require(not self.complete and not self.failed and value==self.next_command(),'Fixture command outside fixed keyboard sequence')
        self.done_commands.append(value)
    def baseline_allowed(self):
        require(not self.complete and not self.failed and len(self.done_commands)>=len(self.setup) and self.next_command() is None,'Keyboard action before required fixture command or after completion/failure')
        require(self.acquired or self.acquisitions<12,'Bounded Tab acquisition exhausted')
    def check(self,w):
        self.baseline_allowed()
        if self.last_after is not None:require(w['before']['uptime']>self.last_after,'Duplicate/stale keyboard witness time')
        if not self.acquired:require(w['phase']=='acquire','Native Tab acquisition required before semantic keys')
        elif self.spec['mode']=='disabled' and self.phase_index==0 and not self.held_space:
            require(w['phase'] in {'disabled-held-space','disabled-navigation'},'Disabled focus observation phase required')
            if w['phase']=='disabled-navigation':require(focused(w['before'])!='authored-toggle','Retained disabled focus must receive observed silent Space before traversal')
        else:require(w['phase']==self.phases[self.phase_index],'Keyboard phase missing/reordered/duplicated')
    def advance(self,w):
        self.check(w);self.last_after=w['after']['uptime']
        if not self.acquired:
            self.acquisitions+=1;self.acquired=focused(w['after'])=='authored-toggle';return
        if w['phase']=='disabled-held-space':self.held_space=True;return
        self.phase_index+=1;self.complete=self.phase_index==len(self.phases)

def verdict(candidate,case,action,before,after,file_changed=True):
    try:
        require(case in CASES and candidate=='diagnostic' and action=='native-keyboard','Closed keyboard candidate/action required')
        w=witness(before['keyboardWitness'],before['keyboardBinding']);require(w['case']==case,'Witness case mismatch')
        b,a=before['state'],after['state'];require(state_contract.state(b) and state_contract.state(a),'Strict attached application states required')
        require(after['events'][:len(before['events'])]==before['events'],'Native event history prefix changed')
        events=after['events'];require(type(events) is list and all(type(e) is dict and set(e)=={'sequence','uptime','stage','reason','state'} and natural(e['sequence']) and number(e['uptime']) and type(e['reason']) is str and type(e['stage']) is str and (state_contract.state_shape(e['state']) if i<len(before['events']) else state_contract.state(e['state'])) for i,e in enumerate(events)),'Native event schema malformed')
        require([e['sequence'] for e in events]==list(range(len(events))) and [e['uptime'] for e in events]==sorted(e['uptime'] for e in events),'Native event order invalid')
        trace=after['diagnosticTrace'];prior=before['diagnosticTrace'];require(type(trace) is list and trace[:len(prior)]==prior,'Native trace prefix changed')
        require(type(after['diagnosticTraceDropped']) is int and after['diagnosticTraceDropped']==0 and all(type(t) is dict and type(t['sequence']) is int and number(t['uptime']) and type(t['kind']) is str for t in trace) and [t['uptime'] for t in trace]==sorted(t['uptime'] for t in trace) and [t['sequence'] for t in trace]==list(range(1,len(trace)+1)),'Native trace incomplete')
        new=events[len(before['events']):];delta=trace[len(prior):];phase=w['phase'];f0=focused(w['before']);f1=focused(w['after'])
        count=lambda k:a[k]-b[k]
        semantic=['eventCount','acceptedCount','panAcceptedCount','panNoChangeCount','panCancellationCount','primaryCount','rejectedCount','accessibilityActivationCount']
        axn=sum(t['kind']=='carrierAccessibilityActivateEnter' for t in delta)
        primary=sum(t['kind']=='carrierPrimaryTarget' for t in delta)
        returns=[t for t in delta if t['kind']=='carrierAccessibilityActivateReturn']
        native_frames=[]
        for snapshot,native in [(w['before'],b),(w['after'],a)]:
            rectangle=json.loads(native['frameInWindow'].replace('{','[').replace('}',']'));x,y=rectangle[0];width,height=rectangle[1]
            native_frames.append(all(abs(snapshot['elements']['authored-toggle']['frame'][k]-v)<=1 for k,v in [('x',x),('y',y),('width',width),('height',height)]))
        p={'sameNativeCarrier':a['identity']==b['identity'],'sameAXBinding':w['before']['elements']['authored-toggle']['selected'] is b['isOn'] and w['after']['elements']['authored-toggle']['selected'] is a['isOn'],
           'nativeEnabledMetadata':w['before']['elements']['authored-toggle']['enabled'] is b['enabled'] and w['after']['elements']['authored-toggle']['enabled'] is a['enabled'],
           'keyboardNotSyntheticTouch':not any(t['kind'] in {'carrierTouchesBegan','recognizerShouldReceiveTouch','authoredPanCallback'} for t in delta),
           'noPanOrPreview':all(count(k)==0 for k in ['panAcceptedCount','panNoChangeCount','panCancellationCount']) and a['panActive'] is False and a['previewThumbX'] is None,
           'exactAXRouteCount':count('accessibilityActivationCount')==axn and axn in [0,1],
           'exactPrimaryRouteCount':count('primaryCount')==primary and primary in [0,1],
           'nativeCurrentGeometry':all(native_frames),
           'exactAccessibilityReturnCount':len(returns)==axn and all(type(t.get('result')) is bool for t in returns)}
        values=[e for e in new if e['reason']=='valueChanged']
        accepted=phase in {'space-first','space-reverse','resumed-space'}
        if phase=='acquire':p['freshInitialCasePremise']=b['isOn'] is SPECS[case]['initial'] and b['enabled'] is True and b['allowed'] is True
        if axn:p['exactNativeAccessibilityReturn']=returns[0]['result'] is accepted if len(returns)==1 else False
        if accepted:
            p.update(nativeToggleFocused=f0==f1=='authored-toggle',currentEnabledGate=b['enabled'] is True and b['allowed'] is True and a['enabled'] is True and a['allowed'] is True,
                     exactNativePrimary=primary==1,exactAcceptedTransition=a['isOn'] is (not b['isOn']) and count('acceptedCount')==1 and count('eventCount')==1 and count('rejectedCount')==0,
                     exactValueEvent=len(values)==1 and a['eventValues']==b['eventValues']+[not b['isOn']] and values[0]['state']['eventValues']==a['eventValues'],freshApplicationTransition=file_changed is True,
                     primaryCompletionOrder=len([e for e in new if e['reason']=='primaryAccepted'])==1 and len(values)==1 and values[0]['sequence']<next(e['sequence'] for e in new if e['reason']=='primaryAccepted'))
        else:
            p.update(bindingAndValuesSilent=a['isOn'] is b['isOn'] and count('eventCount')==count('acceptedCount')==0 and a['eventValues']==b['eventValues'] and values==[])
            if phase=='stale-space':
                p.update(staleFocused=f0==f1=='authored-toggle' and b['enabled'] is True and b['allowed'] is False and a['allowed'] is False,
                         exactRejectedRoute=(axn==1 and primary==0 and count('rejectedCount')==0) or (axn==0 and primary==1 and count('rejectedCount')==1),freshRejectedKeyboard=file_changed is True)
            elif phase in {'disabled-held-space','disabled-space'}:
                p.update(disabledNativeTrait=b['enabled'] is False and a['enabled'] is False and b['notEnabledTrait'] is True,
                         disabledSemanticRoute=primary==axn==count('rejectedCount')==0)
                if phase=='disabled-held-space':p['actualRetainedDisabledFocus']=f0=='authored-toggle'
                else:
                    neighbor_events=sum(t['kind']=='referencePrimaryTarget' for t in delta) if f0=='plain-uibutton-reference' else sum(e['reason']=='nextButton' for e in new) if f0=='next-focus' else 0
                    p['nativeEnabledNeighborDelivery']=f0==f1 and f0 in {'plain-uibutton-reference','next-focus'} and neighbor_events==1 and file_changed is True
            else:
                p['silentSemanticRoute']=all(count(k)==0 for k in semantic)
                p['actualNativeFocusTraversal']=f0!=f1 and f1 is not None
                expected={'tab-reference':('authored-toggle','plain-uibutton-reference'),'tab-next':('plain-uibutton-reference','next-focus'),'reverse-reference':('next-focus','plain-uibutton-reference'),'reverse-toggle':('plain-uibutton-reference','authored-toggle')}.get(phase)
                if expected:p['actualNeighborOrder']=(f0,f1)==expected
                if phase.startswith('disabled-'):p['disabledExcludedFromTraversal']=b['enabled'] is False and f1 in {'plain-uibutton-reference','next-focus'} and w['after']['elements'][f1]['enabled'] is True
        return {'schema':'mixer.apple-toggle.keyboard-verdict.1','candidate':candidate,'case':case,'action':action,'phase':phase,
                'predicates':p,'passed':all(v is True for v in p.values()),'keyboardWitness':w,'keyboardBinding':before['keyboardBinding'],
                'observedFocusBefore':f0,'observedFocusAfter':f1,'nativeAppFocusedBefore':b['focused'],'nativeAppFocusedAfter':a['focused'],
                'scope':'Public XCTest key and native AX/application observations only; no physical keyboard/VoiceOver, live adapter, parity, dogfood or GA acceptance'}
    except (KeyError,ValueError,TypeError,IndexError,AssertionError,StopIteration,AttributeError) as error:
        return {'schema':'mixer.apple-toggle.keyboard-verdict.1','candidate':candidate,'case':case,'action':action,'passed':False,'predicates':{'closedCompleteKeyboardEvidence':False},'failure':type(error).__name__+': '+str(error),'keyboardWitness':before.get('keyboardWitness')}
