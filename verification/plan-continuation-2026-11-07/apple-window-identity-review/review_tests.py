"""Independent pure-host controls; no actual backend/process/UI operations."""
import contextlib, errno, hashlib, json, os, stat, sys, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
CANDIDATE = HERE.parent / 'apple-window-identity-campaign'
MODE = 'baseline' if 'baseline' in sys.argv else ('optimized' if sys.flags.optimize else 'normal')
OUT = HERE / MODE
OUT.mkdir(exist_ok=True)
sys.path.insert(1, str(CANDIDATE))
sys.dont_write_bytecode = True

def audit(event, args):
    if event in ('subprocess.Popen', 'os.system', 'os.kill', 'os.killpg', 'os.posix_spawn', 'os.exec') or event.startswith('socket.'):
        raise RuntimeError('Host-only review forbids ' + event)
    if event == 'ctypes.dlopen' and args[0] and ('ApplicationServices' in str(args[0]) or 'CoreFoundation' in str(args[0])):
        raise RuntimeError('No native AX library in host review')
    if event == 'open':
        path, mode, flags = args
        writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (isinstance(flags, int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))
        if writing and isinstance(path, (str, bytes, os.PathLike)) and not Path(path).resolve().is_relative_to(HERE):
            raise RuntimeError('Review write outside ownership: ' + str(path))
original_audit=audit
def audit(event,args):
    original_audit(event,args)
    if event in ('os.mkdir','os.remove','os.rmdir','os.rename','os.link','os.symlink'):
        paths=args[:2] if event in ('os.rename','os.link','os.symlink') else args[:1]
        for path in paths:
            if isinstance(path,(str,bytes,os.PathLike)) and not Path(path).resolve().is_relative_to(HERE):
                raise RuntimeError('Filesystem mutation outside review: '+str(path))
sys.addaudithook(audit)

import commands, controller, mac_backend, test_controller, verify_bindings
from test_controller import Fake, O, W, UID, BASE
from dataclasses import replace

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def put(name, value): (OUT/name).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')

class BindingControls(unittest.TestCase):
    def test_actual_final_source_and_seal(self):
        seal = json.loads((CANDIDATE/'candidate-seal.json').read_text())
        actual = {n:sha(CANDIDATE/n) for n in seal['sourceFiles']}
        tree = hashlib.sha256(json.dumps(actual,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        put('source.json',dict(sealSHA256=sha(CANDIDATE/'candidate-seal.json'),sourceFiles=actual,sourceTreeSHA256=tree))
        self.assertEqual(actual, seal['sourceFiles'])
        self.assertEqual(tree, seal['sourceTreeSHA256'])
        self.assertEqual(sha(CANDIDATE/'baseline-source/candidate-seal.json'), '51d42199a60518870fbdad4eb4bca4d2c2b13b1efd1874aefff0613c7334cbe2')
    def test_handoff_all_files_unchanged(self):
        seal=json.loads((CANDIDATE/'baseline-source/candidate-seal.json').read_text())
        actual={n:sha(CANDIDATE/'baseline-source'/n) for n in seal['sourceFiles']}
        self.assertEqual(actual,seal['sourceFiles'])
    def test_unchanged_accepted_verifier_readonly(self):
        result=verify_bindings.verify()
        put('bindings.json', result)
        self.assertFalse(result['dispatchCalled'])
        self.assertTrue(result['markersUnchanged'] and result['inputsUnchanged'])
        self.assertEqual(result['verified']['packetSHA256'], '38850f4a1f9fe8326c101d398823249ad25711c9e5113e6ac3bc95891624cef5')

class FinalBackendControls(unittest.TestCase):
    def backend(self):
        b=object.__new__(mac_backend.MacBackend)
        b.owned=O; b.index=0; b.folder=OUT; b.calls=[]; b.baseline_windows=[]; b.baseline_frontends={}; b.inventory_frontends={W.pid:W.process_identity}
        return b
    def test_correct_v9_name(self):
        b=self.backend()
        b.command=lambda label,argv,*a: b.calls.append(argv) or UID
        with patch.object(mac_backend,'write'):
            owned=b.create_owned()
        self.assertTrue(owned.name.startswith('MixerFocusReferenceV9-'))
        self.assertEqual(b.calls[0][3],owned.name)
    def test_frontend_sort_is_numeric(self):
        b=self.backend()
        def command(label,argv,*a):
            b.calls.append(argv)
            return '[90124,90123]' if label=='frontend-pids' else argv[2]+' start '+mac_backend.EXE
        b.command=command
        self.assertEqual(list(b.frontends()),[90123,90124])
    def test_runtime_build_preflight(self):
        b=self.backend()
        for rows,good in [([],False),([dict(identifier=mac_backend.RUNTIME,isAvailable=True,buildversion='other')],False),([dict(identifier=mac_backend.RUNTIME,isAvailable=False,buildversion='23F77')],False),([dict(identifier=mac_backend.RUNTIME,isAvailable=True,buildversion='23F77')],True)]:
            with self.subTest(rows=rows),patch.object(mac_backend,'verify',return_value='verified'):
                b.command=lambda *a:json.dumps(dict(runtimes=rows))
                if good:self.assertEqual(b.verify_bindings(),'verified')
                else:
                    with self.assertRaises(controller.Refused):b.verify_bindings()
    def test_current_holds_complete(self):
        holds={40708,40709,40711,23663,20745,20770,20780,20817,20842,20851,20866,2424,2621}
        self.assertEqual(dict(commands=sorted(holds-commands.HELD),controller=sorted(holds-controller.HELD)),dict(commands=[],controller=[]))
    def test_changed_token_and_title_is_not_absence(self):
        b=self.backend(); b.ax=SimpleNamespace(release=lambda:None)
        b.inventory=lambda:[(W.pid,W.process_identity,'changed-token','changed-title',object())]
        try: matches=b.windows_for_device(UID)
        except controller.Refused:return
        self.assertNotEqual(matches,[], 'Unclassified live window became proved absence')
    def test_partial_open_unknown_window_is_retained(self):
        b=self.backend();b.owned=replace(O,window=None);b.ax=SimpleNamespace(release=lambda:None)
        b.inventory=lambda:[(W.pid,W.process_identity,'new-token','unexpected-title',object())]
        try: matches=b.windows_for_device(UID)
        except controller.Refused:return
        self.assertNotEqual(matches,[], 'Unclassified partial-open window became proved absence')
    def test_revoked_ax_stops_before_frontend_probe(self):
        b=self.backend(); b.ax=SimpleNamespace(trusted=lambda:False); b.frontends=lambda:self.fail('frontend query after revoked AX')
        with self.assertRaises(controller.Refused):b.inventory()

class PolicyFailureControls(unittest.TestCase):
    def test_dispatch_identity_drift_stops(self):
        b=Fake(); b.rows[UID]['name']='changed'
        with self.assertRaises(controller.Refused):controller.dispatch(b,O,BASE)
        self.assertNotIn('dispatch',b.actions)
    def test_ambiguous_dispatch_stops(self):
        b=Fake();b.windows=[W,W]
        with self.assertRaises(controller.Refused):controller.dispatch(b,O,BASE)
        self.assertNotIn('dispatch',b.actions)
    def test_revoked_ax_dispatch_stops(self):
        b=Fake();b.trusted=False
        with self.assertRaises(controller.Refused):controller.dispatch(b,O,BASE)
        self.assertEqual(b.actions,['ax'])

class Pipe:
    def __init__(self,fd):self.fd=fd;self.closed=False
    def fileno(self):return self.fd
    def close(self):self.closed=True
class Process:
    pid=90199
    returncode=0
    def __init__(self):self.stdout=Pipe(101);self.stderr=Pipe(102)
    def poll(self):return self.returncode
    def wait(self):return self.returncode
class Selector:
    def __init__(self):self.rows=[]
    def register(self,pipe,events,name):self.rows.append(SimpleNamespace(fileobj=pipe,data=name))
    def unregister(self,pipe):self.rows=[x for x in self.rows if x.fileobj is not pipe]
    def select(self,*a):return [(r,1) for r in self.rows]
    def close(self):pass

class CustodyFailureControls(unittest.TestCase):
    def runner(self):
        path=OUT/self._testMethodName;path.mkdir(exist_ok=True)
        return commands.Commands(path)
    @contextlib.contextmanager
    def boundaries(self,kind):
        p=Process()
        def killpg(pid,sig):
            if kind in ('eperm-probe','eperm-term'):raise PermissionError(errno.EPERM,'fake ownership denied')
            if kind=='group-present':return
            raise ProcessLookupError()
        with contextlib.ExitStack() as s:
            spawn=s.enter_context(patch.object(commands.subprocess,'Popen',return_value=p))
            s.enter_context(patch.object(commands.selectors,'DefaultSelector',Selector))
            s.enter_context(patch.object(commands.os,'set_blocking'))
            s.enter_context(patch.object(commands.os,'killpg',side_effect=killpg))
            s.enter_context(patch.object(commands.os,'read',side_effect=OSError('fake pipe failure') if kind=='read-error' else None,return_value=b''))
            if kind=='eperm-term':s.enter_context(patch.object(commands.time,'monotonic',side_effect=[0,121]))
            yield spawn
    def failure(self,kind):
        c=self.runner()
        with self.boundaries(kind) as spawn:
            with self.assertRaises((RuntimeError,OSError)):c.run('first',[sys.executable,'-c','pass'],120)
            latched=c.unresolved
            with self.assertRaises((RuntimeError,OSError,StopIteration)):c.run('second',[sys.executable,'-c','pass'],120)
            calls=spawn.call_count
        observed=dict(fakeOnly=True,kind=kind,unresolvedLatched=latched,spawnCalls=calls,receiptCount=len(list(c.directory.glob('*.command.json'))))
        put(self._testMethodName+'.json',observed)
        self.assertEqual((latched,calls),(True,1),observed)
    def test_eperm_group_probe_latches_before_followup(self):self.failure('eperm-probe')
    def test_eperm_term_latches_before_followup(self):self.failure('eperm-term')
    def test_pipe_error_latches_before_followup(self):self.failure('read-error')
    def test_observed_group_present_latches(self):self.failure('group-present')
    def test_latched_runner_never_spawns(self):
        c=self.runner();c.unresolved=True
        with patch.object(commands.subprocess,'Popen') as spawn:
            with self.assertRaisesRegex(RuntimeError,'Prior command'):c.run('refused',[sys.executable],120)
            spawn.assert_not_called()

if __name__=='__main__':
    sys.modules['review_tests']=sys.modules[__name__]
    suite=unittest.TestSuite()
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(test_controller))
    import repair_tests
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(repair_tests))
    import independent_tests
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(independent_tests))
    for cls in [BindingControls,FinalBackendControls,PolicyFailureControls,CustodyFailureControls]:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
    if 'baseline' in sys.argv:
        suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n,independent_tests) for n in ['EntryControls.test_setup_external_baseline_drift_is_sticky_at_real_entrypoint','ActualBackendDrift.test_changed_external_device_stops_setup_before_followup_command','EntryControls.test_missing_session_terminal_field_fails_closed','EntryControls.test_boolean_exit_code_fails_closed'])
    else:
        import r3_tests
        suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(r3_tests))
    import fresh_tests
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(fresh_tests))
    import adoption_tests
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(adoption_tests))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    put('test-result.json',dict(testsRun=result.testsRun,failures=[dict(test=str(t),traceback=e) for t,e in result.failures],errors=[dict(test=str(t),traceback=e) for t,e in result.errors],python=sys.version,optimize=sys.flags.optimize,nativeAttempts=0,builds=0,UIActions=0))
    sys.exit(0 if result.wasSuccessful() else 1)
