"""Fresh entrypoint and stop-on-drift controls; candidate imported unchanged."""
import copy, json, sys, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import controller, mac_backend, future_run, commands
from review_tests import OUT, CANDIDATE, Fake, O, W, UID, BASE, put

GATES=['loopback-server-shutdown','loopback-server-close','loopback-thread-join','ephemeral-capability-workspace-removal','owned-simulator-and-baseline-reconciliation']

def terminal():
    return dict(schema='mixer.apple-focus-reference-runtime.9',cleanupResults=[dict(resource=g,passed=True) for g in GATES],sessionFailure=None,reportingFailures=[],xcodebuildExitCode=65,runPassed=False,gaAccepted=False)

class EntryControls(unittest.TestCase):
    def execute(self, value, *, interrupted=False, missing=False, drift=False):
        root=OUT/('entry-'+self._testMethodName);root.mkdir()
        for name in [*json.loads((CANDIDATE/'candidate-seal.json').read_text())['sourceFiles'],'candidate-seal.json']:
            (root/name).write_bytes((CANDIDATE/name).read_bytes())
        folder=root/'attempt'
        b=Fake();b.c=SimpleNamespace(unresolved=False);b.unknown=False
        del b.rows[UID];b.windows=[]
        b.assert_custody=lambda:mac_backend.MacBackend.assert_custody(b)
        b.dispatch_unchanged=lambda owned,baseline:dict(argv=['fake-native-boundary'])
        events=[]
        def native(argv):
            events.append('native')
            if interrupted:
                b.c.unresolved=True;raise RuntimeError('fake interrupted dispatch, outer group absent')
            if not missing:(folder/'dispatch-result.json').write_text(json.dumps(value))
            # Actual accepted inner cleanup has already deleted the owned device.
            b.rows.pop(UID,None);b.windows=[]
        b.native_dispatch=native
        observed=[];device_reads=0
        original_devices=b.devices
        def devices():
            nonlocal device_reads
            device_reads+=1
            row=original_devices()
            if drift and device_reads==3:
                row[next(iter(BASE))]['state']='Shutdown';observed.append('outside-baseline-drift')
            elif drift and observed:observed.append('device-query-after-drift')
            return row
        b.devices=devices
        error=None
        with patch.object(future_run,'HERE',root),patch.object(future_run,'MacBackend',return_value=b):
            try:future_run.run(folder.resolve(),commands.digest((root/'candidate-seal.json').read_bytes()))
            except BaseException as e:error=dict(type=type(e).__name__,message=str(e))
        result=json.loads((folder/'result.json').read_text())
        detail=dict(error=error,result=result,actions=[str(a) for a in b.actions],native=events,deviceReads=device_reads,observed=observed,latched=b.c.unresolved)
        put(self._testMethodName+'.json',detail)
        return b,detail
    def test_normal_completed_original_failure_allows_cleanup_without_native_pass(self):
        b,d=self.execute(terminal())
        self.assertIsNone(d['error']);self.assertTrue(d['result']['outerCleanup']['cleanupPassed'])
        self.assertFalse(d['result']['native']['runPassed']);self.assertFalse(d['result']['gaAccepted'])
        self.assertEqual(d['native'],['native']);self.assertFalse(d['latched'])
    def test_interruption_blocks_actual_cleanup_entry(self):
        b,d=self.execute(terminal(),interrupted=True)
        self.assertTrue(d['latched']);self.assertIn('Unknown custody',d['result']['cleanupFailure'])
        self.assertEqual(d['deviceReads'],4)
    def test_missing_terminal_file_blocks_actual_cleanup_entry(self):
        b,d=self.execute(terminal(),missing=True)
        self.assertTrue(d['latched']);self.assertIn('Unknown custody',d['result']['cleanupFailure'])
        self.assertEqual(d['deviceReads'],4)
    def test_failed_gate_blocks_actual_cleanup_entry(self):
        v=terminal();v['cleanupResults'][2]['passed']=False
        b,d=self.execute(v);self.assertTrue(d['latched']);self.assertNotIn('outerCleanup',d['result'])
    def test_duplicate_gates_block_actual_cleanup_entry(self):
        v=terminal();v['cleanupResults'][2]=v['cleanupResults'][0]
        b,d=self.execute(v);self.assertTrue(d['latched']);self.assertNotIn('outerCleanup',d['result'])
    def test_reported_session_failure_blocks_actual_cleanup_entry(self):
        v=terminal();v['sessionFailure']={'message':'nested unknown'}
        b,d=self.execute(v);self.assertTrue(d['latched']);self.assertNotIn('outerCleanup',d['result'])
    def test_reporting_failure_blocks_actual_cleanup_entry(self):
        v=terminal();v['reportingFailures']=[{'operation':'receipt','error':'disk'}]
        b,d=self.execute(v);self.assertTrue(d['latched']);self.assertNotIn('outerCleanup',d['result'])
    def test_missing_session_terminal_field_fails_closed(self):
        v=terminal();del v['sessionFailure']
        b,d=self.execute(v);self.assertTrue(d['latched'],d)
    def test_boolean_exit_code_fails_closed(self):
        v=terminal();v['xcodebuildExitCode']=False
        b,d=self.execute(v);self.assertTrue(d['latched'],d)
    def test_setup_external_baseline_drift_is_sticky_at_real_entrypoint(self):
        b,d=self.execute(terminal(),drift=True)
        self.assertEqual(d['native'],[])
        self.assertEqual(d['observed'],['outside-baseline-drift'],d)

class ActualBackendDrift(unittest.TestCase):
    def test_changed_external_device_stops_setup_before_followup_command(self):
        b=object.__new__(mac_backend.MacBackend)
        b.c=SimpleNamespace(unresolved=False);b.unknown=False;b.owned=None;b.index=0;b.folder=OUT
        b.baseline_windows=None;b.baseline_frontends=None
        b.ax_trusted=lambda:True;b.verify_bindings=lambda:None
        calls=[];count=0;owned_row=dict(name=O.name,state='Booted',runtime=O.runtime,deviceType=O.device_type)
        def devices():
            nonlocal count
            b.assert_custody();count+=1;calls.append('devices-'+str(count))
            rows=copy.deepcopy(BASE)
            if count>1:rows[UID]=dict(owned_row)
            if count==3:rows[next(iter(BASE))]['state']='Shutdown'
            return rows
        b.devices=devices
        def create():b.owned=O;return O
        b.create_owned=create;b.boot=lambda uid:None;b.open_owned_window=lambda owned:owned
        b.windows_for_device=lambda uid:[W]
        b.keyboard_connected=lambda w:True
        b.close_window=lambda w:calls.append('CLOSE-AFTER-DRIFT')
        with self.assertRaises(controller.Refused):controller.setup(b)
        put(self._testMethodName+'.json',dict(calls=calls,unknown=b.unknown,commandUnresolved=b.c.unresolved))
        self.assertNotIn('devices-4',calls,calls)
        self.assertNotIn('CLOSE-AFTER-DRIFT',calls,calls)
