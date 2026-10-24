"""Independent synthetic keyboard/AX controls. Host evidence never qualifies native delivery."""
import copy
import json
import pathlib
import tempfile
import unittest
from unittest import mock
import composition as run
run.inherited=run.h
o=run.oracle.original


def state(initial,enabled=True,allowed=True):
    s={k:False for k in o.state_contract.BOOLS};s.update({k:0 for k in o.state_contract.COUNTERS})
    s.update(identity='host-carrier',isOn=initial,retainedOn=initial,selectedTrait=initial,enabled=enabled,allowed=allowed,notEnabledTrait=not enabled,
             toggleTrait=True,buttonTrait=True,configurationNil=True,menuNil=True,panState=0,previewThumbX=None,eventValues=[False,True],eventCount=2,
             traits=1,label='Sync entries',hint='Updates the sync preference',value=None,buttonType=0,scrollOffsetY=0,frameInWindow='{{303,244},{63,44}}',bounds='{{0,0},{63,44}}',displayScale=3,
             primaryCount=7,acceptedCount=5,rejectedCount=2,panAcceptedCount=3,panCancellationCount=2,accessibilityActivationCount=3)
    return s

def ax(focus,selected,enabled,t):
    rows={}
    for name in o.IDS:
        rows[name]=dict(identifier=name,exists=True,hittable=True,enabled=enabled if name=='authored-toggle' else True,selected=selected if name=='authored-toggle' else False,hasFocus=name==focus,label='Sync entries' if name=='authored-toggle' else name,frame=dict(x=303,y=244,width=63,height=44))
    return dict(uptime=t,appForeground=True,elements=rows)

def fixture(mode='enabled',initial=False,phase='space-first',ax_route=False,neighbor='plain-uibutton-reference'):
    case='keyboard-'+mode+'-'+('on' if initial else 'off');accepted=phase in {'space-first','space-reverse','resumed-space'}
    value=not initial if phase=='space-reverse' else initial;enabled=mode!='disabled';allowed=phase!='stale-space';b=state(value,enabled,allowed);a=copy.deepcopy(b)
    routes={'acquire':('plain-uibutton-reference','authored-toggle'),'tab-reference':('authored-toggle','plain-uibutton-reference'),'tab-next':('plain-uibutton-reference','next-focus'),'reverse-reference':('next-focus','plain-uibutton-reference'),'reverse-toggle':('plain-uibutton-reference','authored-toggle'),'disabled-navigation':(None,neighbor),'disabled-reverse':(neighbor,'next-focus' if neighbor=='plain-uibutton-reference' else 'plain-uibutton-reference')}
    f0,f1=routes.get(phase,('authored-toggle','authored-toggle'))
    if phase=='disabled-space':f0=f1=neighbor
    primary=1 if accepted or (phase=='stale-space' and not ax_route) else 0
    a['primaryCount']+=primary;a['accessibilityActivationCount']+=int(ax_route)
    if phase=='stale-space' and not ax_route:a['rejectedCount']+=1
    if accepted:
        new=not value;a.update(isOn=new,retainedOn=new,selectedTrait=new,eventCount=b['eventCount']+1,acceptedCount=b['acceptedCount']+1,eventValues=b['eventValues']+[new])
    def event(reason,s,seq,t):return dict(sequence=seq,uptime=t,stage='host-only',reason=reason,state=copy.deepcopy(s))
    startup=copy.deepcopy(b);startup.update(displayScale=0,bounds='{{0,0},{0,0}}',frameInWindow='{{0,0},{0,0}}')
    before=dict(state=b,events=[event('startup',startup,0,100)],diagnosticTrace=[],diagnosticTraceDropped=0)
    events=copy.deepcopy(before['events']);trace=[]
    def record(kind,**values):trace.append(dict(sequence=len(trace)+1,uptime=101.15+len(trace)*.001,kind=kind,**values))
    if ax_route:record('carrierAccessibilityActivateEnter')
    if primary:record('carrierPrimaryTarget')
    if ax_route:record('carrierAccessibilityActivateReturn',result=accepted)
    if accepted:events+=[event('valueChanged',a,1,101.18),event('primaryAccepted',a,2,101.19)]
    if phase=='disabled-space':
        if neighbor=='plain-uibutton-reference':record('referencePrimaryTarget')
        else:events.append(event('nextButton',a,1,101.19))
    binding=dict(case=case,generation=1,actionIndex=1,baselineUptime=100.5,evaluatedUptime=102.5)
    w=dict(case=case,generation=1,actionIndex=1,phase=phase,key=o.PHASE_KEYS[phase],publicAPI=o.API,returned=True,
           before=ax(f0,value,enabled,101),startedUptime=101.1,finishedUptime=101.2,after=ax(f1,a['isOn'],enabled,102))
    before.update(keyboardWitness=w,keyboardBinding=binding)
    after=dict(state=a,events=events,diagnosticTrace=trace,diagnosticTraceDropped=0)
    return case,before,after

def verdict(c,b,a):return o.verdict('diagnostic',c,'native-keyboard',b,a)

class OracleControls(unittest.TestCase):
    def test_all_closed_phases_both_initial_values_and_native_routes(self):
        for initial in [False,True]:
            for mode,phases in [('enabled',['acquire']+o.ENABLED_PHASES),('stale',['acquire']+o.STALE_PHASES),('disabled',['acquire','disabled-held-space']+o.DISABLED_PHASES)]:
                for phase in phases:
                    for route in ([False,True] if phase in {'space-first','space-reverse','resumed-space','stale-space'} else [False]):
                        with self.subTest(mode=mode,phase=phase,initial=initial,ax=route):
                            c,b,a=fixture(mode,initial,phase,route)
                            if phase=='acquire' and mode=='disabled':b['state'].update(enabled=True,notEnabledTrait=False);a['state'].update(enabled=True,notEnabledTrait=False);b['keyboardWitness']['before']['elements']['authored-toggle']['enabled']=True;b['keyboardWitness']['after']['elements']['authored-toggle']['enabled']=True
                            self.assertTrue(verdict(c,b,a)['passed'],verdict(c,b,a))
        for neighbor in ['plain-uibutton-reference','next-focus']:
            c,b,a=fixture('disabled',False,'disabled-space',neighbor=neighbor);self.assertTrue(verdict(c,b,a)['passed'])

    def test_missing_keyboard_delivery_or_focus_never_passes(self):
        changes=[lambda b,a:b.pop('keyboardWitness'),lambda b,a:b['keyboardWitness'].update(publicAPI='performPrimaryAction'),lambda b,a:b['keyboardWitness'].update(returned=False),
                 lambda b,a:b['keyboardWitness']['before']['elements']['authored-toggle'].update(hasFocus=False),lambda b,a:b['keyboardWitness']['after']['elements']['authored-toggle'].update(hasFocus=False),
                 lambda b,a:a.update(diagnosticTrace=[]),lambda b,a:a.update(state=copy.deepcopy(b['state']),events=copy.deepcopy(b['events']),diagnosticTrace=[])]
        for mutate in changes:
            c,b,a=fixture();mutate(b,a);self.assertFalse(verdict(c,b,a)['passed'])

    def test_rejects_duplicate_missing_wrong_events_counters_identity_and_order(self):
        changes=[lambda a:a['state'].update(identity='replacement'),lambda a:a['state'].update(eventCount=99),lambda a:a['state'].update(acceptedCount=99),lambda a:a['state'].update(primaryCount=99),lambda a:a['state'].update(rejectedCount=99),
                 lambda a:a['state'].update(accessibilityActivationCount=99),lambda a:a['state'].update(eventValues=[False,True,False]),lambda a:a['state'].update(panAcceptedCount=99),
                 lambda a:a.update(events=a['events'][:-1]),lambda a:a['events'].append(copy.deepcopy(a['events'][-1])),lambda a:a['events'][1].update(reason='primaryAccepted'),
                 lambda a:a['events'][0].update(reason='changed-prefix'),lambda a:a.update(diagnosticTraceDropped=1),lambda a:a['diagnosticTrace'][0].update(sequence=True),
                 lambda a:a['diagnosticTrace'].append(dict(sequence=2,uptime=101.16,kind='carrierTouchesBegan')),
                 lambda a:a['state'].update(selectedTrait=False),lambda a:a['state'].update(displayScale=0)]
        for change in changes:
            c,b,a=fixture();change(a);self.assertFalse(verdict(c,b,a)['passed'])

    def test_strict_witness_types_binding_ids_and_fresh_native_times(self):
        bads=[('generation',True),('generation',2),('actionIndex',True),('actionIndex',2),('case','keyboard-enabled-on'),('phase','arbitrary'),('key','return'),('returned',1),('startedUptime',0),('finishedUptime',101.0),('finishedUptime',float('nan'))]
        for key,value in bads:
            c,b,a=fixture();b['keyboardWitness'][key]=value;self.assertFalse(verdict(c,b,a)['passed'])
        for key in ['generation','actionIndex','baselineUptime','evaluatedUptime']:
            c,b,a=fixture();b['keyboardBinding'][key]=True;self.assertFalse(verdict(c,b,a)['passed'])
        for when in ['before','after']:
            for field in ['exists','hittable','enabled','selected','hasFocus']:
                c,b,a=fixture();b['keyboardWitness'][when]['elements']['authored-toggle'][field]=1;self.assertFalse(verdict(c,b,a)['passed'])
            c,b,a=fixture();b['keyboardWitness'][when]['elements']['unknown']=b['keyboardWitness'][when]['elements'].pop('next-focus');self.assertFalse(verdict(c,b,a)['passed'])
            c,b,a=fixture();b['keyboardWitness'][when]['elements']['plain-uibutton-reference']['hasFocus']=True;self.assertFalse(verdict(c,b,a)['passed'])
            c,b,a=fixture();b['keyboardWitness'][when]['elements']['authored-toggle']['frame']['x']+=10;self.assertFalse(verdict(c,b,a)['passed'])

    def test_stale_disabled_and_traversal_negative_controls(self):
        for mode,phase in [('stale','stale-space'),('disabled','disabled-held-space'),('disabled','disabled-space'),('disabled','disabled-navigation'),('enabled','tab-reference')]:
            c,b,a=fixture(mode,False,phase);a['state']['eventCount']+=1;a['state']['eventValues'].append(True);self.assertFalse(verdict(c,b,a)['passed'])
        c,b,a=fixture('enabled',False,'tab-reference');b['keyboardWitness']['after']['elements']['plain-uibutton-reference']['hasFocus']=False;b['keyboardWitness']['after']['elements']['next-focus']['hasFocus']=True;self.assertFalse(verdict(c,b,a)['passed'])
        c,b,a=fixture('enabled',False,'acquire');b['keyboardWitness']['after']=copy.deepcopy(b['keyboardWitness']['before']);b['keyboardWitness']['after']['uptime']=102;self.assertFalse(verdict(c,b,a)['passed'])
        c,b,a=fixture('disabled',False,'disabled-space');a['diagnosticTrace']=[];self.assertFalse(verdict(c,b,a)['passed'])

class CursorControls(unittest.TestCase):
    def prepare(self,name):
        c=o.Cursor(name)
        for command in o.CASE_COMMAND_SEQUENCE[name]:c.command(command)
        return c
    def test_fixed_setup_commands_and_acquisition_limit(self):
        c=o.Cursor('keyboard-enabled-off')
        for command in ['disable','stale','set-on']:
            with self.assertRaises(ValueError):c.command(command)
        with self.assertRaises(ValueError):c.baseline_allowed()
        c=self.prepare(c.name)
        for n in range(12):
            _,b,_=fixture('enabled',False,'acquire');w=b['keyboardWitness'];w['after']=ax('next-focus',False,True,102+n*10);w['before']['uptime']=101+n*10;c.advance(w)
        with self.assertRaises(ValueError):c.baseline_allowed()
    def test_duplicate_stale_reordered_and_missing_phases_fail(self):
        c=self.prepare('keyboard-enabled-off');_,b,_=fixture('enabled',False,'acquire');c.advance(b['keyboardWitness'])
        _,b,_=fixture();w=b['keyboardWitness'];w['before']['uptime']=111;w['after']['uptime']=112;c.advance(w)
        with self.assertRaises(ValueError):c.advance(w)
        w=copy.deepcopy(w);w['before']['uptime']=121;w['after']['uptime']=122;w['phase']='tab-next'
        with self.assertRaises(ValueError):c.advance(w)
    def test_stale_resume_and_disabled_commands_are_phase_locked(self):
        for mode in ['stale','disabled']:
            c=self.prepare('keyboard-'+mode+'-off');_,b,_=fixture(mode,False,'acquire');c.advance(b['keyboardWitness'])
            with self.assertRaises(ValueError):c.baseline_allowed()
            command='stale' if mode=='stale' else 'disable';c.command(command)
            with self.assertRaises(ValueError):c.command(command)
            if mode=='stale':
                _,b,_=fixture(mode,False,'stale-space');w=b['keyboardWitness'];w['before']['uptime']=111;w['after']['uptime']=112;c.advance(w)
                with self.assertRaises(ValueError):c.baseline_allowed()
                c.command('resume');self.assertFalse(c.complete)
    def test_disabled_focus_removal_is_observed_not_assumed(self):
        for held in [False,True]:
            c=self.prepare('keyboard-disabled-off');_,b,_=fixture('disabled',False,'acquire');c.advance(b['keyboardWitness']);c.command('disable')
            if held:
                _,b,_=fixture('disabled',False,'disabled-held-space');w=b['keyboardWitness'];w['before']['uptime']=111;w['after']['uptime']=112;c.advance(w)
            _,b,_=fixture('disabled',False,'disabled-navigation');w=b['keyboardWitness'];w['before']['uptime']=121;w['after']['uptime']=122;c.advance(w)
            self.assertEqual(c.held_space,held);self.assertEqual(c.phase_index,1)

if __name__=='__main__':unittest.main()
