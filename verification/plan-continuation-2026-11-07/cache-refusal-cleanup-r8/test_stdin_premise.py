"""Exercise real CPython stdin descriptor setup with OS child creation forbidden."""
import json
import os
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest import mock
from stdin_guard import accepted_stdin, write_guard, run_direct, _stdin_scope
HERE = Path(__file__).resolve().parent

def no_children(event, args):
    if event in {'subprocess.Popen','os.system','os.fork','os.forkpty','os.posix_spawn','os.kill','os.killpg','os.exec','os.spawn'} or event.startswith('socket.'):
        raise RuntimeError('Pure premise forbids real child/process/network operations')
sys.addaudithook(no_children)
write_guard(HERE)

class Controls(unittest.TestCase):
    def handles(self):
        obj = object.__new__(subprocess.Popen)
        obj._closed_child_pipe_fds = False
        obj.pipesize = -1
        fds = []
        try:
            fds = obj._get_handles(subprocess.DEVNULL, subprocess.PIPE, subprocess.PIPE)
            self.assertEqual(os.read(fds[0], 1), b'')
            self.assertEqual(os.write(fds[0], b'discarded'), 9)
            return list(fds)
        finally:
            for fd in set(list(fds) + ([obj._devnull] if hasattr(obj,'_devnull') else [])):
                if fd >= 0: os.close(fd)
    def test_baseline_refuses_actual_stdin_setup(self):
        with self.assertRaisesRegex(RuntimeError,'Write outside owned correction: /dev/null'):
            self.handles()
    def test_scoped_actual_controller_stdin_path(self):
        events=[]
        def run(label, argv, cwd, **kwargs):
            self.assertEqual(label,'optimized-member-validation')
            self.assertEqual(kwargs,{'timeout':15,'allowed':(0,1)})
            events.append(self.handles())
            self.outside_writes_refused()
        run_direct(types.SimpleNamespace(run=run), ['owned-fixture'], HERE)
        self.assertEqual(len(events),1)
        self.assertFalse(_stdin_scope.get())
        with self.assertRaises(RuntimeError):self.handles()
    def outside_writes_refused(self):
        for path,flags in [('/dev/null',os.O_RDWR),('/dev/null',os.O_WRONLY),
                ('/dev/null',os.O_RDWR|os.O_TRUNC),(str(HERE.parent/'r5-forbidden-write'),os.O_WRONLY|os.O_CREAT)]:
            with self.assertRaises(RuntimeError): os.open(path,flags,0o600)
        with self.assertRaises(RuntimeError):sys.audit('os.rename',str(HERE/'owned'),str(HERE.parent/'foreign'),-1,-1)
        with self.assertRaises(RuntimeError):sys.audit('socket.__new__')
    def test_outside_writes_refuse_without_scope(self):self.outside_writes_refused()
    def test_scope_resets_on_exception(self):
        def fail(*args,**kwargs):raise ValueError('synthetic prelaunch failure')
        with self.assertRaises(ValueError):run_direct(types.SimpleNamespace(run=fail),[],HERE)
        self.assertFalse(_stdin_scope.get())
        with self.assertRaises(RuntimeError):self.handles()
    def test_owned_file_still_writable(self):
        p=HERE/'premise-owned.txt';p.write_text('owned');self.assertEqual(p.read_text(),'owned');p.unlink()
    def test_no_inner_process_operation(self):
        for event,args in [('subprocess.Popen',('fake',)),('os.killpg',(987654321,0))]:
            with self.assertRaises(RuntimeError):sys.audit(event,*args)

result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
(HERE/('premise-result-'+('optimized' if sys.flags.optimize else 'normal')+'.json')).write_text(json.dumps({'tests':result.testsRun,'successful':result.wasSuccessful(),
 'errors':[(str(t),e)for t,e in result.errors],'failures':[(str(t),e)for t,e in result.failures],
 'real_inner_children':0,'actual_stdlib_get_handles_executed':True,'private_method_patched':False,
 'scope':'DEVNULL setup only; 27 fakes separately include actual projected test_original.main with fake suite.'},indent=2)+'\n')
sys.exit(0 if result.wasSuccessful()else 1)
