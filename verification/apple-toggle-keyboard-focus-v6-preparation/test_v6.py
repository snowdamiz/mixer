"""Same-route post-tap capture boundary controls through the actual Bridge."""
import copy
import http.client
import json
import math
import pathlib
import threading
import unittest
from unittest import mock
import test_v5_independent26 as independent
import replay
import settings_telemetry as t

HERE = pathlib.Path(__file__).resolve().parent
STALE = HERE.parent/'apple-toggle-keyboard-focus-v5-independent-review/witnesses/pre-tap-destination/captures'
REASON = 'Route opened capture precedes same-route tap completion'

class V6Tests(unittest.TestCase):
    def flow(self, index=0, tap=True):
        f = independent.Flow(); self.addCleanup(f.close)
        f.mark('settings-launched')
        for i in range(index):
            f.observe('route-search', index=i); f.tap(i); f.observe('route-opened', index=i)
        f.observe('route-search', index=index)
        if tap: f.tap(index)
        return f

    def attempted(self, f, index, start):
        r, payloads = f.observe('route-opened', index=index, upload=False)
        r.update(captureStartedUptime=start, captureFinishedUptime=start+.0002)
        r['snapshot']['observedUptime']=start+.0001
        r['routeWitness']['destination']['observedUptime']=start+.0001
        return r, payloads

    def durable(self, f):
        return {p.name:p.read_bytes() for p in f.bridge.output.glob('0000-settings-*.json')}

    def reject(self, f, r, reason=REASON):
        s=f.bridge.settings
        state=copy.deepcopy({k:v for k,v in s.__dict__.items() if k not in ['persist','persist_file','now']})
        files=self.durable(f)
        with self.assertRaisesRegex(ValueError, reason): f.send(r)
        self.assertEqual(state,{k:v for k,v in s.__dict__.items() if k not in ['persist','persist_file','now']})
        self.assertEqual(files,self.durable(f))
        self.assertEqual(s.summary(),replay.replay(f.bridge.output))
        self.assertFalse(s.summary()['setupObservationSatisfied'])
        self.assertFalse(s.summary()['selectedRouteEvidenceExpected'])
        self.assertNotIn(r['routeIndex'],s.opened_routes)
        self.assertFalse(any(b['routeIndex']==r['routeIndex'] for b in s.route_opened_bindings))

    def test_each_route_pre_start_overlap_just_before_equal_after(self):
        for i in range(3):
            for boundary in ['pre-start','overlap','just-before','equal','after']:
                with self.subTest(route=i,boundary=boundary):
                    f=self.flow(i); d=f.taps[i]['detail']; finish=d['finishedUptime']
                    starts={'pre-start':math.nextafter(d['startedUptime'],-math.inf),
                            'overlap':(d['startedUptime']+finish)/2,
                            'just-before':math.nextafter(finish,-math.inf),
                            'equal':finish,'after':math.nextafter(finish,math.inf)}
                    r,p=self.attempted(f,i,starts[boundary])
                    self.assertGreaterEqual(r['captureStartedUptime'],f.searches[i]['captureFinishedUptime'])
                    if boundary in ['pre-start','overlap','just-before']:self.reject(f,r)
                    else:
                        f.send(r); f.upload(p)
                        b=f.bridge.settings.route_opened_bindings[i]
                        self.assertTrue(b['destinationMatched'])
                        self.assertEqual(b['routeIndex'],i)
                        self.assertEqual(b['tapSequence'],f.taps[i]['sequence'])
                        self.assertEqual(b['tapFinishedUptime'],finish)
                        self.assertEqual(b['captureStartedUptime'],starts[boundary])
                        self.assertEqual(f.bridge.settings.summary(),replay.replay(f.bridge.output))

    def test_each_route_other_route_completion_cannot_authorize(self):
        for i in range(3):
            with self.subTest(route=i):
                f=self.flow(i, tap=False)
                before=f.bridge.settings.summary();files=self.durable(f)
                # A tap completion bearing another fixed route cannot enter
                # this route's binding, including route zero where the closed
                # grammar has no valid earlier route.
                with self.assertRaisesRegex(ValueError,'Route tap order'):
                    f.tap(i,lambda r:r['detail'].update(routeIndex=(i+1)%3))
                self.assertEqual(before,f.bridge.settings.summary());self.assertEqual(files,self.durable(f))
                f.tap(i)
                # A capture after an older accepted completion (the initial
                # start for route zero, actual prior route for routes 1/2)
                # still must follow this exact route's tap completion.
                stale=f.taps[i-1]['detail']['finishedUptime'] if i else f.bridge.settings.start_runner
                start=f.searches[i]['captureFinishedUptime']+.0001
                self.assertLess(stale,start)
                self.assertLess(start,f.taps[i]['detail']['finishedUptime'])
                r,_=self.attempted(f,i,start)
                self.reject(f,r)

    def test_exact_tap_finished_value_retained_and_route_identity_guarded(self):
        for i in range(3):
            with self.subTest(route=i):
                f=self.flow(i);binding=f.bridge.settings.route_bindings[i]
                self.assertEqual(binding['finishedUptime'],f.taps[i]['detail']['finishedUptime'])
                self.assertEqual(binding['tapSequence'],f.taps[i]['sequence'])
                self.assertEqual(binding['searchSequence'],f.searches[i]['sequence'])
                r,_=self.attempted(f,i,f.taps[i]['detail']['finishedUptime'])
                # Host-state fault injection proves index/sequence fail closed;
                # no untrusted wire field is introduced for this internal state.
                for change in [{'routeIndex':(i+1)%3},{'tapSequence':r['sequence']}]:
                    old=copy.deepcopy(binding);binding.update(change)
                    with self.assertRaisesRegex(ValueError,'Route opened same-route tap sequence'):f.send(r)
                    self.assertNotIn(i,f.bridge.settings.opened_routes)
                    binding.clear();binding.update(old)

    def test_actual_http_stale_each_route_rejects_without_durable_advance(self):
        for i in range(3):
            with self.subTest(route=i):
                f=self.flow(i); r,_=self.attempted(f,i,math.nextafter(f.taps[i]['detail']['finishedUptime'],-math.inf))
                before=f.bridge.settings.summary(); files=self.durable(f)
                server=independent.producer.h.server_for(f.bridge)
                thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
                try:
                    client.request('POST','/evaluate',body=json.dumps({'settingsDiagnostic':r}).encode(),headers={'X-Mixer-Capability':'independent-review-capability','Content-Type':'application/json'})
                    response=client.getresponse();body=response.read()
                    self.assertEqual(response.status,400);self.assertLessEqual(len(body),8192)
                    self.assertIn(REASON,body.decode())
                finally:client.close();server.shutdown();server.server_close();thread.join(3)
                self.assertEqual(before,f.bridge.settings.summary());self.assertEqual(files,self.durable(f))
                self.assertEqual(before,replay.replay(f.bridge.output))

    def test_opened_persistence_failure_keeps_completion_and_cursor_transactional(self):
        for i in range(3):
            f=self.flow(i);r,_=self.attempted(f,i,f.taps[i]['detail']['finishedUptime'])
            before=f.bridge.settings.summary();files=self.durable(f)
            with mock.patch.object(f.bridge,'save',side_effect=OSError('synthetic fsync failure')):
                with self.assertRaises(OSError):f.send(r)
            self.assertEqual(before,f.bridge.settings.summary());self.assertEqual(files,self.durable(f))
            f.send(r)
            self.assertEqual(f.bridge.settings.route_opened_bindings[i]['tapSequence'],f.taps[i]['sequence'])

    def test_exact_sealed_v5_stale_journal_rejects(self):
        paths=sorted(STALE.glob('0000-settings-*.json'))
        self.assertEqual(len(paths),32)
        opened=[json.loads(p.read_bytes())['record'] for p in paths if json.loads(p.read_bytes())['record'].get('stage')=='route-opened']
        self.assertEqual([r['routeIndex'] for r in opened],[0,1,2])
        with self.assertRaisesRegex(ValueError,REASON):replay.replay(STALE)

    def test_each_route_mutated_offline_capture_rejects(self):
        for i in range(3):
            f=independent.Flow();self.addCleanup(f.close);f.finish()
            paths=sorted(f.bridge.output.glob('0000-settings-*.json'))
            p=next(p for p in paths if (lambda r:r.get('stage')=='route-opened' and r['routeIndex']==i)(json.loads(p.read_bytes())['record']))
            saved=json.loads(p.read_bytes());r=saved['record'];start=math.nextafter(f.taps[i]['detail']['finishedUptime'],-math.inf)
            r.update(captureStartedUptime=start,captureFinishedUptime=start+.0002)
            r['snapshot']['observedUptime']=start+.0001;r['routeWitness']['destination']['observedUptime']=start+.0001
            p.write_text(json.dumps(saved))
            with self.assertRaisesRegex(ValueError,REASON):replay.replay(f.bridge.output)

    def test_qualification_boundary_and_bounds_remain_unchanged(self):
        self.assertEqual((t.CHUNK,t.MAX_TOTAL,t.MAX_REQUESTS,t.MAX_EVENTS,t.MAX_UPLOADS,t.MAX_DURATION),(3072,7000000,2500,100,32,29.0))
        f=independent.Flow();self.addCleanup(f.close);f.finish()
        summary=independent.producer.summary('interaction',f.bridge,0,{'type':'ValueError','message':'Strict XCTest result failed; preserved evidence is authoritative'},[])
        self.assertTrue(summary['expectedDiagnosticQualificationBoundary'])
        self.assertTrue(summary['diagnosticCompleted']);self.assertEqual(len(summary['dependentCasesUnrun']),6)
        for k in ['nativeKeyboardQualification','carrierAccepted','runPassed','gaAccepted','strictNativeVerdictsPassed']:self.assertIs(summary[k],False)

if __name__=='__main__':unittest.main(verbosity=2)
