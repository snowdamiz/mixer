"""Review-owned composition: exact candidate modules; extracted fixture definitions only."""
import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock
sys.dont_write_bytecode=True
OWN=Path(__file__).resolve().parent
ROOT=OWN.parents[2]
CAND=OWN
HERE=CAND
MODE='optimized' if sys.flags.optimize else 'normal'
EVIDENCE=OWN/('evidence-'+MODE)
EVIDENCE.mkdir()

import subprocess
import contextvars
sys.path[0:0]=[str(OWN),str(CAND)]
import stdin_guard as guard
def process_guard(event,args):
    if event in {'subprocess.Popen','os.system','os.fork','os.forkpty','os.posix_spawn','os.kill','os.killpg','os.exec','os.spawn'} or event.startswith('socket.'):
        raise RuntimeError('Review forbids inner process/network operations: '+event)
sys.addaudithook(process_guard)
guard.write_guard(OWN)

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def definitions(path,namespace,names=None,imports=True):
    # Select whole syntax nodes. Never rewrite text, nested literals, or candidate code.
    tree=ast.parse(path.read_bytes(),filename=str(path))
    body=[n for n in tree.body if (imports and isinstance(n,(ast.Import,ast.ImportFrom))) or
          (isinstance(n,(ast.FunctionDef,ast.ClassDef)) and (names is None or n.name in names))]
    exec(compile(ast.Module(body=body,type_ignores=[]),str(path),'exec'),namespace)

def review(label,candidate):
    evidence=EVIDENCE/label;evidence.mkdir()
    adapter=load(label+'_adoption',candidate/'adopt_fixture.py')
    fakes=types.ModuleType(label+'_fakes');fakes.__file__=str(candidate/'test_fakes.py')
    fakes.__dict__.update(HERE=candidate,MODE=MODE,EVIDENCE=evidence/('candidate-'+MODE))
    fakes.EVIDENCE.mkdir()
    with mock.patch.dict(sys.modules,{'adopt_fixture':adapter}):
        definitions(candidate/'test_fakes.py',fakes.__dict__)
    module=types.ModuleType(label+'_review');module.__file__=str(OWN.parent/'cache-custody-review-r2/review_fakes.py')
    module.__dict__.update(HERE=OWN,ROOT=ROOT,CAND=candidate,MODE=MODE,EVIDENCE=evidence,fakes=fakes,adoption=adapter,ast=ast,contextlib=contextlib,hashlib=hashlib,json=json,os=os,Path=Path,mock=mock)
    definitions(Path(module.__file__),module.__dict__,{'DrainSentinel','Extra'},imports=False)
    module.__dict__.update(ast=ast,contextlib=contextlib,hashlib=hashlib,json=json,os=os,Path=Path,mock=mock)
    return module

old=review('old-r2',OWN.parent/'cache-custody-premise-r2')
new=review('successor-r4',CAND)
definitions(CAND/'combined_fakes.py',globals(),{'Successor','Extra','Projection'},imports=False)

class ReviewControls(unittest.TestCase):
    def test_guards_and_fixture_global_ownership(self):
        for event,args in [('subprocess.Popen',('synthetic',)),('os.killpg',(987654321,0)),('socket.__new__',()),('open',(str(ROOT/'forbidden-review-write'),'w',os.O_WRONLY))]:
            with self.assertRaises(RuntimeError):sys.audit(event,*args)
        self.assertIs(new.fakes.Controls.context.__globals__,new.fakes.__dict__)
        self.assertIs(new.Extra.wrapper.__wrapped__.__globals__,new.__dict__)
        self.assertEqual(new.fakes.EVIDENCE.parent,new.EVIDENCE)
        self.assertEqual(new.adoption.HERE,CAND)
        (EVIDENCE/'composition.json').write_text(json.dumps({'candidate_exact_module':str(CAND),'fixture_globals_explicit':True,'nested_string_rewrites':0,'audit_hooks_installed':1,'audit_guard_controls_passed':True},indent=2))

    def test_successor_missing_source_and_wrong_seal(self):
        helper=Projection()
        project,candidate=helper.make('successor-negative-closure',CAND,True)
        controller=project/'verification/plan-continuation-2026-11-07/native-custody-premise/cleanup_control.py'
        original=controller.read_bytes();controller.unlink()
        with helper.isolated(project,candidate) as adapter:
            with mock.patch.object(sys,'argv',[str(candidate/'adopt_fixture.py'),'verify','--workflow-installed']):
                with self.assertRaisesRegex(RuntimeError,'Regular source required: .*cleanup_control.py'):adapter.main()
        controller.write_bytes(original)
        sealpath=candidate/'sources.json';sealbytes=sealpath.read_bytes()
        seal=json.loads(sealbytes);seal['tree_sha256']='0'*64
        sealpath.write_text(json.dumps(seal))
        with helper.isolated(project,candidate) as adapter:
            with mock.patch.object(sys,'argv',[str(candidate/'adopt_fixture.py'),'verify','--workflow-installed']):
                with self.assertRaisesRegex(RuntimeError,'Derivative source tree differs'):adapter.main()
        sealpath.write_bytes(sealbytes)
        with helper.isolated(project,candidate) as adapter:
            self.assertTrue(adapter.verify(True)['installed'])
        (EVIDENCE/'successor-negative-closure.json').write_text(json.dumps({'missing_controller_refused':True,'wrong_seal_refused':True,'restored_exact_bytes_pass':True},indent=2))

    def test_sparse_roster_and_candidate_hashes(self):
        lines=(CAND/'workflow-job.yml').read_text().splitlines()
        start=lines.index('          sparse-checkout: |')+1
        patterns=[]
        for line in lines[start:]:
            if not line.startswith('            /'):break
            patterns.append(line.strip().lstrip('/'))
        selected=json.loads((CAND/'projection-paths.json').read_bytes())
        for path in selected:
            self.assertTrue(any(path.startswith(p) if p.endswith('/') else path==p for p in patterns),path)
        seal=json.loads((CAND/'sources.json').read_bytes())
        self.assertEqual(hashlib.sha256((CAND/'sources.json').read_bytes()).hexdigest(),sys.argv[2])
        for row in seal['members']:
            self.assertEqual(hashlib.sha256((CAND/row['path']).read_bytes()).hexdigest(),row['sha256'])
        self.assertEqual(seal['tree_sha256'],sys.argv[3])


stdin_tests=types.ModuleType('retained_stdin_tests')
stdin_tests.__dict__.update(HERE=OWN,__file__=str(CAND/'test_stdin_premise.py'))
definitions(CAND/'test_stdin_premise.py',stdin_tests.__dict__,{'Controls'})


import errno
import signal
import time

scope_tests=types.ModuleType('retained_scope_tests')
scope_tests.__dict__.update(HERE=OWN,OUT=EVIDENCE,observations=[],__file__=str(CAND/'test_scope.py'))
definitions(CAND/'test_scope.py',scope_tests.__dict__,{'ScopeControls'})

preflight=load('reviewed_descriptor_preflight', CAND/'descriptor_preflight.py')
preflight.HERE=OWN
observations=[]

class Independent(unittest.TestCase):
    def devnull(self):
        obj=object.__new__(subprocess.Popen)
        try:
            fd=subprocess.Popen._get_devnull(obj)
            self.assertEqual(os.read(fd,1),b'')
        finally:
            if hasattr(obj,'_devnull'):os.close(obj._devnull)

    def denied(self,ctx):
        with self.assertRaisesRegex(RuntimeError,'Write outside owned correction'):
            ctx.run(self.devnull)

    def test_copy_of_copy_revoked_and_cannot_be_revived_by_new_entry(self):
        saved=[]
        def run(*a,**k):
            saved.append(contextvars.copy_context())
            saved.append(saved[0].copy())
            for c in saved:c.run(self.devnull)
        guard.run_direct(types.SimpleNamespace(run=run),[],OWN)
        self.assertIs(saved[0].get(guard._stdin_scope),saved[1].get(guard._stdin_scope))
        for c in saved:self.denied(c)
        with guard.accepted_stdin():
            self.devnull()
            for c in saved:self.denied(c)
        observations.append({'case':self._testMethodName,'positive_in_scope':True,'late_copies_refused':True})

    def test_nested_entry_from_copy_preserves_active_owner(self):
        copies=[]
        with guard.accepted_stdin():
            outer=contextvars.copy_context()
            outer_cap=guard._stdin_scope.get()
            def nested():
                with guard.accepted_stdin():
                    self.assertIsNot(outer_cap,guard._stdin_scope.get())
                    copies.append(contextvars.copy_context())
                    self.devnull()
            outer.run(nested)
            self.denied(copies[0])
            outer.run(self.devnull)
            self.assertTrue(outer_cap.active)
        self.denied(outer)
        self.denied(copies[0])

    def test_context_reset_error_still_revokes_capability(self):
        manager=guard.accepted_stdin()
        owner=contextvars.Context()
        owner.run(manager.__enter__)
        cap=owner.get(guard._stdin_scope)
        self.assertTrue(cap.active)
        owner.run(self.devnull)
        with self.assertRaisesRegex(ValueError,'different Context'):
            manager.__exit__(None,None,None)
        self.assertFalse(cap.active)
        self.denied(owner)
        self.assertIsNone(guard._stdin_scope.get())

    def test_original_bodies_and_limits_preserved(self):
        adapter=load('original_body_adapter',CAND/'original_adapter.py')
        source=(CAND.parent/'cache-deadline-control-fix/runner-controls.py').read_bytes()
        proof=adapter.proof(source)
        self.assertEqual(len(proof['test_bodies']),36)
        self.assertEqual(proof['source_sha256'],'1ec5eeb5a80d257aaebd22544f715abdaa0765daa24a45f077554422ff770ab2')
        self.assertEqual(proof['adapted_sha256'],'0d41e07c37fa32e1870b30e93e7f090e0ff7e8bc3c542a3a8d7e94e8d05eeddd')
        for mode,name in [('normal','original-normal-ch5imm61'),('optimized','original-optimized-ml8t3czc')]:
            retained=json.loads((CAND.parent/'cache-stdin-lifetime-fix-r6'/'evidence'/name/'source-identity.json').read_bytes())
            self.assertEqual(retained,proof)
        text=(CAND/'adopt_fixture.py').read_text()
        self.assertIn('== (600, 60, 60, 8388608)',text)
        (EVIDENCE/'original-body-proof.json').write_text(json.dumps(proof,indent=2)+'\n')

    def test_workflow_preflight_precedes_real_original36(self):
        workflow=(CAND/'workflow-job.yml').read_text()
        first_original=workflow.index('/test_original.py')
        self.assertLess(workflow.index('python3 -B "$MIXER_STDIN_DIR/descriptor_preflight.py"'),first_original)
        self.assertLess(workflow.index('python3 -B -O "$MIXER_STDIN_DIR/descriptor_preflight.py"'),first_original)
        self.assertIn('timeout-minutes: 1',workflow[workflow.index('- name: Pure descriptor'):first_original])
        self.assertEqual((ROOT/'.github/workflows/verify.yml').read_text().count((CAND/'previous-job.yml').read_text()),1)

    def preflight_case(self,label,popen=None):
        actual_popen=subprocess.Popen
        proxy=types.SimpleNamespace(Popen=popen or actual_popen,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE,__file__=subprocess.__file__)
        captured=io.StringIO()
        with mock.patch.object(preflight,'subprocess',proxy),contextlib.redirect_stdout(captured):
            code=preflight.main()
        data=json.loads(captured.getvalue())
        data.update(review_case=label,review_injection=popen is not None,review_candidate_source_unchanged=True)
        (EVIDENCE/('preflight-'+label+'.json')).write_text(json.dumps({'returncode':code,**data},indent=2)+'\n')
        self.assertTrue(data['timer_disarmed'])
        self.assertEqual(data['real_inner_children'],0)
        for fd in data['closed_descriptors']:
            with self.assertRaises(OSError) as caught:os.fstat(fd)
            self.assertEqual(caught.exception.errno,errno.EBADF)
        self.assertIs(subprocess.Popen,actual_popen)
        return code,data

    def test_preflight_actual_positive_and_five_descriptors(self):
        code,data=self.preflight_case('actual')
        self.assertEqual(code,0)
        self.assertTrue(data['passed'])
        self.assertEqual(len(data['closed_descriptors']),5)
        self.assertEqual(data['events'],[{'path':'/dev/null','flags':os.O_RDWR|getattr(os,'O_CLOEXEC',0),'original_code':True}])
        self.assertIsNone(guard._stdin_scope.get())

    def test_preflight_changed_caller_refused(self):
        class Changed(subprocess.Popen):
            def _get_devnull(self):
                self._devnull=os.open('/dev/null',os.O_RDWR)
                return self._devnull
        code,data=self.preflight_case('changed-caller',Changed)
        self.assertEqual(code,1)
        self.assertIn('Write outside owned correction',data['error'])

    def test_preflight_changed_flags_refused(self):
        method=subprocess.Popen._get_devnull
        namespace=dict(method.__globals__,os=types.SimpleNamespace(devnull='/dev/null',O_RDWR=os.O_WRONLY,open=os.open))
        class Changed(subprocess.Popen):pass
        Changed._get_devnull=types.FunctionType(method.__code__,namespace)
        self.assertIs(Changed._get_devnull.__code__,guard._devnull_code)
        code,data=self.preflight_case('changed-flags',Changed)
        self.assertEqual(code,1)
        self.assertIn('Write outside owned correction',data['error'])

    def test_preflight_truncated_layout_refused(self):
        class Changed(subprocess.Popen):
            def _get_handles(self,*args):
                h=list(super()._get_handles(*args))
                os.close(h[-1])
                return h[:-1]
        code,data=self.preflight_case('truncated-layout',Changed)
        self.assertEqual(code,1)
        self.assertIn('Unexpected selected-interpreter handle layout',data['error'])
        self.assertEqual(len(data['closed_descriptors']),4)

    def test_preflight_aliased_stdout_stderr_refused(self):
        class Changed(subprocess.Popen):
            def _get_handles(self,*args):
                h=list(super()._get_handles(*args))
                os.close(h[4]);os.close(h[5])
                h[4:6]=h[2:4]
                return h
        code,data=self.preflight_case('aliased-stdout-stderr',Changed)
        # stdout and stderr must have independent pipe pairs: five distinct descriptors.
        self.assertEqual(code,1,'False admission: aliased stdout/stderr accepted with '+str(len(data['closed_descriptors']))+' descriptors')

    def test_preflight_closed_descriptor_refused(self):
        class Changed(subprocess.Popen):
            def _get_handles(self,*args):
                h=list(super()._get_handles(*args));os.close(h[5]);return h
        code,data=self.preflight_case('closed-descriptor',Changed)
        self.assertEqual(code,1)
        self.assertFalse(data['passed'])
        self.assertTrue(data['cleanup_errors'])

    def test_preflight_real_five_second_alarm(self):
        class Changed(subprocess.Popen):
            def _get_handles(self,*args):
                time.sleep(8)
                raise RuntimeError('alarm did not fire')
        started=time.monotonic()
        code,data=self.preflight_case('timeout',Changed)
        elapsed=time.monotonic()-started
        self.assertEqual(code,1)
        self.assertIn('Descriptor preflight exceeded five seconds',data['error'])
        self.assertLess(elapsed,7)
        self.assertEqual(data['closed_descriptors'],[])
        observations.append({'case':self._testMethodName,'elapsed_seconds':elapsed,'scope':'alarm control, not performance'})

    def test_preflight_no_process_or_network_admission(self):
        for event in ['subprocess.Popen','os.system','os.fork','os.forkpty','os.posix_spawn','os.kill','os.killpg','os.exec','os.spawn','socket.__new__']:
            with self.subTest(event=event),self.assertRaises(RuntimeError):sys.audit(event)

    def test_preflight_stdin_binding_refused(self):
        class Changed(subprocess.Popen):
            def _get_handles(self,*args):
                h=list(super()._get_handles(*args));h[0],h[2]=h[2],h[0];return h
        code,data=self.preflight_case('wrong-stdin-binding',Changed)
        self.assertEqual(code,1)
        self.assertIn('Stdin must be the cached DEVNULL descriptor',data['error'])
        self.assertEqual(len(data['closed_descriptors']),5)

    def test_preflight_missing_cached_devnull_refused(self):
        class Changed(subprocess.Popen):
            def _get_handles(self,*args):
                h=list(super()._get_handles(*args));del self._devnull;return h
        code,data=self.preflight_case('missing-cached-devnull',Changed)
        self.assertEqual(code,1)
        self.assertIn('Stdin must be the cached DEVNULL descriptor',data['error'])
        self.assertEqual(len(data['closed_descriptors']),5)

    def test_preflight_aliased_pipe_endpoint_refused(self):
        class Changed(subprocess.Popen):
            def _get_handles(self,*args):
                h=list(super()._get_handles(*args));os.close(h[3]);h[3]=h[2];return h
        code,data=self.preflight_case('aliased-pipe-endpoint',Changed)
        self.assertEqual(code,1)
        self.assertIn('Five distinct nonnegative descriptors required',data['error'])
        self.assertEqual(len(data['closed_descriptors']),4)

    def test_preflight_closed_stdin_refused(self):
        class Changed(subprocess.Popen):
            def _get_handles(self,*args):
                h=list(super()._get_handles(*args));os.close(h[0]);return h
        code,data=self.preflight_case('closed-stdin',Changed)
        self.assertEqual(code,1)
        self.assertFalse(data['passed'])
        self.assertTrue(data['cleanup_errors'])

    def test_preflight_live_descriptor_inventory_recorded(self):
        code,data=self.preflight_case('live-descriptor-inventory')
        self.assertEqual(code,0)
        self.assertEqual(len(set(data['validated_descriptors'])),5)
        self.assertEqual(set(data['validated_descriptors']),set(data['closed_descriptors']))
        self.assertTrue(data['stdin_matches_cached_devnull'])


class R7Additional(unittest.TestCase):
    def case(self, label, replacement=None, alias=False, actual=False):
        allocated=[]; io_calls=[]; stats=[]; closed_by_review=[]
        class Changed(subprocess.Popen):
            def _get_handles(self,*args):
                h=list(super()._get_handles(*args))
                allocated.extend([h[0],*h[2:]])
                if alias:
                    os.close(h[4]);os.close(h[5]);h[4:6]=h[2:4]
                elif not actual:
                    os.close(h[5]);h[5]=replacement
                return h
        real_os=preflight.os
        def observed_fstat(fd):
            stats.append(fd);return os.fstat(fd)
        def observed_io(name,*args):
            io_calls.append({'operation':name,'fd':args[0],'prior_fstats':list(stats)})
            if not actual:raise AssertionError('Blocking IO reached before layout refusal')
            return getattr(os,name)(*args)
        os_proxy=types.SimpleNamespace(**vars(os))
        os_proxy.fstat=observed_fstat
        os_proxy.read=lambda *a:observed_io('read',*a)
        os_proxy.write=lambda *a:observed_io('write',*a)
        proxy=types.SimpleNamespace(Popen=Changed,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE,__file__=subprocess.__file__)
        captured=io.StringIO(); code=None; escaped=None; data=None; live=[]
        evidence_dir=OWN/'evidence'
        before=set(evidence_dir.iterdir()) if evidence_dir.exists() else set()
        try:
            with mock.patch.object(preflight,'subprocess',proxy),mock.patch.object(preflight,'os',os_proxy),contextlib.redirect_stdout(captured):
                try:code=preflight.main()
                except BaseException as error:escaped={'type':type(error).__name__,'repr':repr(error)}
            if captured.getvalue():data=json.loads(captured.getvalue())
            for fd in allocated:
                try:os.fstat(fd);live.append(fd)
                except OSError as error:
                    if error.errno!=errno.EBADF:raise
        finally:
            for fd in allocated:
                try:os.close(fd);closed_by_review.append(fd)
                except OSError as error:
                    if error.errno!=errno.EBADF:raise
        for fd in allocated:
            with self.assertRaises(OSError) as caught:os.fstat(fd)
            self.assertEqual(caught.exception.errno,errno.EBADF)
        created=sorted(str(p) for p in set(evidence_dir.iterdir())-before)
        receipt={'label':label,'review_injection':True,'actual_python_invalid_layout_claimed':False,
                 'candidate_source_unchanged':True,'returncode':code,'escaped':escaped,'report':data,
                 'allocated':allocated,'live_after_candidate':live,'closed_by_review':closed_by_review,
                 'all_owned_descriptors_closed':True,'io_calls':io_calls,'fstats':stats,
                 'timer_disarmed':signal.getitimer(signal.ITIMER_REAL)==(0.0,0.0),
                 'created_directories':created,'candidate_receipts':[str(Path(p)/'result.json') for p in created if (Path(p)/'result.json').exists()],
                 'stdout':captured.getvalue()}
        (EVIDENCE/('additional-'+label+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
        self.assertTrue(receipt['timer_disarmed'])
        self.assertIsNone(guard._stdin_scope.get())
        self.assertIs(preflight.os,real_os)
        return receipt

    def test_alias_refuses_before_blocking_io(self):
        r=self.case('alias-before-io',alias=True)
        self.assertEqual(r['returncode'],1)
        self.assertEqual(r['io_calls'],[])
        self.assertEqual(r['live_after_candidate'],[])
        self.assertEqual(len(r['report']['closed_descriptors']),3)

    def test_negative_descriptor_refusal_closes_and_reports(self):
        r=self.case('negative-descriptor',replacement=-2)
        self.assertEqual(r['returncode'],1)
        self.assertEqual(r['io_calls'],[])
        self.assertEqual(r['live_after_candidate'],[])
        self.assertEqual(len(r['report']['closed_descriptors']),4)

    def test_none_descriptor_refusal_closes_and_reports(self):
        r=self.case('none-descriptor',replacement=None)
        self.assertEqual(r['io_calls'],[])
        self.assertEqual(r['live_after_candidate'],[], 'Refusal left allocated descriptors open; escaped='+str(r['escaped']))
        self.assertEqual(r['returncode'],1)
        self.assertEqual(len(r['candidate_receipts']),1)

    def test_string_descriptor_refusal_closes_and_reports(self):
        r=self.case('string-descriptor',replacement='invalid-descriptor')
        self.assertEqual(r['io_calls'],[])
        self.assertEqual(r['live_after_candidate'],[], 'Refusal left allocated descriptors open; escaped='+str(r['escaped']))
        self.assertEqual(r['returncode'],1)
        self.assertEqual(len(r['candidate_receipts']),1)

    def test_actual_all_live_checks_precede_io(self):
        r=self.case('actual-fstat-before-io',actual=True)
        self.assertEqual(r['returncode'],0)
        self.assertEqual(r['io_calls'][0]['prior_fstats'],r['report']['validated_descriptors'])
        self.assertEqual(r['live_after_candidate'],[])

suite=unittest.TestSuite()
suite.addTest(ReviewControls('test_guards_and_fixture_global_ownership'))
suite.addTest(ReviewControls('test_sparse_roster_and_candidate_hashes'))
for name in ['test_review_missing_eof_exceeds_cleanup_bound','test_review_reap_failure_followup_reproduced']:suite.addTest(old.Extra(name))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(new.fakes.Controls))
for name in sorted(n for n in new.Extra.__dict__ if n.startswith('test_review_')):suite.addTest(Successor(name))
for name in sorted(n for n in Extra.__dict__ if n.startswith('test_')):suite.addTest(Extra(name))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Projection))
suite.addTest(ReviewControls('test_successor_missing_source_and_wrong_seal'))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(stdin_tests.Controls))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(scope_tests.ScopeControls))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Independent))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(R7Additional))
definitions(OWN/'focused_controls.py',globals(),{'RefusalCleanup'},imports=False)
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(RefusalCleanup))
expected=suite.countTestCases()
result=unittest.TextTestRunner(verbosity=2).run(suite)
(EVIDENCE/'result.json').write_text(json.dumps({'tests':result.testsRun,'expected':expected,'successful':result.wasSuccessful(),'failures':[(str(t),e)for t,e in result.failures],'errors':[(str(t),e)for t,e in result.errors],'independent_observations':observations,'scope_observations':scope_tests.observations,'real_inner_children':0,'actual_original36_run':False,'fake36_plumbing_not_counted':True},indent=2)+'\n')
sys.exit(0 if result.wasSuccessful() else 1)
