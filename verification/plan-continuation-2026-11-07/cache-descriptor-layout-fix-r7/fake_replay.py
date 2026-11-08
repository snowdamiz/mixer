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
EVIDENCE=OWN/sys.argv[1]
EVIDENCE.mkdir()

def audit(event,args):
    if event in {'subprocess.Popen','os.system','os.fork','os.forkpty','os.posix_spawn','os.kill','os.killpg','os.exec','os.spawn'} or event.startswith('socket.'):
        raise RuntimeError('Forbidden inner OS process/network call: '+event)
    paths=[]
    if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)) and args[2] & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):paths=args[:1]
    elif event in {'os.mkdir','os.remove','os.rmdir','os.chmod'}:paths=args[:1]
    elif event in {'os.rename','os.link','os.symlink'}:paths=args[:2]
    for p in paths:
        if not Path(os.fsdecode(p)).resolve().is_relative_to(OWN):raise RuntimeError('Mutation outside assigned review: '+str(p))
sys.addaudithook(audit)

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

suite=unittest.TestSuite()
suite.addTest(ReviewControls('test_guards_and_fixture_global_ownership'))
suite.addTest(ReviewControls('test_sparse_roster_and_candidate_hashes'))
for name in ['test_review_missing_eof_exceeds_cleanup_bound','test_review_reap_failure_followup_reproduced']:suite.addTest(old.Extra(name))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(new.fakes.Controls))
for name in sorted(n for n in new.Extra.__dict__ if n.startswith('test_review_')):suite.addTest(Successor(name))
for name in sorted(n for n in Extra.__dict__ if n.startswith('test_')):suite.addTest(Extra(name))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Projection))
suite.addTest(ReviewControls('test_successor_missing_source_and_wrong_seal'))
result=unittest.TextTestRunner(verbosity=2,failfast=True).run(suite)
(EVIDENCE/'result.json').write_text(json.dumps({'tests':result.testsRun,'successful':result.wasSuccessful(),'failures':[(str(t),e) for t,e in result.failures],'errors':[(str(t),e) for t,e in result.errors],'mode':MODE,'scope':'Exact candidate fake APIs and projected CLI/main with fake 36-method suite; old positive defect controls separate.'},indent=2)+'\n')
sys.exit(0 if result.wasSuccessful() else 1)
