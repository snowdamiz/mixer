#!/usr/bin/env python3
"""Independent synthetic inputs sent through sealed V7 Bridge/Session/replay.

This is not native, XCUI, screenshot, or keyboard qualification evidence.
The producer fixtures and verifier are not used to authorize any assertion.
"""
import base64
import copy
import hashlib
import http.client
import importlib.util
import json
import math
import os
import pathlib
import struct
import sys
import threading
import unittest
import zlib
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/apple-toggle-keyboard-focus-v7-preparation'
sys.path.insert(0, str(PRODUCER))
spec = importlib.util.spec_from_file_location('independently_reviewed_v7', PRODUCER / 'run.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
t = p.settings_telemetry
spec = importlib.util.spec_from_file_location('independently_reviewed_v7_replay', PRODUCER / 'replay.py')
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)


def image():
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 2, 1, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b'\x00' + b'\xff\x00\x00\xff' * 2)) + chunk(b'IEND', b'')


class Flow:
    count = 0
    def __init__(self, name='case'):
        Flow.count += 1
        self.root = HERE / 'host-evidence' / os.environ.get('MIXER_REVIEW_ATTEMPT', 'attempt-1') / (f'{Flow.count:04d}-' + name)
        self.root.mkdir(parents=True, exist_ok=False)
        docs = self.root / 'Documents'
        docs.mkdir()
        self.bridge = p.h.Bridge({'diagnostic': docs, 'comparator': docs}, self.root / 'captures', 'independent-synthetic-capability', {'scope': 'synthetic-host-only'}, allowed_cases=p.keyboard_oracle.CASES)
        self.host = 200.0
        self.now = 20.0
        self.bridge.settings.now = lambda: self.host
        self.bridge.settings.deadline = 500.0
        self.send(dict(kind='start', case=t.CASE, uptime=self.now))

    def send(self, record):
        # Match the public JSON boundary's ownership of decoded request objects.
        return self.bridge.request('evaluate', json.loads(json.dumps({'settingsDiagnostic': record})))

    def record(self, kind, **fields):
        self.now += .02
        self.host += .001
        return dict(kind=kind, case=t.CASE, generation=self.bridge.settings.token, sequence=self.bridge.settings.sequence + 1, uptime=self.now, **fields)

    def snap(self, *, kind='parent', value='0', observed=None):
        return dict(bundle='com.apple.Preferences', foreground=True, appState=4, observedUptime=self.now+.001 if observed is None else observed,
                    identifier='FKAEnabledSwitch' if kind == 'parent' else '', label='Full Keyboard Access' if kind == 'parent' else '', elementType=40,
                    exists=True, hittable=True, enabled=True, valueKind='string', value=value,
                    frame=dict(x=36, y=146.3333282470703, width=330, height=28) if kind == 'parent' else dict(x=305, y=146.3333282470703, width=63, height=28))

    def witness(self, parent):
        return dict(relation='immediate-child-switch', parentCount=1, leafCount=1, leafSwitchChildCount=0, leafSwitchDescendantCount=0,
                    leaf=self.snap(kind='leaf', value=parent['value'], observed=parent['observedUptime']+.0001), screen=dict(x=0, y=0, width=402, height=874), hitPoint=dict(x=336.5, y=160.3333282470703))

    def mark(self, stage, detail=None):
        r = self.record('mark', stage=stage, detail=detail or {})
        self.send(r)
        return r

    def observation(self, stage, value='0', index=3):
        self.now += .02
        start = self.now
        snap = self.snap(value=value)
        payloads = {} if stage == 'poll' else {'ax': b'Independent synthetic host AX; no native hierarchy\n'}
        if not stage.startswith('route-') and stage != 'poll':
            payloads['png'] = image()
        r = self.record('observe', stage=stage, routeIndex=index, attempt=0, captureStartedUptime=start, captureFinishedUptime=start+.004, snapshot=snap,
                        files={key: dict(bytes=len(data), sha256=t.sha(data)) for key, data in payloads.items()})
        if stage == 'route-search':
            snap.update(identifier=['com.apple.settings.accessibility', 'KEYBOARDS', 'FULL_KEYBOARD_ACCESS'][index], label=t.ROUTE[index], elementType=75, valueKind='unsupported', value='', frame=dict(x=10, y=100, width=300, height=60))
            target = {**copy.deepcopy(snap), 'identifier': '', 'elementType': 48, 'frame': dict(x=20, y=110, width=200, height=20)}
            r['routeWitness'] = dict(relation='descendant', target=target)
        elif stage == 'route-opened':
            snap.update(identifier='', label='', elementType=0, exists=False, hittable=False, enabled=False, valueKind='absent', value='', frame=dict(x=0, y=0, width=0, height=0))
            destination = {**self.snap(observed=start+.002), 'identifier': t.ROUTE[index], 'label': '', 'elementType': 21, 'valueKind': 'unsupported', 'value': '', 'frame': dict(x=0, y=10, width=402, height=44)}
            r['routeWitness'] = dict(destination=destination)
        else:
            r['switchWitness'] = self.witness(snap)
        return r, payloads

    def chunks(self, payloads):
        for slot in list(self.bridge.settings.pending):
            form = slot.rsplit('-', 1)[1]
            data = payloads[form]
            item = self.bridge.settings.uploads[slot]
            for index in range(item['count']):
                yield self.record('chunk', slot=slot, index=index, count=item['count'], bytes=len(data), sha256=t.sha(data), data=base64.b64encode(data[index*3072:(index+1)*3072]).decode())

    def upload(self, payloads):
        for chunk in self.chunks(payloads):
            self.send(chunk)

    def observe(self, stage, value='0', index=3, alter=None):
        r, payloads = self.observation(stage, value, index)
        if alter: alter(r)
        self.send(r)
        self.upload(payloads)
        return r

    def routes(self, suffix=None):
        self.mark('settings-launched')
        for i in range(3):
            r = self.observe('route-search', index=i, alter=(lambda r: r['snapshot'].update(label=suffix)) if i == 2 and suffix else None)
            target = copy.deepcopy(r['routeWitness']['target'])
            target['observedUptime'] = self.now+.001
            started, finished = self.now+.002, self.now+.003
            self.mark('route-tap', dict(routeIndex=i, searchSequence=r['sequence'], target=target, startedUptime=started, finishedUptime=finished))
            self.observe('route-opened', index=i)

    def before(self, initial='0', suffix=None):
        self.routes(suffix)
        self.observe('before-switch', initial)

    def action(self, initial='0', send=True):
        parent = copy.deepcopy(self.bridge.settings.before['snapshot'])
        parent['observedUptime'] = self.now+.001
        witness = self.witness(parent)
        started = self.now+.003
        finished = started+.001 if initial == '0' else started
        anchor = finished if initial == '0' else self.bridge.settings.before['snapshot']['observedUptime']
        r = self.record('mark', stage='switch-action', detail=dict(action='tap' if initial == '0' else 'no-tap', beforeSequence=self.bridge.settings.before['sequence'], parent=parent, switchWitness=witness,
                                                                  startedUptime=started, finishedUptime=finished, anchorUptime=anchor, deadlineUptime=anchor+3.0))
        if send: self.send(r)
        return r

    def complete(self, initial='0'):
        self.before(initial)
        self.action(initial)
        self.observe('after-switch', '1')
        self.observe('terminal', '1')
        for stage in ['terminate-before', 'terminate-after', 'test-case-finished', 'suite-finished', 'bundle-finished']:
            self.mark(stage)

    def state(self):
        return copy.deepcopy({key:value for key,value in self.bridge.settings.__dict__.items() if key not in ['persist', 'persist_file', 'now']})

    def journal(self):
        return {path.name:path.read_bytes() for path in self.bridge.output.glob('0000-settings-*.json')}


class IndependentHostChecks(unittest.TestCase):
    def reject(self, flow, record, reason='.'):
        state, journal = flow.state(), flow.journal()
        with self.assertRaisesRegex((ValueError, OSError), reason):
            flow.send(record)
        self.assertEqual(state, flow.state())
        self.assertEqual(journal, flow.journal())
        self.assertEqual(flow.bridge.settings.summary(), replay.replay(flow.bridge.output))

    def test_initial_states_one_marker_no_extra_tap_host_and_replay(self):
        for initial, expected in [('0', 'tap'), ('1', 'no-tap')]:
            f = Flow('initial-' + initial); f.complete(initial)
            s = f.bridge.settings.summary()
            self.assertTrue(s['setupObservationSatisfied'])
            self.assertEqual(s['switchAction'], expected)
            self.assertEqual(s, replay.replay(f.bridge.output))
            self.assertEqual(len([e for e in f.bridge.settings.events if e.get('stage') == 'switch-action']), 1)
            self.assertEqual(s['applicationCasesExecuted'], 0)
            self.assertFalse(s['nativeKeyboardQualification'])
            self.assertEqual(s['switchActionBinding']['switchWitness']['hitPoint']['x'], 336.5)

    def test_closed_integer_query_counts_and_old_composite_center(self):
        f = Flow('counts'); f.routes()
        for key in ['parentCount','leafCount','leafSwitchChildCount','leafSwitchDescendantCount']:
            for bad in [True, False, None, 1.0, -1, 2]:
                r, _ = f.observation('before-switch'); r['switchWitness'][key] = bad
                self.reject(f, r, 'Switch public query count')
        r, _ = f.observation('before-switch'); r['switchWitness']['hitPoint']['x'] = 201.0
        self.reject(f, r, 'Switch leaf center')

    def test_exact_metadata_flags_values_relation_and_nested_leaf(self):
        f = Flow('metadata'); f.routes()
        changes = [('bundle','wrong'),('identifier','wrong'),('label','wrong'),('elementType',75),('appState',3),('foreground',False),('exists',False),('hittable',False),('enabled',1),('valueKind','unsupported'),('value','2')]
        for side in ['parent','leaf']:
            for key, value in changes:
                r, _ = f.observation('before-switch'); v = r['snapshot'] if side == 'parent' else r['switchWitness']['leaf']; v[key] = value
                self.reject(f, r)
        for relation in ['descendant','self','immediate-child','']:
            r, _ = f.observation('before-switch'); r['switchWitness']['relation'] = relation; self.reject(f, r)
        r, _ = f.observation('before-switch'); r['switchWitness']['leaf']['value'] = '1'; self.reject(f, r, 'raw value agreement')

    def test_strict_interior_screen_and_parent_neighbors(self):
        f = Flow('geometry'); f.routes()
        for side, key, value in [('leaf','x',500),('leaf','width',0),('screen','width',336.5),('screen','x',336.5),('parent','width',300.5),('parent','x',True),('leaf','height',float('inf'))]:
            r, _ = f.observation('before-switch'); w = r['switchWitness']; rect = r['snapshot']['frame'] if side == 'parent' else w['leaf']['frame'] if side == 'leaf' else w['screen']; rect[key] = value
            if side == 'leaf': w['hitPoint'] = dict(x=rect['x']+rect['width']/2, y=rect['y']+rect['height']/2)
            self.reject(f, r)
        r, _ = f.observation('before-switch'); r['switchWitness']['screen']['width'] = math.nextafter(336.5, -math.inf); self.reject(f, r)
        r, payloads = f.observation('before-switch'); r['switchWitness']['screen']['width'] = math.nextafter(336.5, math.inf); f.send(r); f.upload(payloads)

    def test_action_exact_fresh_binding_and_timing_neighbors(self):
        f = Flow('binding'); f.before()
        for change in ['before-sequence','stale-parent','late-leaf','screen','parent-frame','leaf-frame','initial-value','anchor','deadline','end-before-start','no-tap']:
            r = f.action(send=False); d = r['detail']; w = d['switchWitness']
            if change == 'before-sequence': d['beforeSequence'] = True
            elif change == 'stale-parent': d['parent']['observedUptime'] = math.nextafter(f.bridge.settings.before['captureFinishedUptime'], -math.inf)
            elif change == 'late-leaf': w['leaf']['observedUptime'] = math.nextafter(d['startedUptime'], math.inf)
            elif change == 'screen': w['screen']['height'] += 1
            elif change == 'parent-frame': d['parent']['frame']['width'] += 1
            elif change == 'leaf-frame': w['leaf']['frame']['width'] += 1; w['hitPoint']['x'] += .5
            elif change == 'initial-value': d['parent']['value'] = w['leaf']['value'] = '1'
            elif change == 'anchor': d['anchorUptime'] += .001; d['deadlineUptime'] = d['anchorUptime']+3
            elif change == 'deadline': d['deadlineUptime'] = math.nextafter(d['deadlineUptime'], math.inf)
            elif change == 'end-before-start': d['finishedUptime'] = math.nextafter(d['startedUptime'], -math.inf)
            else: d['action'] = 'no-tap'
            self.reject(f, r)
        r = f.action(send=False); d = r['detail']; boundary = f.bridge.settings.before['captureFinishedUptime']; d['parent']['observedUptime'] = d['switchWitness']['leaf']['observedUptime'] = boundary; f.send(r)
        self.reject(f, f.action(send=False), 'Switch action shape/order')

    def test_initial_on_no_action_duration_and_immutable_original_anchor(self):
        f = Flow('initial-on'); f.before('1')
        for mode in ['tap','duration','anchor']:
            r = f.action('1', send=False); d = r['detail']
            if mode == 'tap': d['action'] = 'tap'
            elif mode == 'duration': d['finishedUptime'] = math.nextafter(d['startedUptime'], math.inf)
            else: d['anchorUptime'] = d['startedUptime']; d['deadlineUptime'] = d['anchorUptime']+3
            self.reject(f,r)
        f.action('1'); self.assertEqual(f.bridge.settings.anchor, f.bridge.settings.before['snapshot']['observedUptime'])

    def test_after_capture_equal_or_after_completion_and_reject_one_ulp_before(self):
        for direction in [-math.inf, 0, math.inf]:
            f = Flow('after-boundary'); f.before(); a = f.action(); r, payloads = f.observation('after-switch', '1')
            boundary = a['detail']['finishedUptime']; start = boundary if direction == 0 else math.nextafter(boundary, direction)
            r.update(captureStartedUptime=start, captureFinishedUptime=start+.003); r['snapshot']['observedUptime'] = start+.001; r['switchWitness']['leaf']['observedUptime'] = start+.002
            if direction == -math.inf: self.reject(f, r, 'Switch capture precedes action completion')
            else: f.send(r); f.upload(payloads)

    def test_deadline_before_equal_after_and_no_marker_extension(self):
        for direction, expected in [(-math.inf,True),(0,True),(math.inf,False)]:
            f = Flow('window'); f.before(); f.action(); f.observe('after-switch'); r, _ = f.observation('poll','1'); deadline = f.bridge.settings.observation_deadline
            observed = deadline if direction == 0 else math.nextafter(deadline,direction)
            r.update(captureStartedUptime=observed-.001,captureFinishedUptime=observed+.001,uptime=observed+.002); r['snapshot']['observedUptime'] = r['switchWitness']['leaf']['observedUptime'] = observed
            f.send(r); f.now = r['uptime']; f.observe('terminal','1')
            self.assertEqual(f.bridge.settings.summary()['setupObservationSatisfied'],expected)
            self.assertEqual(f.bridge.settings.summary(), replay.replay(f.bridge.output))

    def test_route2_status_labels_and_wrong_metadata_do_not_gain_route_credit(self):
        for label, good in [('Full Keyboard Access, Off',True),('Full Keyboard Access, On',True),('Full Keyboard Access, Off extra',False),('Full Keyboard Access, Enabled',False)]:
            f = Flow('route-suffix'); f.before(suffix=label); f.action(); f.observe('after-switch','1'); f.observe('terminal','1')
            self.assertEqual(f.bridge.settings.summary()['selectedRouteEvidenceExpected'],good)
        f = Flow('route-witness'); f.routes()
        search = next(e for e in f.bridge.settings.events if e.get('stage')=='route-search' and e['routeIndex']==2)
        for change in ['identifier','self','target','disjoint']:
            container = copy.deepcopy(search['snapshot']); container['label']='Full Keyboard Access, Off'; witness = copy.deepcopy(search['routeWitness'])
            if change == 'identifier': container['identifier']=''
            elif change == 'self': witness['relation']='self'
            elif change == 'target': witness['target']['label']='wrong'
            else: witness['target']['frame']['x']=900
            self.assertFalse(t.route_target(container,witness,2))

    def test_selected_prewrite_persistence_failures_rollback_and_replay(self):
        for stage in ['switch-action','after-switch']:
            f = Flow('prewrite-failure'); f.before()
            if stage == 'switch-action': r=f.action(send=False)
            else: f.action(); r,_=f.observation('after-switch','1')
            with mock.patch.object(f.bridge,'save',side_effect=OSError('independent prewrite journal failure')):
                self.reject(f,r,'independent prewrite journal failure')
            f.send(r)
            self.assertEqual(f.bridge.settings.sequence,r['sequence'])

    def test_actual_http_rejection_count_and_framing_without_durable_advance(self):
        f=Flow('http'); f.before(); r=f.action(send=False); r['detail']['switchWitness']['leafCount']=True
        state,journal=f.state(),f.journal(); server=p.h.server_for(f.bridge); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        try:
            for body in [json.dumps({'settingsDiagnostic':r}).encode(), b'{"settingsDiagnostic":{},"settingsDiagnostic":{}}']:
                client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=2)
                try:
                    client.request('POST','/evaluate',body=body,headers={'X-Mixer-Capability':'independent-synthetic-capability','Content-Type':'application/json'})
                    response=client.getresponse(); data=response.read(); self.assertEqual(response.status,400); self.assertLessEqual(len(data),8192)
                finally: client.close()
        finally: server.shutdown(); server.server_close(); thread.join(3); self.assertFalse(thread.is_alive())
        self.assertEqual(state,f.state()); self.assertEqual(journal,f.journal())

    def test_bounds_no_app_begin_and_monotonicity(self):
        self.assertEqual((t.MAX_DURATION,t.MAX_REQUESTS,t.MAX_EVENTS,t.MAX_UPLOADS,t.MAX_TOTAL,t.CHUNK),(29,2500,100,32,7000000,3072))
        f=Flow('bounds'); f.before()
        with self.assertRaisesRegex(ValueError,'Setup-only diagnostic'): f.bridge.request('begin',{})
        r=f.action(send=False); r['uptime']=math.nextafter(49, math.inf); self.reject(f,r,'Diagnostic monotonic time')
        r=f.action(send=False); prior=f.host; f.host=math.nextafter(f.bridge.settings.last_host,-math.inf); self.reject(f,r,'host receipt'); f.host=prior

    def test_exact_compiled_independent_swift_wire_decodes_through_real_validator(self):
        value=json.loads((HERE/'swift-independent-witness.json').read_bytes()); parent=t.snapshot(value['snapshot']); self.assertEqual(t.switch_witness(parent,value['switchWitness'],50,51),value['switchWitness'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
