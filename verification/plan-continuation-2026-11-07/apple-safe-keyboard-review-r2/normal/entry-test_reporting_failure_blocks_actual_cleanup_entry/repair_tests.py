"""Behavior controls over final outer code; all process and AX boundaries are fake."""
import contextlib, errno, json, sys, unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import commands, controller, mac_backend, future_run, holds
from review_tests import Process, Selector, OUT, W, O, UID, BASE, Fake

class RepairCommands(unittest.TestCase):
    def runner(self):
        return commands.Commands(OUT/('repair-'+self._testMethodName))
    @contextlib.contextmanager
    def fake(self, *, clock=None, read_error=None, spawn_error=None, held=None):
        p=Process(); events=[]
        if held is not None:p.pid=held
        p.poll=lambda:events.append('poll') or 0
        p.wait=lambda:events.append('wait') or 0
        def kill(pid,sig):
            events.append(('killpg',pid,sig)); raise ProcessLookupError()
        with contextlib.ExitStack() as s:
            spawn=s.enter_context(patch.object(commands.subprocess,'Popen',return_value=p,side_effect=spawn_error))
            s.enter_context(patch.object(commands.selectors,'DefaultSelector',Selector))
            s.enter_context(patch.object(commands.os,'set_blocking'))
            s.enter_context(patch.object(commands.os,'killpg',side_effect=kill))
            s.enter_context(patch.object(commands.os,'read',return_value=b'',side_effect=read_error))
            if clock is not None:s.enter_context(patch.object(commands.time,'monotonic',side_effect=clock))
            yield p,spawn,events
    def test_reap_before_initial_signal_and_absence_probe(self):
        c=self.runner()
        with self.fake(clock=[0,121,121]) as (_,spawn,events):
            with self.assertRaises(RuntimeError):c.run('timeout',[sys.executable],120)
        self.assertLess(events.index('wait'),next(i for i,e in enumerate(events) if isinstance(e,tuple)))
        self.assertFalse(c.unresolved)
        self.assertTrue(c.events[0]['reaped'] and c.events[0]['ownedGroupAbsent'])
    def test_popen_exception_latches_and_records(self):
        c=self.runner()
        with self.fake(spawn_error=OSError('possible acquisition')) as (_,spawn,events):
            with self.assertRaises(OSError):c.run('spawn',[sys.executable])
            with self.assertRaises(RuntimeError):c.run('again',[sys.executable])
            self.assertEqual(spawn.call_count,1);self.assertEqual(events,[])
        self.assertTrue(c.unresolved);self.assertTrue((c.directory/'spawn.command.json').is_file())
    def test_read_exception_stops_before_any_signal_or_probe(self):
        c=self.runner()
        with self.fake(read_error=OSError('read failed')) as (_,spawn,events):
            with self.assertRaises(OSError):c.run('read',[sys.executable])
            self.assertFalse(any(isinstance(x,tuple) for x in events))
        row=c.events[0];self.assertTrue(c.unresolved)
        self.assertFalse(row['streams']['stdout']['eof']);self.assertFalse(row['streams']['stderr']['eof'])
    def test_receipt_write_failure_cannot_clear_latch(self):
        c=self.runner(); actual=commands.write
        def write(path,row):
            if str(path).endswith('.command.json'):raise OSError('receipt write failed')
            return actual(path,row)
        with self.fake() as (_,spawn,events),patch.object(commands,'write',side_effect=write):
            with self.assertRaises(OSError):c.run('write',[sys.executable])
            count=len(events)
            with self.assertRaises(RuntimeError):c.run('again',[sys.executable])
            self.assertEqual(len(events),count);self.assertEqual(spawn.call_count,1)
        self.assertTrue(c.unresolved);self.assertTrue((c.directory/'write.exception.json').exists())
    def test_all_receipt_writes_fail_still_stops(self):
        c=self.runner()
        with self.fake() as (_,spawn,events),patch.object(commands,'write',side_effect=OSError('disk')):
            with self.assertRaises(OSError):c.run('write',[sys.executable])
            with self.assertRaises(RuntimeError):c.run('again',[sys.executable])
            self.assertEqual(spawn.call_count,1)
        self.assertTrue(c.unresolved)
    def test_each_held_identity_refused_without_probe(self):
        for held in holds.HELD:
            c=commands.Commands(OUT/('held-'+str(held)))
            with self.fake(held=held) as (_,spawn,events):
                with self.assertRaises(RuntimeError):c.run('collision',[sys.executable])
                self.assertEqual(events,[]);self.assertTrue(c.unresolved)
    def test_hold_set_is_one_object(self):
        self.assertIs(commands.HELD,controller.HELD);self.assertIs(mac_backend.HELD,holds.HELD)
    def test_950_requires_explicit_dispatch_operation(self):
        c=self.runner()
        with patch.object(commands.subprocess,'Popen') as spawn:
            for label in ['host','unchanged-native-dispatch']:
                with self.assertRaises(ValueError):c.run(label,[sys.executable],950)
            for timeout in [120,951]:
                with self.assertRaises(ValueError):c.run('native',[sys.executable],timeout,operation='native-dispatch')
            spawn.assert_not_called()
        with self.fake():self.assertEqual(c.run('native',[sys.executable],950,operation='native-dispatch'),'')
        self.assertFalse(c.unresolved)
    def test_native_timeout_retains_nested_custody_despite_outer_absence(self):
        c=self.runner()
        with self.fake(clock=[0,951,951]) as (_,spawn,events):
            with self.assertRaises(RuntimeError):c.run('native',[sys.executable],950,operation='native-dispatch')
            with self.assertRaises(RuntimeError):c.run('cleanup',[sys.executable])
            self.assertEqual(spawn.call_count,1)
        row=c.events[0]
        self.assertTrue(row['reaped'] and row['ownedGroupAbsent'] and all(x['eof'] for x in row['streams'].values()))
        self.assertTrue(c.unresolved and row['nestedCustodyUnknown'])
    def test_interrupted_native_exit_retains_nested_custody(self):
        c=self.runner()
        with self.fake() as (p,spawn,events):
            p.returncode=-9
            with self.assertRaises(RuntimeError):c.run('native',[sys.executable],950,operation='native-dispatch')
        self.assertTrue(c.unresolved and c.events[0]['nestedCustodyUnknown'])
    def test_cleanup_and_ax_stop_without_queries_after_unknown(self):
        b=object.__new__(mac_backend.MacBackend);b.c=SimpleNamespace(unresolved=True)
        b.ax=SimpleNamespace(trusted=lambda:self.fail('AX queried'))
        b.devices=lambda:self.fail('devices queried')
        for action in [lambda:controller.cleanup(b,O,BASE),b.ax_trusted,b.inventory,lambda:b.close_window(W),lambda:b.native_dispatch([])]:
            with self.assertRaises(controller.Refused):action()

class WindowRepair(unittest.TestCase):
    outside=(90124,'90124 outside identity','outside-id','Other project')
    def backend(self,owned=O):
        b=object.__new__(mac_backend.MacBackend);b.owned=owned;b.unknown=False;b.c=SimpleNamespace(unresolved=False)
        b.folder=OUT;b.baseline_windows=[self.outside];b.baseline_frontends={90124:self.outside[1]}
        b.inventory_frontends={**b.baseline_frontends,W.pid:W.process_identity}
        b.ax=SimpleNamespace(release=lambda:None)
        return b
    def rows(self,*keys):return [(*k,object()) for k in keys]
    def owned_key(self):return (W.pid,W.process_identity,W.identifier,W.title)
    def test_absent_owned_preserves_all_outside_windows(self):
        b=self.backend();b.inventory=lambda:self.rows(self.outside)
        self.assertEqual(b.windows_for_device(UID),[]);self.assertFalse(b.unknown)
    def test_changed_title_and_token_latches(self):
        b=self.backend();b.inventory=lambda:self.rows(self.outside,(W.pid,W.process_identity,'new','new'))
        with self.assertRaises(controller.Refused):b.windows_for_device(UID)
        b.inventory=lambda:self.fail('reprobe after unknown')
        with self.assertRaises(controller.Refused):b.windows_for_device(UID)
    def test_partial_open_unclassified_latches(self):
        b=self.backend(replace(O,window=None));b.inventory=lambda:self.rows(self.outside,(W.pid,W.process_identity,'new','new'))
        with self.assertRaises(controller.Refused):b.windows_for_device(UID)
        self.assertTrue(b.unknown)
    def test_changed_or_missing_outside_window_latches(self):
        for outside in [[],[(90124,self.outside[1],'outside-id','renamed')]]:
            b=self.backend();b.inventory=lambda:self.rows(*outside,self.owned_key())
            with self.assertRaises(controller.Refused):b.windows_for_device(UID)
    def test_extra_unclassified_window_latches(self):
        b=self.backend();b.inventory=lambda:self.rows(self.outside,self.owned_key(),(90123,W.process_identity,'extra','Other'))
        with self.assertRaises(controller.Refused):b.windows_for_device(UID)
    def test_changed_frontend_identity_latches(self):
        b=self.backend();b.inventory_frontends[90124]='new start';b.inventory=lambda:self.rows(self.outside)
        with self.assertRaises(controller.Refused):b.windows_for_device(UID)
    def test_unknown_empty_frontend_latches(self):
        b=self.backend();b.inventory_frontends[90125]='new frontend';b.inventory=lambda:self.rows(self.outside)
        with self.assertRaises(controller.Refused):b.windows_for_device(UID)
    def test_full_backend_inventory_and_capture(self):
        b=self.backend(replace(O,window=None));b.baseline_windows=None;b.baseline_frontends=None
        b.frontends=lambda:{90124:self.outside[1]}
        b.ax=SimpleNamespace(trusted=lambda:True,app=lambda pid:pid,children=lambda *args:[self.outside],
            text=lambda obj,name,*args:obj[2] if name=='AXIdentifier' else obj[3],release=lambda:None)
        with patch.object(mac_backend,'write'):b.capture_window_baseline()
        self.assertEqual(b.baseline_windows,[self.outside]);self.assertEqual(b.baseline_frontends,{90124:self.outside[1]})
        self.assertEqual(b.windows_for_device(UID),[])
    def test_exact_close_reconciles_outside_before_press(self):
        b=self.backend();b.inventory=lambda:self.rows(self.owned_key())
        b.ax.press=lambda _:self.fail('close after outside disappeared')
        with self.assertRaises(controller.Refused):b.close_window(W)
        self.assertTrue(b.unknown)
    def test_open_command_failure_never_reprobes_for_cleanup(self):
        b=self.backend(replace(O,window=None));b.capture_window_baseline=lambda:None
        b.command=lambda *args:(_ for _ in ()).throw(RuntimeError('partial open'))
        with self.assertRaises(RuntimeError):b.open_owned_window(b.owned)
        b.devices=lambda:self.fail('cleanup query')
        with self.assertRaises(controller.Refused):controller.cleanup(b,b.owned,BASE)

class FutureDispatch(unittest.TestCase):
    def test_future_dispatch_wires_only_explicit_950(self):
        b=object.__new__(mac_backend.MacBackend);b.index=0;b.c=SimpleNamespace(unresolved=False,run=lambda *args,**kw:(args,kw))
        args,kw=b.native_dispatch(['exact-accepted-wrapper'])
        self.assertEqual(args[2],950);self.assertEqual(kw,dict(operation='native-dispatch'))
    def test_future_finally_skips_cleanup_probes_on_interrupted_dispatch(self):
        folder=OUT/'future-interrupted'
        b=object.__new__(mac_backend.MacBackend);b.c=SimpleNamespace(unresolved=False)
        b.ax_trusted=lambda:True
        def run(argv):b.c.unresolved=True;raise RuntimeError('outer exited; nested unknown')
        b.native_dispatch=run;b.devices=lambda:self.fail('cleanup probe after interrupted dispatch')
        seal=commands.digest((future_run.HERE/'candidate-seal.json').read_bytes())
        # Only the folder-parent binding is adjusted for this fake run. No real native operations.
        with patch.object(future_run,'HERE',OUT),patch.object(future_run,'MacBackend',return_value=b),patch.object(future_run,'setup',return_value=(O,BASE)),patch.object(future_run,'dispatch',return_value={'argv':['fake']}):
            source=json.loads((Path(__file__).parent/'candidate-seal.json').read_bytes())
            (OUT/'candidate-seal.json').write_text(json.dumps({'sourceFiles':{}}))
            seal=commands.digest((OUT/'candidate-seal.json').read_bytes())
            with self.assertRaises(controller.Refused):future_run.run(folder.resolve(),seal)
        result=json.loads((folder/'result.json').read_text())
        self.assertIn('Unknown custody',result['cleanupFailure']);self.assertTrue(b.c.unresolved)

class ReceiptAndInventoryGuards(unittest.TestCase):
    def test_backend_receipt_failure_blocks_all_followup(self):
        b=object.__new__(mac_backend.MacBackend);b.unknown=False;b.c=SimpleNamespace(unresolved=False)
        with patch.object(mac_backend,'write',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):b.record(OUT/'fake-receipt',{})
        b.ax=SimpleNamespace(trusted=lambda:self.fail('AX after receipt failure'))
        with self.assertRaises(controller.Refused):b.ax_trusted()
    def test_cleanup_rechecks_outside_windows_after_device_mutation(self):
        b=Fake();checks=[]
        b.verify_outside_windows=lambda:checks.append('windows')
        controller.cleanup(b,O,BASE)
        self.assertGreaterEqual(len(checks),4)
    def test_setup_command_unknown_blocks_finally_cleanup(self):
        b=Fake();del b.rows[UID];b.windows=[];b.unknown=False
        def guard():controller.require(not b.unknown,'Unknown custody')
        b.assert_custody=guard
        def boot(uid):b.unknown=True;raise OSError('EPERM')
        b.boot=boot
        with self.assertRaises(controller.Refused):controller.setup(b)
        self.assertFalse(any(isinstance(a,tuple) and a[0] in ('shutdown','delete') for a in b.actions))
