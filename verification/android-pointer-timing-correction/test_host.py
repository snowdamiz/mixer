#!/usr/bin/env python3
"""Finite host controls only; never Android delivery or native acceptance."""
import argparse
import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import support

WORK = None
RESULTS = []
COMMON, OLD_RUN, OLD_PACKET = support.prior_modules()
OLD_ORACLE = support.load('timing_original_oracle', support.PRIOR / 'oracle.py')
ORACLE = support.load('timing_oracle_tests', support.HERE / 'oracle.py')
RUN = support.load('timing_wrapper_tests', support.HERE / 'run.py')
sys.modules['oracle'] = OLD_ORACLE
sys.modules['run'] = OLD_RUN
sys.modules['bounded_output'] = support.load('bounded_output', support.PRIOR / 'bounded_output.py')
PRIOR_TESTS = support.load('timing_prior_tests', support.PRIOR / 'test_host.py')
PRIOR_TESTS.oracle = ORACLE

class CorrectionTests(unittest.TestCase):
    def fixture(self, name, mutation=None):
        directory = WORK / name
        native, metadata = PRIOR_TESTS.synthetic_oracle_fixture(directory)
        rows = [json.loads(line) for line in (directory / 'pointer-observations.jsonl').read_text().splitlines()]
        if mutation: mutation(native, rows)
        PRIOR_TESTS.rewrite_rows(directory, native, rows)
        return native, directory, metadata

    def test_exact_five_retained_independent_negative_controls(self):
        cases = json.loads((support.REVIEW / 'findings.json').read_text())
        for finding in cases:
            for name in finding['falseAcceptanceCases']:
                with self.subTest(case=name):
                    directory = support.REVIEW / 'host-review-2/reproductions' / name
                    native = json.loads((directory / 'native.json').read_text())
                    metadata = json.loads((directory / 'metadata.json').read_text())
                    original = OLD_ORACLE.validate(native, directory, metadata)
                    with self.assertRaises(ValueError) as caught: ORACLE.validate(native, directory, metadata)
                    RESULTS.append({'case': name, 'finding': finding['id'], 'exactFixture': str(directory.relative_to(support.ROOT)),
                                    'nativeFixture': support.bind(directory / 'native.json'), 'metadata': support.bind(directory / 'metadata.json'),
                                    'oldOracleAccepted': original['status'], 'correctedOracleAccepted': False,
                                    'rejection': str(caught.exception), 'syntheticOnly': True, 'nativeEvidence': False})
        self.assertEqual(len(RESULTS), 5)

    def test_worker_requests_reject_history_for_every_action_type(self):
        for action in (0, 1, 2, 3):
            def mutate(native, rows, action=action):
                row = next(r for r in rows if r['kind'] == 'worker-send' and r['event']['action'] == action)
                row['event']['history'] = [{'eventTime': row['event']['eventTime'] - 1, 'pointers': []}]
            with self.subTest(action=action):
                with self.assertRaisesRegex(ValueError, 'unbatched'): ORACLE.validate(*self.fixture('worker-history-' + str(action), mutate))

    def test_nonmove_down_history_rejects(self):
        def mutate(native, rows):
            for row in rows:
                if row['kind'] in ('activity-entry', 'activity-exit') and row['event']['action'] == 0:
                    row['event']['history'] = [{'eventTime': row['event']['eventTime'] - 1, 'pointers': []}]
        with self.assertRaisesRegex(ValueError, 'non-MOVE'): ORACLE.validate(*self.fixture('down-history', mutate))

    def test_exact_same_millisecond_all_event_boundaries_accept(self):
        def mutate(native, rows):
            for row in rows:
                if row['kind'] == 'worker-send': row['workerBefore'] = row['workerAfter'] = row['event']['eventTime']
                elif row['kind'] == 'activity-entry': row['workerIndependentUptime'] = row['event']['eventTime']
                elif row['kind'] == 'activity-exit': row['uptime'] = row['event']['eventTime']
        self.assertEqual(ORACLE.validate(*self.fixture('same-ms-inclusive', mutate))['requestedEvents'], 124)

    def test_current_coalesced_move_uses_current_worker_not_historical_workers(self):
        native, directory, metadata = self.fixture('coalesced-earlier-workers', PRIOR_TESTS.coalesce)
        rows = [json.loads(line) for line in (directory / 'pointer-observations.jsonl').read_text().splitlines()]
        row = next(r for r in rows if r['kind'] == 'activity-entry' and r['event']['history'])
        worker = next(r for r in rows if r['kind'] == 'worker-send' and r['actionId'] == row['actionId'] and r['event']['eventTime'] == row['event']['eventTime'])
        self.assertTrue(all(sample['eventTime'] < worker['workerBefore'] for sample in row['event']['history']))
        self.assertEqual(ORACLE.validate(native, directory, metadata)['observedActivityEntries'], 117)

    def test_finite_timestamps_reject_nan_infinite_boolean_and_float(self):
        for index, value in enumerate((float('nan'), float('inf'), True, 10001.0)):
            def mutate(native, rows, value=value):
                next(r for r in rows if r['kind'] == 'activity-entry')['workerIndependentUptime'] = value
            with self.subTest(value=value):
                with self.assertRaises(ValueError): ORACLE.validate(*self.fixture('finite-time-' + str(index), mutate))

    def test_finite_coordinate_and_history_offset_guards_survive(self):
        for index, value in enumerate((float('nan'), float('inf'), float('-inf'))):
            def mutate(native, rows, value=value):
                PRIOR_TESTS.coalesce(native, rows)
                for r in rows:
                    if r['kind'] in ('activity-entry', 'activity-exit') and r['event']['history']: r['event']['pointers'][0]['x'] = value
            with self.subTest(value=value):
                with self.assertRaises(ValueError): ORACLE.validate(*self.fixture('finite-history-' + str(index), mutate))

class AdaptationTests(unittest.TestCase):
    def test_loaded_callbacks_and_exact_unchanged_concrete_source(self):
        runner, source, _ = RUN.load_runner()
        self.assertEqual(source.encode(), (support.PRIOR / 'runner-source-4/transformed_runner.py').read_bytes())
        self.assertEqual(runner._pointer_validate_native.__code__.co_filename, str(support.HERE / 'oracle.py'))
        self.assertIs(runner._pointer_runtime_directory, support.runtime_directory)
        self.assertIsNot(runner._pointer_runtime_directory, COMMON.runtime_directory)
        binding = runner._ADAPTATION['timingCorrection']
        self.assertEqual(binding['oracleSHA256'], support.sha(support.HERE / 'oracle.py'))
        self.assertEqual(binding['wrapperSHA256'], support.sha(support.HERE / 'run.py'))
        self.assertEqual(binding['unchangedConcreteRunnerSHA256'], support.CONCRETE)
        self.assertEqual(binding['rootCorrectionSelection'], support.bind(support.SELECTION))
        self.assertEqual(binding['overrides'], ['_pointer_validate_native', '_pointer_runtime_directory'])

    def test_contract_drift_fails_before_loading_reviewed_runner(self):
        with patch.object(RUN, 'CONTRACT_SHA256', '0' * 64), patch.object(support, 'prior_modules', side_effect=AssertionError('must fail first')):
            with self.assertRaises(ValueError): RUN.load_runner()

    def test_implementation_and_tool_drift_fail_closed(self):
        contract = json.loads((support.HERE / 'runner-contract.json').read_text())
        original = support.sha
        for target in (support.HERE / 'oracle.py', Path(next(iter(contract['toolBindings'])))):
            def altered(path, target=target): return '0' * 64 if Path(path) == target else original(path)
            with patch.object(support, 'sha', side_effect=altered):
                with self.assertRaises(ValueError): RUN.load_runner()

    def test_new_wrapper_checks_packet_before_runner_entry(self):
        class Stop(Exception): pass
        fake = type('Packet', (), {'check': lambda self: (_ for _ in ()).throw(Stop())})()
        argv = [str(support.HERE / 'run.py'), '--build', 'candidate-5', '--attempt', 'runtime-99991', '--execute-native']
        with patch.object(sys, 'argv', argv), patch.object(support, 'load', return_value=fake), patch.object(RUN, 'load_runner', side_effect=AssertionError('must not load runner')):
            with self.assertRaises(Stop): RUN.main()
        self.assertFalse((support.HERE / 'runtime/runtime-99991').exists())

    def test_no_dispatch_switch_rejects_before_output_or_packet_read(self):
        argv = [str(support.HERE / 'run.py'), '--build', 'candidate-5', '--attempt', 'runtime-99992']
        with patch.object(sys, 'argv', argv), patch.object(support, 'load', side_effect=AssertionError('must not read packet')), patch('sys.stderr', new=io.StringIO()):
            with self.assertRaises(SystemExit) as caught: RUN.main()
        self.assertEqual(caught.exception.code, 2)
        self.assertFalse((support.HERE / 'runtime/runtime-99992').exists())

    def test_output_policy_exact_seal_containment_and_symlinks(self):
        root = WORK / 'correction-policy'; here = root / 'verification/android-pointer-timing-correction'
        here.mkdir(parents=True); (root / 'docs').mkdir(); (root / 'docs/android-pointer-timing-correction.md').write_text('bound')
        (here / 'nested').mkdir(); (here / 'nested/artifact-seal.json').write_text('{}'); (here / 'nested/receipt.json').write_text('{}')
        (here / 'packet-seal.json').write_text('{}'); runtime = here / 'runtime'; runtime.mkdir(); (runtime / 'runtime-1').mkdir()
        (runtime / 'runtime-1/receipt.json').write_text('{}')
        with patch.object(support, 'HERE', here), patch.object(support, 'ROOT', root):
            for attempt in ('../runtime-2', 'runtime/runtime-2', 'runtime-0', 'runtime-01', '/tmp/runtime-2', 'runtime-1'):
                with self.assertRaises(ValueError): support.runtime_directory(attempt)
            self.assertEqual(support.runtime_directory('runtime-2'), runtime / 'runtime-2')
            bound = support.files(); self.assertEqual(len(bound), 3)
            self.assertIn('verification/android-pointer-timing-correction/nested/artifact-seal.json', bound)
            (runtime / 'runtime-1/receipt.json').write_text('{"changed":true}'); self.assertEqual(bound, support.files())
            (here / 'nested/receipt.json').write_text('{"changed":true}'); self.assertNotEqual(bound, support.files())
            link = runtime / 'link'; link.symlink_to(root / 'docs/android-pointer-timing-correction.md')
            try:
                with self.assertRaises(ValueError): support.files()
                with self.assertRaises(ValueError): support.runtime_directory('runtime-2')
            finally: link.unlink()

def main():
    global WORK
    parser = argparse.ArgumentParser(); parser.add_argument('--work', required=True); parser.add_argument('--results', required=True); args = parser.parse_args()
    WORK = Path(args.work); WORK.mkdir()
    PRIOR_TESTS.WORK = WORK
    PRIOR_TESTS.RUNNER, _, _ = RUN.load_runner()
    prior = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in (PRIOR_TESTS.HostTests, PRIOR_TESTS.RepairTests, PRIOR_TESTS.HostPacketPolicyTests)])
    count = prior.countTestCases(); assert count == 42
    fresh = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in (CorrectionTests, AdaptationTests)])
    added = fresh.countTestCases()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([prior, fresh]))
    support.save(args.results, {'priorTests': count, 'correctionTests': added, 'executed': result.testsRun,
                               'failures': len(result.failures), 'errors': len(result.errors), 'exactFiveControls': RESULTS,
                               'status': 'passed' if result.wasSuccessful() else 'failed', 'syntheticOnly': True, 'nativeCommands': 0})
    raise SystemExit(0 if result.wasSuccessful() else 1)

if __name__ == '__main__': main()
