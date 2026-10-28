#!/usr/bin/env python3
"""Independent bounded source/file/mock review; never starts a fixture child."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANDIDATE = ROOT / 'verification/cache-fixture-shared-input-candidate'
sys.dont_write_bytecode = True
sys.path.insert(0, str(CANDIDATE))
import offline_audit
offline_audit.install(HERE)

import ast
from contextlib import contextmanager
from datetime import datetime, timezone
import difflib
import hashlib
import io
import json
import os
import shutil
import tempfile
import types
import unittest
from unittest import mock
import materialize_pack as m
import test_materializer
import test_runner
import verify_candidate

r = test_runner.r
EXPECTED_SEAL = 'db6ba0fcb4c66f5a38dd0f93ce9dc381a869b12fbf8eda7ecb8f5b3f57bfeca7'
EXPECTED_TREE = '96a51f27039c6c091eae9fd0e447bc9ca2d71f453eebc6c8ca6e58474640c698'
PENDING_RUNTIME = {
    'test_checks_active_under_optimized_python',
    'test_missing_and_failed_commands_keep_raw_receipts',
    'test_timeout_owned_child_group_and_output_cap',
    'test_owned_descendant_group_is_stopped',
    'test_every_child_gets_owned_default_temporary_directory',
    'test_fixture_temporary_override_stays_inside_owned_scratch',
    'test_postflight_deadline_is_terminal_and_preserves_scratch',
    'test_retention_deadline_is_terminal_and_preserves_scratch',
}


def binding(path):
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size,
            'sha256': m.sha(path)}


def test_names(path):
    return {node.name for node in ast.walk(ast.parse(path.read_bytes()))
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_')}


@contextmanager
def owned_materializer():
    with tempfile.TemporaryDirectory(prefix='integration-', dir=HERE / 'scratch') as raw:
        owner = Path(raw).resolve()
        base = owner / 'base'
        overlay = owner / 'overlay'
        manifest = owner / 'overlay-manifest.json'
        shutil.copytree(m.BASE, base)
        shutil.copytree(m.OVERLAY, overlay)
        shutil.copyfile(m.OVERLAY_MANIFEST, manifest)
        with mock.patch.object(m, 'HERE', owner), mock.patch.object(m, 'BASE', base), \
             mock.patch.object(m, 'OVERLAY', overlay), mock.patch.object(m, 'OVERLAY_MANIFEST', manifest), \
             mock.patch.object(m, 'MATERIALIZED', owner / 'materialized'):
            yield owner


class IndependentIntegrationControls(unittest.TestCase):
    def test_source_postflight_rejects_base_change_after_materialization(self):
        with owned_materializer():
            m.materialize()
            source = m.BASE / 'source/library/cache_state.rs'
            source.write_bytes(source.read_bytes() + b'changed-after-copy')
            with self.assertRaisesRegex(RuntimeError, 'Missing/extra/mutated pack member'):
                m.verify_materialized()
            self.assertTrue((m.MATERIALIZED / 'ownership.json').is_file())
            self.assertTrue((m.MATERIALIZED / 'pack/source/library/cache_state.rs').is_file())

    def test_missing_compiler_fails_with_zero_children_and_normal_source_postflight(self):
        with owned_materializer() as owner:
            m.materialize()
            runs = owner / 'runs'
            runs.mkdir()
            inert_signal = types.SimpleNamespace(
                SIGALRM=r.signal.SIGALRM, SIGINT=r.signal.SIGINT, SIGTERM=r.signal.SIGTERM,
                ITIMER_REAL=r.signal.ITIMER_REAL, getsignal=mock.Mock(return_value=None),
                signal=mock.Mock(), setitimer=mock.Mock())
            with mock.patch.object(r, 'RUNS', runs), mock.patch.object(r, 'PACK', m.MATERIALIZED / 'pack'), \
                 mock.patch.object(r, 'signal', inert_signal), \
                 mock.patch.object(r.platform, 'platform', return_value='source-file-mock-control'), \
                 mock.patch.object(r.shutil, 'which', return_value=None), \
                 mock.patch.object(r.subprocess, 'Popen', side_effect=AssertionError('must not spawn')) as spawn, \
                 mock.patch.object(sys, 'stdout', io.StringIO()):
                out = r.fresh_output(runs / 'missing-compiler')
                self.assertEqual(r.execute(out, 'unavailable-declared-compiler'), 1)
            spawn.assert_not_called()
            receipt = m.load(out / 'receipt.json')
            self.assertEqual(receipt['status'], 'failed')
            self.assertEqual(receipt['commands'], [])
            self.assertEqual(receipt['errors'][0]['message'], 'Compiler launcher missing')
            self.assertTrue(receipt['postflight']['shared-input-overlay']['passed'])
            self.assertTrue(receipt['postflight']['pack']['passed'])
            self.assertTrue(receipt['cleanup']['removed'])
            self.assertFalse(receipt.get('active_checks_completed', False))
            self.assertTrue((out / 'retention.json').is_file())

    def test_spawn_failure_withholds_cpu_delta_and_keeps_original_error(self):
        control = test_runner.RunnerControls()
        control.setUp()
        try:
            c = control.commands()
            missing = FileNotFoundError(2, 'synthetic unavailable compiler')
            snapshots = types.SimpleNamespace(ru_utime=1., ru_stime=2., ru_minflt=3, ru_majflt=4)
            with mock.patch.object(r.subprocess, 'Popen', side_effect=missing), \
                 mock.patch.object(r.resource, 'getrusage', return_value=snapshots):
                with self.assertRaises(FileNotFoundError) as observed:
                    c.run('missing-compiler', ['synthetic-unavailable-compiler'], control.base)
            self.assertIs(observed.exception, missing)
            row = m.load(c.out / 'commands/missing-compiler.json')
            self.assertIsNone(row['child_resource_usage']['aggregate_delta'])
            self.assertFalse(row['child_resource_usage']['terminal_facts_verified'])
            self.assertFalse(row['child_returned'])
            self.assertFalse(row['owned_group_gone'])
            self.assertFalse(row['custody_hold'])
            self.assertEqual(row['spawn_error'], str(missing))
            self.assertEqual(row['context_phase_progress'], [])
        finally:
            control.tearDown()

    def test_cpu_regression_and_missing_snapshots_fail_without_fabricating_delta(self):
        before = {'ru_utime': 2., 'ru_stime': 1., 'ru_minflt': 3, 'ru_majflt': 4}
        after = dict(before, ru_utime=1.)
        with self.assertRaisesRegex(RuntimeError, 'regressed'):
            r.child_accounting(before, after, True)
        with self.assertRaisesRegex(RuntimeError, 'Missing child resource snapshots'):
            r.child_accounting(None, after, True)
        self.assertIsNone(r.child_accounting(before, after, False)['aggregate_delta'])

    def test_progress_is_diagnostic_and_cannot_replace_terminal_method_verification(self):
        text = ('context_progress completed=1003/1003 elapsed_ms=120 prepare_ms=5 '
                'analyze_ms=80 report_assert_ms=3 cleanup_ms=2\n')
        row = r.context_phase_progress(text)[0]
        self.assertTrue(row['progress_is_not_completion'])
        self.assertEqual(row['unattributed_elapsed_remainder_ms'], 30)
        self.assertIn('caller context cloning', row['scope'])
        with self.assertRaises(RuntimeError):
            r.verify_methods(text, ['required_method'], True)
        self.assertEqual(r.context_phase_progress(text.replace('completed=', 'completed?')), [])

    def test_exact_toolchain_environment_preserved_and_auto_install_disabled(self):
        with mock.patch.dict(os.environ, {'RUSTUP_TOOLCHAIN': '1.98.1-aarch64-apple-darwin',
                                         'RUSTUP_AUTO_INSTALL': '1', 'RUST_TEST_SHUFFLE': '1'}):
            env = r.environment({})
        self.assertEqual(env['RUSTUP_TOOLCHAIN'], '1.98.1-aarch64-apple-darwin')
        self.assertEqual(env['RUSTUP_AUTO_INSTALL'], '0')
        self.assertNotIn('RUST_TEST_SHUFFLE', env)
        manifest = m.load(m.BASE / 'manifest.json')
        self.assertIn(['aarch64-apple-darwin', '1.98.1'], manifest['compiler_targets'])


def main():
    m.need(m.sha(CANDIDATE / 'seal.json') == EXPECTED_SEAL, 'Expected shipping seal differs')
    verified = verify_candidate.verify()
    m.need(verified['candidate_tree_sha256'] == EXPECTED_TREE, 'Expected shipping tree differs')
    seal = m.load(CANDIDATE / 'seal.json')
    m.need(len(seal['members']) == 21 and sum(row['bytes'] for row in seal['members']) == 231418,
           'Expected shipping count/bytes differ')
    prior = m.load(CANDIDATE / 'offline-controls.json')
    prior_paths = [ROOT / row['path'] for row in prior['readset']]
    m.need(len(prior_paths) == 114 and [binding(path) for path in prior_paths] == prior['readset'],
           'Original 114-member offline read-set differs')
    paths = sorted(set(prior_paths + [CANDIDATE / 'seal.json'] +
                       [CANDIDATE / row['path'] for row in seal['members']]))
    before = [binding(path) for path in paths]
    base = ROOT / 'verification/swift-cache-state-ci'
    expected_diffs = []
    for stem, amendment in [('check_cache_state.py', 'runner-amendment.diff'),
                            ('test_runner.py', 'controls-amendment.diff')]:
        actual = ''.join(difflib.unified_diff((base / stem).read_text().splitlines(True),
                        (CANDIDATE / stem).read_text().splitlines(True),
                        fromfile=(base / stem).relative_to(ROOT).as_posix(),
                        tofile=(CANDIDATE / stem).relative_to(ROOT).as_posix()))
        m.need(actual == (CANDIDATE / amendment).read_text(), 'Recorded amendment differs')
        expected_diffs.append({'path': amendment, 'sha256': m.sha(CANDIDATE / amendment)})
    original = test_names(base / 'test_runner.py')
    candidate = test_names(CANDIDATE / 'test_runner.py')
    m.need(len(original) == 32 and original <= candidate and len(candidate) == 36,
           'Control preservation differs')
    selected = sorted(candidate - PENDING_RUNTIME)
    m.need(len(selected) == 28 and PENDING_RUNTIME <= candidate, 'Pure/pending control split differs')
    m.need((r.CHILD_SECONDS, r.ACTIVE_SECONDS, r.CLEANUP_SECONDS, r.OUTPUT_CAP) ==
           (60, 600, 60, 8388608), 'Fixture command bounds differ')
    base_bindings = m.load(m.BASE / 'inventories/bindings.json')
    overlay_bindings = m.load(m.OVERLAY / 'inventories/bindings.json')
    m.need({k: v for k, v in overlay_bindings.items() if k != 'shared_input_harness_amendment'} == base_bindings,
           'Unrelated bindings or fixture setup predecessor changed')
    base_roster = m.load(m.BASE / 'inventories/source-roster.json')
    candidate_roster = m.load(m.OVERLAY / 'inventories/source-roster.json')
    changed = [(old, new) for old, new in zip(base_roster['rows'], candidate_roster['rows']) if old != new]
    m.need(len(base_roster['rows']) == len(candidate_roster['rows']) == 78 and len(changed) == 1,
           'Unrelated source roster row changed')
    old, new = changed[0]
    m.need(new['packed'] == old['packed'] == 'source/regression/independent_tests.rs'
           and new['shared_input_predecessor'] == old and new['sha256'] == m.ACCEPTED_SOURCE_SHA256
           and new['historical_predecessor'] == old['historical_predecessor'],
           'Source roster predecessor or accepted-source binding changed')
    m.need({k: v for k, v in candidate_roster.items() if k not in {'rows', 'selected_source_bytes'}} ==
           {k: v for k, v in base_roster.items() if k not in {'rows', 'selected_source_bytes'}}
           and candidate_roster['selected_source_bytes'] ==
           base_roster['selected_source_bytes'] + new['bytes'] - old['bytes'],
           'Unrelated source roster metadata changed')
    methods = m.load(m.BASE / 'inventories/methods.json')
    m.need(2 + 4 + 16 + 7 + len(methods['producer_debug_partition']) + 56 == 103,
           'Complete fixture child-command count differs')
    budget = m.load(CANDIDATE / 'command-budget.json')
    m.need(budget['fixture_child_commands'] == 103 and budget['complete_fixture_invocations'] == 1
           and budget['automatic_retries'] == 0 and budget['focused_runner_controls'] == 36,
           'Declared fixture scope differs')
    workflow = (CANDIDATE / 'workflow/cache-fixture-shared-input-diagnostic.yml').read_text()
    for token in ["RUSTUP_AUTO_INSTALL: '0'", "RUSTUP_TOOLCHAIN: '1.98.1-aarch64-apple-darwin'",
                  'test "$GITHUB_RUN_ATTEMPT" = 1', 'workflow_dispatch:',
                  'cancel-in-progress: false', 'if: always()', 'include-hidden-files: true']:
        m.need(token in workflow, 'Missing manual workflow constraint: ' + token)
    m.need(workflow.count('"$MIXER_SHARED_INPUT_DIR/check_cache_state.py"') == 1
           and workflow.index('test_materializer.py') < workflow.index('test_runner.py')
           < workflow.index('check_cache_state.py'), 'Runtime controls must precede sole fixture')
    m.need('rustup toolchain install' not in workflow and 'continue-on-error' not in workflow,
           'Unexpected install or failure bypass')
    stream = io.StringIO()
    scratch = HERE / 'scratch'
    scratch.mkdir()
    results = []
    try:
        with tempfile.TemporaryDirectory(prefix='controls-', dir=scratch) as raw:
            owner = Path(raw).resolve()
            assets = owner / 'assets'
            assets.mkdir()
            shutil.copyfile(CANDIDATE / 'overlay-manifest.json', assets / 'overlay-manifest.json')
            with mock.patch.object(tempfile, 'tempdir', str(owner)), \
                 mock.patch.object(test_materializer, 'HERE', assets), \
                 mock.patch.object(test_runner, 'HERE', assets):
                with mock.patch.object(m, 'HERE', owner), \
                     mock.patch.object(m, 'MATERIALIZED', owner / 'materialized'):
                    m.materialize()
                    with mock.patch.object(r, 'PACK', m.MATERIALIZED / 'pack'), \
                         mock.patch.object(r.resource, 'getrusage', return_value=types.SimpleNamespace(
                             ru_utime=0., ru_stime=0., ru_minflt=0, ru_majflt=0)):
                        suite = unittest.TestSuite(test_runner.RunnerControls(name) for name in selected)
                        results.append(unittest.TextTestRunner(stream=stream, verbosity=2).run(suite))
                results.append(unittest.TextTestRunner(stream=stream, verbosity=2).run(
                    unittest.defaultTestLoader.loadTestsFromModule(test_materializer)))
                results.append(unittest.TextTestRunner(stream=stream, verbosity=2).run(
                    unittest.defaultTestLoader.loadTestsFromTestCase(IndependentIntegrationControls)))
    finally:
        if scratch.exists() and not any(scratch.iterdir()):
            scratch.rmdir()
    after = [binding(path) for path in paths]
    m.need(before == after, 'Independent read-set changed')
    m.need(not offline_audit.DENIED, 'Forbidden operation attempted')
    verify_candidate.verify()
    (HERE / 'controls.stdout').write_text(stream.getvalue())
    report = {
        'schema': 1, 'created_utc': datetime.now(timezone.utc).isoformat(),
        'command': 'python3 -B verification/cache-fixture-overlay-independent/review.py',
        'python': sys.version, 'host_uname': list(os.uname()),
        'review_source_sha256': m.sha(HERE / 'review.py'),
        'source_revision': 'Not probed; Git operations forbidden in this bounded source/file lane.',
        'status': 'accepted-integration-source-and-pure-controls' if all(x.wasSuccessful() for x in results) else 'failed',
        'candidate_seal_sha256': EXPECTED_SEAL, 'candidate_tree_sha256': EXPECTED_TREE,
        'candidate_shipping_members': 21, 'candidate_shipping_bytes': 231418,
        'candidate_runner_sha256': m.sha(CANDIDATE / 'check_cache_state.py'),
        'candidate_workflow_sha256': m.sha(CANDIDATE / 'workflow/cache-fixture-shared-input-diagnostic.yml'),
        'accepted_source_sha256': m.ACCEPTED_SOURCE_SHA256,
        'accepted_source_review_tree_sha256': verified['inputs']['review_tree_sha256'],
        'effective_pack': verified['inputs'], 'amendments_exact': expected_diffs,
        'control_counts': {'retained_base': 32, 'candidate_total': 36, 'runner_pure_executed': results[0].testsRun,
                           'materializer_groups_executed': results[1].testsRun,
                           'independent_integration_executed': results[2].testsRun},
        'runner_runtime_controls_pending': sorted(PENDING_RUNTIME),
        'independent_controls': unittest.defaultTestLoader.getTestCaseNames(IndependentIntegrationControls),
        'denied_operation_attempts': offline_audit.DENIED,
        'readset': before, 'readset_tree_sha256': m.tree(before), 'readset_count': len(before),
        'original_offline_readset_count': 114,
        'original_offline_readset_tree_sha256': prior['readset_tree_sha256'],
        'readset_postflight_unchanged': before == after,
        'cleanup': {'owned_scratch_absent': not scratch.exists(),
                    'candidate_default_materialization_absent': not (CANDIDATE / 'materialized').exists(),
                    'no_process_or_native_or_capture_started': True},
        'limits': ['Source/file/mock review only; no Rust, compiler, product runtime, Git command, process inventory, '
                   'signal/timer/wait syscall, socket, UI, native runtime, capture, held-group probe, push or dispatch.',
                   'Six additional integration controls use synthetic compiler absence, spawn failure and inert signals; '
                   'they are not evidence for real subprocess, timer or compiler behavior.',
                   'Progress rows are informational extraction, not monotonicity/completeness validation; '
                   'completed=1003 cannot authorize completion or replace exact method/command and postflight checks.',
                   'CPU snapshots are sequential reaped-child aggregates, not isolated-process accounting.',
                   'Actual declared-compiler availability, all 36 runtime controls and one complete 103-command '
                   'Debug/optimized fixture remain pending; absence or wrong identity fails, without claiming a test pass.',
                   'Historical timeout remains failed; no regression, speedup, native, release or GA conclusion.'],
    }
    m.save(HERE / 'review.json', report)
    print(json.dumps({k: report[k] for k in ['status', 'control_counts', 'readset_count',
                     'readset_tree_sha256', 'cleanup']}, sort_keys=True))
    m.need(report['status'] == 'accepted-integration-source-and-pure-controls', stream.getvalue())


if __name__ == '__main__':
    main()
