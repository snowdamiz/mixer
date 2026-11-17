
"""Pure owned small-tree controls; never accepts a real toolchain path."""
import ast
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import signal
import stat
import sys
import tempfile
import time
import types
import unittest
import unittest.mock

HERE = Path(__file__).resolve().parent
MODULE = runpy.run_path(str(HERE / 'swift-tree-profile.py'), run_name='inert_profile_controls')
G = MODULE['profile_once'].__globals__
ROOT = Path(os.environ['R5144_SOURCE_ROOT']).resolve()
OUTPUT = Path(os.environ['R5144_CONTROL_OUTPUT']).resolve()
OUTPUT.mkdir(exist_ok=False)
OWNER = ROOT / 'cli/Sources/MixerBuild/Resources/android-build.py'
SOURCE = OWNER.read_bytes()

class Controls(unittest.TestCase):
    def test_small_production_reference_and_alias_reads(self):
        with tempfile.TemporaryDirectory(dir=OUTPUT) as tmp:
            base = Path(tmp)
            tree = base / 'tree'
            tree.mkdir()
            (tree / 'a').write_bytes(b'abc')
            os.link(tree / 'a', tree / 'alias')
            (tree / 'sub').mkdir()
            (tree / 'sub/b').write_bytes(b'x' * (1048576 + 7))
            (tree / 'slink').symlink_to('a')
            (tree / 'linked').symlink_to('sub', target_is_directory=True)
            nodes = [n for n in ast.parse(SOURCE).body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in ('InspectionDigests','tree')]
            selected = ast.Module(body=nodes,type_ignores=[])
            original = ast.dump(selected,include_attributes=False)
            self.assertEqual(hashlib.sha256(original.encode()).hexdigest(), '1a86c774df593c8391c2007df6e1d4a021e4784bff00f5d103c0e72ed7af2d25')
            namespace = dict(os=os,hashlib=hashlib,pathlib=__import__('pathlib'),stat=stat)
            exec(compile(selected,'actual-selected-production-owner','exec'),namespace)
            expected = namespace['tree'](tree,namespace['InspectionDigests']())
            out = base / 'profile'
            out.mkdir()
            with contextlib.redirect_stdout(io.StringIO()):
                G['profile_once'](OWNER,tree,out,reference=expected)
            metrics = json.loads((out / 'metrics.json').read_text())
            decision = json.loads((out / 'decision.json').read_text())
            self.assertTrue(decision['removing_timing_restores_exact_original_ast'])
            self.assertEqual(metrics['digest'],expected)
            counts = metrics['source_counters']
            self.assertEqual(counts['read_bytes'],1048576 + 10)
            self.assertEqual(counts['read_calls'],5)
            self.assertEqual(counts['file_open_calls'],4)
            self.assertEqual(counts['cache_hits'],2)
            self.assertEqual(metrics['inventory']['unique_inodes'],2)
            self.assertEqual(counts['entries_completed'],5)
            # Identity and FIFO refusal are actual selected production code.
            d=namespace['InspectionDigests']()
            d(tree/'a')
            (tree/'a').write_bytes(b'changed')
            with self.assertRaisesRegex(RuntimeError,'changed during inspection'):
                d(tree/'alias')
            fifo=base/'fifo'
            os.mkfifo(fifo)
            with self.assertRaisesRegex(RuntimeError,'Unsupported installed tool file'):
                d(fifo)
            write={k:metrics[k] for k in ('source_counters','inventory','digest')}
            (OUTPUT/'small-tree-evidence.json').write_text(json.dumps(write,indent=2)+'\n')

    def test_sampler_lifetime_and_restoration(self):
        old_mask=signal.pthread_sigmask(signal.SIG_BLOCK,set())
        calls=[]
        with self.assertRaisesRegex(ValueError,'inert unwind'):
            with G['AlarmSampler'](lambda *_: calls.append(1)):
                time.sleep(0.28)
                raise ValueError('inert unwind')
        self.assertGreaterEqual(len(calls),1)
        self.assertEqual(signal.getsignal(signal.SIGALRM),signal.SIG_DFL)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.0,0.0))
        self.assertEqual(signal.pthread_sigmask(signal.SIG_BLOCK,set()),old_mask)
        with self.assertRaisesRegex(ValueError,'timer unwind'):
            G['observe']('control-unwind',lambda: (_ for _ in ()).throw(ValueError('timer unwind')))
        self.assertEqual(G['TIMES']['control-unwind']['calls'],1)
        self.assertIsNone(sys.getprofile())

    def test_foreign_handler_and_timer_refused_without_replacement(self):
        def foreign(*_): pass
        signal.signal(signal.SIGALRM,foreign)
        try:
            with self.assertRaisesRegex(RuntimeError,'Foreign SIGALRM'):
                with G['AlarmSampler'](lambda *_: None): pass
            self.assertIs(signal.getsignal(signal.SIGALRM),foreign)
        finally:
            signal.signal(signal.SIGALRM,signal.SIG_DFL)
        signal.setitimer(signal.ITIMER_REAL,30)
        try:
            with self.assertRaisesRegex(RuntimeError,'Foreign timer'):
                with G['AlarmSampler'](lambda *_: None): pass
            self.assertGreater(signal.getitimer(signal.ITIMER_REAL)[0],20)
        finally:
            signal.setitimer(signal.ITIMER_REAL,0)


    def test_profile_cli_deadline_unwind_restores_handler(self):
        target=OUTPUT/'inert-deadline'
        target.mkdir()
        original=G['profile_once']
        def inert(*_):
            self.assertNotEqual(signal.getsignal(signal.SIGTERM),signal.SIG_DFL)
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM,None)
        G['profile_once']=inert
        try:
            with self.assertRaisesRegex(TimeoutError,'180-second'):
                G['cli'](['_profile','--owner',str(OWNER),'--tree',str(target),'--output',str(target)])
        finally:
            G['profile_once']=original
        self.assertEqual(signal.getsignal(signal.SIGTERM),signal.SIG_DFL)

    def test_cli_and_mismatch_before_work(self):
        invalid = OUTPUT/'invalid-args'
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                G['cli'](['launch','--admission','invented','--output',str(invalid)])
        self.assertFalse(invalid.exists())
        mismatch=OUTPUT/'mismatch'
        before=G['check_inputs']
        def forbidden(): raise AssertionError('Source/tree/download work reached')
        G['check_inputs']=forbidden
        try:
            with self.assertRaisesRegex(RuntimeError,'Runner mismatch'):
                G['cli'](['launch','--admission','exact-original-image','--output',str(mismatch)])
        finally:
            G['check_inputs']=before
        self.assertEqual({p.name for p in mismatch.iterdir()},{'runner-admission.json'})
        env=dict(GITHUB_ACTIONS='true',RUNNER_OS='macOS',RUNNER_ARCH='X64',ImageOS='macos26',ImageVersion='20261117.changed')
        strict=G['admission']('exact-original-image',env,'Darwin','x86_64','3.14.8')
        current=G['admission']('same-class-current-image',env,'Darwin','x86_64','3.14.8')
        self.assertFalse(strict['admitted'])
        self.assertTrue(current['admitted'])
        self.assertFalse(current['exact_image_match'])
        self.assertFalse(current['exact_python_match'])
        self.assertFalse(G['admission']('same-class-current-image',env,'Darwin','arm64','3.14.8')['admitted'])


    def _publication_failure(self, primary, publication, stage):
        # Execute the complete helper main logic, including its exact handler.
        # Only external profiler/artifact collaborators and the fault site vary.
        with tempfile.TemporaryDirectory(dir=OUTPUT) as tmp:
            base = Path(tmp)
            tree = base / 'tree'
            tree.mkdir()
            (tree / 'a').write_bytes(b'abc')
            target = base / 'profile'
            target.mkdir()
            events = []
            origin = []
            class Profiler:
                def enable(self): events.append('enable')
                def disable(self): events.append('disable')
                def dump_stats(self, path):
                    events.append('dump')
                    if stage == 'dump': raise publication
            def stats(_):
                if stage == 'stats': raise publication
                return types.SimpleNamespace(stats={})
            original_walk = G['observed_walk']
            def walk(*args, **kwargs):
                if primary is not None:
                    try:
                        raise primary
                    except BaseException as error:
                        origin.append(error.__traceback__)
                        raise
                return original_walk(*args, **kwargs)
            original_save = G['profile_save']
            def publish(name, value):
                if name == stage: raise publication
                return original_save(name, value)
            replacements = dict(cProfile=types.SimpleNamespace(Profile=Profiler),
                pstats=types.SimpleNamespace(Stats=stats),
                observed_walk=walk, profile_save=publish)
            captured = None
            output = io.StringIO()
            with unittest.mock.patch.dict(G, replacements), contextlib.redirect_stdout(output):
                try:
                    G['profile_once'](OWNER, tree, target, reference='unused-on-failure')
                except BaseException as error:
                    captured = error
            self.assertEqual(events[:2], ['enable', 'disable'])
            self.assertEqual(signal.getsignal(signal.SIGALRM), signal.SIG_DFL)
            self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))
            self.assertIsNone(sys.getprofile())
            self.assertEqual(output.getvalue(), '')
            return captured, origin

    def test_primary_inspection_error_survives_publication_failures(self):
        for primary_type in (ValueError, TimeoutError):
            for publication in (OSError(28, 'private ENOSPC detail'), PermissionError(13, 'private permission detail')):
                for stage in ('dump', 'stats', 'profile-functions.json', 'samples.json', 'metrics.json'):
                    with self.subTest(primary=primary_type.__name__, errno=publication.errno, stage=stage):
                        primary = primary_type('original inspection sentinel')
                        caught, origin = self._publication_failure(primary, publication, stage)
                        self.assertIs(caught, primary)
                        self.assertIs(type(caught), primary_type)
                        frames = []
                        current = caught.__traceback__
                        while current is not None:
                            frames.append(current)
                            current = current.tb_next
                        self.assertIn(origin[0], frames)
                        self.assertNotIn('dump_stats', [f.tb_frame.f_code.co_name for f in frames])
                        self.assertEqual(len(caught.__notes__), 1)
                        note = caught.__notes__[0]
                        self.assertIn('type=' + type(publication).__name__, note)
                        self.assertIn('errno=' + str(publication.errno), note)
                        self.assertLessEqual(len(note), 160)
                        self.assertNotIn('private', note)
                        self.assertNotIn('detail', note)

    def test_success_path_publication_failure_remains_fatal(self):
        for publication in (OSError(28, 'ENOSPC'), PermissionError(13, 'permission')):
            for stage in ('dump', 'stats', 'profile-functions.json', 'samples.json', 'metrics.json'):
                with self.subTest(errno=publication.errno, stage=stage):
                    caught, origin = self._publication_failure(None, publication, stage)
                    self.assertIs(caught, publication)
                    self.assertEqual(origin, [])
                    self.assertFalse(hasattr(caught, '__notes__'))

    def test_primary_traceback_notes_survive_secondary_baseexception(self):
        primary = ValueError('primary sentinel with prior note')
        primary.add_note('existing primary note')
        caught, origin = self._publication_failure(primary, KeyboardInterrupt('private detail'), 'dump')
        self.assertIs(caught, primary)
        self.assertEqual(caught.__notes__[0], 'existing primary note')
        self.assertEqual(caught.__notes__[1], 'Profile artifact publication failed separately: type=KeyboardInterrupt; errno=None')
        self.assertIsNotNone(origin[0])

if __name__ == '__main__':
    unittest.main(verbosity=2)
