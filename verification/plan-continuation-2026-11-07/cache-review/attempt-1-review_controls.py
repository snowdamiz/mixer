#!/usr/bin/env python3
"""Independent source/admission review. All workload children are Python fakes."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest import mock

REVIEW = Path(__file__).resolve().parent
ROOT = REVIEW.parents[2]
FIX = REVIEW.parent / 'cache-fix'
BASE = REVIEW.parent / 'baseline'
ARTIFACT = Path('/tmp/mixer-20261107-baseline/cache')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


# Install the inspected subject guard before importing any subject code, with
# a strictly narrower write root than the subject's own standalone test mode.
guard = module('offline_guard', FIX / 'offline_guard.py')
guard.install(REVIEW)
WRITE_DENIALS = []


def write_boundary(event, args):
    """Additionally fail closed on fd-relative mutations not used by controls."""
    targets = []
    if event == 'open':
        if args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            targets = [args[0]]
    elif event in {'os.mkdir', 'os.rmdir', 'os.remove', 'os.chmod', 'os.truncate', 'os.utime'}:
        targets = [args[0]]
    elif event in {'os.rename', 'os.link', 'os.symlink'}:
        targets = args[:2]
    for path in targets:
        if not isinstance(path, (str, bytes, os.PathLike)):
            WRITE_DENIALS.append(event)
            raise RuntimeError('Review forbids mutation via an unbound descriptor')
        path = Path(os.fsdecode(path))
        if not path.is_absolute() or not path.resolve().is_relative_to(REVIEW):
            WRITE_DENIALS.append(event)
            raise RuntimeError('Review writes must use absolute paths within cache-review')


sys.addaudithook(write_boundary)
original_tempdir = tempfile.TemporaryDirectory


def owned_tempdir(*args, **kwargs):
    # Preserve the provided suite's source reads and subject module roots;
    # relocate only its otherwise forbidden scratch writes.
    if Path(kwargs.get('dir', REVIEW)).resolve() == FIX:
        kwargs['dir'] = REVIEW
    return original_tempdir(*args, **kwargs)


sys.path.insert(0, str(FIX))
with mock.patch.object(guard, 'install', side_effect=lambda root: None):
    supplied = module('reviewed_selection_controls', FIX / 'test_selection.py')
a = supplied.a


def input_hashes():
    paths = [FIX / name for name in (*a.SHIPPING, 'sources.json', 'receipt.json',
                                     'controls.stdout', 'controls.stderr')]
    paths += list((BASE / 'cache-fixture').glob('*')) + [BASE / 'swift-cache-state.log']
    dependencies = json.loads((a.OLD / 'dependencies.json').read_bytes())['members']
    seal = json.loads((a.OLD / 'seal.json').read_bytes())['members']
    paths += [ROOT / row['path'] for row in dependencies]
    paths += [a.OLD / row['path'] for row in seal]
    paths += [a.OLD / 'seal.json']
    return {str(p.relative_to(ROOT)): digest(p) for p in sorted(set(paths))}


def prospective_workflow():
    """Apply the exact supplied unified patch in memory, including context."""
    lines = (ROOT / '.github/workflows/verify.yml').read_text().splitlines(keepends=True)
    patch = (FIX / 'workflow.diff').read_text().splitlines(keepends=True)
    if patch[:2] != ['--- a/.github/workflows/verify.yml\n', '+++ b/.github/workflows/verify.yml\n']:
        raise AssertionError('Unexpected patch target')
    output, cursor, index = [], 0, 2
    while index < len(patch):
        header = re.fullmatch(r'@@ -(\d+),(\d+) \+(\d+),(\d+) @@\n', patch[index])
        if header is None:
            raise AssertionError('Unexpected hunk header')
        index += 1
        body = []
        while index < len(patch) and not patch[index].startswith('@@ '):
            body.append(patch[index])
            index += 1
        before = [line[1:] for line in body if line[0] in ' -']
        after = [line[1:] for line in body if line[0] in ' +']
        if len(before) != int(header[2]) or len(after) != int(header[4]):
            raise AssertionError('Patch hunk count mismatch')
        matches = [i for i in range(cursor, len(lines) - len(before) + 1)
                   if lines[i:i + len(before)] == before]
        if len(matches) != 1:
            raise AssertionError('Patch hunk context is ambiguous or missing')
        start = matches[0]
        output.extend(lines[cursor:start])
        output.extend(after)
        cursor = start + len(before)
    output.extend(lines[cursor:])
    return ''.join(output)


class IndependentControls(unittest.TestCase):
    def setUp(self):
        self.temporary = original_tempdir(dir=REVIEW, prefix='independent-')
        self.scratch = Path(self.temporary.name)

    def tearDown(self):
        for path in sorted(self.scratch.rglob('*'), key=lambda p: len(p.parts), reverse=True):
            path.rmdir() if path.is_dir() and not path.is_symlink() else path.unlink()
        self.scratch.rmdir()
        self.temporary.cleanup()

    def test_baseline_receipt_identity_and_manifest_join(self):
        selection = json.loads((FIX / 'compiler-selection.json').read_bytes())
        baseline = BASE / 'cache-fixture'
        original = ARTIFACT / 'verification/cache-fixture-shared-input-candidate-v2/runs/ci-40974383080-1'
        self.assertEqual((baseline / 'receipt.json').read_bytes(), (original / 'receipt.json').read_bytes())
        receipt = json.loads((baseline / 'receipt.json').read_bytes())
        verbose = (baseline / 'compiler-identity.stdout').read_text()
        observed = selection['observed_baseline']
        self.assertEqual(observed['receipt_sha256'], digest(baseline / 'receipt.json'))
        self.assertEqual(observed['verbose_stdout_sha256'], digest(baseline / 'compiler-identity.stdout'))
        self.assertEqual(observed['job_log_sha256'], digest(BASE / 'swift-cache-state.log'))
        self.assertEqual(verbose, a.VERBOSE)
        self.assertEqual(receipt['rustc']['sha256'], a.COMPILER_SHA256)
        self.assertEqual(receipt['commands'][1]['stdout_sha256'], digest(baseline / 'compiler-identity.stdout'))
        self.assertEqual(receipt['commands'][1]['argv'][0], receipt['rustc']['path'])
        self.assertEqual(receipt['status'], 'failed')
        self.assertEqual(receipt['errors'], observed['errors'])
        self.assertEqual([c['name'] for c in receipt['commands']], ['compiler-sysroot', 'compiler-identity'])
        self.assertTrue(receipt['cleanup']['removed'])
        self.assertFalse(selection['qualified'])

    def test_original_dependencies_match_retained_run_artifact(self):
        dependencies = json.loads((a.OLD / 'dependencies.json').read_bytes())['members']
        seal = json.loads((a.OLD / 'seal.json').read_bytes())['members']
        names = [row['path'] for row in dependencies]
        names += [str((a.OLD / row['path']).relative_to(ROOT)) for row in seal]
        names += [str((a.OLD / 'seal.json').relative_to(ROOT))]
        for name in names:
            with self.subTest(name=name):
                self.assertEqual(digest(ROOT / name), digest(ARTIFACT / name))

    def test_exact_patch_changes_only_cache_job_and_preserves_parent_android_step(self):
        before = (ROOT / '.github/workflows/verify.yml').read_text()
        after = prospective_workflow()
        old = a.baseline()
        old_job = old.job_text(before)
        new_job = (FIX / 'workflow/swift-cache-state-fixture.yml').read_text()
        self.assertEqual(after, before.replace(old_job, new_job, 1))
        self.assertEqual(old_job, (a.OLD / 'workflow/swift-cache-state-fixture.yml').read_text())
        self.assertIn('      - name: Show retained Android host failure diagnostics\n', after)
        candidate = self.scratch / 'prospective.yml'
        candidate.write_text(after)
        with mock.patch.object(a, 'WORKFLOW', candidate):
            proof = a.verify(True)
        self.assertTrue(proof['installed_job_verified'])
        self.assertFalse(proof['compiler_qualified'])
        (REVIEW / 'prospective-workflow.yml').write_text(after)

    def test_hook_reads_its_current_output_receipt_not_a_previous_run(self):
        output = self.scratch / 'current'
        output.mkdir()
        prior = self.scratch / 'prior'
        prior.mkdir()
        inert = self.scratch / 'inert-rustc-data'
        inert.write_bytes(b'inert; no executable permission or child invocation')
        evidence = {'path': str(inert), 'sha256': a.COMPILER_SHA256}
        runner = a.load_runner(output)
        runner.save(prior / 'receipt.json', {'rustc': evidence})
        with mock.patch.object(runner, 'sha', return_value=a.COMPILER_SHA256):
            with self.assertRaises(FileNotFoundError):
                runner.rust_identity(a.VERBOSE)
            runner.save(output / 'receipt.json', {'rustc': evidence})
            self.assertEqual(runner.rust_identity(a.VERBOSE), a.IDENTITY)
            runner.save(output / 'receipt.json', {'rustc': {**evidence, 'sha256': '0' * 64}})
            with self.assertRaisesRegex(RuntimeError, 'fingerprint'):
                runner.rust_identity(a.VERBOSE)

    def test_no_alias_or_directory_binary_is_admitted(self):
        runner = a.load_runner(self.scratch)
        actual = self.scratch / 'actual'
        actual.mkdir()
        inert = actual / 'inert'
        inert.write_bytes(b'inert')
        alias = self.scratch / 'alias'
        alias.symlink_to(actual, target_is_directory=True)
        for path in [alias / 'inert', actual]:
            with self.subTest(path=path), mock.patch.object(runner, 'sha', return_value=a.COMPILER_SHA256):
                with self.assertRaisesRegex(RuntimeError, 'Regular source'):
                    a.select_identity(a.VERBOSE, {'path': str(path), 'sha256': a.COMPILER_SHA256}, runner)

    def fake_invocation(self, verbose, observed_hash, terminal_mutation=None, raw_hash=False):
        runs = self.scratch / 'runs'
        runs.mkdir()
        output = runs / 'one'
        inert = self.scratch / 'inert-compiler-data'
        inert.write_bytes(b'fake compiler bytes; never executed')
        runner = a.load_runner(output)
        real_sha = runner.sha
        workload = []
        candidate = self.scratch / 'prospective.yml'
        candidate.write_text(prospective_workflow())

        def fake_child(out, requested):
            (out / 'commands').mkdir()
            (out / 'commands/compiler-identity.stdout').write_text(verbose)
            receipt = {'rustc': {'path': str(inert), 'sha256': observed_hash},
                       'commands': [{'name': 'fake-sysroot'}, {'name': 'fake-identity'}]}
            runner.save(out / 'receipt.json', receipt)
            # Exercise the real installed hook before any synthetic workload.
            selected = runner.rust_identity(verbose)
            workload.append('synthetic-workload')
            receipt.update(status='passed-host-fixture-check', active_checks_completed=True, errors=[])
            receipt['rustc'].update(identity=selected, version_verbose=verbose)
            receipt['commands'] += [{'name': f'fake-{i}'} for i in range(101)]
            if terminal_mutation:
                terminal_mutation(receipt, out)
            runner.save(out / 'receipt.json', receipt)
            return 0

        def controlled_sha(path):
            return a.COMPILER_SHA256 if path == inert and not raw_hash else real_sha(path)

        with mock.patch.dict(a.os.environ, {'RUSTUP_AUTO_INSTALL': '0'}), \
             mock.patch.object(a, 'WORKFLOW', candidate), \
             mock.patch.object(a, 'load_runner', return_value=runner), \
             mock.patch.object(runner, 'RUNS', runs), \
             mock.patch.object(runner, 'sha', side_effect=controlled_sha), \
             mock.patch.object(runner, 'execute', side_effect=fake_child) as fake:
            status = a.run_fixture(output, '/inert/fake-launcher')
            self.assertEqual(fake.call_count, 1)
        result = json.loads((output / 'selection-result.json').read_bytes())
        self.assertFalse(result['compiler_qualified'])
        self.assertEqual(result['selection_sha256'], digest(FIX / 'compiler-selection.json'))
        return status, result, workload

    def test_unknown_compiler_refused_before_any_fake_workload(self):
        status, result, workload = self.fake_invocation(a.VERBOSE.replace('1.99.1', '1.100.0'), a.COMPILER_SHA256)
        self.assertEqual(status, 1)
        self.assertEqual(workload, [])
        self.assertIn('verbose identity differs', result['errors'][0]['message'])

    def test_real_inert_hash_cannot_be_admitted_with_exact_verbose(self):
        status, result, workload = self.fake_invocation(a.VERBOSE, a.COMPILER_SHA256, raw_hash=True)
        self.assertEqual(status, 1)
        self.assertEqual(workload, [])
        self.assertIn('fingerprint differs', result['errors'][0]['message'])

    def test_matching_synthetic_hook_path_remains_unqualified(self):
        status, result, workload = self.fake_invocation(a.VERBOSE, a.COMPILER_SHA256)
        self.assertEqual(status, 0)
        self.assertEqual(workload, ['synthetic-workload'])
        self.assertEqual(result['errors'], [])

    def test_terminal_compiler_evidence_drift_overrides_fake_success(self):
        def mutate(receipt, out):
            receipt['rustc']['sha256'] = '0' * 64
        status, result, workload = self.fake_invocation(a.VERBOSE, a.COMPILER_SHA256, mutate)
        self.assertEqual(status, 1)
        self.assertEqual(result['fixture_return_status'], 0)
        self.assertEqual(result['errors'][0]['phase'], 'selection-postflight')

    def test_manifest_member_mutation_refuses_before_fixture_loading(self):
        candidate = self.scratch / 'candidate'
        candidate.mkdir()
        for name in (*a.SHIPPING, 'sources.json'):
            dest = candidate / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((FIX / name).read_bytes())
        with mock.patch.object(a, 'HERE', candidate):
            self.assertFalse(a.verify()['compiler_qualified'])
            (candidate / 'compiler-selection.json').write_text('{}\n')
            with self.assertRaisesRegex(RuntimeError, 'Pinned source differs'):
                a.verify()


before = input_hashes()
supplied_suite = unittest.defaultTestLoader.loadTestsFromModule(supplied)
with mock.patch.object(tempfile, 'TemporaryDirectory', side_effect=owned_tempdir):
    supplied_result = unittest.TextTestRunner(stream=sys.stderr, verbosity=2).run(supplied_suite)
independent_suite = unittest.defaultTestLoader.loadTestsFromTestCase(IndependentControls)
independent_result = unittest.TextTestRunner(stream=sys.stderr, verbosity=2).run(independent_suite)
after = input_hashes()
stable = before == after
summary = {
    'supplied_tests': supplied_result.testsRun,
    'supplied_passed': supplied_result.wasSuccessful(),
    'independent_tests': independent_result.testsRun,
    'independent_passed': independent_result.wasSuccessful(),
    'reviewed_inputs_unchanged': stable,
    'input_hashes': after,
    'guard_runtime_denials': guard.DENIED,
    'write_denials': WRITE_DENIALS,
    'compiler_or_rustup_executed': False,
    'real_fixture_execute_called': False,
    'compiler_qualified': False,
    'write_root': str(REVIEW),
    'subject_test_scratch_relocated': True,
    'python': sys.version,
    'python_executable': sys.executable,
    'python_sha256': digest(Path(sys.executable).resolve()),
    'scope': 'Prospective selection, source closure and fake-child orchestration only; positive binary hashes mocked',
    'scratch_absent': not list(REVIEW.glob('control-*')) and not list(REVIEW.glob('independent-*')),
}
(REVIEW / 'controls-result.json').write_text(json.dumps(summary, sort_keys=True, indent=2) + '\n')
print(json.dumps({k: v for k, v in summary.items() if k != 'input_hashes'}, sort_keys=True))
sys.exit(0 if supplied_result.wasSuccessful() and independent_result.wasSuccessful()
         and stable and not guard.DENIED and not WRITE_DENIALS and summary['scratch_absent'] else 1)
