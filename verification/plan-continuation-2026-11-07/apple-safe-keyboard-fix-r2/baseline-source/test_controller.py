import copy, unittest
from dataclasses import replace
from controller import Owned, Window, cleanup, dispatch, setup, Refused, PROTECTED

UID='11111111-2222-4333-8444-555555555555'
W=Window(90123,'90123 start /Applications/Xcode_26.6.app/Contents/Developer/Applications/Simulator.app/Contents/MacOS/Simulator','public-window-token','MixerKeyboard-owned',UID)
O=Owned(UID,'MixerKeyboard-owned','ios26.5','iphone17pro',W)
BASE={u:dict(name=u,state='Booted',runtime='ios26.5',deviceType='iphone17pro',dataPath='/protected/'+u) for u in PROTECTED}
ROW=dict(name=O.name,state='Booted',runtime=O.runtime,deviceType=O.device_type)
class Fake:
    def __init__(self):
        self.rows={**copy.deepcopy(BASE),UID:dict(ROW)}; self.windows=[W]
        self.actions=[]; self.trusted=True; self.connected=True; self.close_drift=False
    def devices(self): return copy.deepcopy(self.rows)
    def ax_trusted(self): self.actions.append('ax'); return self.trusted
    def windows_for_device(self,uid): return list(self.windows)
    def close_window(self,w):
        self.actions.append(('close-window',w)); self.windows=[]
        if self.close_drift: self.rows[next(iter(PROTECTED))]['state']='Shutdown'
    def shutdown(self,uid): self.actions.append(('shutdown',uid)); self.rows[uid]['state']='Shutdown'
    def delete(self,uid): self.actions.append(('delete',uid)); del self.rows[uid]
    def verify_bindings(self): self.actions.append('verify')
    def create_owned(self): self.actions.append('create'); self.rows[UID]=dict(ROW); return replace(O,window=None)
    def boot(self,uid): self.actions.append(('boot',uid))
    def open_owned_window(self,o): self.actions.append('open'); self.windows=[W]; return O
    def keyboard_connected(self,w): return self.connected
    def dispatch_unchanged(self,o,b): self.actions.append('dispatch'); return 'unchanged-dispatch'

class Safety(unittest.TestCase):
    def test_cleanup_preserves_both_external_devices_and_data(self):
        b=Fake(); result=cleanup(b,O,BASE)
        self.assertEqual(b.rows,BASE); self.assertTrue(result['cleanupPassed'])
        self.assertEqual([a[0] for a in b.actions if isinstance(a,tuple)],['close-window','shutdown','delete'])
    def test_close_side_effect_stops_before_shutdown_delete(self):
        b=Fake(); b.close_drift=True
        with self.assertRaisesRegex(Refused,'External baseline'): cleanup(b,O,BASE)
        self.assertFalse(any(isinstance(a,tuple) and a[0] in ('shutdown','delete') for a in b.actions))
    def test_existing_drift_refuses_all_actions(self):
        b=Fake(); b.rows[next(iter(PROTECTED))]['state']='Shutdown'
        with self.assertRaises(Refused): cleanup(b,O,BASE)
        self.assertEqual(b.actions,[])
    def test_unknown_window_refused(self):
        b=Fake(); b.windows=[replace(W,identifier='another')]
        with self.assertRaises(Refused): cleanup(b,O,BASE)
        self.assertFalse(any(isinstance(a,tuple) for a in b.actions))
    def test_duplicate_window_refused(self):
        b=Fake(); b.windows=[W,W]
        with self.assertRaises(Refused): cleanup(b,O,BASE)
    def test_empty_window_identifier_refused(self):
        with self.assertRaises(Refused): cleanup(Fake(),replace(O,window=replace(W,identifier='')),BASE)
    def test_unknown_partial_open_retained(self):
        b=Fake()
        with self.assertRaisesRegex(Refused,'Unidentified window'): cleanup(b,replace(O,window=None),BASE)
        self.assertEqual(b.actions,[])
    def test_no_window_no_frontend_operation(self):
        b=Fake(); b.windows=[]
        self.assertTrue(cleanup(b,replace(O,window=None),BASE)['cleanupPassed'])
        self.assertEqual(b.actions,[('shutdown',UID),('delete',UID)])
    def test_absent_owned_device_idempotent(self):
        b=Fake(); b.windows=[]; del b.rows[UID]
        self.assertTrue(cleanup(b,O,BASE)['cleanupPassed']); self.assertEqual(b.rows,BASE)
    def test_ax_revocation_retains_resources(self):
        b=Fake(); b.trusted=False
        with self.assertRaises(Refused): cleanup(b,O,BASE)
        self.assertIn(UID,b.rows); self.assertEqual(b.windows,[W])
    def test_protected_uuid_refused(self):
        for uid in PROTECTED:
            with self.assertRaises(Refused): cleanup(Fake(),replace(O,uuid=uid),BASE)
    def test_held_frontend_refused(self):
        with self.assertRaises(Refused): cleanup(Fake(),replace(O,window=replace(W,pid=23663)),BASE)
    def test_changed_owned_identity_refused(self):
        b=Fake(); b.rows[UID]['name']='other'
        with self.assertRaises(Refused): cleanup(b,O,BASE)
        self.assertEqual(b.actions,[])
    def test_shutdown_failure_cannot_delete(self):
        b=Fake(); b.shutdown=lambda uid: b.actions.append(('shutdown-no-effect',uid))
        with self.assertRaisesRegex(Refused,'positively Shutdown'): cleanup(b,O,BASE)
        self.assertIn(UID,b.rows)
    def test_ax_failure_prevents_verification_and_setup(self):
        b=Fake(); b.trusted=False
        with self.assertRaises(Refused): setup(b)
        self.assertEqual(b.actions,['ax'])
    def test_setup_verifies_before_creation(self):
        b=Fake(); del b.rows[UID]; b.windows=[]
        owned,baseline=setup(b)
        self.assertEqual(b.actions[:3],['ax','verify','create']); self.assertEqual(baseline,BASE)
        self.assertEqual(owned,O)
    def test_failed_binding_prevents_creation(self):
        b=Fake()
        def fail(): raise Refused('binding mismatch')
        b.verify_bindings=fail
        with self.assertRaises(Refused): setup(b)
        self.assertNotIn('create',b.actions)
    def test_no_keyboard_no_dispatch(self):
        b=Fake(); b.connected=False
        with self.assertRaises(Refused): dispatch(b,O,BASE)
        self.assertNotIn('dispatch',b.actions)
    def test_valid_dispatch_uses_unchanged_callback(self):
        b=Fake(); self.assertEqual(dispatch(b,O,BASE),'unchanged-dispatch')
        self.assertEqual(b.actions,['ax','verify','dispatch'])
    def test_new_external_device_is_not_erased(self):
        b=Fake(); b.rows['new-external']=dict(ROW)
        with self.assertRaises(Refused): cleanup(b,O,BASE)
        self.assertIn('new-external',b.rows)

class NativeBackendContract(unittest.TestCase):
    def backend(self):
        from mac_backend import MacBackend
        b=object.__new__(MacBackend)
        b.owned=O; b.index=0; b.calls=[]
        b.command=lambda label,argv,*args: b.calls.append(argv) or ''
        return b
    def test_real_backend_shutdown_exact_uuid(self):
        b=self.backend(); b.shutdown(UID)
        self.assertEqual(b.calls,[['/usr/bin/xcrun','simctl','shutdown',UID]])
    def test_real_backend_delete_exact_uuid(self):
        b=self.backend(); b.delete(UID)
        self.assertEqual(b.calls,[['/usr/bin/xcrun','simctl','delete',UID]])
    def test_real_backend_rejects_other_uuid_before_command(self):
        b=self.backend()
        for op in [b.shutdown,b.delete,b.boot]:
            with self.assertRaises(Refused): op(next(iter(PROTECTED)))
        self.assertEqual(b.calls,[])
    def test_public_window_mapping_rejects_unknown_identifier(self):
        b=self.backend()
        class AXFake:
            def release(self): pass
        b.ax=AXFake()
        b.inventory=lambda:[(W.pid,W.process_identity,'',O.name,object())]
        with self.assertRaisesRegex(Refused,'identifier unavailable'): b.windows_for_device(UID)
    def test_public_window_mapping_keeps_title_change_visible(self):
        b=self.backend()
        class AXFake:
            def release(self): pass
        b.ax=AXFake()
        b.inventory=lambda:[(W.pid,W.process_identity,W.identifier,'renamed',object())]
        self.assertEqual(b.windows_for_device(UID),[replace(W,title='renamed')])
    def test_real_close_refuses_reused_pid(self):
        b=self.backend()
        b.inventory=lambda:[(W.pid,'different start',W.identifier,W.title,object())]
        with self.assertRaisesRegex(Refused,'Exact window'): b.exact_element(W)
    def test_real_close_uses_exact_window_close_button(self):
        b=self.backend(); events=[]
        class AXFake:
            def text(self,obj,name): return 'AXWindow'
            def attr(self,obj,name): events.append(('attribute',obj,name)); return 'exact-close-button'
            def flag(self,obj,name): return True
            def press(self,obj): events.append(('press',obj))
            def release(self): events.append('release')
        b.ax=AXFake(); b.exact_element=lambda w:'exact-window'
        import mac_backend
        from unittest.mock import patch
        b.folder=__import__('pathlib').Path('/unused-fake')
        with patch.object(mac_backend,'write',lambda *args:None): b.close_window(W)
        self.assertEqual(events,[('attribute','exact-window','AXCloseButton'),('press','exact-close-button'),'release'])
    def test_all_candidate_modules_import_without_commands(self):
        import importlib.util
        from pathlib import Path
        from unittest.mock import patch
        with patch('subprocess.Popen',side_effect=AssertionError('No command on import')):
            for filename in ['mac_backend.py','future_run.py','dispatch_once.py','validate.py']:
                spec=importlib.util.spec_from_file_location('import_control_'+filename[:-3],Path(__file__).parent/filename)
                module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)

if __name__=='__main__': unittest.main(verbosity=2)
