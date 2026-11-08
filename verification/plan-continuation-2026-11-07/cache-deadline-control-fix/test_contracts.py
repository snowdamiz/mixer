#!/usr/bin/env python3
"""Executable timer/oracle mutations, deterministic deadline boundaries and adoption integrity."""
import ast
import argparse
import copy
import json
import signal
import sys
import types
import unittest
from unittest import mock
from local_support import HERE, original_source, save, workspace, write_guard
from control_source import control_source
import adopt_fixture as adoption
import deadline_control

write_guard()
MODE = 'optimized' if sys.flags.optimize else 'normal'
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--label', default='contracts-' + MODE)
OPTIONS, REMAINING = parser.parse_known_args()
sys.argv = [sys.argv[0], *REMAINING]


class Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        adoption.verify()
        cls.subject, cls.destination = workspace(OPTIONS.label, control_source())

    def case(self):
        case = self.subject.RunnerControls('test_postflight_deadline_is_terminal_and_preserves_scratch')
        case.setUp()
        self.addCleanup(case.tearDown)
        return case

    def test_all_original_36_method_bodies_preserved(self):
        def methods(source):
            owner = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef) and n.name == 'RunnerControls')
            return {n.name: ast.get_source_segment(source.decode(), n) for n in owner.body
                    if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')}
        before, after = methods(original_source()), methods(control_source())
        self.assertEqual(len(before), 36)
        self.assertEqual(after, before)

    def mutation(self, label, replacement):
        source = (HERE / 'deadline_control.py').read_text()
        needle = '                    return handler(number, frame)\n'
        self.assertEqual(source.count(needle), 1)
        altered = source.replace(needle, replacement, 1)
        module = types.ModuleType('deadline_fault_' + label)
        exec(compile(altered, str(HERE / 'deadline_control.py'), 'exec'), module.__dict__)
        evidence = self.destination / label
        evidence.mkdir()
        with self.assertRaises(RuntimeError) as error:
            module.run(self.case(), self.subject.r, evidence, 'postflight')
        raw = json.loads((evidence / 'logs/deadline-postflight-control.json').read_bytes())
        save(evidence / 'oracle-rejection.json', {'error': str(error.exception),
            'retained_before_rejection': raw['retained_before_assertions_and_teardown'],
            'mutation': replacement, 'actual_timer_registered': raw['state']['stage_timer_started']})
        self.assertTrue(raw['state']['stage_timer_started'])
        self.assertTrue(raw['timer_disarmed'])
        self.assertTrue(raw['handlers_restored'])
        return raw, str(error.exception)

    def test_missing_actual_handler_rejected(self):
        raw, error = self.mutation('missing-handler', '                    return None\n')
        self.assertTrue(raw['state']['after_delay'])
        self.assertFalse(raw['receipt']['cleanup'].get('deadline_expired', False))

    def test_continued_work_even_with_handler_rejected(self):
        raw, error = self.mutation('continued-work',
            "                    try:\n                        return handler(number, frame)\n                    finally:\n                        state['after_delay'] = True\n")
        self.assertIn('Work continued', error)
        self.assertTrue(raw['receipt']['cleanup']['deadline_expired'])

    def test_deleted_scratch_even_with_handler_rejected(self):
        raw, error = self.mutation('deleted-scratch',
            "                    try:\n                        return handler(number, frame)\n                    finally:\n                        runner.shutil.rmtree(out / 'scratch')\n")
        self.assertIn('scratch must remain', error)
        self.assertTrue(raw['receipt']['cleanup']['deadline_expired'])

    def logic(self, delta, expired):
        case, runner = self.case(), self.subject.r
        runs = case.base / 'runs'
        runs.mkdir()
        clock, calls, registrations = {'value': 100.0}, [], []
        original = runner.verify_pack
        def verify(base):
            calls.append(str(base))
            if len(calls) == 3:
                clock['value'] = 100.0 + delta
            return original(base)
        fake_signal = types.SimpleNamespace(**{n: getattr(signal, n) for n in
            ['SIGALRM', 'SIGINT', 'SIGTERM', 'ITIMER_REAL', 'getsignal']},
            signal=lambda *a: None, setitimer=lambda *a: registrations.append(a))
        with mock.patch.object(runner, 'RUNS', runs), mock.patch.object(runner, 'CLEANUP_SECONDS', .05), \
             mock.patch.object(runner, 'time', types.SimpleNamespace(monotonic=lambda: clock['value'])), \
             mock.patch.object(runner, 'signal', fake_signal), mock.patch.object(runner, 'verify_pack', verify), \
             mock.patch.object(runner.overlay, 'verify_materialized', return_value={'control': 'logic-only'}), \
             mock.patch.object(runner.platform, 'platform', return_value='pure control; no platform subprocess'), \
             mock.patch.object(runner.shutil, 'which', return_value=None), \
             mock.patch.object(runner.subprocess, 'Popen', side_effect=RuntimeError('No child allowed')) as spawn:
            out = runner.fresh_output(runs / 'logic')
            status = runner.execute(out, 'mixer-no-such-official-compiler-control')
        receipt = json.loads((out / 'receipt.json').read_bytes())
        preserved = (out / 'scratch/ownership.json').is_file()
        save(self.destination / ('logical-' + str(delta) + '.json'), {
            'scope': 'Deterministic remaining() comparison; timer registration recorded but not scheduled. No wall latency claim.',
            'receipt': receipt, 'status': status, 'clock': clock, 'registrations': registrations,
            'spawn_calls': spawn.call_count, 'scratch_preserved': preserved,
            'retained_before_assertions_and_teardown': True})
        self.assertEqual(status, 1)  # The deliberately absent compiler is still an active failure.
        self.assertEqual(receipt['commands'], [])
        self.assertEqual(spawn.call_count, 0)
        self.assertEqual(receipt['cleanup'].get('deadline_expired', False), expired)
        self.assertEqual(receipt['cleanup']['removed'], not expired)
        self.assertEqual(preserved, expired)
        self.assertEqual(receipt['cleanup_elapsed_seconds'], delta)
        self.assertEqual(len(calls), 3 if expired else 4)

    def test_logical_deadline_before_boundary(self):
        self.logic(.049, False)

    def test_logical_deadline_at_boundary(self):
        self.logic(.05, True)

    def test_logical_deadline_after_boundary(self):
        self.logic(.051, True)

    def test_installed_job_requires_exact_new_proposal(self):
        with mock.patch.object(adoption, 'WORKFLOW', HERE / 'workflow/swift-cache-state-fixture.yml'):
            self.assertTrue(adoption.verify(True)['installed_job_verified'])
        with mock.patch.object(adoption, 'WORKFLOW', HERE / 'workflow/previous-job.yml'):
            with self.assertRaisesRegex(RuntimeError, 'Installed job differs'):
                adoption.verify(True)

    def test_old_adapter_or_seal_mutation_rejected_before_import(self):
        real_sha = adoption.sha
        for name in ['adopt_fixture.py', 'sources.json']:
            with mock.patch.object(adoption, 'sha', side_effect=lambda p: '0' * 64 if p == adoption.PREVIOUS / name else real_sha(p)), \
                 mock.patch.object(adoption, 'load') as loader:
                with self.assertRaises(RuntimeError):
                    adoption.verify()
                loader.assert_not_called()

    def test_new_helper_mutation_rejected(self):
        old = adoption.previous()
        historical = old.baseline()
        real_sha = historical.sha
        with mock.patch.object(historical, 'sha', side_effect=lambda p: '0' * 64 if p == HERE / 'deadline_control.py' else real_sha(p)), \
             mock.patch.object(old, 'baseline', return_value=historical), \
             mock.patch.object(adoption, 'previous', return_value=old):
            with self.assertRaisesRegex(RuntimeError, 'Pinned source differs'):
                adoption.verify()

    def test_fixture_wrapper_reuses_old_execution_and_identity(self):
        real_previous, seen = adoption.previous, []
        def previous():
            module = real_previous()
            def pretend(out, rustc):
                seen.append((out, rustc, module.verify(True)))
                return 17
            module.run_fixture = pretend
            return module
        with mock.patch.object(adoption, 'WORKFLOW', HERE / 'workflow/swift-cache-state-fixture.yml'), \
             mock.patch.object(adoption, 'previous', side_effect=previous):
            self.assertEqual(adoption.run_fixture(HERE / 'unused-output', 'unused-compiler'), 17)
        self.assertEqual(len(seen), 1)
        self.assertTrue(seen[0][2]['installed_job_verified'])
        self.assertFalse(seen[0][2]['compiler_qualified'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
