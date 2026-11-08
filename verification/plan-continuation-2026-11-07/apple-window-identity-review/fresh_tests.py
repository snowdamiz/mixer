"""Independent R3 wrapper and incident-path controls, all host boundaries fake."""
import copy, hashlib, json, runpy, sys, unittest
from types import SimpleNamespace
from unittest.mock import patch
import controller, mac_backend, verify_bindings
from review_tests import OUT, CANDIDATE, Fake, O, UID, BASE, put
from independent_tests import terminal

REAL_BACKEND = mac_backend.MacBackend

class WrapperControls(unittest.TestCase):
    def invoke(self, label, raw=None, *, drift_at=None, keyboard=True):
        root=OUT/('fresh-'+label);root.mkdir()
        seal=json.loads((CANDIDATE/'candidate-seal.json').read_text())
        for name in [*seal['sourceFiles'],'candidate-seal.json']:
            (root/name).write_bytes((CANDIDATE/name).read_bytes())
        folder=root/'attempt'
        b=Fake();b.c=SimpleNamespace(unresolved=False);b.unknown=False;b.folder=folder
        del b.rows[UID];b.windows=[];b.connected=keyboard
        b.assert_custody=lambda:REAL_BACKEND.assert_custody(b)
        events=[];reads=0
        original_devices=b.devices
        def devices():
            nonlocal reads
            b.assert_custody();reads+=1;events.append('devices-'+str(reads))
            rows=original_devices()
            if reads==drift_at:
                rows[next(iter(BASE))]['state']='Shutdown';events.append('INCIDENT')
            return rows
        b.devices=devices
        b.verify_outside_windows=lambda:events.append('windows-'+str(reads))
        def record(path,value):
            self.assertTrue(b.unknown and b.c.unresolved)
            events.append('incident-record')
            REAL_BACKEND.record(b,path,value)
        b.record=record
        b.dispatch_unchanged=lambda *a:dict(argv=['fake-native'])
        def native(argv):
            events.append('native')
            (folder/'dispatch-result.json').write_bytes(raw if raw is not None else json.dumps(terminal()).encode())
            # Successful fake inner cleanup removes only its exact owned device.
            b.rows.pop(UID,None);b.windows=[]
        b.native_dispatch=native
        for name in ['close_window','shutdown','delete']:
            original=getattr(b,name)
            def action(*a,_name=name,_original=original):
                b.assert_custody();events.append(_name);return _original(*a)
            setattr(b,name,action)
        error=None
        argv=[str(CANDIDATE/'future_run.py'),'run-reviewed-once',str(folder),hashlib.sha256((root/'candidate-seal.json').read_bytes()).hexdigest()]
        with patch.object(verify_bindings,'HERE',root),patch.object(mac_backend,'MacBackend',return_value=b),patch.object(sys,'argv',argv):
            try:runpy.run_path(str(CANDIDATE/'future_run.py'),run_name='__main__')
            except BaseException as e:error=dict(type=type(e).__name__,message=str(e))
        result=json.loads((folder/'result.json').read_text())
        detail=dict(events=events,error=error,result=result,deviceReads=reads,unknown=b.unknown,unresolved=b.c.unresolved,wrapperSourceSHA256=hashlib.sha256((CANDIDATE/'future_run.py').read_bytes()).hexdigest())
        put('fresh-'+label+'.json',detail)
        return b,detail,folder

    def test_actual_main_rejects_invalid_terminal_bytes(self):
        values=[('empty',b''),('truncated',b'{"runPassed":true'),('utf8',b'\xff'),('junk',b'{} trailing'),('array',b'[]'),('scalar',b'false')]
        missing=terminal();del missing['sessionFailure'];missing['runPassed']=True
        boolean=terminal();boolean['xcodebuildExitCode']=False;boolean['runPassed']=True
        values.extend([('missing-session',json.dumps(missing).encode()),('boolean-exit',json.dumps(boolean).encode())])
        for label,field,value in [('wrong-schema','schema','wrong'),('reported-session','sessionFailure',{'message':'incomplete'}),('boolean-true-exit','xcodebuildExitCode',True)]:
            malformed=terminal();malformed[field]=value
            values.append((label,json.dumps(malformed).encode()))
        missing_schema=terminal();del missing_schema['schema']
        values.append(('missing-schema',json.dumps(missing_schema).encode()))
        for label,raw in values:
            with self.subTest(label=label):
                b,d,_=self.invoke('invalid-'+label,raw)
                self.assertIsNotNone(d['error'],d)
                self.assertTrue(d['unresolved'])
                self.assertNotIn('outerCleanup',d['result'])
                self.assertIn('cleanupFailure',d['result'])
                self.assertFalse(d['result']['gaAccepted'])
                self.assertEqual(d['events'][-1],'native',d)
                self.assertEqual(d['deviceReads'],4)

    def test_actual_main_allows_completed_original_failure(self):
        b,d,_=self.invoke('valid-failure')
        self.assertIsNone(d['error'],d)
        self.assertTrue(d['result']['outerCleanup']['cleanupPassed'])
        self.assertFalse(d['result']['native']['runPassed'])
        self.assertFalse(d['result']['gaAccepted'])
        self.assertFalse(d['unresolved'])

    def test_actual_main_transient_drift_setup_dispatch_cleanup(self):
        for label,index,keyboard in [('setup-create',2,True),('setup-open',3,True),('dispatch',4,True),('outer-cleanup',5,True),('keyboard-cleanup',5,False)]:
            with self.subTest(label=label):
                b,d,folder=self.invoke('drift-'+label,drift_at=index,keyboard=keyboard)
                self.assertIsNotNone(d['error'],d)
                self.assertTrue(d['unknown'] and d['unresolved'])
                self.assertEqual(d['deviceReads'],index,d)
                self.assertEqual(d['events'][d['events'].index('INCIDENT')+1:],['incident-record'],d)
                saved=json.loads((folder/'preservation-failure.json').read_text())
                self.assertTrue(saved['rootRecoveryRequired'])
                self.assertIn('External baseline',saved['message'])
                if label in ('setup-create','setup-open','dispatch','keyboard-cleanup'):
                    self.assertNotIn('native',d['events'])
                else:self.assertIn('native',d['events'])
                # The underlying fake rows already match the baseline again.
                self.assertEqual(controller.external(b.rows,UID),BASE)
                before=list(d['events'])
                for action in [lambda:controller.setup(b),lambda:controller.dispatch(b,O,BASE),lambda:controller.cleanup(b,O,BASE),lambda:controller.check_snapshot(b,O,BASE)]:
                    with self.assertRaisesRegex(controller.Refused,'Unknown custody'):action()
                self.assertEqual(d['events'],before)
                self.assertEqual(json.loads((folder/'preservation-failure.json').read_text()),saved)

    def test_actual_main_known_keyboard_failure_cleans_without_dispatch(self):
        b,d,_=self.invoke('keyboard-failure',keyboard=False)
        self.assertIsNotNone(d['error'])
        self.assertNotIn('native',d['events'])
        self.assertEqual([x for x in d['events'] if x in ('close_window','shutdown','delete')],['close_window','shutdown','delete'])
        self.assertEqual(b.rows,BASE)
        self.assertNotIn('preservationFailure',d['result'])
