#!/usr/bin/env python3
"""Fresh independent emitters against the sealed, real V5 Bridge and Session.

Every AX/PNG and input marker here is synthetic host data, never native evidence.
No producer fixtures, adapted test classes, native runners, or Git are invoked.
CONTRACT assertions deliberately remain ordinary assertions if a hole is found.
"""
import base64
import copy
import hashlib
import http.client
import importlib.util
import json
import pathlib
import shutil
import struct
import sys
import tempfile
import threading
import unittest
import zlib
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = HERE
sys.path.insert(0, str(PRODUCER))
spec = importlib.util.spec_from_file_location('reviewed_v6_run', PRODUCER / 'run.py')
producer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(producer)
t = producer.settings_telemetry
spec = importlib.util.spec_from_file_location('reviewed_v6_replay', PRODUCER / 'replay.py')
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)
SCRATCH = HERE / '.scratch'
SCRATCH.mkdir(exist_ok=True)


def image():
    def chunk(name, data):
        return struct.pack('>I', len(data)) + name + data + struct.pack('>I', zlib.crc32(name + data) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b'\x00\x00\x00\x00\xff')) + chunk(b'IEND', b'')


class Flow:
    def __init__(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='real-v5-', dir=SCRATCH)
        self.root = pathlib.Path(self.temporary.name)
        docs = self.root / 'Documents'
        docs.mkdir()
        self.bridge = producer.h.Bridge({'diagnostic': docs, 'comparator': docs}, self.root / 'captures', 'independent-review-capability', {'scope': 'synthetic-host-only'}, allowed_cases=producer.keyboard_oracle.CASES)
        self.clock = 100.0
        self.runner = 10.0
        self.bridge.settings.now = lambda: self.clock
        self.bridge.settings.deadline = 500.0
        self.send({'kind': 'start', 'case': t.CASE, 'uptime': self.runner})
        self.searches = {}
        self.taps = {}

    def close(self):
        self.temporary.cleanup()

    def send(self, record):
        return self.bridge.request('evaluate', {'settingsDiagnostic': record})

    def record(self, kind, **fields):
        self.runner += .01
        self.clock += .001
        return {'kind': kind, 'case': t.CASE, 'generation': self.bridge.settings.token, 'sequence': self.bridge.settings.sequence + 1, 'uptime': self.runner, **fields}

    def mark(self, stage, detail=None):
        r = self.record('mark', stage=stage, detail={} if detail is None else detail)
        self.send(r)
        return r

    def snap(self, **fields):
        return {'bundle': 'com.apple.Preferences', 'foreground': True, 'appState': 4, 'observedUptime': self.runner + .001, 'identifier': 'FKAEnabledSwitch', 'label': 'Full Keyboard Access', 'elementType': 40, 'exists': True, 'hittable': True, 'enabled': True, 'valueKind': 'string', 'value': '0', 'frame': {'x': 10, 'y': 100, 'width': 300, 'height': 50}, **fields}

    def observe(self, stage, index=3, attempt=0, value='0', alter=None, upload=True):
        self.runner += .01
        started = self.runner
        raw = self.snap(value=value)
        witness = None
        if stage == 'route-search':
            raw.update(identifier='', label='', elementType=75, valueKind='unsupported', value='')
            target = self.snap(identifier='', label=t.ROUTE[index], elementType=48, valueKind='unsupported', value='', frame=dict(x=20, y=110, width=200, height=20))
            witness = {'relation': 'descendant', 'target': target}
        elif stage == 'route-opened':
            raw.update(identifier='', label='', elementType=75, hittable=False, valueKind='unsupported', value='', frame=dict(x=-105, y=100, width=300, height=50))
            witness = {'destination': self.snap(identifier=t.ROUTE[index], label='', elementType=21, valueKind='unsupported', value='', frame=dict(x=0, y=10, width=320, height=44))}
        payloads = {} if stage == 'poll' else {'ax': b'Independent synthetic AX text; not a native hierarchy\n'}
        if stage in ['before-switch', 'after-switch', 'terminal']:
            payloads['png'] = image()
        files = {form: {'bytes': len(data), 'sha256': t.sha(data)} for form, data in payloads.items()}
        r = self.record('observe', stage=stage, routeIndex=index, attempt=attempt, captureStartedUptime=started, captureFinishedUptime=started+.002, snapshot=raw, files=files)
        if witness is not None:
            r['routeWitness'] = witness
        if alter:
            alter(r)
        if upload:
            self.send(r)
            self.upload(payloads)
        if stage == 'route-search':
            self.searches[index] = r
        return r, payloads

    def upload(self, payloads):
        for slot in list(self.bridge.settings.pending):
            form = slot.rsplit('-', 1)[1]
            data = payloads[form]
            item = self.bridge.settings.uploads[slot]
            for index in range(item['count']):
                r = self.record('chunk', slot=slot, index=index, count=item['count'], bytes=len(data), sha256=t.sha(data), data=base64.b64encode(data[index*t.CHUNK:(index+1)*t.CHUNK]).decode())
                self.send(r)

    def tap(self, index, alter=None):
        target = copy.deepcopy(self.searches[index]['routeWitness']['target'])
        target['observedUptime'] = self.runner+.001
        r = self.record('mark', stage='route-tap', detail={'routeIndex': index, 'searchSequence': self.searches[index]['sequence'], 'target': target, 'startedUptime': self.runner+.002, 'finishedUptime': self.runner+.003})
        # Python evaluates keyword arguments before record advances the clock.
        if alter:
            alter(r)
        self.send(r)
        self.taps[index] = r
        return r

    def routes(self, search_alter=None, tap_alter=None, opened_alter=None):
        self.mark('settings-launched')
        for index in range(3):
            self.observe('route-search', index=index, alter=(lambda r: search_alter(r)) if search_alter else None)
            self.tap(index, (lambda r: tap_alter(r)) if tap_alter else None)
            self.observe('route-opened', index=index, alter=(lambda r: opened_alter(r)) if opened_alter else None)

    def before(self, initial='0', **options):
        self.routes(**options)
        self.observe('before-switch', value=initial)

    def action(self, initial='0'):
        anchor = self.runner+.001 if initial == '0' else self.bridge.settings.before['snapshot']['observedUptime']
        self.mark('switch-action', {'action': 'tap' if initial == '0' else 'no-tap', 'anchorUptime': anchor, 'deadlineUptime': anchor+3.0})

    def completion(self):
        for stage in ['terminate-before', 'terminate-after', 'test-case-finished', 'suite-finished', 'bundle-finished']:
            self.mark(stage)

    def finish(self, initial='0', **options):
        self.before(initial, **options)
        self.action(initial)
        self.observe('after-switch', value='1')
        self.observe('terminal', value='1')
        self.completion()

    def witness(self, name, detail):
        out = HERE / 'witnesses' / name
        out.mkdir(parents=True, exist_ok=True)
        shutil.copytree(self.bridge.output, out/'captures', dirs_exist_ok=True)
        (out/'witness.json').write_text(json.dumps({'syntheticHostOnly': True, 'nativeExecuted': False, 'detail': detail, 'settingsDiagnostic': self.bridge.settings.summary(), 'replayed': replay.replay(self.bridge.output)}, indent=2, sort_keys=True)+'\n')


class IndependentV5Tests(unittest.TestCase):
    def flow(self):
        f = Flow(); self.addCleanup(f.close); return f

    def test_real_positive_bridge_replay_has_only_diagnostic_authority(self):
        f = self.flow(); f.finish()
        s = f.bridge.settings.summary()
        self.assertTrue(s['setupObservationSatisfied'])
        self.assertEqual(s, replay.replay(f.bridge.output))
        runtime = producer.summary('interaction', f.bridge, 0, None, [])
        self.assertTrue(runtime['diagnosticCompleted'])
        self.assertEqual(len(runtime['dependentCasesUnrun']), 6)
        for key in ['runPassed', 'nativeKeyboardQualification', 'carrierAccepted', 'gaAccepted', 'strictNativeVerdictsPassed']:
            self.assertIs(runtime[key], False)
        self.assertEqual(runtime['applicationCasesExecuted'], 0)

    def test_wrong_descendant_label_identity_type_and_state_cannot_complete(self):
        for change in [{'label':'Other'}, {'identifier':'Other'}, {'elementType':75}, {'hittable':False}, {'enabled':False}, {'foreground':False}, {'appState':3}]:
            with self.subTest(change=change):
                f=self.flow(); f.finish(search_alter=lambda r: r['routeWitness']['target'].update(change))
                self.assertFalse(f.bridge.settings.summary()['setupObservationSatisfied'])

    def test_outside_descendant_geometry_cannot_complete(self):
        for change in [{'x':0}, {'y':90}, {'width':400}, {'height':100}]:
            with self.subTest(change=change):
                f=self.flow(); f.finish(search_alter=lambda r:r['routeWitness']['target']['frame'].update(change))
                self.assertFalse(f.bridge.settings.summary()['selectedRouteEvidenceExpected'])

    def test_anonymous_container_without_explicit_target_is_rejected(self):
        f=self.flow(); f.mark('settings-launched')
        r,_=f.observe('route-search',index=0,upload=False); del r['routeWitness']
        with self.assertRaises(ValueError): f.send(r)
        self.assertEqual(f.bridge.settings.route_bindings, [])

    def test_self_relation_requires_container_target_exact_metadata(self):
        f=self.flow(); f.finish(search_alter=lambda r:r['routeWitness'].update(relation='self'))
        self.assertFalse(f.bridge.settings.summary()['setupObservationSatisfied'])
        f=self.flow()
        def direct(r):
            r['snapshot']=copy.deepcopy(r['routeWitness']['target']);r['routeWitness']['relation']='self'
        f.finish(search_alter=direct)
        self.assertTrue(f.bridge.settings.summary()['setupObservationSatisfied'])

    def test_actual_tap_target_metadata_must_equal_last_search(self):
        for change in [{'label':'Other'}, {'identifier':'Other'}, {'elementType':9}, {'frame':dict(x=21,y=110,width=200,height=20)}, {'valueKind':'string','value':'changed'}]:
            with self.subTest(change=change):
                f=self.flow();f.finish(tap_alter=lambda r:r['detail']['target'].update(change))
                self.assertFalse(f.bridge.settings.summary()['setupObservationSatisfied'])

    def test_tap_sequence_and_times_reject_stale_and_nonfinite_transactionally(self):
        changes=[lambda r:r['detail'].update(searchSequence=True),lambda r:r['detail'].update(searchSequence=0),lambda r:r['detail']['target'].update(observedUptime=0),lambda r:r['detail'].update(startedUptime=0),lambda r:r['detail'].update(finishedUptime=float('nan')),lambda r:r['detail'].update(finishedUptime=r['uptime']+1)]
        for change in changes:
            with self.subTest(change=changes.index(change)):
                f=self.flow();f.mark('settings-launched');f.observe('route-search',index=0)
                before=f.bridge.settings.summary()
                with self.assertRaises(ValueError):f.tap(0,change)
                self.assertEqual(f.bridge.settings.summary(),before)

    def test_previous_search_cannot_be_tapped_after_retry(self):
        f=self.flow();f.mark('settings-launched');old,_=f.observe('route-search',index=0);f.observe('route-search',index=0,attempt=1)
        with self.assertRaises(ValueError): f.tap(0,lambda r:r['detail'].update(searchSequence=old['sequence']))

    def test_zero_frame_unhittable_raw_search_allows_bounded_retry_only(self):
        f=self.flow();f.mark('settings-launched')
        def zero(r):
            for s in [r['snapshot'],r['routeWitness']['target']]:s.update(hittable=False,frame=dict(x=0,y=0,width=0,height=0))
        f.observe('route-search',index=0,alter=zero)
        with self.assertRaises(ValueError):f.tap(0)
        f.observe('route-search',index=0,attempt=1);f.tap(0)
        self.assertTrue(f.bridge.settings.route_bindings[0]['rowMatched'])

    def test_zero_partial_nonfinite_and_hittable_frames_are_rejected(self):
        for frame,hittable in [(dict(x=0,y=0,width=0,height=0),True),(dict(x=0,y=0,width=0,height=5),False),(dict(x=float('nan'),y=0,width=0,height=0),False),(dict(x=0,y=0,width=-1,height=0),False)]:
            with self.subTest(frame=frame,hittable=hittable):
                f=self.flow();f.mark('settings-launched')
                with self.assertRaises(ValueError):f.observe('route-search',index=0,alter=lambda r:r['routeWitness']['target'].update(frame=frame,hittable=hittable))

    def test_zero_frame_actual_target_switch_and_destination_are_rejected(self):
        zero=dict(x=0,y=0,width=0,height=0)
        f=self.flow();f.mark('settings-launched');f.observe('route-search',index=0)
        with self.assertRaises(ValueError):f.tap(0,lambda r:r['detail']['target'].update(frame=zero,hittable=False))
        f.tap(0)
        with self.assertRaises(ValueError):f.observe('route-opened',index=0,alter=lambda r:r['routeWitness']['destination'].update(frame=zero,hittable=False))
        f=self.flow();f.routes()
        with self.assertRaises(ValueError):f.observe('before-switch',alter=lambda r:r['snapshot'].update(frame=zero,hittable=False))

    def test_old_offscreen_selector_is_retained_and_not_used_as_destination(self):
        f=self.flow();f.finish()
        self.assertTrue(all(not b['oldSelectorAbsent'] and b['destinationMatched'] for b in f.bridge.settings.route_opened_bindings))
        def old(r):r['routeWitness']['destination']=copy.deepcopy(r['snapshot'])
        f=self.flow();f.finish(opened_alter=old)
        self.assertFalse(f.bridge.settings.summary()['setupObservationSatisfied'])

    def test_wrong_destination_type_label_identity_context_cannot_complete(self):
        for change in [{'label':'Other'},{'identifier':'Other'},{'elementType':75},{'exists':False},{'enabled':False},{'foreground':False},{'appState':3},{'frame':dict(x=-1,y=10,width=300,height=44)}]:
            with self.subTest(change=change):
                f=self.flow();f.finish(opened_alter=lambda r:r['routeWitness']['destination'].update(change))
                self.assertFalse(f.bridge.settings.summary()['setupObservationSatisfied'])

    def test_nested_search_and_destination_timestamps_are_capture_bound(self):
        for stage,key in [('route-search','target'),('route-opened','destination')]:
            for stamp in [True,-1,float('inf'),1000]:
                with self.subTest(stage=stage,stamp=stamp):
                    f=self.flow();f.mark('settings-launched')
                    if stage=='route-opened':f.observe('route-search',index=0);f.tap(0)
                    with self.assertRaises(ValueError):f.observe(stage,index=0,alter=lambda r:r['routeWitness'][key].update(observedUptime=stamp))

    def test_CONTRACT_destination_captured_before_tap_return_cannot_complete(self):
        f=self.flow()
        def stale(r):
            search=f.searches[r['routeIndex']]
            start=search['captureFinishedUptime']+.0001
            r.update(captureStartedUptime=start,captureFinishedUptime=start+.0002)
            r['snapshot']['observedUptime']=start+.0001
            r['routeWitness']['destination']['observedUptime']=start+.0001
        # V6 rejects the attempted record before it can enter the durable journal.
        attempted = []
        original_stale = stale
        def retained_stale(r):
            original_stale(r)
            attempted.append(copy.deepcopy(r))
        with self.assertRaisesRegex(ValueError, 'Route opened capture precedes same-route tap completion'):
            f.finish(opened_alter=retained_stale)
        detail=[{'routeIndex':r['routeIndex'],'searchFinished':f.searches[r['routeIndex']]['captureFinishedUptime'],'tapStarted':f.taps[r['routeIndex']]['detail']['startedUptime'],'tapFinished':f.taps[r['routeIndex']]['detail']['finishedUptime'],'destinationObserved':r['routeWitness']['destination']['observedUptime'],'openedCaptureFinished':r['captureFinishedUptime']} for r in attempted]
        self.assertEqual(len(detail), 1)
        self.assertTrue(all(d['destinationObserved']<d['tapStarted'] for d in detail))
        self.assertEqual(f.bridge.settings.route_opened_bindings, [])
        self.assertEqual(f.bridge.settings.summary(), replay.replay(f.bridge.output))
        self.assertFalse(f.bridge.settings.summary()['setupObservationSatisfied'],'Pre-tap destination snapshots satisfy post-navigation setup evidence')

    def test_switch_window_cannot_extend_reset_or_accept_late_enable(self):
        f=self.flow();f.before();f.action();anchor=f.bridge.settings.anchor
        with self.assertRaises(ValueError):f.mark('switch-action',{'action':'tap','anchorUptime':anchor+.1,'deadlineUptime':anchor+3.1})
        f.runner=anchor+3.01;f.observe('after-switch',value='1');f.observe('terminal',value='1')
        self.assertFalse(f.bridge.settings.summary()['setupObservationSatisfied'])
        self.assertEqual(f.bridge.settings.observation_deadline,anchor+3)

    def test_initial_enabled_anchor_survives_upload_delay(self):
        f=self.flow();f.before(initial='1');observed=f.bridge.settings.before['snapshot']['observedUptime']
        f.runner+=4;f.action(initial='1');f.observe('after-switch',value='1');f.observe('terminal',value='1')
        self.assertEqual(f.bridge.settings.anchor,observed)
        self.assertEqual(f.bridge.settings.enabled_samples,[f.bridge.settings.before['sequence']])

    def test_wrong_target_and_nonforeground_polls_never_supply_window(self):
        for change in [{'identifier':'Other'},{'label':'Other'},{'elementType':9},{'foreground':False},{'appState':3},{'enabled':False},{'hittable':False},{'valueKind':'unsupported','value':''}]:
            with self.subTest(change=change):
                f=self.flow();f.before();f.action();f.observe('after-switch',value='0');f.observe('poll',value='1',alter=lambda r:r['snapshot'].update(change))
                f.runner=f.bridge.settings.observation_deadline+.1;f.observe('terminal',value='1')
                self.assertFalse(f.bridge.settings.summary()['setupObservationSatisfied'])

    def test_valid_in_window_poll_with_late_terminal_is_allowed(self):
        f=self.flow();f.before();f.action();f.observe('after-switch',value='0');f.observe('poll',value='1')
        f.runner=f.bridge.settings.observation_deadline+.1;f.observe('terminal',value='1')
        self.assertTrue(f.bridge.settings.summary()['setupObservationSatisfied'])

    def test_replay_rejects_host_clock_regression_and_duration_expiry(self):
        for stamp in [99,129.001,True,float('nan')]:
            with self.subTest(stamp=stamp):
                f=self.flow();f.finish();p=f.bridge.output/'0000-settings-0001.json';r=json.loads(p.read_bytes());r['receivedUptime']=stamp;p.write_text(json.dumps(r))
                with self.assertRaises(ValueError):replay.replay(f.bridge.output)

    def test_replay_rejects_identity_sequence_payload_and_extra_record_mutation(self):
        changes=[lambda r:r.update(ownedSimulatorIdentity={'scope':'other'}),lambda r:r['record'].update(sequence=999),lambda r:r.update(extra='unselected')]
        for change in changes:
            with self.subTest(change=changes.index(change)):
                f=self.flow();f.finish();p=f.bridge.output/'0000-settings-0001.json';r=json.loads(p.read_bytes());change(r);p.write_text(json.dumps(r))
                with self.assertRaises(ValueError):replay.replay(f.bridge.output)
        f=self.flow();f.finish();p=next(f.bridge.output.glob('*.png'));p.write_bytes(p.read_bytes()+b'x')
        with self.assertRaises(ValueError):replay.replay(f.bridge.output)

    def test_partial_upload_or_missing_journal_never_completes(self):
        f=self.flow();f.routes();r,_=f.observe('before-switch',upload=False);f.send(r)
        self.assertFalse(replay.replay(f.bridge.output)['settingsEvidenceComplete'])
        f=self.flow();f.finish();(f.bridge.output/'0000-settings-0002.json').unlink()
        with self.assertRaises(ValueError):replay.replay(f.bridge.output)

    def test_replay_rejects_symlinked_journal_or_payload(self):
        for glob in ['0000-settings-0001.json','*.png']:
            with self.subTest(glob=glob):
                f=self.flow();f.finish();p=next(f.bridge.output.glob(glob));saved=f.root/'saved';saved.write_bytes(p.read_bytes());p.unlink();p.symlink_to(saved)
                with self.assertRaises(ValueError):replay.replay(f.bridge.output)

    def test_actual_http_semantic_rejection_is_bounded_and_cursor_does_not_advance(self):
        f=self.flow();f.mark('settings-launched');record,_=f.observe('route-search',index=0,upload=False)
        record['snapshot']['frame']['width']=0
        before=f.bridge.settings.summary()
        server=producer.h.server_for(f.bridge);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(lambda:(server.shutdown(),server.server_close(),thread.join(3)))
        client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
        try:
            client.request('POST','/evaluate',body=json.dumps({'settingsDiagnostic':record}).encode(),headers={'X-Mixer-Capability':'independent-review-capability','Content-Type':'application/json'})
            response=client.getresponse();body=response.read()
            self.assertEqual(response.status,400);self.assertLessEqual(len(body),8192)
            self.assertIn('Attached Settings geometry',json.loads(body)['error'])
        finally:client.close()
        self.assertEqual(f.bridge.settings.summary(),before)

    def test_persistence_failure_is_transactional_and_not_acknowledged(self):
        f=self.flow();before=f.bridge.settings.summary()
        with mock.patch.object(f.bridge,'save',side_effect=OSError('independent review disk fault')):
            with self.assertRaises(OSError):f.mark('settings-launched')
        self.assertEqual(before,f.bridge.settings.summary())

    def test_all_attempt_request_event_upload_and_time_constants_unchanged(self):
        spec=importlib.util.spec_from_file_location('unchanged_v4_telemetry',ROOT/'verification/apple-toggle-keyboard-focus-v4/settings_telemetry.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
        for key in ['CHUNK','MAX_TOTAL','MAX_REQUESTS','MAX_EVENTS','MAX_UPLOADS','MAX_DURATION']:
            self.assertEqual(getattr(t,key),getattr(old,key))
        f=self.flow();f.mark('settings-launched')
        for attempt in range(6):f.observe('route-search',index=0,attempt=attempt)
        with self.assertRaises(ValueError):f.observe('route-search',index=0,attempt=6)
        f=self.flow();f.bridge.settings.requests=t.MAX_REQUESTS
        with self.assertRaises(ValueError):f.mark('settings-launched')
        f=self.flow();f.clock=129.01
        with self.assertRaises(ValueError):f.mark('settings-launched')


if __name__=='__main__':unittest.main(verbosity=2)
