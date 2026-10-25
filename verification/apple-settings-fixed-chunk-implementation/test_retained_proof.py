"""Actual V9 Session/Bridge/replay controls. Every input and PNG here is synthetic."""
import copy
import http.client
import importlib.util
import json
import math
import pathlib
import threading
import types
import unittest
from unittest import mock
import fixtures as f
import replay
import settings_telemetry as t

HERE=pathlib.Path(__file__).resolve().parent

class V9Tests(unittest.TestCase):
    def flow(self,before=True,initial='0'):
        flow=f.Flow();self.addCleanup(flow.close)
        if before:flow.before(initial)
        return flow
    def durable(self,flow):
        return {p.name:p.read_bytes() for p in flow.bridge.output.glob('0000-settings-*.json')}
    def state(self,flow):
        return copy.deepcopy({k:v for k,v in flow.bridge.settings.__dict__.items() if k not in ['persist','persist_file','now','transaction']})
    def reject(self,flow,r,reason=None):
        state=self.state(flow);files=self.durable(flow)
        with self.assertRaisesRegex((ValueError,OSError),reason or '.'):
            flow.send(r)
        self.assertEqual(state,self.state(flow));self.assertEqual(files,self.durable(flow))
        self.assertEqual(flow.bridge.settings.summary(),replay.replay(flow.bridge.output))
    def observation(self,flow,stage='before-switch',value='0'):
        return flow.observe(stage,value=value,upload=False)[0]
    def test_initial_off_one_tap_and_on_zero_tap_complete_actual_bridge_and_replay(self):
        for initial,action in [('0','tap'),('1','no-tap')]:
            with self.subTest(initial=initial):
                flow=self.flow(False);flow.finish(initial)
                s=flow.bridge.settings.summary();self.assertTrue(s['setupObservationSatisfied'])
                self.assertEqual(s['switchAction'],action);self.assertEqual(s,replay.replay(flow.bridge.output))
                marks=[e for e in flow.bridge.settings.events if e.get('stage')=='switch-action']
                self.assertEqual(len(marks),1)
                b=s['switchActionBinding'];self.assertLess(b['beforeSequence'],b['actionSequence'])
                self.assertEqual(b['switchWitness']['hitPoint'],dict(x=336.5,y=160.3333282470703))
                result=f.producer.summary('interaction',flow.bridge,0,None,[])
                self.assertTrue(result['diagnosticCompleted']);self.assertEqual(len(result['dependentCasesUnrun']),6)
                for key in ['nativeKeyboardQualification','carrierAccepted','gaAccepted','runPassed','strictNativeVerdictsPassed']:self.assertIs(result[key],False)
    def test_query_counts_exact_integer_missing_ambiguous_boolean_reject_transactionally(self):
        for key,expected in [('parentCount',1),('leafCount',1),('leafSwitchChildCount',0),('leafSwitchDescendantCount',0)]:
            for bad in [None,True,False,expected+.0,-1,2,3]:
                with self.subTest(key=key,bad=bad):
                    flow=self.flow(False);flow.routes();r=self.observation(flow)
                    if bad is None:del r['switchWitness'][key]
                    else:r['switchWitness'][key]=bad
                    self.reject(flow,r,'Switch witness fields|Switch public query count')
    def test_public_relation_closed_and_root_composite_is_not_leaf(self):
        for relation in ['self','descendant','children','immediate-child','',None]:
            flow=self.flow(False);flow.routes();r=self.observation(flow);r['switchWitness']['relation']=relation
            self.reject(flow,r,'Switch public query relation')
        flow=self.flow(False);flow.routes();r=self.observation(flow)
        r['switchWitness']['leaf']=copy.deepcopy(r['snapshot'])
        self.reject(flow,r,'Exact public switch leaf')
    def test_parent_and_leaf_metadata_value_and_flags_fail_closed(self):
        changes=[('identifier','bad'),('label','bad'),('elementType',48),('elementType',True),('bundle','example'),('appState',3),('foreground',False),('exists',False),('hittable',False),('enabled',False),('enabled',1),('valueKind','unsupported'),('value',1),('value','2')]
        for target in ['parent','leaf']:
            for key,bad in changes:
                with self.subTest(target=target,key=key,bad=bad):
                    flow=self.flow(False);flow.routes();r=self.observation(flow);snap=r['snapshot'] if target=='parent' else r['switchWitness']['leaf'];snap[key]=bad
                    self.reject(flow,r)
        flow=self.flow(False);flow.routes();r=self.observation(flow);r['switchWitness']['leaf']['value']='1';self.reject(flow,r,'raw value agreement')
    def test_strict_geometry_screen_center_overlap_no_tolerance(self):
        changes=[('leaf','width',0),('parent','height',0),('leaf','x',500),('leaf','x',334.5),('leaf','y',174.3333282470703),('screen','width',336.5),('screen','height',160.3333282470703),('screen','x',336.5),('screen','y',160.3333282470703),('leaf','x',float('nan')),('parent','x',True)]
        for target,key,bad in changes:
            with self.subTest(target=target,key=key,bad=bad):
                flow=self.flow(False);flow.routes();r=self.observation(flow)
                rect=r['snapshot']['frame'] if target=='parent' else r['switchWitness']['leaf']['frame'] if target=='leaf' else r['switchWitness']['screen'];rect[key]=bad
                if target=='leaf':
                    leaf=rect;r['switchWitness']['hitPoint']=dict(x=leaf['x']+leaf['width']/2,y=leaf['y']+leaf['height']/2)
                self.reject(flow,r)
        for direction,okay in [(-math.inf,False),(math.inf,True)]:
            flow=self.flow(False);flow.routes();r,p=flow.observe('before-switch',upload=False)
            r['switchWitness']['screen']['width']=math.nextafter(336.5,direction)
            if okay:flow.send(r);flow.upload(p);self.assertIsNotNone(flow.bridge.settings.before)
            else:self.reject(flow,r,'strict interior')
        flow=self.flow(False);flow.routes();r=self.observation(flow);r['switchWitness']['hitPoint']['x']=201
        self.reject(flow,r,'leaf center')
    def test_observation_snapshot_times_capture_equal_and_neighbors(self):
        for key in ['parent','leaf']:
            for bound in ['before','after']:
                flow=self.flow(False);flow.routes();r=self.observation(flow)
                snap=r['snapshot'] if key=='parent' else r['switchWitness']['leaf']
                snap['observedUptime']=math.nextafter(r['captureStartedUptime'] if bound=='before' else r['captureFinishedUptime'],-math.inf if bound=='before' else math.inf)
                self.reject(flow,r,'Capture ordering|fresh public snapshot timing')
        flow=self.flow(False);flow.routes();r=self.observation(flow);r['switchWitness']['leaf']['observedUptime']=math.nextafter(r['snapshot']['observedUptime'],-math.inf)
        self.reject(flow,r,'fresh public snapshot timing')
    def test_action_before_sequence_missing_bool_and_wrong_binding_reject(self):
        for bad in [True,False,0,999,None]:
            flow=self.flow();r=flow.action_record()
            if bad is None:del r['detail']['beforeSequence']
            else:r['detail']['beforeSequence']=bad
            self.reject(flow,r,'Switch action shape/order|Switch before sequence binding')
    def test_action_fresh_snapshot_time_before_equal_after(self):
        for which in ['parent','leaf']:
            for direction in [-math.inf,0,math.inf]:
                flow=self.flow();r=flow.action_record();d=r['detail'];bound=flow.bridge.settings.before['captureFinishedUptime']
                parent=d['parent'];leaf=d['switchWitness']['leaf']
                if which=='parent':
                    parent['observedUptime']=bound if direction==0 else math.nextafter(bound,direction)
                else:
                    parent['observedUptime']=bound;leaf['observedUptime']=bound if direction==0 else math.nextafter(bound,direction)
                if direction==-math.inf:self.reject(flow,r,'fresh public snapshot timing')
                else:flow.send(r);self.assertIsNotNone(flow.bridge.settings.action_binding)
        flow=self.flow();r=flow.action_record();r['detail']['switchWitness']['leaf']['observedUptime']=math.nextafter(r['detail']['startedUptime'],math.inf)
        self.reject(flow,r,'fresh public snapshot timing')
    def test_action_exact_public_identity_state_values_geometry_bound_to_before(self):
        for mode in ['parent-frame','leaf-frame','screen','value','parent-identifier','leaf-identity','query','point']:
            flow=self.flow();r=flow.action_record();d=r['detail'];w=d['switchWitness']
            if mode=='parent-frame':d['parent']['frame']['width']+=1
            elif mode=='leaf-frame':w['leaf']['frame']['width']+=1;w['hitPoint']['x']+=.5
            elif mode=='screen':w['screen']['height']+=1
            elif mode=='value':d['parent']['value']=w['leaf']['value']='1'
            elif mode=='parent-identifier':d['parent']['identifier']='Full Keyboard Access'
            elif mode=='leaf-identity':w['leaf']['identifier']='FKAEnabledSwitch'
            elif mode=='query':w['leafCount']=2
            else:w['hitPoint']['x']+=1
            self.reject(flow,r)
    def test_action_order_anchor_completion_and_single_action(self):
        for mode in ['started-before','finished-before','finished-after-record','wrong-anchor','wrong-window','tap-on-initial-on','no-tap-on-initial-off','on-duration']:
            initial='1' if mode in ['tap-on-initial-on','on-duration'] else '0'
            flow=self.flow(initial=initial);r=flow.action_record(initial);d=r['detail']
            if mode=='started-before':d['startedUptime']=math.nextafter(flow.bridge.settings.before['captureFinishedUptime'],-math.inf)
            elif mode=='finished-before':d['finishedUptime']=math.nextafter(d['startedUptime'],-math.inf)
            elif mode=='finished-after-record':d['finishedUptime']=math.nextafter(r['uptime'],math.inf)
            elif mode=='wrong-anchor':d['anchorUptime']=math.nextafter(d['finishedUptime'],math.inf);d['deadlineUptime']=d['anchorUptime']+3
            elif mode=='wrong-window':d['deadlineUptime']=math.nextafter(d['deadlineUptime'],math.inf)
            elif mode=='tap-on-initial-on':d['action']='tap'
            elif mode=='no-tap-on-initial-off':d['action']='no-tap'
            else:d['finishedUptime']=math.nextafter(d['startedUptime'],math.inf)
            self.reject(flow,r)
        flow=self.flow();flow.action();r=flow.action_record();self.reject(flow,r,'Switch action shape/order')
    def test_after_switch_capture_must_follow_same_action_completion(self):
        for direction in [-math.inf,0,math.inf]:
            flow=self.flow();action=flow.action();r,p=flow.observe('after-switch',value='1',upload=False)
            boundary=action['detail']['finishedUptime'];start=boundary if direction==0 else math.nextafter(boundary,direction)
            # Earlier captures must also follow the before capture; these do.
            r.update(captureStartedUptime=start,captureFinishedUptime=start+.002)
            r['snapshot']['observedUptime']=start+.001;r['switchWitness']['leaf']['observedUptime']=start+.0011
            if direction==-math.inf:self.reject(flow,r,'Switch capture precedes action completion')
            else:flow.send(r);flow.upload(p);self.assertIsNotNone(flow.bridge.settings.after)
        flow=self.flow();r=self.observation(flow,'after-switch');self.reject(flow,r,'Switch capture precedes action completion')
    def test_after_and_poll_cannot_change_parent_leaf_binding(self):
        for stage in ['after-switch','poll','terminal']:
            flow=self.flow();flow.action()
            if stage!='after-switch':flow.observe('after-switch')
            r=self.observation(flow,stage,'1');r['switchWitness']['screen']['height']+=1
            self.reject(flow,r,'Switch observation public binding changed')
    def test_enabled_window_exact_completion_anchor_before_equal_after(self):
        for direction,expected in [(-math.inf,True),(0,True),(math.inf,False)]:
            flow=self.flow();flow.action();flow.observe('after-switch',value='0')
            r=self.observation(flow,'poll','1');boundary=flow.bridge.settings.observation_deadline
            observed=boundary if direction==0 else math.nextafter(boundary,direction)
            r.update(captureStartedUptime=observed-.001,captureFinishedUptime=observed+.001,uptime=observed+.002)
            r['snapshot']['observedUptime']=observed;r['switchWitness']['leaf']['observedUptime']=observed
            flow.send(r);flow.runner=r['uptime'];flow.observe('terminal',value='1');flow.completion()
            s=flow.bridge.settings.summary();self.assertEqual(bool(s['enabledWithinWindowSequences']),expected);self.assertEqual(s['setupObservationSatisfied'],expected)
            self.assertEqual(s,replay.replay(flow.bridge.output))
    def test_action_and_observation_persistence_failure_roll_back_then_retry(self):
        for stage in ['switch-action','after-switch']:
            flow=self.flow()
            if stage=='switch-action':r=flow.action_record()
            else:flow.action();r=self.observation(flow,'after-switch','1')
            with mock.patch.object(flow.bridge.persistence,'commit',side_effect=OSError('selected synthetic journal fsync failure')):
                self.reject(flow,r,'selected synthetic journal fsync failure')
            flow.send(r);self.assertEqual(flow.bridge.settings.sequence,r['sequence'])
    def test_offline_replay_rejects_mutated_fresh_action_witness(self):
        flow=self.flow(False);flow.finish()
        path=next(p for p in flow.bridge.output.glob('0000-settings-*.json') if json.loads(p.read_bytes())['record'].get('stage')=='switch-action')
        saved=json.loads(path.read_bytes());saved['record']['detail']['switchWitness']['leaf']['observedUptime']=0;path.write_text(json.dumps(saved))
        with self.assertRaisesRegex(ValueError,'fresh public snapshot timing'):replay.replay(flow.bridge.output)
    def test_exact_route2_suffixes_only_descendant_with_identified_container(self):
        for label in ['Full Keyboard Access, Off','Full Keyboard Access, On','Full Keyboard Access, Disabled','Full Keyboard Access, Off extra','Full Keyboard Access, Off, On','Full Keyboard AccessX']:
            for identifier in ['FULL_KEYBOARD_ACCESS','','WRONG']:
                flow=self.flow(False)
                def alter(r):
                    if r['routeIndex']==2:r['snapshot'].update(identifier=identifier,label=label)
                flow.before(search_alter=alter);flow.action();flow.observe('after-switch',value='1');flow.observe('terminal',value='1')
                expected=label in ['Full Keyboard Access, Off','Full Keyboard Access, On'] and identifier=='FULL_KEYBOARD_ACCESS'
                self.assertEqual(flow.bridge.settings.summary()['selectedRouteEvidenceExpected'],expected)
        flow=self.flow(False);flow.routes();search=flow.searches[2]
        container=copy.deepcopy(search['snapshot']);container.update(identifier='FULL_KEYBOARD_ACCESS',label='Full Keyboard Access, Off')
        witness=copy.deepcopy(search['routeWitness'])
        for change in ['wrong-target','self','wrong-type','wrong-state','disjoint','missing-query']:
            c=copy.deepcopy(container);w=copy.deepcopy(witness)
            if change=='wrong-target':w['target']['label']='wrong'
            elif change=='self':w['relation']='self'
            elif change=='wrong-type':c['elementType']=48
            elif change=='wrong-state':c['appState']=3
            elif change=='disjoint':w['target']['frame']['x']=999
            else:w['relation']='unknown'
            self.assertFalse(t.route_target(c,w,2))
    def test_route_same_tap_completion_order_and_metadata_preserved(self):
        for index in range(3):
            flow=self.flow(False);flow.mark('settings-launched')
            for i in range(index):flow.observe('route-search',index=i);flow.tap(i);flow.observe('route-opened',index=i)
            flow.observe('route-search',index=index);tap=flow.tap(index);r,_=flow.observe('route-opened',index=index,upload=False)
            start=math.nextafter(tap['detail']['finishedUptime'],-math.inf);r.update(captureStartedUptime=start,captureFinishedUptime=start+.002)
            r['snapshot']['observedUptime']=start+.001;r['routeWitness']['destination']['observedUptime']=start+.001
            self.reject(flow,r,'Route opened capture precedes same-route tap completion')

    def test_all_bounds_and_no_application_begin_remain_closed(self):
        self.assertEqual((t.CHUNK,t.MAX_TOTAL,t.MAX_REQUESTS,t.MAX_EVENTS,t.MAX_UPLOADS,t.MAX_DURATION),(4992,7000000,2500,100,32,29.0))
        flow=self.flow(False)
        with self.assertRaisesRegex(ValueError,'Setup-only diagnostic'):flow.bridge.request('begin',{})
        flow.before();r=flow.action_record();r['uptime']=math.nextafter(flow.bridge.settings.start_runner+29,math.inf);self.reject(flow,r,'Diagnostic monotonic time')

if __name__=='__main__':unittest.main(verbosity=2)
