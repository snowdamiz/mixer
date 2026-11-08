"""R3 incident transitions and terminal shapes, with every host boundary faked."""
import copy, json, unittest
from types import SimpleNamespace
from unittest.mock import patch
import controller, mac_backend, independent_tests
from review_tests import Fake, O, UID, BASE, OUT, put

class IncidentTransitions(unittest.TestCase):
    def execute(self, configure):
        def fake():
            b=Fake()
            configure(b)
            return b
        with patch.object(independent_tests, 'Fake', side_effect=fake):
            return independent_tests.EntryControls.execute(self, independent_tests.terminal())

    def drift(self, b, kind):
        original=b.devices
        b.reads=0; b.window_checks=[]
        def devices():
            b.reads+=1
            rows=original()
            if b.reads>=3:
                if kind=='persistent': rows[next(iter(BASE))]['state']='Shutdown'
                elif b.reads==3: rows[UID]['name']='different owner'
            return rows
        b.devices=devices
        b.verify_outside_windows=lambda:b.window_checks.append(b.reads)

    def retained(self,b,d):
        self.assertEqual(d['native'],[])
        self.assertEqual(d['deviceReads'],3)
        self.assertEqual(b.window_checks,[2])
        self.assertTrue(d['latched'] and b.unknown)
        self.assertIn(UID,b.rows)
        self.assertTrue(d['result']['preservationFailure']['rootRecoveryRequired'])
        self.assertFalse(any(isinstance(a,tuple) and a[0] in ('close-window','shutdown','delete') for a in b.actions))
        incident=copy.deepcopy(b.preservation_failure)
        # Returning to the old observations does not release the recorded incident.
        b.rows={**copy.deepcopy(BASE),UID:dict(name=O.name,state='Booted',runtime=O.runtime,deviceType=O.device_type)}
        for action in [lambda:controller.check_snapshot(b,O,BASE),lambda:controller.cleanup(b,O,BASE),lambda:controller.dispatch(b,O,BASE)]:
            with self.assertRaisesRegex(controller.Refused,'Unknown custody'):action()
        self.assertEqual(b.reads,3)
        self.assertEqual(b.preservation_failure,incident)

    def test_persistent_external_drift_blocks_before_window_query(self):
        b,d=self.execute(lambda b:self.drift(b,'persistent'))
        self.retained(b,d)
        self.assertIn('External baseline',b.preservation_failure['message'])

    def test_transient_owned_identity_loss_never_recovers_implicitly(self):
        b,d=self.execute(lambda b:self.drift(b,'identity'))
        self.retained(b,d)
        self.assertIn('Owned device identity',b.preservation_failure['message'])

    def test_ordinary_keyboard_failure_still_cleans_known_owned_resources(self):
        b,d=self.execute(lambda b:setattr(b,'connected',False))
        self.assertEqual(d['native'],[])
        self.assertEqual(b.rows,BASE)
        self.assertEqual(b.windows,[])
        self.assertEqual([a[0] for a in b.actions if isinstance(a,tuple)],['boot','close-window','shutdown','delete'])
        self.assertNotIn('preservationFailure',d['result'])
        self.assertIn('keyboard connection',d['result']['failure']['message'])

    def test_incident_receipt_written_with_latch_already_set(self):
        b=Fake();b.c=SimpleNamespace(unresolved=False);b.unknown=False
        b.rows[next(iter(BASE))]['state']='Shutdown'
        b.folder=OUT/self._testMethodName;b.folder.mkdir()
        def record(path,row):
            self.assertTrue(b.c.unresolved and b.unknown)
            mac_backend.MacBackend.record(b,path,row)
        b.record=record
        with self.assertRaisesRegex(controller.Refused,'External baseline'):controller.check_snapshot(b,O,BASE)
        saved=json.loads((b.folder/'preservation-failure.json').read_text())
        self.assertTrue(saved['rootRecoveryRequired'])
        self.assertEqual(saved,b.preservation_failure)
        self.assertEqual(b.actions,[])

    def test_incident_receipt_failure_cannot_release_custody(self):
        def configure(b):
            self.drift(b,'persistent')
            b.folder=OUT
            def fail(path,row):
                self.assertTrue(b.c.unresolved and b.unknown)
                raise OSError('fake incident receipt disk failure')
            b.record=fail
        b,d=self.execute(configure)
        self.retained(b,d)
        self.assertIn('disk failure',d['result']['preservationFailure']['receiptFailure'])

    def test_failed_outside_window_observation_is_sticky(self):
        b=Fake();b.c=SimpleNamespace(unresolved=False);b.unknown=False
        calls=[]
        def fail():calls.append('window');raise controller.Refused('outside window changed')
        b.verify_outside_windows=fail
        with self.assertRaisesRegex(controller.Refused,'outside window'):controller.check_snapshot(b,O,BASE)
        b.verify_outside_windows=lambda:self.fail('window retry after incident')
        b.devices=lambda:self.fail('device retry after incident')
        with self.assertRaises(controller.Refused):controller.cleanup(b,O,BASE)
        self.assertEqual(calls,['window'])
        self.assertTrue(b.unknown and b.c.unresolved)
        put(self._testMethodName+'.json',b.preservation_failure)

    def test_device_observation_exception_retains_before_cleanup(self):
        b=Fake();b.c=SimpleNamespace(unresolved=False);b.unknown=False
        def fail():raise OSError('fake observation unavailable')
        b.devices=fail
        with self.assertRaises(OSError):controller.check_snapshot(b,O,BASE)
        b.devices=lambda:self.fail('device retry after unavailable observation')
        with self.assertRaises(controller.Refused):controller.cleanup(b,O,BASE)
        self.assertTrue(b.unknown and b.c.unresolved)

class TerminalShapes(unittest.TestCase):
    def execute(self,value,suffix):
        name=self._testMethodName
        self._testMethodName=name+'-'+suffix
        try:return independent_tests.EntryControls.execute(self,value)
        finally:self._testMethodName=name

    def rejected(self,value,suffix):
        b,d=self.execute(value,suffix)
        self.assertIsNotNone(d['error'])
        self.assertTrue(d['latched'])
        self.assertNotIn('outerCleanup',d['result'])
        self.assertEqual(d['deviceReads'],4)

    def test_required_result_fields_and_schema(self):
        for field in ['schema','runPassed','gaAccepted','cleanupResults','sessionFailure','xcodebuildExitCode','reportingFailures']:
            with self.subTest(field=field):
                value=independent_tests.terminal();del value[field]
                self.rejected(value,'missing-'+field)
        for i,value in enumerate([None,[],False,{},'result']):
            with self.subTest(value=value):self.rejected(value,'shape-'+str(i))
        value=independent_tests.terminal();value['schema']='other'
        self.rejected(value,'wrong-schema')

    def test_strict_exit_codes_and_success_field_types(self):
        for i,code in enumerate([False,True,0.0,65.0,'0','65',None,-9,1]):
            with self.subTest(code=code):
                value=independent_tests.terminal();value['xcodebuildExitCode']=code
                self.rejected(value,'exit-'+str(i))
        for field,values in [('runPassed',[0,1,None,'false']),('gaAccepted',[0,1,True,None]),('sessionFailure',[False,{},[]]),('reportingFailures',[None,{},False])]:
            for i,bad in enumerate(values):
                with self.subTest(field=field,bad=bad):
                    value=independent_tests.terminal();value[field]=bad
                    self.rejected(value,field+'-'+str(i))

    def test_exact_five_passing_gates(self):
        good=independent_tests.terminal()['cleanupResults']
        variants=[None,{},good[:-1],good+[good[0]],[*good[:4],None],[*good[:4],dict(resource=[],passed=True)],
                  [*good[:4],dict(resource='other',passed=True)],[*good[:4],dict(resource=good[4]['resource'],passed=1)]]
        for i,gates in enumerate(variants):
            with self.subTest(i=i):
                value=independent_tests.terminal();value['cleanupResults']=gates
                self.rejected(value,'gates-'+str(i))

    def test_both_integer_terminal_codes_allow_cleanup_without_native_acceptance(self):
        for code in [0,65]:
            value=independent_tests.terminal();value['xcodebuildExitCode']=code
            b,d=self.execute(value,str(code))
            self.assertIsNone(d['error'])
            self.assertTrue(d['result']['outerCleanup']['cleanupPassed'])
            self.assertFalse(d['latched'])
            self.assertFalse(d['result']['native']['runPassed'])
            self.assertFalse(d['result']['gaAccepted'])
