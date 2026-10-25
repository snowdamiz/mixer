"""Host controls only. Retained JSON is data; no selected code is executed."""
import copy
import json
import re
import sys
import unittest

import focus_diagnostic as diagnostic
import prepare


def fixed_focus(snapshot):
    """Independent limited predicate model, not an oracle verdict reexecution."""
    rows = snapshot['elements']
    if set(rows) != set(diagnostic.IDS):
        raise ValueError('Fixed three-ID membership changed')
    focused = [name for name in diagnostic.IDS if rows[name]['hasFocus'] is True]
    if len(focused) > 1:
        raise ValueError('Multiple focused fixed IDs')
    return focused[0] if focused else None


def traversal(witness):
    before, after = fixed_focus(witness['before']), fixed_focus(witness['after'])
    return before != after and after is not None


class RetainedDecisionHarness:
    """Opaque failed-decision/cursor test double, never a native authority.

    Returns the retained verdict bytes as data only. It tests the diagnostic
    adapter's isolation and the fail-latched branch; it grants no oracle credit.
    """
    def __init__(self, witness, verdict):
        self.expected_witness = witness
        self.verdict = copy.deepcopy(verdict)
        self.failed = False
        self.complete = False
        self.acquired = False
        self.acquisitions = 0
        self.phase_index = 0
        self.actions = []

    def evaluate(self, body):
        if set(body) != {'keyboardWitness'} or body['keyboardWitness'] is not self.expected_witness:
            raise ValueError('Diagnostic adapter changed strict input')
        self.actions.append(('evaluate', body))
        if self.verdict['passed'] is True:
            self.acquisitions += 1
        else:
            self.failed = True
        return self.verdict

    def begin(self):
        if not self.complete:
            raise ValueError('Prior application case must complete before next begin')


def apply_patch(original, patch):
    """Independent in-memory application validates every emitted diff hunk."""
    files = dict(original)
    lines = patch.splitlines(True)
    index = 0
    while index < len(lines):
        old = lines[index].removeprefix('--- ').strip()
        new = lines[index + 1].removeprefix('+++ ').strip()
        if not lines[index].startswith('--- ') or not lines[index + 1].startswith('+++ b/'):
            raise ValueError('Unexpected file header')
        name = new[2:]
        source = [] if old == '/dev/null' else files[old[2:]].splitlines(True)
        target, position = [], 0
        index += 2
        while index < len(lines) and lines[index].startswith('@@ '):
            match = re.fullmatch(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@\n', lines[index])
            if match is None:
                raise ValueError('Invalid hunk header')
            start = int(match[1]) - 1 if int(match[1]) else 0
            target.extend(source[position:start]); position = start
            index += 1
            removed = added = 0
            while index < len(lines) and not lines[index].startswith(('@@ ', '--- ')):
                line = lines[index]; index += 1
                if line[0] in ' -':
                    if position >= len(source) or source[position] != line[1:]:
                        raise ValueError('Patch context mismatch')
                    position += 1; removed += 1
                if line[0] in ' +':
                    target.append(line[1:]); added += 1
            if removed != int(match[2] or 1) or added != int(match[4] or 1):
                raise ValueError('Hunk count mismatch')
        target.extend(source[position:]); files[name] = ''.join(target)
    return files


class FocusDiagnosticControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = prepare.verified_inputs()
        cls.packet = json.loads(cls.inputs[prepare.V3 + 'runtime/captures/0001-keyboard-witness-1.json'])
        cls.after = json.loads(cls.inputs[prepare.V3 + 'runtime/captures/0001-after-1.json'])
        cls.witness = cls.packet['witness']
        cls.binding = {key: cls.packet['binding'][key] for key in ('case', 'generation', 'actionIndex')}
        cls.original, cls.changed = prepare.render(cls.inputs)

    def sample_diagnostic(self):
        return {'schema': diagnostic.SCHEMA, 'authoritative': False, **self.binding,
                'followUp': {'captureStatus': 'complete', 'rows': [{'identifier': 'authored-toggle', 'hasFocus': True}]}}

    def evaluate_with(self, value):
        harness = RetainedDecisionHarness(self.witness, self.after['verdict'])
        saved = []
        body = diagnostic.strip_and_retain({'keyboardWitness': self.witness, 'focusDiagnostic': value},
                                           self.binding, lambda name, value: saved.append((name, value)))
        result = harness.evaluate(body)
        return harness, saved, result

    def test_sealed_null_witness_remains_the_single_predicate_failure(self):
        self.assertEqual(fixed_focus(self.witness['before']), 'authored-toggle')
        self.assertIsNone(fixed_focus(self.witness['after']))
        self.assertFalse(traversal(self.witness))
        verdict = self.after['verdict']
        self.assertIs(verdict['passed'], False)
        self.assertEqual([key for key, value in verdict['predicates'].items() if value is not True], ['actualNativeFocusTraversal'])
        self.assertEqual(verdict['keyboardWitness'], self.witness)

    def test_favorable_second_sample_cannot_advance_failed_cursor(self):
        original_bytes = prepare.stable_json(self.witness)
        harness, saved, result = self.evaluate_with(self.sample_diagnostic())
        self.assertEqual(result, self.after['verdict'])
        self.assertTrue(harness.failed)
        self.assertEqual((harness.complete, harness.acquired, harness.acquisitions, harness.phase_index), (False, False, 0, 0))
        with self.assertRaisesRegex(ValueError, 'Prior application case'):
            harness.begin()
        self.assertEqual(len(harness.actions), 1)
        self.assertEqual(saved[0][0], 'focus-diagnostic-1')
        self.assertEqual(prepare.stable_json(self.witness), original_bytes)

    def test_prefocused_launch_still_requires_first_tab(self):
        harness = self.changed['harness/UITests/ToggleUITests.swift']
        original = self.original['harness/UITests/ToggleUITests.swift']
        self.assertEqual(harness[harness.index('    private func acquire()'):], original[original.index('    private func acquire()'):])
        self.assertIn('let after = try key("acquire", "tab")', harness)
        self.assertEqual(harness.count('.typeKey('), original.count('.typeKey('))
        self.assertFalse(traversal(self.witness))

    def test_positive_fixed_destination_and_closed_membership_controls(self):
        witness = copy.deepcopy(self.witness)
        witness['after']['elements']['next-focus']['hasFocus'] = True
        self.assertTrue(traversal(witness))
        witness['after']['elements']['outside'] = {'hasFocus': True}
        with self.assertRaisesRegex(ValueError, 'membership'):
            traversal(witness)

    def test_context_explicit_null_is_distinct_from_outside_identifier(self):
        null = diagnostic.endpoint(None)
        outside = diagnostic.endpoint({'identifier': 'native-scroll-row', 'class': 'UILabel',
                                       'identity': 'fixture-only', 'frame': {'x': 1, 'y': 2, 'width': 3, 'height': 4}})
        anonymous = diagnostic.endpoint({'identifier': None, 'class': 'UIView', 'identity': 'anonymous', 'frame': {}})
        self.assertEqual(diagnostic.endpoint_scope(null), 'explicit-null')
        self.assertEqual(diagnostic.endpoint_scope(outside), 'outside-fixed-ids')
        self.assertEqual(diagnostic.endpoint_scope(anonymous), 'outside-fixed-ids')
        self.assertEqual(anonymous['state'], 'item')
        self.assertIsNone(null['class'])
        self.assertEqual(outside['class'], 'UILabel')

    def test_context_trace_is_bounded_with_exact_drop_accounting(self):
        trace = diagnostic.ContextBuffer()
        for i in range(139):
            trace.append('controller', None, None, 16, i)
        self.assertEqual((len(trace.entries), trace.dropped, trace.revision), (128, 11, 139))
        self.assertEqual([row['sequence'] for row in trace.entries], list(range(1, 129)))
        self.assertEqual(trace.entries[-1]['uptime'], 127)
        self.assertEqual(trace.entries[-1]['heading'], 16)

    def test_non_atomic_per_row_intervals_are_retained(self):
        rows = [{'startedUptime': 2, 'finishedUptime': 3}, {'startedUptime': 4, 'finishedUptime': 5}]
        status = diagnostic.observation_status(rows, 1, 6)
        self.assertFalse(status['atomic'])
        self.assertEqual(status['rowCount'], 2)
        rows[1]['startedUptime'] = 2.5
        with self.assertRaisesRegex(ValueError, 'Nonmonotonic'):
            diagnostic.observation_status(rows, 1, 6)

    def test_second_focus_observation_is_one_fixed_pass_with_original_deadline(self):
        clock = [10.0]; calls = []
        def read(identifier):
            calls.append(identifier); clock[0] += .01
            return identifier == 'authored-toggle'
        observation = diagnostic.focus_only_once(read, lambda: clock[0], 10.1)
        self.assertEqual(calls, list(diagnostic.IDS))
        self.assertEqual(observation['deadlineUptime'], 10.1)
        self.assertEqual(observation['captureStatus'], 'complete')
        self.assertFalse(observation['atomic'])
        self.assertEqual(len(observation['rows']), 3)

    def test_late_uninterruptible_read_is_incomplete_and_stops(self):
        clock = [10.0]; calls = []
        def read(identifier):
            calls.append(identifier); clock[0] += 1
            return True
        observation = diagnostic.focus_only_once(read, lambda: clock[0], 10.15)
        self.assertEqual(calls, ['authored-toggle'])
        self.assertEqual(observation['deadlineUptime'], 10.15)
        self.assertEqual(observation['captureStatus'], 'incomplete-budget')
        self.assertGreater(observation['finishedUptime'], observation['deadlineUptime'])

    def test_expired_budget_makes_no_additional_reads(self):
        calls = []
        observation = diagnostic.focus_only_once(calls.append, lambda: 12, 11)
        self.assertEqual(calls, [])
        self.assertEqual(observation['captureStatus'], 'incomplete-budget')

    def test_invalid_and_oversize_diagnostics_never_replace_original_failure(self):
        for value in (None, {'schema': diagnostic.SCHEMA, 'authoritative': True},
                      {**self.sample_diagnostic(), 'generation': True},
                      {**self.sample_diagnostic(), 'generation': 2},
                      {**self.sample_diagnostic(), 'padding': 'x' * 4096}):
            with self.subTest(value=type(value).__name__):
                harness, saved, result = self.evaluate_with(value)
                self.assertIs(result['passed'], False)
                self.assertTrue(harness.failed)
                self.assertIn('incomplete-', saved[0][1]['captureStatus'])
                self.assertLessEqual(len(prepare.stable_json(saved[0][1])), 4096)

    def test_diagnostic_storage_failure_is_not_converted_to_acceptance(self):
        def fail(*_):
            raise OSError('fixture storage failure')
        with self.assertRaisesRegex(OSError, 'storage failure'):
            diagnostic.strip_and_retain({'keyboardWitness': self.witness, 'focusDiagnostic': self.sample_diagnostic()}, self.binding, fail)

    def test_canonical_witness_only_route_is_untouched(self):
        body = {'keyboardWitness': self.witness}
        self.assertIs(diagnostic.strip_and_retain(body, self.binding, lambda *_: self.fail('unexpected save')), body)
        malformed = {'keyboardWitness': self.witness, 'focusDiagnostic': {}, 'extra': True}
        self.assertIs(diagnostic.strip_and_retain(malformed, self.binding, lambda *_: self.fail('unexpected save')), malformed)

    def test_generated_patch_applies_exactly_to_bound_sources_in_memory(self):
        patch, manifest_bytes = prepare.artifacts()
        self.assertEqual(apply_patch(self.original, patch.decode()), self.changed)
        manifest = json.loads(manifest_bytes)
        self.assertEqual(len(manifest['preparedSources']), 6)
        self.assertLess(len(patch), 30000)
        self.assertFalse(manifest['commandFinalizationChanged'])
        self.assertFalse(manifest['runtimeSelected'])

    def test_original_bridge_authority_branch_remains_byte_identical(self):
        target = 'runtime/verification/apple-toggle-keyboard-focus/keyboard_bridge.py'
        addition = ('            if op==\'evaluate\' and self.current is not None and \'baseline\' in self.current:\n'
                    '                body=focus_diagnostic.strip_and_retain(body,{\'case\':self.current[\'case\'],\'generation\':self.generation,\'actionIndex\':self.current[\'actionIndex\']},self.save)\n')
        restored = self.changed[target].replace('import focus_diagnostic as focus_diagnostic\n', '').replace(addition, '')
        self.assertEqual(restored, self.original[target])
        self.assertNotIn('keyboard_oracle.py', '\n'.join(self.changed))
        self.assertNotIn('harness.py', '\n'.join(self.changed))

    def test_original_trace_sequence_and_focus_behavior_stay_separate(self):
        original = self.original['source/Prototype/DiagnosticTrace.swift']
        changed = self.changed['source/Prototype/DiagnosticTrace.swift']
        self.assertEqual(changed[changed.index('    func append(_ kind:'):], original[original.index('    func append(_ kind:'):])
        for name in ('source/Prototype/main.swift', 'source/Prototype/AuthoredToggleCarrier.swift'):
            self.assertEqual(self.changed[name].count('setNeedsFocusUpdate()'), self.original[name].count('setNeedsFocusUpdate()'))
            self.assertEqual(self.changed[name].count('updateFocusIfNeeded()'), self.original[name].count('updateFocusIfNeeded()'))
        self.assertIn('focusContextEntries.count < 128', changed)
        self.assertIn('focusContextDropped += 1', changed)

    def test_no_selected_runtime_module_was_imported(self):
        forbidden = (prepare.V3, prepare.V9)
        for module in tuple(sys.modules.values()):
            path = str(getattr(module, '__file__', '') or '')
            self.assertFalse(any(segment in path for segment in forbidden), path)


if __name__ == '__main__':
    unittest.main(verbosity=2)
