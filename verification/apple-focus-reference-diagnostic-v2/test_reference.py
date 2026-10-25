"""Host controls only; synthetic reference transitions never become native receipts."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import prepare
import reference_contract as contract


class ReferenceControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.accepted, cls.selected, cls.inherited, _ = prepare.inputs()
        cls.derived = prepare.render(cls.accepted)
        cls.temporary = tempfile.TemporaryDirectory(prefix='pure-oracle-', dir=prepare.BASE)
        cls.pure = Path(cls.temporary.name)
        for rel in prepare.ORACLES:
            name = 'inputs/runtime/verification/' + rel
            path = cls.pure / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(cls.selected[name])
        path = cls.pure / 'inputs/runtime/verification' / prepare.ORACLES[0]
        spec = importlib.util.spec_from_file_location('reference_diagnostic_pure_original_oracle', path)
        cls.oracle = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.oracle)
        cls.old_before = json.loads((prepare.OLD / 'runtime/captures/0001-before-1.json').read_bytes())
        cls.old_after = json.loads((prepare.OLD / 'runtime/captures/0001-after-1.json').read_bytes())
        cls.retained = json.loads((prepare.OLD / 'runtime/captures/0001-keyboard-witness-1.json').read_bytes())

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def synthetic(self, destination='next-focus'):
        before = copy.deepcopy(self.old_before['observation'])
        before['state']['focused'] = False
        after = copy.deepcopy(before)
        witness = copy.deepcopy(self.retained['witness'])
        for snapshot, focus in [(witness['before'], contract.REFERENCE), (witness['after'], destination)]:
            for identifier, element in snapshot['elements'].items():
                element['hasFocus'] = identifier == focus
        binding = copy.deepcopy(self.retained['binding'])
        baseline = copy.deepcopy(before)
        baseline.update(keyboardWitness=witness, keyboardBinding=binding)
        verdict = self.oracle.verdict('diagnostic', contract.CASE, 'native-keyboard', baseline, after, False)
        premise = {'schema': contract.SCHEMA, 'case': contract.CASE, 'phase': 'acquire', 'generation': witness['generation'],
            'actionIndex': witness['actionIndex'], 'requiredFocus': contract.REFERENCE, 'observedFocus': contract.REFERENCE,
            'passed': True, 'actionInjectionCount': 0, 'before': copy.deepcopy(witness['before'])}
        return premise, verdict, {'before': before, 'after': after, 'fileChanged': False}

    def classify(self, premise=None, verdict=None, pair=None):
        if premise is None: premise, verdict, pair = self.synthetic()
        return contract.result([premise], [] if verdict is None else [verdict], self.oracle, [] if pair is None else [pair])

    def test_01_exact_39_source_members_and_two_changes(self):
        self.assertEqual(len(self.derived), 39)
        self.assertEqual({name for name in self.derived if self.derived[name] != self.accepted[name]}, {prepare.APP, prepare.RUNNER})

    def test_02_app_change_only_initial_focus_preference(self):
        self.assertEqual(self.derived[prepare.APP].replace(b'{ [referenceButton] }', b'{ [toggle] }'), self.accepted[prepare.APP])

    def test_03_original_six_test_methods_unchanged(self):
        for name in ['test010EnabledFromOff', 'test020EnabledFromOn', 'test030StaleFromOff', 'test040StaleFromOn', 'test050DisabledFromOff', 'test060DisabledFromOn']:
            original = next(line for line in self.accepted[prepare.RUNNER].splitlines() if b'func ' + name.encode() + b'()' in line)
            self.assertEqual(self.derived[prepare.RUNNER].splitlines().count(original), 1)

    def test_04_new_method_exactly_one_tab_without_acquisition_loop(self):
        text = self.derived[prepare.RUNNER].decode()
        method = text.split('    func test010ReferenceFirstTab() throws {\n', 1)[1].split('    }\n', 1)[0]
        self.assertEqual(method, '        _ = try launchCase("keyboard-enabled-off", initial: false)\n        try key("acquire", "tab", requiredFocusBefore: "plain-uibutton-reference")\n')

    def test_05_authoritative_precondition_before_public_call(self):
        text = self.derived[prepare.RUNNER].decode()
        before = text.index('        let before = try ax("before")\n')
        guard = text.index('            guard premisePassed else { throw Failure.focus("Reference first-Tab precondition failed before key injection") }')
        call = text.index('        if value == "shift-tab" { app.typeKey')
        self.assertLess(before, guard)
        self.assertLess(guard, call)

    def test_06_native_key_and_observation_timebounds_unchanged(self):
        old = self.accepted[prepare.RUNNER].decode(); new = self.derived[prepare.RUNNER].decode()
        for start, end in [('        let start = ProcessInfo.processInfo.systemUptime\n', '        let result = try bridge("evaluate",'),
                           ('    private func focusOnlyDiagnostic(', '    private func focus(_ snapshot:')]:
            self.assertEqual(old[old.index(start):old.index(end, old.index(start))], new[new.index(start):new.index(end, new.index(start))])

    def test_07_fixed_three_ids_unchanged(self):
        line = b'    private let ids = ["authored-toggle", "plain-uibutton-reference", "next-focus"]'
        self.assertIn(line, self.accepted[prepare.RUNNER].splitlines())
        self.assertIn(line, self.derived[prepare.RUNNER].splitlines())

    def test_08_packet_generation_deterministic(self):
        self.assertEqual(prepare.generated(), prepare.generated())

    def test_09_source_archive_exact_round_trip(self):
        with tempfile.TemporaryDirectory(prefix='archive-control-', dir=prepare.BASE) as temporary:
            path = Path(temporary) / 'sources.tar.gz'
            rows = prepare.manifest(self.derived, self.inherited['materializedSources'])
            prepare.write_archive(path, self.derived, rows)
            self.assertEqual(prepare.archive(path, rows, 'accepted/', prepare.row(path)['sha256']), self.derived)

    def test_10_archive_corruption_fails_closed(self):
        with tempfile.TemporaryDirectory(prefix='corrupt-control-', dir=prepare.BASE) as temporary:
            path = Path(temporary) / 'changed.tar.gz'
            path.write_bytes((prepare.SOURCES_BASE / 'accepted-sources.tar.gz').read_bytes() + b'changed')
            with self.assertRaises(ValueError):
                prepare.archive(path, {}, 'accepted/', prepare.row(prepare.SOURCES_BASE / 'accepted-sources.tar.gz')['sha256'])

    def test_11_ambiguous_derivation_anchor_rejected(self):
        with self.assertRaises(ValueError): prepare.once('twice twice', 'twice', 'new')

    def test_12_original_failure_replayed_completely_unchanged(self):
        before = copy.deepcopy(self.old_before['observation'])
        before.update(keyboardWitness=self.retained['witness'], keyboardBinding=self.retained['binding'])
        replayed = self.oracle.verdict('diagnostic', contract.CASE, 'native-keyboard', before, self.old_after['observation'], self.old_before['signature'] != self.old_after['signature'])
        recorded = copy.deepcopy(self.old_after['verdict'])
        for field in ['generation','actionIndex','ownedSimulatorIdentity']: recorded.pop(field)
        self.assertEqual(replayed, recorded)
        self.assertEqual([name for name, value in replayed['predicates'].items() if value is not True], ['actualNativeFocusTraversal'])

    def test_13_synthetic_reference_to_next_passes_original_oracle(self):
        p, v, pair = self.synthetic()
        self.assertTrue(v['passed'], v)
        self.assertTrue(self.classify(p, v, pair)['singleTabDiagnosticEvidencePassed'])

    def test_14_synthetic_reference_to_no_focus_fails_original_oracle(self):
        p, v, pair = self.synthetic(None)
        result = self.classify(p, v, pair)
        self.assertFalse(v['passed'])
        self.assertFalse(v['predicates']['actualNativeFocusTraversal'])
        self.assertEqual(result['status'], 'one-original-oracle-result')
        self.assertEqual(result['keyInjectionCount'], 1)
        self.assertFalse(result['singleTabDiagnosticEvidencePassed'])

    def test_15_same_reference_after_tab_fails_original_oracle(self):
        p, v, pair = self.synthetic(contract.REFERENCE)
        self.assertFalse(self.classify(p, v, pair)['singleTabDiagnosticEvidencePassed'])

    def test_16_failed_premise_proves_zero_injections(self):
        p, _, _ = self.synthetic()
        p['before']['elements'][contract.REFERENCE]['hasFocus'] = False
        p.update(passed=False, observedFocus=None)
        result = self.classify(p)
        self.assertEqual(result['status'], 'failed-reference-precondition')
        self.assertEqual(result['keyInjectionCount'], 0)
        self.assertFalse(result['singleTabDiagnosticEvidencePassed'])

    def test_17_failed_premise_with_result_rejected(self):
        p, v, pair = self.synthetic()
        p['before']['elements'][contract.REFERENCE]['hasFocus'] = False
        p.update(passed=False, observedFocus=None)
        self.assertEqual(self.classify(p, v, pair)['status'], 'invalid-or-incomplete-evidence')

    def test_18_true_premise_without_result_never_infers_zero(self):
        p, _, _ = self.synthetic()
        result = self.classify(p)
        self.assertEqual(result['status'], 'incomplete-after-passing-precondition')
        self.assertIsNone(result['keyInjectionCount'])

    def test_19_duplicate_original_results_rejected(self):
        p, v, pair = self.synthetic()
        result = contract.result([p], [v, v], self.oracle, [pair])
        self.assertEqual(result['status'], 'invalid-or-incomplete-evidence')

    def test_20_mutated_original_predicate_set_rejected(self):
        p, v, pair = self.synthetic()
        v['predicates'].pop('pairedNativeFocusBefore')
        self.assertEqual(self.classify(p, v, pair)['status'], 'invalid-or-incomplete-evidence')

    def test_21_mutated_witness_binding_rejected(self):
        p, v, pair = self.synthetic()
        v['keyboardBinding']['generation'] += 1
        self.assertEqual(self.classify(p, v, pair)['status'], 'invalid-or-incomplete-evidence')

    def test_22_missing_application_replay_evidence_rejected(self):
        p, v, _ = self.synthetic()
        self.assertEqual(self.classify(p, v)['status'], 'invalid-or-incomplete-evidence')

    def test_23_success_cannot_complete_original_cursor(self):
        p, v, pair = self.synthetic()
        cursor = self.oracle.Cursor(contract.CASE)
        for command in ['resume', 'reset']: cursor.command(command)
        cursor.advance(v['keyboardWitness'])
        self.assertEqual(cursor.acquisitions, 1)
        self.assertFalse(cursor.complete)
        self.assertFalse(cursor.acquired)
        result = self.classify(p, v, pair)
        for name in ['completeCaseSet','cursorCompletionCredit','runPassed','fullSixCaseQualification','nativeKeyboardQualification','carrierAccepted','gaAccepted']:
            self.assertIs(result[name], False)

    def test_24_unknown_precondition_fields_rejected(self):
        p, v, pair = self.synthetic(); p['bypass'] = True
        self.assertEqual(self.classify(p, v, pair)['status'], 'invalid-or-incomplete-evidence')

    def test_25_only_nine_pure_files_imported_and_temporary(self):
        self.assertEqual(len([path for path in self.pure.rglob('*') if path.is_file()]), 9)
        self.assertEqual({str(path.relative_to(self.pure)) for path in self.pure.rglob('*') if path.is_file()},
                         {'inputs/runtime/verification/' + rel for rel in prepare.ORACLES})

    def test_26_wrong_initial_focus_claim_rejected(self):
        p, v, pair = self.synthetic(); p['observedFocus'] = 'authored-toggle'
        self.assertEqual(self.classify(p, v, pair)['status'], 'invalid-or-incomplete-evidence')


    def reject_frozen_counterexample(self, name):
        evidence = json.loads((prepare.REVIEW / 'counterexamples.json').read_bytes())
        matches = [item for item in evidence['examples'] if item['name'] == name]
        self.assertEqual(len(matches), 1)
        item = matches[0]
        self.assertIs(item['syntheticOnly'], True)
        self.assertIs(item['actual']['singleTabDiagnosticEvidencePassed'], True)
        result = contract.result(item['premises'], item['verdicts'], self.oracle, item['observations'])
        self.assertEqual(result['status'], 'invalid-or-incomplete-evidence')
        self.assertIs(result['singleTabDiagnosticEvidencePassed'], False)
        self.assertIsNone(result['keyInjectionCount'])
        self.assertEqual(result['returnedPublicKeyWitnessCount'], 0)
        if not hasattr(type(self), 'regression_outcomes'): type(self).regression_outcomes = []
        type(self).regression_outcomes.append({'name': name, 'syntheticOnly': True,
            'input': 'Frozen independent-review counterexample', 'priorStatus': item['actual']['status'],
            'priorDiagnosticSuccess': item['actual']['singleTabDiagnosticEvidencePassed'],
            'status': result['status'], 'failure': result.get('failure'),
            'singleTabDiagnosticEvidencePassed': result['singleTabDiagnosticEvidencePassed'],
            'keyInjectionCount': result['keyInjectionCount'], 'returnedPublicKeyWitnessCount': result['returnedPublicKeyWitnessCount']})
        for field in ['completeCaseSet', 'cursorCompletionCredit', 'runPassed', 'fullSixCaseQualification',
                      'nativeKeyboardQualification', 'carrierAccepted', 'gaAccepted']:
            self.assertIs(result[field], False)

    def test_27_originalOraclePassed_bool_to_int_frozen_counterexample_rejected(self):
        self.reject_frozen_counterexample('typed-original-verdict-originalOraclePassed')

    def test_28_pairedFocusDisagreement_bool_to_int_frozen_counterexample_rejected(self):
        self.reject_frozen_counterexample('typed-original-verdict-pairedFocusDisagreement')

    def test_29_missingAppFocusUpdateSignal_bool_to_int_frozen_counterexample_rejected(self):
        self.reject_frozen_counterexample('typed-original-verdict-missingAppFocusUpdateSignal')

    def test_30_nativeAppFocusedBefore_bool_to_int_frozen_counterexample_rejected(self):
        self.reject_frozen_counterexample('typed-original-verdict-nativeAppFocusedBefore')

    def test_31_nativeAppFocusedAfter_bool_to_int_frozen_counterexample_rejected(self):
        self.reject_frozen_counterexample('typed-original-verdict-nativeAppFocusedAfter')

    def test_32_outer_generation_float_frozen_counterexample_rejected(self):
        self.reject_frozen_counterexample('typed-reporting-generation')

    def test_33_outer_actionIndex_float_frozen_counterexample_rejected(self):
        self.reject_frozen_counterexample('typed-reporting-actionIndex')

    def test_34_huge_integer_uptime_returns_structured_failure(self):
        p, v, pair = self.synthetic()
        p['before']['uptime'] = 10 ** 1000
        result = self.classify(p, v, pair)
        self.assertEqual(result['status'], 'invalid-or-incomplete-evidence')
        self.assertTrue(result['failure'].startswith('OverflowError: '))
        self.assertIs(result['singleTabDiagnosticEvidencePassed'], False)
        self.assertIsNone(result['keyInjectionCount'])
        if not hasattr(type(self), 'regression_outcomes'): type(self).regression_outcomes = []
        type(self).regression_outcomes.append({'name': 'malformed-large-integer-uptime', 'syntheticOnly': True,
            'input': 'Exact independent-review mutation: premise before uptime = 10 ** 1000',
            'priorStatus': 'OverflowError: int too large to convert to float', 'status': result['status'],
            'failure': result.get('failure'), 'singleTabDiagnosticEvidencePassed': result['singleTabDiagnosticEvidencePassed'],
            'keyInjectionCount': result['keyInjectionCount'], 'returnedPublicKeyWitnessCount': result['returnedPublicKeyWitnessCount']})


if __name__ == '__main__': unittest.main()
