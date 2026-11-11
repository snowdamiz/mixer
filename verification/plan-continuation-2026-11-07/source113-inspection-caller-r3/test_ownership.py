"""Exact producer tests plus independent fake-only wrapper controls in owned copies."""
from pathlib import Path
import sys
import importlib.util
import json
import hashlib
import unittest
import os
from contextlib import ExitStack
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
MODE = 'optimized' if sys.flags.optimize else 'normal'
HERE = ROOT / 'verification/plan-continuation-2026-11-07/source113-inspection-caller-r3'
sys.argv = [sys.argv[0]]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

# The exact shipping suite installs its independent process/socket/write guard
# before importing the actual adapter. Every write stays in our owned projection.
t = load('shipping_binding_tests', HERE / 'test_binding.py')
a = t.a
patched = t.patched
(HERE / 'control-scratch').mkdir(exist_ok=True)

class Independent(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.temp = tempfile.TemporaryDirectory(dir=HERE / 'control-scratch')
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.workflow = self.work / 'verify.yml'
        self.workflow.write_bytes((HERE / 'verify.yml.candidate').read_bytes())
        self.base = a.bind()
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patched(a, 'WORKFLOW', self.workflow))
        self.stack.enter_context(patched(os, 'environ', {'RUSTUP_AUTO_INSTALL':'0','GITHUB_SHA':'a'*40}))
        self.calls = []

    def actual_adapter(self, effect):
        runner, ordinary, proof = self.base.load_runner()
        fresh = runner.fresh_output
        # Only place output under this owned control directory; retain the actual
        # freshness/symlink/ownership implementation, with a synthetic repo root.
        self.stack.enter_context(patched(runner, 'fresh_output', lambda p: fresh(p, self.work / 'synthetic-repo')))
        def execute(out, rustc):
            self.calls.append(('execute', str(out), rustc))
            return effect(out)
        self.stack.enter_context(patched(runner, 'execute', execute))
        self.stack.enter_context(patched(self.base, 'load_runner', lambda: (runner, ordinary, proof)))
        return runner

    def test_actual_admission_rejects_bad_environment_without_execute(self):
        self.actual_adapter(lambda out: 0)
        out = self.work / 'absent'
        with patched(os, 'environ', {'RUSTUP_AUTO_INSTALL':'1','GITHUB_SHA':'a'*40}):
            self.assertEqual(a.run_fixture(self.base, out, '/fake/rustc'), 1)
        self.assertEqual(self.calls, [])
        self.assertFalse(out.exists())

    def test_actual_admission_rejects_bad_revision_without_execute(self):
        self.actual_adapter(lambda out: 0)
        out = self.work / 'absent'
        with patched(os, 'environ', {'RUSTUP_AUTO_INSTALL':'0','GITHUB_SHA':'not-a-revision'}):
            self.assertEqual(a.run_fixture(self.base, out, '/fake/rustc'), 1)
        self.assertEqual(self.calls, [])
        self.assertFalse(out.exists())

    def test_refused_existing_output_is_not_adopted_or_modified(self):
        self.actual_adapter(lambda out: 0)
        out = self.work / 'existing'; out.mkdir()
        (out / 'foreign.txt').write_text('preserve')
        self.assertEqual(a.run_fixture(self.base, out, '/fake/rustc'), 1)
        self.assertEqual(self.calls, [])
        self.assertEqual(sorted(p.name for p in out.iterdir()), ['foreign.txt'])

    def test_refused_symlink_parent_does_not_write_through(self):
        self.actual_adapter(lambda out: 0)
        target = self.work / 'target'; target.mkdir()
        out = target / 'existing'; out.mkdir()
        alias = self.work / 'alias'; alias.symlink_to(target, target_is_directory=True)
        self.assertEqual(a.run_fixture(self.base, alias / 'existing', '/fake/rustc'), 1)
        self.assertEqual(self.calls, [])
        self.assertEqual(list(out.iterdir()), [])

    def test_actual_execute_failure_preserves_both_receipts_and_postflight(self):
        self.actual_adapter(lambda out: 7)
        out = self.work / 'fresh'
        self.assertEqual(a.run_fixture(self.base, out, '/fake/rustc'), 1)
        self.assertEqual(len(self.calls), 1)
        original = json.loads((out / 'adapter-result.json').read_text())
        successor = json.loads((out / 'caller-binding-result.json').read_text())
        self.assertEqual(original['fixture_return_status'], 7)
        self.assertTrue(original['source_postflight']['installed_job_verified'])
        self.assertEqual(successor['fixture_return_status'], 1)
        self.assertEqual(successor['errors'], [])

    def test_actual_execute_exception_preserves_original_exception(self):
        def raised(out): raise RuntimeError('independent fake execution exploded')
        self.actual_adapter(raised)
        out = self.work / 'fresh'
        self.assertEqual(a.run_fixture(self.base, out, '/fake/rustc'), 1)
        old = json.loads((out / 'adapter-result.json').read_text())
        self.assertEqual(old['adapter_exception']['message'], 'independent fake execution exploded')
        self.assertTrue(old['source_postflight']['installed_job_verified'])
        self.assertIsNone(old['fixture_return_status'])
        self.assertEqual(len(self.calls), 1)

    def test_actual_execute_success_requires_terminal_validation_and_replay(self):
        def succeeded(out):
            (out / 'receipt.json').write_text(json.dumps({'rustc':{'path':'/fake/rustc','sha256':'f'*64},'status':'synthetic'}))
            return 0
        self.actual_adapter(succeeded)
        events = []
        self.stack.enter_context(patched(self.base, 'validate_terminal', lambda *args: events.append('validate')))
        module_at = self.base.module_at
        def replay_module(name, source):
            if source == a.HISTORICAL / 'terminal_replay.py':
                return SimpleNamespace(replay=lambda *args: events.append('replay') or {'synthetic':True})
            return module_at(name, source)
        self.stack.enter_context(patched(self.base, 'module_at', replay_module))
        out = self.work / 'fresh'
        self.assertEqual(a.run_fixture(self.base, out, '/fake/rustc'), 0)
        self.assertEqual(events, ['validate','replay'])
        self.assertEqual(len(self.calls), 1)
        self.assertFalse(json.loads((out / 'adapter-result.json').read_text())['exact_compiler_qualified'])

    def test_success_status_cannot_hide_postflight_job_drift(self):
        def drift(out):
            self.workflow.write_text(self.workflow.read_text().replace('timeout-minutes: 12','timeout-minutes: 13'))
            return 0
        self.actual_adapter(drift)
        out = self.work / 'fresh'
        self.assertEqual(a.run_fixture(self.base, out, '/fake/rustc'), 1)
        old = json.loads((out / 'adapter-result.json').read_text())
        new = json.loads((out / 'caller-binding-result.json').read_text())
        self.assertTrue(any(e.get('phase') == 'source-postflight' for e in old['errors']))
        self.assertIn('Installed ordinary', new['errors'][0]['message'])

    def test_unrelated_job_change_admitted_but_swift_change_rejected(self):
        self.workflow.write_text(self.workflow.read_text() + '  independent-review-unrelated:\n    runs-on: ubuntu-latest\n')
        self.assertTrue(self.base.verify(True)['installed_job_verified'])
        self.workflow.write_text(self.workflow.read_text().replace('timeout-minutes: 12', 'timeout-minutes: 13'))
        with self.assertRaisesRegex(RuntimeError, 'Installed ordinary'): self.base.verify(True)

    def test_every_shipping_member_missing_refuses_and_restores(self):
        members = json.loads((HERE / 'seal.json').read_text())['members']
        for member in members:
            path = HERE / member['path']; data = path.read_bytes()
            try:
                path.unlink()
                with self.subTest(member=member['path']), self.assertRaises(RuntimeError): self.base.verify(False)
            finally: path.write_bytes(data)

    def test_sparse_and_artifact_closure_has_every_required_file(self):
        job = (HERE / 'swift-job.yml').read_text()
        sparse = job.split('          sparse-checkout: |\n',1)[1].split('      - name:',1)[0]
        entries = [line.strip().lstrip('/') for line in sparse.splitlines()]
        dep = json.loads((a.HISTORICAL / 'dependencies.json').read_text())['members']
        new = json.loads((HERE / 'seal.json').read_text())['members']
        names = [r['path'] for r in dep] + [str((HERE/r['path']).relative_to(ROOT)) for r in new]
        names += [str((HERE/'seal.json').relative_to(ROOT))]
        names += list(json.loads((HERE/'source-inputs.json').read_text()))
        for name in names:
            self.assertTrue(not name.startswith('verification/') or any(name == e or e.endswith('/') and name.startswith(e) for e in entries), name)
        self.assertIn('${{ github.workspace }}/verification/plan-continuation-2026-11-07/source113-inspection-caller-r3/',job)
        self.assertEqual(job.count('adopt_envelope.py" run '),1)
        self.assertEqual(job.count('adopt_envelope.py" verify --workflow-installed'),2)

    def test_patch_applies_as_data_and_full_patch_transports_exact_files(self):
        import re
        def apply(before, patch):
            lines=patch.splitlines(True); source=before.splitlines(True); out=[]; cursor=0; i=2
            while i<len(lines):
                match=re.fullmatch(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@\n',lines[i])
                self.assertIsNotNone(match,lines[i]); i+=1
                start=int(match[1]); oldn=int(match[2] or 1); newn=int(match[4] or 1)
                index=start-1 if oldn else start
                self.assertGreaterEqual(index,cursor); out+=source[cursor:index]; cursor=index
                used=added=0
                while i<len(lines) and not lines[i].startswith('@@ '):
                    line=lines[i]; i+=1
                    if line[0] in ' -': self.assertEqual(source[cursor],line[1:]); cursor+=1; used+=1
                    if line[0] in ' +': out.append(line[1:]); added+=1
                self.assertEqual((used,added),(oldn,newn))
            return ''.join(out+source[cursor:])
        old=(HERE/'current-verify.yml').read_text()
        expected=(HERE/'verify.yml.candidate').read_text()
        # The immutable transport patch predates the later exact job edits.
        for change in reversed(json.loads((HERE/'job-changes.json').read_text())[1:]):
            self.assertEqual(expected.count(change['after']), change['count'])
            expected=expected.replace(change['after'], change['before'])
        self.assertEqual(apply(old,(HERE/'workflow.patch').read_text()),expected)
        patch=''.join(line for line in (HERE/'full.patch').read_text().splitlines(True)
                      if not line.startswith(('diff --git ', 'new file mode ', 'index ')))
        sections=re.split(r'(?m)(?=^--- )',patch)
        sections=[s for s in sections if s]
        # Runtime patches transport only the workflow to avoid self-referential seals.
        # The generator's external full/incremental maps prove the entire closure.
        self.assertEqual(len(sections), 1)
        self.assertEqual(apply(old,sections[0]),expected)

# Embedded in review_tests.py before the two supervised invocations.
class Ownership(unittest.TestCase):
    setUp = Independent.setUp
    actual_adapter = Independent.actual_adapter

    def test_existing_marker_and_traversal_leave_history_untouched(self):
        self.actual_adapter(lambda out: 0)
        for label in ('marker','traversal'):
            with self.subTest(label=label):
                out=self.work/label; out.mkdir()
                marker=out/'output-ownership.json'; marker.write_text('{"purpose":"mixer-fixture-envelope-ci-output","token":"old"}')
                original=marker.read_bytes()
                path=out if label=='marker' else out/'..'/label
                self.assertEqual(a.run_fixture(self.base,path,'/fake/rustc'),1)
                self.assertEqual(sorted(p.name for p in out.iterdir()),['output-ownership.json'])
                self.assertEqual(marker.read_bytes(),original)
        self.assertEqual(self.calls,[])

    def test_preflight_failure_does_not_touch_existing_path(self):
        out=self.work/'existing'; out.mkdir()
        (out/'caller-binding-result.json').write_text('old receipt')
        self.workflow.write_text('invalid workflow')
        with self.assertRaises(RuntimeError): a.run_fixture(self.base,out,'/fake/rustc')
        self.assertEqual((out/'caller-binding-result.json').read_text(),'old receipt')
        self.assertEqual(len(list(out.iterdir())),1)

    def test_fake_directory_creation_is_not_positive_admission(self):
        out=self.work/'fake'
        def fake(path, compiler):
            path.mkdir()
            (path/'adapter-result.json').write_text('original')
            raise RuntimeError('preserved refusal')
        import io
        from contextlib import redirect_stderr
        stream=io.StringIO()
        with patched(self.base,'run_fixture',fake),redirect_stderr(stream):
            self.assertEqual(a.run_fixture(self.base,out,'/fake/rustc'),1)
        self.assertEqual(sorted(p.name for p in out.iterdir()),['adapter-result.json'])
        self.assertIn('preserved refusal',stream.getvalue())
        self.assertIn('No positive fresh output admission',stream.getvalue())

    def test_identity_marker_or_ancestry_replacement_skips_auxiliary_evidence(self):
        for mutation in ('directory','marker','ancestor','symlink'):
            with self.subTest(mutation=mutation):
                parent=self.work/mutation; parent.mkdir()
                out=parent/'fresh'
                runner,ordinary,proof=self.base.load_runner()
                original_fresh=runner.fresh_output
                runner.fresh_output=lambda p: original_fresh(p,self.work/'synthetic-repo')
                def fake(path,compiler):
                    self.base.load_runner()[0].fresh_output(path)
                    if mutation=='directory':
                        path.rename(parent/'original'); path.mkdir()
                        (path/'foreign').write_text('preserve')
                    elif mutation=='marker':
                        (path/'output-ownership.json').write_text('changed')
                    else:
                        parent.rename(self.work/(mutation+'-original'))
                        if mutation=='symlink':
                            parent.symlink_to(self.work/(mutation+'-original'),target_is_directory=True)
                        else:
                            parent.mkdir(); path.mkdir()
                    return 1
                with patched(self.base,'load_runner',lambda:(runner,ordinary,proof)),patched(self.base,'run_fixture',fake):
                    self.assertEqual(a.run_fixture(self.base,out,'/fake/rustc'),1)
                self.assertFalse((out/'caller-binding-result.json').exists())
                self.assertFalse(any(p.name.startswith('executed-caller-binding') for p in out.iterdir()))

    def test_incremental_patch_retargets_only_successor_job(self):
        old=(HERE/'current-verify.yml').read_text()
        new=(HERE/'verify.yml.candidate').read_text()
        base=a.load()
        self.assertEqual(old.replace(base.job_text(old),''),new.replace(a.swift_ci_graph(base, new),''))
        self.assertIn('--out "$RUNNER_TEMP/analyzer-envelope"',new)
        self.assertEqual((HERE/'incremental.patch').read_bytes(),(HERE/'full.patch').read_bytes())


def run(suite):
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    return {'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'passed':result.wasSuccessful(),
            'failure_details':[{'test':str(test),'traceback':text} for test,text in result.failures+result.errors]}

def load_suite():
    return unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in (t.BindingControls, Independent, Ownership))
