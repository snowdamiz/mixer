"""One combined pure/fake suite; no inner operating-system child or network calls."""
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

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MODE = 'optimized' if sys.flags.optimize else 'normal'
EVIDENCE = HERE / MODE
EVIDENCE.mkdir()

def audit(event, args):
    if event in {'subprocess.Popen','os.system','os.fork','os.forkpty','os.posix_spawn','os.kill','os.killpg','os.exec','os.spawn'} or event.startswith('socket.'):
        raise RuntimeError('Forbidden inner OS process/network call: '+event)
    paths = []
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)) and args[2] & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND): paths=args[:1]
    elif event in {'os.mkdir','os.remove','os.rmdir','os.chmod'}: paths=args[:1]
    elif event in {'os.rename','os.link','os.symlink'}: paths=args[:2]
    for p in paths:
        if not Path(os.fsdecode(p)).resolve().is_relative_to(HERE): raise RuntimeError('Mutation outside R3: '+str(p))
sys.addaudithook(audit)

def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def review(label,candidate):
    source=(HERE.parent/'cache-custody-review-r2/review_fakes.py').read_text()
    source=source[:source.index('suite=unittest.defaultTestLoader')]
    source=source.replace("HERE = Path(__file__).resolve().parent", "HERE = REVIEW_ROOT")
    source=source.replace("CAND = HERE.parent / 'cache-custody-premise-r2'", "CAND = CANDIDATE")
    source=source.replace("EVIDENCE = HERE / MODE", "EVIDENCE = HERE / MODE / LABEL")
    source=source.replace('sys.addaudithook(audit)', '# R3 audit already installed', 1)
    m=types.ModuleType(label);m.__file__=str(HERE.parent/'cache-custody-review-r2/review_fakes.py')
    m.REVIEW_ROOT=HERE;m.CANDIDATE=candidate;m.LABEL=label
    with mock.patch.dict(sys.modules,{'adopt_fixture':load(label+'_adoption',candidate/'adopt_fixture.py')}):
        exec(compile(source,m.__file__,'exec'),m.__dict__)
    return m

old=review('old-r2',HERE.parent/'cache-custody-premise-r2')
new=review('successor-r3',HERE)

class Successor(new.Extra):
    def test_review_missing_eof_exceeds_cleanup_bound(self):
        w=new.fakes.World('success');r,c=self.context('review-no-eof-bound',w)
        def select(seconds):
            w.clock+=.5
            if w.clock>20: raise new.DrainSentinel('review sentinel at fake 20 seconds')
            return []
        w.select=select
        with self.assertRaisesRegex(TimeoutError,'Finite custody'): c.run('no-eof',['fake'],c.out)
        row=c.receipt['commands'][-1]
        self.assertTrue(row['timed_out'] and row['child_returned'] and row['owned_group_gone'])
        self.assertTrue(c.unknown_custody and row['custody_hold'])
        self.assertFalse(row['stdout_eof'] or row['stderr_eof'])
        self.assertLess(w.clock,12)
        before=list(w.events)
        for fn in [lambda:c.run('forbidden',['fake'],c.out),lambda:c.stop(w,row),lambda:c.gone(w.pid),lambda:c.observe(w.poll)]:
            with self.assertRaises(RuntimeError):fn()
        self.assertEqual(before,w.events)
        self.retain('review-no-eof-bound',w,c)

    def test_review_reap_failure_followup_reproduced(self):
        w=new.fakes.World('success');r,c=self.context('review-reap-failure',w)
        error=ChildProcessError(10,'synthetic lost direct child ownership')
        def poll():w.events.append('REAP-ERROR');raise error
        w.poll=poll
        with self.assertRaises(ChildProcessError) as caught:c.run('reap-error',['fake'],c.out)
        self.assertIs(caught.exception,error)
        self.assertEqual(w.events,['spawn','REAP-ERROR'])
        self.assertTrue(c.unknown_custody)
        self.retain('review-reap-failure',w,c)

class Extra(new.fakes.Controls):
    def test_observation_failures_are_sticky(self):
        for operation in ['poll','wait','group']:
            for exception in [OSError(5,'observation IO failure'),ValueError('observation failure'),PermissionError(1,'denial')]:
                name=operation+'-'+type(exception).__name__
                w=new.fakes.World('success');r,c=self.context(name,w)
                def fail(*args,**kw):w.events.append('OBSERVATION-ERROR');raise exception
                if operation=='group':r.os.killpg=fail
                else:setattr(w,operation,fail)
                with self.assertRaises(type(exception)) as caught:c.run(name,['fake'],c.out)
                self.assertIs(caught.exception,exception)
                self.assertEqual(w.events[w.events.index('OBSERVATION-ERROR')+1:],[])
                row=c.receipt['commands'][-1]
                self.assertTrue(c.unknown_custody and row['custody_hold'])
                self.assertIsNone(row['child_resource_usage']['aggregate_delta'])
                before=list(w.events)
                with self.assertRaises(RuntimeError):c.run('forbidden',['fake'],c.out)
                self.assertEqual(w.events,before)
                self.retain(name,w,c)

    def test_ordinary_permission_read_error_still_cleans(self):
        w=new.fakes.World('success');r,c=self.context('ordinary-read-error',w)
        error=PermissionError(13,'ordinary read denied')
        def read(*a):raise error
        r.os.read=read
        with self.assertRaises(PermissionError) as caught:c.run('read-error',['fake'],c.out)
        self.assertIs(caught.exception,error)
        self.assertIn('group:0',w.events)
        row=c.receipt['commands'][-1]
        self.assertTrue(row['child_returned'] and row['owned_group_gone'])
        self.assertFalse(row['stdout_eof'] or row['stderr_eof'])
        self.assertTrue(row['custody_hold'] and c.unknown_custody)
        self.retain('ordinary-read-error',w,c)

    def test_preserved_inventory_and_body_bytes(self):
        new.adoption.verify()
        import local_support
        a=local_support.original_source().decode()
        b=(new.adoption.OLD/'runner-controls.py').read_text()
        def bodies(s):
            cls=next(n for n in ast.parse(s).body if isinstance(n,ast.ClassDef) and n.name=='RunnerControls')
            return {n.name:ast.get_source_segment(s,n) for n in cls.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
        self.assertEqual(bodies(a),bodies(b));self.assertEqual(len(bodies(b)),36)
        pack=ROOT/'verification/swift-cache-state-ci/pack'
        methods=json.loads((pack/'inventories/methods.json').read_bytes())
        counts={k:len(methods[k]) for k in ['host','producer','independent','controls']}
        self.assertEqual(counts,dict(host=84,producer=108,independent=98,controls=94))
        cases=json.loads((pack/'inventories/file-cases.json').read_bytes())
        self.assertEqual(len(cases['cases'])*4,124)
        budget=json.loads((ROOT/'verification/cache-fixture-shared-input-candidate-v2/command-budget.json').read_bytes())
        self.assertEqual(budget['fixture_child_commands'],103)
        (EVIDENCE/'identity.json').write_text(json.dumps({'methods':counts,'both_modes':768,'captures':124,'commands':103,'original_body_sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in bodies(b).items()},'deadline_helper_sha256':hashlib.sha256((new.adoption.OLD/'deadline_control.py').read_bytes()).hexdigest()},indent=2))

class Projection(unittest.TestCase):
    @contextlib.contextmanager
    def isolated(self,project,candidate):
        removed={k:v for k,v in list(sys.modules.items()) if str(getattr(v,'__file__','')).startswith(str(ROOT))}
        for k in removed:sys.modules.pop(k,None)
        paths=list(sys.path);temp=tempfile.tempdir
        sys.path.insert(0,str(candidate))
        adapter=load('projection_adapter',candidate/'adopt_fixture.py')
        sys.modules['adopt_fixture']=adapter
        try:yield adapter
        finally:
            for k,v in list(sys.modules.items()):
                if str(getattr(v,'__file__','')).startswith(str(ROOT)):sys.modules.pop(k,None)
            sys.modules.update(removed);sys.path[:]=paths;tempfile.tempdir=temp

    def make(self,label,candidate,controller):
        project=EVIDENCE/label;project.mkdir()
        selected=json.loads((HERE/'projection-paths.json').read_bytes())
        for rel in selected:
            if rel.endswith('native-custody-premise/cleanup_control.py') and not controller:continue
            dest=project/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,dest)
        dest=project/candidate.relative_to(ROOT);dest.mkdir(parents=True,exist_ok=True)
        seal=json.loads((candidate/'sources.json').read_bytes())
        for rel in [r['path'] for r in seal['members']]+['sources.json']:
            target=dest/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(candidate/rel,target)
        workflow=(ROOT/'.github/workflows/verify.yml').read_text()
        oldjob=(HERE/'previous-job.yml').read_text()
        self.assertEqual(workflow.count(oldjob),1)
        (project/'.github/workflows/verify.yml').write_text(workflow.replace(oldjob,(candidate/'workflow-job.yml').read_text(),1))
        return project,dest

    def entry(self,adapter,candidate,old_expected=False,setup_error=False):
        entry=load('projected_original_entry',candidate/'test_original.py')
        adapter.previous()
        import local_support
        initial=local_support.HERE
        initial_path=list(sys.path)
        hooks=[];observed=[]
        def fake_suite(module):
            self.assertEqual(local_support.HERE,candidate)
            self.assertEqual(Path(module.r.Commands.run.__code__.co_filename),candidate/'commands.py')
            self.assertEqual(len([n for n in dir(module.RunnerControls) if n.startswith('test_')]),36)
            observed.append(module.__file__)
            return unittest.TestSuite([unittest.FunctionTestCase(lambda:None) for _ in range(36)])
        with mock.patch.object(sys,'argv',[str(candidate/'test_original.py'),'-v']), mock.patch.object(sys,'addaudithook',side_effect=hooks.append),mock.patch.object(unittest.defaultTestLoader,'loadTestsFromModule',side_effect=fake_suite):
            if setup_error:
                with mock.patch.object(local_support,'workspace',side_effect=ValueError('setup fault')):
                    with self.assertRaisesRegex(ValueError,'setup fault'):entry.main()
            elif old_expected:
                with self.assertRaisesRegex(RuntimeError,'Exact correction shipping roster required'):entry.main()
            else:self.assertEqual(entry.main(),0)
        if old_expected:
            self.assertEqual(local_support.HERE,candidate)
            local_support.HERE=initial;sys.path[:]=initial_path
        else:
            self.assertEqual(local_support.HERE,initial)
            self.assertEqual(sys.path,initial_path)
            self.assertTrue(adapter.verify(True)['installed'])
        self.assertTrue(hooks)
        if not setup_error:self.assertEqual(len(observed),1)
        return {'original_suite_faked':True,'fake_methods':0 if setup_error else 36,'real_workspace':not setup_error,'HERE_restored':not old_expected,'final_verifier_passed':not old_expected,'audit_registration_intercepted':True,'outer_write_process_network_guard_active':True}

    def test_sparse_preflight_and_original_entrypoint(self):
        p,c=self.make('old-sparse',HERE.parent/'cache-custody-premise-r2',False)
        with self.isolated(p,c) as adapter:
            with mock.patch.object(sys,'argv',[str(c/'adopt_fixture.py'),'verify','--workflow-installed']):
                with self.assertRaisesRegex(RuntimeError,'Regular source required: .*native-custody-premise/cleanup_control.py'):adapter.main()
        controller='verification/plan-continuation-2026-11-07/native-custody-premise/cleanup_control.py'
        (p/controller).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/controller,p/controller)
        with self.isolated(p,c) as adapter:
            self.assertTrue(adapter.verify(True)['installed'])
            old_result=self.entry(adapter,c,old_expected=True)
        p,c=self.make('new-sparse',HERE,True)
        with self.isolated(p,c) as adapter:
            with mock.patch.object(sys,'argv',[str(c/'adopt_fixture.py'),'verify','--workflow-installed']),contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(adapter.main(),0)
            preflight=json.loads(output.getvalue())
            result=self.entry(adapter,c)
            setup=self.entry(adapter,c,setup_error=True)
        (EVIDENCE/'sparse-entrypoints.json').write_text(json.dumps({'old_missing_input_reproduced':True,'old_finalverify_wrongseal_reproduced':old_result,'successor':result,'setup_failure':setup,'preflight':preflight,'projection_tracked_files':len(json.loads((HERE/'projection-paths.json').read_bytes())),'no_OS_processes':True},indent=2))

suite=unittest.TestSuite()
for name in ['test_review_missing_eof_exceeds_cleanup_bound','test_review_reap_failure_followup_reproduced']:suite.addTest(old.Extra(name))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(new.fakes.Controls))
for name in sorted(n for n in new.Extra.__dict__ if n.startswith('test_review_')):suite.addTest(Successor(name))
for name in sorted(n for n in Extra.__dict__ if n.startswith('test_')):suite.addTest(Extra(name))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Projection))
result=unittest.TextTestRunner(verbosity=2).run(suite)
(EVIDENCE/'result.json').write_text(json.dumps({'tests':result.testsRun,'successful':result.wasSuccessful(),'failures':[(str(t),e) for t,e in result.failures],'errors':[(str(t),e) for t,e in result.errors],'mode':MODE,'scope':'Old failures positively reproduced; successor pure/fake checks. No original real-process suite or real descendant.'},indent=2)+'\n')
sys.exit(0 if result.wasSuccessful() else 1)
