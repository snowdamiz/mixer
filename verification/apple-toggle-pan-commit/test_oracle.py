"""Synthetic controls exercise rejection rules; no native action is generated here."""
import copy
import json
import pathlib
import unittest
import sys
import commit_oracle as o


def snapshot(initial):
    s={k:False for k in o.BOOLS};s.update({k:0 for k in o.COUNTERS})
    s.update(identity='host-control-carrier',isOn=initial,retainedOn=initial,selectedTrait=initial,
             enabled=True,allowed=True,toggleTrait=True,buttonTrait=True,configurationNil=True,menuNil=True,
             panState=0,previewThumbX=None,eventValues=[False,True],eventCount=2,traits=1,label='Sync entries',
             hint='Updates the sync preference',value=None,buttonType=0,scrollOffsetY=0,frameInWindow='{{303,244},{63,44}}',
             bounds='{{0,0},{63,44}}',displayScale=3,primaryCount=7,acceptedCount=5,panAcceptedCount=3,panCancellationCount=2)
    return s


def fixture(name):
    spec=o.SPECS[name];mode=spec['mode'];initial=spec['initial'];proposed=not initial
    # Explicit outcome table independent from carrier control flow.
    outcomes={'rebind':(False,initial),'stale':(False,initial),'disable':(False,initial),'cancel':(False,initial),
              'direction':(False,initial),'nested-primary':(True,proposed),'nested-accessibility':(True,proposed),'after-event-rebind':(True,initial)}
    accepted,final=outcomes[mode];late=mode=='after-event-rebind';b=snapshot(initial)
    def event(reason,s,t,sequence):return dict(reason=reason,state=copy.deepcopy(s),uptime=t,sequence=sequence,stage='host-only')
    before=dict(state=copy.deepcopy(b),events=[event('baseline',b,100,0)],diagnosticTrace=[],diagnosticTraceDropped=0,panCommitRecords=[],nativeInterruptions=[])
    gesture=dict(identity='host-control-native-pan',**{'class':'UIPanGestureRecognizer'},state=3,touchCount=0,enabled=True,cancelsTouches=True,allowedTouchTypes=[0,1,2,3],translationInWindow={'x':-20 if initial else 20,'y':0},velocityInWindow={'x':120,'y':0})
    trace=[dict(kind='recognizerShouldReceiveTouch',phase=0,sequence=1,uptime=100.1),dict(kind='shouldBeginDecision',isAuthoredPan=True,result=True,admissionReason='accepted',sequence=2,uptime=100.2)]
    for n,(phase,t,x) in enumerate([(1,101,2),(2,101.2,10),(3,102,20)],3):
        g=copy.deepcopy(gesture);g.update(state=phase,touchCount=0 if phase==3 else 1,sequence=n,uptime=t,kind='authoredPanCallback');g['translationInWindow']['x']=-x if initial else x;trace.append(g)
    preview=copy.deepcopy(b);preview.update(panActive=True,previewThumbX=12,panState=2)
    hb=copy.deepcopy(b);hb.update(isOn=proposed,retainedOn=proposed,selectedTrait=proposed,panState=3)
    events=copy.deepcopy(before['events'])+[event('panPreview',preview,101.1,1),event('selection',hb,102,2)]
    if late:
        for key in ['acceptedCount','panAcceptedCount','eventCount']:hb[key]+=1
        hb['eventValues'].append(proposed)
        events+=[event('valueChanged',hb,102.005,3),event('panAccepted',hb,102.009,4)]
    ha=copy.deepcopy(hb)
    if mode in ['rebind','after-event-rebind']:
        ha.update(isOn=initial,retainedOn=initial,selectedTrait=initial)
        events+=[event('selection',ha,102.015,len(events)),event('binding',ha,102.019,len(events)+1)]
    if mode=='disable':ha.update(enabled=False,notEnabledTrait=True)
    if mode=='stale':ha.update(allowed=False)
    if mode=='direction':ha.update(rtl=True)
    if mode=='nested-primary':ha.update(primaryCount=ha['primaryCount']+1,rejectedCount=ha['rejectedCount']+1)
    if mode=='nested-accessibility':ha['accessibilityActivationCount']+=1
    h=dict(mode='arm-commit-'+mode,reason='panAccepted' if late else 'selection',initial=initial,before=hb,after=copy.deepcopy(ha),nativeGestureAtHook=gesture,returned=False if mode=='nested-accessibility' else None,startedUptime=102.01,finishedUptime=102.02,traceSequenceAtCompletion=5)
    events.append(event('panCommitHookComplete',ha,102.03,len(events)))
    a=copy.deepcopy(ha);a.update(isOn=final,retainedOn=final,selectedTrait=final)
    if not accepted:
        a['panCancellationCount']+=1;events.append(event('panCommitRejected',a,102.05,len(events)))
    elif not late:
        for k in ['acceptedCount','panAcceptedCount','eventCount']:a[k]+=1
        a['eventValues'].append(proposed)
        events+=[event('valueChanged',a,102.04,len(events)),event('panAccepted',a,102.05,len(events)+1)]
    after=dict(state=a,events=events,diagnosticTrace=trace,diagnosticTraceDropped=0,panCommitRecords=[h],nativeInterruptions=[])
    return before,after


def result(name,b,a):return o.verdict('diagnostic',name,'native-pan-commit',b,a)

class Controls(unittest.TestCase):
    def test_sixteen_explicit_host_outcome_controls(self):
        self.assertEqual(len(o.SPECS),16)
        for name in o.SPECS:
            with self.subTest(case=name):
                b,a=fixture(name);self.assertTrue(result(name,b,a)['passed'],result(name,b,a))

    def test_rejects_native_hook_order_count_and_value_corruptions(self):
        mutations=[
            lambda a:a['state'].update(identity='replacement'),lambda a:a['state'].update(panActive=True),
            lambda a:a['state'].update(previewThumbX=12),lambda a:a['state'].update(eventCount=999),
            lambda a:a['state'].update(eventValues=[True,True]),lambda a:a['state'].update(primaryCount=99),
            lambda a:a['state'].update(rejectedCount=99),lambda a:a['state'].update(acceptedCount=99),
            lambda a:a['state'].update(panAcceptedCount=99),lambda a:a['state'].update(panNoChangeCount=99),
            lambda a:a['state'].update(panCancellationCount=99),lambda a:a['state'].update(accessibilityActivationCount=99),
            lambda a:a['state'].update(nativeToggleSelection=True),lambda a:a['state'].update(scrollOffsetY=30),
            lambda a:a['state'].update(label='wrong'),lambda a:a['state'].update(enabled=False,notEnabledTrait=True),
            lambda a:a['state'].update(allowed=False),lambda a:a['state'].update(rtl=True),
            lambda a:a.update(panCommitRecords=[]),lambda a:a['panCommitRecords'].append(copy.deepcopy(a['panCommitRecords'][0])),
            lambda a:a['panCommitRecords'][0].update(mode='arm-commit-cancel'),lambda a:a['panCommitRecords'][0].update(reason='selected'),
            lambda a:a['panCommitRecords'][0].update(initial=True),lambda a:a['panCommitRecords'][0].update(returned=True),
            lambda a:a['panCommitRecords'][0].update(startedUptime=0),lambda a:a['panCommitRecords'][0].update(finishedUptime=0),
            lambda a:a['panCommitRecords'][0].update(traceSequenceAtCompletion=999),
            lambda a:a['panCommitRecords'][0]['nativeGestureAtHook'].update(identity='fake'),
            lambda a:a['panCommitRecords'][0]['nativeGestureAtHook'].update(state=2),
            lambda a:a['panCommitRecords'][0]['nativeGestureAtHook'].update(touchCount=1),
            lambda a:a['panCommitRecords'][0]['before'].update(panActive=True),
            lambda a:a['panCommitRecords'][0]['before'].update(eventCount=99),
            lambda a:a['panCommitRecords'][0]['after'].update(eventCount=99),
            lambda a:a.update(diagnosticTraceDropped=1),lambda a:a['diagnosticTrace'][0].update(sequence=99),
            lambda a:a['diagnosticTrace'][0].update(phase=1),lambda a:a['diagnosticTrace'][1].update(result=False),
            lambda a:a['diagnosticTrace'][2].update(identity='fake'),lambda a:a['diagnosticTrace'][-1].update(state=4),
            lambda a:a['diagnosticTrace'][-1].update(uptime=101.05),lambda a:a['diagnosticTrace'][-1]['translationInWindow'].update(x=0),
            lambda a:a.update(events=[e for e in a['events'] if e['reason']!='panPreview']),
            lambda a:a.update(events=[e for e in a['events'] if e['reason']!='valueChanged']),
            lambda a:a.update(events=[e for e in a['events'] if e['reason']!='panCommitHookComplete']),
        ]
        name='commit-nested-primary-off'
        for i,mutate in enumerate(mutations):
            with self.subTest(mutation=i):
                b,a=fixture(name);mutate(a);self.assertFalse(result(name,b,a)['passed'])
        self.assertEqual(len(mutations),44)

    def test_strict_state_types_in_every_snapshot(self):
        name='commit-nested-primary-off';b,a=fixture(name)
        paths=[('state',),('panCommitRecords',0,'before'),('panCommitRecords',0,'after'),('events',2,'state')]
        self.assertEqual(len(o.STATE_KEYS),44)
        for path in paths:
            for key in o.STATE_KEYS:
                with self.subTest(path=path,key=key):
                    b,a=fixture(name);s=a
                    for item in path:s=s[item]
                    s[key]=0 if key in o.BOOLS else True if key in o.COUNTERS or key in ['traits','panState','buttonType','scrollOffsetY','displayScale','previewThumbX'] else 99
                    self.assertFalse(result(name,b,a)['passed'])

    def test_rejects_type_coercion_and_nonfinite_native_evidence(self):
        changes=[lambda a:a.update(diagnosticTraceDropped=False),lambda a:a['events'][0].update(sequence=False),
                 lambda a:a['events'][0].update(uptime=float('nan')),lambda a:a['diagnosticTrace'][0].update(sequence=True),
                 lambda a:a['diagnosticTrace'][0].update(phase=False),lambda a:a['diagnosticTrace'][1].update(result=1),
                 lambda a:a['diagnosticTrace'][2].update(state=True),lambda a:a['diagnosticTrace'][2].update(touchCount=True),
                 lambda a:a['diagnosticTrace'][2]['translationInWindow'].update(x=float('inf')),
                 lambda a:a['panCommitRecords'][0].update(initial=0),lambda a:a['panCommitRecords'][0].update(startedUptime=True),
                 lambda a:a['panCommitRecords'][0].update(traceSequenceAtCompletion=True)]
        for i,change in enumerate(changes):
            with self.subTest(mutation=i):
                b,a=fixture('commit-rebind-off');change(a);self.assertFalse(result('commit-rebind-off',b,a)['passed'])

    def test_rejects_wrong_latest_binding_gate_nested_and_event_order(self):
        for name in o.SPECS:
            b,a=fixture(name);s=a['state'];s.update(isOn=not s['isOn'],retainedOn=not s['retainedOn'],selectedTrait=not s['selectedTrait'])
            self.assertFalse(result(name,b,a)['passed'])
        for mode in ['nested-primary','nested-accessibility','after-event-rebind']:
            name='commit-'+mode+'-off';b,a=fixture(name)
            x=next(e for e in a['events'] if e['reason']=='valueChanged');y=next(e for e in a['events'] if e['reason']=='panAccepted')
            x['reason'],y['reason']=y['reason'],x['reason'];self.assertFalse(result(name,b,a)['passed'])
        name='commit-after-event-rebind-off';b,a=fixture(name);a['state']['eventValues'][-1]=False
        self.assertFalse(result(name,b,a)['passed'])

    def test_closed_union_and_original_oracle_passthrough(self):
        self.assertEqual(len(o.ORIGINAL_CASES),10);self.assertEqual(len(o.interruption.CASES),16);self.assertEqual(len(o.CASES),43)
        self.assertEqual(o.COMMANDS,set(sum(o.CASE_COMMAND_SEQUENCE.values(),[])))
        self.assertNotIn('comparator-direct',o.CASES);self.assertNotIn('diagnostic-direct',o.CASES)
        name='commit-rebind-off';b,a=fixture(name)
        self.assertFalse(o.verdict('diagnostic','unknown','native-pan-commit',b,a)['passed'])
        self.assertFalse(o.verdict('comparator',name,'native-pan-commit',b,a)['passed'])
        self.assertFalse(o.verdict('diagnostic',name,'authored-pan',b,a)['passed'])
        self.assertFalse(o.verdict('diagnostic',name,'native-pan-commit',b,a,False)['passed'])
        p=o.BASE.parent/'apple-toggle-pan-origin-correction/runtime/captures'
        for n in range(1,11):
            for f in sorted(p.glob(f'{n:04d}-after-*.json')):
                a=json.loads(f.read_bytes());old=a['verdict'];b=json.loads(f.with_name(f.name.replace('after','before')).read_bytes())['observation']
                self.assertEqual(o.verdict(old['candidate'],old['case'],old['action'],b,a['observation']),o.original.verdict(old['candidate'],old['case'],old['action'],b,a['observation']))

    def test_unchanged_interruption_passthrough(self):
        sys.modules['interruption_oracle']=o.interruption
        controls=o.load('inherited_interruption_controls',o.BASE.parent/'apple-toggle-native-interruption/test_oracle.py')
        for name in o.interruption.CASES:
            b,a=controls.fixture(name)
            self.assertEqual(o.verdict('diagnostic',name,'native-pan-interruption',b,a),o.interruption.verdict('diagnostic',name,'native-pan-interruption',b,a))

    def test_scoped_semantic_keeps_original_failures(self):
        p=o.BASE.parent/'apple-toggle-semantic-activation/runtime-direct/captures'
        b=json.loads((p/'0001-before-1.json').read_bytes())['observation'];a=json.loads((p/'0001-after-1.json').read_bytes())['observation']
        value=o.verdict('diagnostic','semantic-components','direct-suite',b,a)
        self.assertTrue(value['passed'],value);self.assertFalse(value['originalStrictVerdict']['passed']);self.assertEqual(len(value['originalFailures']),4)
        for change in [lambda a:a['checks'][14].update({'pass':True}),lambda a:a['checks'].pop(),lambda a:a['semanticOperations'].pop(),lambda a:a['semanticOperations'][0]['after'].update(events=True),lambda a:a.update(diagnosticSuiteState='running')]:
            broken=copy.deepcopy(a);change(broken);self.assertFalse(o.verdict('diagnostic','semantic-components','direct-suite',b,broken)['passed'])


    def test_hook_counter_snapshots_are_exact(self):
        for mode in ['rebind','nested-primary','nested-accessibility','after-event-rebind']:
            name='commit-'+mode+'-off'
            for when in ['before','after']:
                for key in ['primaryCount','rejectedCount','accessibilityActivationCount','panNoChangeCount','panCancellationCount','acceptedCount','panAcceptedCount']:
                    with self.subTest(mode=mode,when=when,key=key):
                        b,a=fixture(name);a['panCommitRecords'][0][when][key]+=10
                        self.assertFalse(result(name,b,a)['passed'])

    def test_unified_summary_separates_native_and_scoped_direct(self):
        import run
        class Bridge:
            failures=[]
        bridge=Bridge()
        bridge.verdicts=[dict(case=n,action=o.CASE_ACTION[n],passed=True) for n in o.CASES if n!='semantic-components' for _ in range(2 if n.endswith('taps') else 1)]
        raw=dict(passed=False,predicates={'allOriginalStrictChecksTrue':False})
        bridge.verdicts.append(dict(case='semantic-components',action='direct-suite',passed=True,originalStrictVerdict=raw))
        value=run.summary('interaction',bridge,0,None,[dict(resource='synthetic-only',passed=True)])
        self.assertEqual(len(run.METHODS),43);self.assertEqual(len(set(run.METHODS)),43)
        self.assertEqual(len(value['nativeUserInteractionVerdicts']),45)
        self.assertEqual(len(value['scopedDirectComponentVerdicts']),1)
        self.assertTrue(value['strictNativeVerdictsPassed']);self.assertTrue(value['scopedDirectComponentsPassed'])
        self.assertTrue(value['runPassed']);self.assertFalse(value['directOriginalVerdicts'][0]['passed'])
        bridge.verdicts[-1]['passed']=False
        value=run.summary('interaction',bridge,0,None,[dict(resource='synthetic-only',passed=True)])
        self.assertTrue(value['strictNativeVerdictsPassed']);self.assertFalse(value['scopedDirectComponentsPassed']);self.assertFalse(value['runPassed'])
        bridge.verdicts[-1].pop('originalStrictVerdict')
        self.assertEqual(run.summary('interaction',bridge,1,None,[])['directOriginalVerdicts'],[None])
        bridge.verdicts.pop(0)
        self.assertFalse(run.summary('interaction',bridge,0,None,[])['strictNativeVerdictsPassed'])

if __name__=='__main__':unittest.main()
