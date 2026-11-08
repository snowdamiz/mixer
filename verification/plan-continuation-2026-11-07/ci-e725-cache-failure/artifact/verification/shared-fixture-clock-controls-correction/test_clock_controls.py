#!/usr/bin/env python3
"""Pure source/discovery checks and only the four fully mocked CPU controls."""
# Preload unittest.mock's standard-library imports before replacing socket.socket.
import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from strict_guard import DENIED, install
install(HERE)

import adopt_fixture as a
from control_source import AFTER, BEFORE, FROZEN, SOURCE_SHA256, control_source

ORIGINAL_ADOPTION = a.ROOT / 'verification/shared-fixture-default-ci-adoption'
SELECTED = [
    'test_mocked_cpu_custody_hold_withholds_delta',
    'test_mocked_cpu_failure_retains_aggregate_after_terminal_facts',
    'test_mocked_cpu_success_has_raw_snapshots_and_aggregate_delta',
    'test_mocked_cpu_timeout_retains_failure_and_aggregate',
]
OBSERVATIONS = []


def subject(corrected):
    source = control_source(corrected)
    name = 'clock_control_corrected' if corrected else 'clock_control_baseline'
    module = types.ModuleType(name)
    module.__file__ = str(FROZEN)
    sys.modules[name] = module
    sys.path.insert(0, str(FROZEN.parent))
    try:
        exec(compile(source, str(FROZEN), 'exec'), module.__dict__)
    finally:
        if sys.path.pop(0) != str(FROZEN.parent):
            raise RuntimeError('Frozen import path changed')
    return module


class ClockSourceContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proof = a.verify()

    def test_exact_one_line_helper_correction(self):
        original, corrected = control_source(False), control_source(True)
        self.assertEqual(hashlib.sha256(original).hexdigest(), SOURCE_SHA256)
        self.assertEqual(corrected, original.replace(BEFORE, AFTER, 1))
        self.assertEqual(corrected.replace(AFTER, BEFORE, 1), original)
        self.assertEqual(len(corrected.splitlines()), len(original.splitlines()) + 1)
        # Reset deadline before assigning the timeout's original three-value sequence.
        self.assertIn(AFTER + b'  if timed_out:clock.monotonic.side_effect=[100.0,101.0,101.0]\n', corrected)

    def test_all_36_test_names_and_bodies_unchanged(self):
        def methods(source):
            tree = ast.parse(source)
            owner = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                         and node.name == 'RunnerControls')
            return {node.name: ast.dump(node, include_attributes=False)
                    for node in owner.body if isinstance(node, ast.FunctionDef)
                    and node.name.startswith('test_')}
        original = methods(control_source(False))
        self.assertEqual(len(original), 36)
        self.assertEqual(methods(control_source(True)), original)
        self.assertTrue(set(SELECTED).issubset(original))

    def test_all_36_are_discoverable_without_execution(self):
        module = subject(True)
        suite = unittest.defaultTestLoader.loadTestsFromModule(module)
        self.assertEqual(suite.countTestCases(), 36)
        self.assertEqual(module.HERE, FROZEN.parent)
        self.assertEqual(Path(module.r.__file__), FROZEN.parent / 'check_cache_state.py')
        self.assertEqual(module.RunnerControls.test_checks_active_under_optimized_python.__code__.co_filename,
                         str(FROZEN))

    def test_hosted_wrapper_uses_actual_main_globals(self):
        source = (HERE / 'test_runner.py').read_text()
        self.assertIn("globals()['__file__'] = str(FROZEN)", source)
        self.assertIn("exec(compile(_corrected_control_source, str(FROZEN), 'exec'), globals())", source)
        original = control_source(False)
        self.assertIn(b"timeout=15,cwd=HERE)", original)
        self.assertIn(b"destination=HERE/'logs'/(name+'-control')", original)
        # Intercept only unittest entry, then exercise the real wrapper and its
        # actual-main discovery path without running any of the 36 methods.
        main = types.ModuleType('__main__')
        main.__file__ = str(HERE / 'test_runner.py')
        discovered = []
        def discover(*args, **kwargs):
            self.assertEqual(args, ())
            self.assertEqual(kwargs, {'verbosity': 2})
            discovered.append(unittest.defaultTestLoader.loadTestsFromModule(sys.modules['__main__']).countTestCases())
        search_path = list(sys.path)
        try:
            with mock.patch.dict(sys.modules, {'__main__': main}), mock.patch.object(unittest, 'main', side_effect=discover):
                exec(compile(source, main.__file__, 'exec'), main.__dict__)
        finally:
            sys.path[:] = search_path
        self.assertEqual(discovered, [36])
        self.assertEqual(main.HERE, FROZEN.parent)

    def test_adapter_adoption_controls_and_guard_are_byte_identical(self):
        for name in ['adopt_fixture.py', 'test_adoption.py', 'offline_guard.py']:
            self.assertEqual((HERE / name).read_bytes(), (ORIGINAL_ADOPTION / name).read_bytes())

    def test_original_job_preimage_and_only_exact_route_changes(self):
        original = (ORIGINAL_ADOPTION / 'workflow/swift-cache-state-fixture.yml').read_text()
        self.assertEqual((HERE / 'workflow/original-job.yml').read_text(), original)
        expected = original.replace('            /verification/shared-fixture-default-ci-adoption/\n',
                                    '            /verification/shared-fixture-default-ci-adoption/\n'
                                    '            /verification/shared-fixture-clock-controls-correction/\n', 1)
        expected = expected.replace('MIXER_ADOPTION_DIR="$GITHUB_WORKSPACE/verification/shared-fixture-default-ci-adoption"',
                                    'MIXER_ADOPTION_DIR="$GITHUB_WORKSPACE/verification/shared-fixture-clock-controls-correction"')
        expected = expected.replace('python3 -B "$MIXER_SHARED_INPUT_DIR/test_runner.py" -v',
                                    'python3 -B "$MIXER_ADOPTION_DIR/test_runner.py" -v', 1)
        expected = expected.replace('            ${{ github.workspace }}/verification/shared-fixture-default-ci-adoption/\n',
                                    '            ${{ github.workspace }}/verification/shared-fixture-default-ci-adoption/\n'
                                    '            ${{ github.workspace }}/verification/shared-fixture-clock-controls-correction/\n', 1)
        self.assertEqual((HERE / 'workflow/swift-cache-state-fixture.yml').read_text(), expected)

    def test_existing_compiler_and_fixture_bindings_are_identical(self):
        original = json.loads((ORIGINAL_ADOPTION / 'dependencies.json').read_text())
        corrected = json.loads((HERE / 'dependencies.json').read_text())
        for key in ['compiler_policy', 'fixture_source']:
            self.assertEqual(corrected[key], original[key])
        rows = {row['path']: row for row in corrected['members']}
        for row in original['members']:
            self.assertEqual(rows[row['path']], row)
        runner, base, _ = a.load_runner()
        self.assertIs(runner.rust_identity, base.rust_identity)
        self.assertIs(runner.rust_identity.__globals__, base.__dict__)
        self.assertEqual((runner.CHILD_SECONDS, runner.ACTIVE_SECONDS, runner.CLEANUP_SECONDS,
                          runner.OUTPUT_CAP), (60, 600, 60, 8388608))

    def test_four_mocked_controls_at_low_and_high_host_clock_origins(self):
        scratch = HERE / 'control-scratch'
        scratch.mkdir(exist_ok=True)
        old_tempdir = tempfile.tempdir
        tempfile.tempdir = str(scratch)
        try:
            for corrected in [False, True]:
                for origin in [0.0, 1000.0]:
                    with self.subTest(corrected=corrected, host_clock_origin=origin):
                        module = subject(corrected)
                        commands = []
                        original_mocked = module.RunnerControls.mocked_command
                        def capture(instance):
                            result = original_mocked(instance)
                            commands.append(result[0])
                            return result
                        suite = unittest.TestSuite(module.RunnerControls(name) for name in SELECTED)
                        stream = io.StringIO()
                        with mock.patch.object(module, 'time', types.SimpleNamespace(monotonic=lambda: origin)), \
                             mock.patch.object(module.RunnerControls, 'mocked_command', capture):
                            result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
                        label = ('corrected' if corrected else 'baseline') + '-origin-' + str(int(origin))
                        local = HERE / 'logs/local'
                        local.mkdir(parents=True, exist_ok=True)
                        (local / (label + '.txt')).write_text(stream.getvalue())
                        expected_errors = 4 if not corrected and origin == 0.0 else 0
                        self.assertEqual(result.testsRun, 4)
                        self.assertEqual(len(result.errors), expected_errors)
                        self.assertEqual(result.failures, [])
                        self.assertEqual(len(commands), 4)
                        expected_deadline = 120.0 if corrected else origin + 20
                        self.assertEqual([command.deadline for command in commands], [expected_deadline] * 4)
                        if expected_errors:
                            self.assertEqual([len(command.receipt['commands']) for command in commands], [0] * 4)
                            text = stream.getvalue()
                            self.assertIn('Active deadline exhausted', text)
                            self.assertEqual(text.count('IndexError: list index out of range'), 3)
                        else:
                            self.assertTrue(result.wasSuccessful())
                            self.assertEqual([len(command.receipt['commands']) for command in commands], [1] * 4)
                            self.assertEqual([command.receipt['commands'][0]['effective_timeout_seconds']
                                              for command in commands], [.5] * 4)
                            timeout = commands[3].receipt['commands'][0]
                            self.assertTrue(timeout['timed_out'])
                            self.assertEqual(timeout['elapsed_seconds'], 1.0)
                            hold = commands[0].receipt['commands'][0]['child_resource_usage']
                            self.assertFalse(hold['terminal_facts_verified'])
                            self.assertIsNone(hold['aggregate_delta'])
                        OBSERVATIONS.append({'corrected': corrected, 'host_clock_origin': origin,
                                             'controls_run': 4, 'errors': len(result.errors),
                                             'failures': len(result.failures), 'deadline': expected_deadline,
                                             'command_receipts': sum(len(c.receipt['commands']) for c in commands)})
        finally:
            tempfile.tempdir = old_tempdir
            if list(scratch.iterdir()):
                raise RuntimeError('Selected mocked controls left owned scratch')
            scratch.rmdir()

    @classmethod
    def tearDownClass(cls):
        if DENIED:
            raise RuntimeError('Unexpected denied operation attempt: ' + repr(DENIED))


if __name__ == '__main__':
    program = unittest.main(exit=False, verbosity=2)
    print(json.dumps({'schema': 1, 'source_contract_tests': program.result.testsRun,
                      'passed': program.result.wasSuccessful(), 'clock_observations': OBSERVATIONS,
                      'denied_operation_attempts': DENIED,
                      'all_36_controls_discovered_but_not_run_locally': True,
                      'local_scope': 'Only selected four fully mocked CPU controls; guards installed before subject imports.'},
                     sort_keys=True))
    sys.exit(0 if program.result.wasSuccessful() else 1)
