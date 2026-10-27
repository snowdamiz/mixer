"""Bounded host tests; finite actual-row mutations, no Java/product execution."""
import copy
import json
import math
from pathlib import Path
import unittest

import check_descriptor_joins as d


class DescriptorJoinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.joiner = d.Joiner(d.Inputs())
        cls.fixtures = {}
        for name in ['direct-commitText.rows.jsonl.gz', 'query-getSelectedText.rows.jsonl.gz', 'query-getExtractedText.rows.jsonl.gz', 'direct-setComposingRegionWithAttributes.rows.jsonl.gz', 'boundary-000.rows.jsonl.gz', 'direct-close.rows.jsonl.gz']:
            file = next(x for x in cls.joiner.ledger['files'] if x['file'] == name)
            data = cls.joiner.inputs.read(file['input_path'] + '.compact.jsonl')
            cls.fixtures[name] = (list(map(d.loads, data.splitlines())), file['rows'])

    def row(self, name='direct-commitText.rows.jsonl.gz', index=0):
        rows, prior = self.fixtures[name]
        return copy.deepcopy(rows[index]), copy.deepcopy(prior[index])

    def test_exact38_and_source_dispatches(self):
        contract = self.joiner.contract
        self.assertEqual(len(contract), 38)
        self.assertEqual(sum('producer_dispatch' in x for x in contract.values()), 28)
        self.assertEqual(contract['commitText']['declaring_class'], 'dev/mixer/android/NativeEditorConnectionV2$Base')
        self.assertEqual(contract['commitTextWithAttributes']['declaring_class'], 'dev/mixer/android/NativeEditorConnectionV2$Api33')
        self.assertEqual(contract['requestCursorUpdatesFiltered']['descriptor'], '(II)Z')

    def test_actual_direct_and_query_rows(self):
        for name in ['direct-commitText.rows.jsonl.gz', 'query-getSelectedText.rows.jsonl.gz', 'query-getExtractedText.rows.jsonl.gz']:
            with self.subTest(name=name):
                row, prior = self.row(name)
                out = self.joiner.row(row, prior, name)
                self.assertEqual(out['public_result']['value']['status'], 'passed')
                comp = out['native_completions'][0]
                self.assertEqual(comp['status'], 'joined-normal-return')
                self.assertEqual(comp['compiled_callee']['owner'], 'android/view/inputmethod/InputConnection')
                self.assertEqual(comp['resolved_declaring_class'], 'android/view/inputmethod/BaseInputConnection')

    def test_public_refusal_and_native_snapshot_are_independent(self):
        name = 'query-getExtractedText.rows.jsonl.gz'
        row, prior = self.row(name, 1)
        self.assertEqual(row['actual_operation_outcome'], {'kind': 'null'})
        self.assertEqual(row['selected_actual_native_completions'][0]['value']['kind'], 'typed-snapshot')
        out = self.joiner.row(row, prior, name)
        self.assertEqual(out['public_result']['value']['basis'], 'nullable-reference')
        self.assertEqual(out['native_completions'][0]['status'], 'joined-normal-return')

    def test_two_standard_edges_only(self):
        self.assertEqual(self.joiner.assignable('java/lang/String', 'java/lang/CharSequence')['basis'], 'official-JavaSE17-specification')
        self.assertEqual(self.joiner.assignable('java/lang/String', 'java/lang/Object')['basis'], 'official-JavaSE17-specification')
        self.assertEqual(self.joiner.assignable('java/lang/String', 'java/io/Serializable')['status'], 'unresolved')
        self.assertEqual(self.joiner.assignable('java/lang/Integer', 'java/lang/Number')['status'], 'unresolved')

    def test_retained_hierarchy_and_incompatible_reference(self):
        out = self.joiner.assignable('android/text/SpannableStringBuilder', 'java/lang/CharSequence')
        self.assertEqual(out['status'], 'passed')
        self.assertEqual(out['basis'], 'retained-compiled-class-hierarchy')
        self.assertIn('android/text/Editable', out['path'])
        self.assertEqual(self.joiner.assignable('android/view/inputmethod/ExtractedText', 'android/os/Handler')['status'], 'failed')

    def test_full_descriptor_grammar(self):
        # F2 migration: JVMS17 4.2.1/4.2.2 permits '(' in a ClassName segment.
        # Exact original24 source remains unchanged in original_producer_tests.py.
        for text in ['()V', '(ZBCSIJFD)Ljava/lang/Object;', '([[I[Ljava/lang/String;)J', '(' + 'I' * 255 + ')V', '()Lfoo/(Bar;']:
            with self.subTest(valid=text[:40]):
                d.descriptor(text)
        for text in ['', 'I', '(V)I', '()Q', '()L;', '()Ljava.lang.String;', '()Lfoo//Bar;', '(I)Vx', '([V)V', '()Ljava/lang/Object', '(I))V', '(' + 'J' * 128 + ')V', '()[' + '[' * 255 + 'I']:
            with self.subTest(invalid=text[:40]):
                with self.assertRaises(d.Refusal):
                    d.descriptor(text)

    def test_primitive_kind_and_exact_integer_ranges(self):
        for result, bits in [('B', 8), ('S', 16), ('I', 32), ('J', 64)]:
            for value in [-(2 ** (bits - 1)), 2 ** (bits - 1) - 1]:
                with self.subTest(result=result, valid=value):
                    self.assertEqual(self.joiner.value({'kind': 'integer', 'value': value}, result)['status'], 'passed')
            for value in [-(2 ** (bits - 1)) - 1, 2 ** (bits - 1), True, 1.0]:
                with self.subTest(result=result, invalid=value):
                    with self.assertRaises(d.Refusal):
                        self.joiner.value({'kind': 'integer', 'value': value}, result)
        with self.assertRaises(d.Refusal):
            self.joiner.value({'kind': 'integer', 'value': 1}, 'Z')
        with self.assertRaises(d.Refusal):
            self.joiner.value({'kind': 'boolean', 'value': 1}, 'Z')

    def test_floating_character_void_and_null_boundaries(self):
        for value in [0.0, -0.0, 3.4028234663852886e38]:
            self.joiner.value({'kind': 'floating', 'value': value}, 'F')
        for value in [3.4028236e38, math.inf, math.nan, 1]:
            with self.subTest(invalid=value):
                with self.assertRaises(d.Refusal):
                    self.joiner.value({'kind': 'floating', 'value': value}, 'F')
        for value in ['\0', '\uffff', '\ud800']:
            self.joiner.value({'kind': 'character', 'value': value}, 'C')
        for value in ['😀', '', 'xy']:
            with self.assertRaises(d.Refusal):
                self.joiner.value({'kind': 'character', 'value': value}, 'C')
        self.joiner.value({'kind': 'void'}, 'V')
        self.joiner.value({'kind': 'null'}, 'V', native=True)
        self.joiner.value({'kind': 'null'}, 'Ljava/lang/String;')
        with self.assertRaises(d.Refusal):
            self.joiner.value({'kind': 'null'}, 'I')
        with self.assertRaises(d.Refusal):
            self.joiner.value({'kind': 'void'}, 'V', native=True)

    def test_reference_identity_and_class_coherent_mutations(self):
        cases = [
            ({'kind': 'reference', 'class': 'android.os.Handler', 'identity': 'android.os.Handler@99'}, 'Landroid/view/inputmethod/ExtractedText;'),
            ({'kind': 'string', 'value': 'x', 'identity': 'java.lang.Object@99'}, 'Ljava/lang/CharSequence;'),
            ({'kind': 'reference', 'class': 'bad;Class', 'identity': 'bad;Class@99'}, 'Ljava/lang/Object;'),
        ]
        for value, desc in cases:
            with self.subTest(value=value):
                with self.assertRaises(d.Refusal):
                    self.joiner.value(value, desc)
        unknown = self.joiner.value({'kind': 'reference', 'class': 'missing.Example', 'identity': 'missing.Example@99'}, 'Ljava/lang/CharSequence;')
        self.assertEqual(unknown['status'], 'unresolved')
        self.assertEqual(self.joiner.assignable('[Ljava/lang/String;', '[Ljava/lang/CharSequence;')['status'], 'unresolved')

    def test_public_family_wrong_exact_file_and_return_type(self):
        row, prior = self.row()
        row['family'] = prior['family'] = 'commitTextWithAttributes'
        with self.assertRaises(d.Refusal):
            self.joiner.row(row, prior, 'direct-commitText.rows.jsonl.gz')
        row, prior = self.row()
        row['actual_operation_outcome'] = {'kind': 'integer', 'value': 1}
        with self.assertRaises(d.Refusal):
            self.joiner.row(row, prior, 'direct-commitText.rows.jsonl.gz')

    def test_compiled_caller_mutations(self):
        row, _ = self.row()
        original = row['selected_actual_native_completions'][0]
        mutations = [('bci', True), ('bci', 7), ('method', 'lambda$commitText$7'), ('descriptor', '(Ljava/lang/Object;I)Ljava/lang/Boolean;'), ('class', 'dev.mixer.android.NativeEditorConnectionV2$Api33'), ('line', 999)]
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                item = copy.deepcopy(original)
                item['production_frames'][0][field] = value
                with self.assertRaises(d.Refusal):
                    self.joiner.completion(row, item)

    def test_coherent_changed_descriptor_with_same_return_kind(self):
        row, _ = self.row()
        item = row['selected_actual_native_completions'][0]
        item['descriptor'] = '(Ljava/lang/CharSequence;ILandroid/view/inputmethod/TextAttribute;)Z'
        with self.assertRaises(d.Refusal):
            self.joiner.completion(row, item)

    def test_coherent_wrong_global_receiver(self):
        row, _ = self.row()
        item = row['selected_actual_native_completions'][0]
        old = item['receiver_identity']
        item['receiver_identity'] = 'android.os.Handler@999'
        binding = next(x for x in row['native_receiver_bindings'] if x['global_identity'] == old)
        binding['class'] = 'android.os.Handler'
        binding['global_identity'] = item['receiver_identity']
        with self.assertRaises(d.Refusal):
            self.joiner.completion(row, item)

    def test_unknown_receiver_stays_unresolved(self):
        row, _ = self.row()
        item = row['selected_actual_native_completions'][0]
        binding = next(x for x in row['native_receiver_bindings'] if x['global_identity'] == item['receiver_identity'])
        binding['class'] = 'missing.InputConnection'
        binding['global_identity'] = item['receiver_identity'] = 'missing.InputConnection@999'
        self.assertEqual(self.joiner.completion(row, item)['status'], 'unresolved-native-dispatch')

    def test_exact_selected_composing_pair(self):
        name = 'direct-setComposingRegionWithAttributes.rows.jsonl.gz'
        row, prior = self.row(name)
        out = self.joiner.row(row, prior, name)
        self.assertEqual(len(out['native_completions']), 2)
        self.assertIn('inner-return', out['native_completions'][0]['adapter'])
        self.assertIn('outer-return', out['native_completions'][1]['adapter'])
        self.assertTrue(all(x['compiled_callee']['descriptor'] == d.SPECIAL_PAIR[1] for x in out['native_completions']))

    def test_composing_exception_does_not_supply_pair_or_normal_value(self):
        name = 'direct-setComposingRegionWithAttributes.rows.jsonl.gz'
        row, prior = self.row(name, 11)
        out = self.joiner.row(row, prior, name)
        self.assertEqual(len(out['native_completions']), 1)
        self.assertEqual(out['native_completions'][0]['value']['normal_return'], 'pending')
        self.assertNotIn('adapter', out['native_completions'][0])

    def test_composing_rule_cannot_broaden_by_family_or_association(self):
        name = 'direct-setComposingRegionWithAttributes.rows.jsonl.gz'
        row, _ = self.row(name)
        item = copy.deepcopy(row['selected_actual_native_completions'][0])
        row['family'] = 'setComposingRegion'
        with self.assertRaises(d.Refusal):
            self.joiner.completion(row, item)
        row, _ = self.row(name)
        item = copy.deepcopy(row['selected_actual_native_completions'][1])
        item['delegated_leaf_descriptor_pair'] = list(reversed(d.SPECIAL_PAIR))
        with self.assertRaises(d.Refusal):
            self.joiner.completion(row, item)
        item = copy.deepcopy(row['selected_actual_native_completions'][0])
        item['native_outcome_association'] = 'selected-original-delegated-overload-return'
        with self.assertRaises(d.Refusal):
            self.joiner.completion(row, item)

    def test_coherent_composing_pair_wrong_values(self):
        name = 'direct-setComposingRegionWithAttributes.rows.jsonl.gz'
        row, prior = self.row(name)
        row['selected_actual_native_completions'][1]['value'] = {'kind': 'boolean', 'value': False}
        prior['actual_selected_native_typed_outcomes'][1] = {'kind': 'boolean', 'value': False}
        with self.assertRaises(d.Refusal):
            self.joiner.row(row, prior, name)

    def test_exception_keeps_original_exception_and_normal_pending(self):
        row, prior = self.row(index=11)
        out = self.joiner.row(row, prior, 'direct-commitText.rows.jsonl.gz')
        self.assertEqual(out['public_result']['value']['normal_return'], 'pending')
        self.assertEqual(out['native_completions'][0]['value']['normal_return'], 'pending')
        item = row['selected_actual_native_completions'][0]
        item['value'] = {'kind': 'boolean', 'value': False}
        with self.assertRaises(d.Refusal):
            self.joiner.completion(row, item)

    def test_selected_exact_pair_and_identity_mutation(self):
        row, prior = self.row()
        row['selected_actual_native_completions'][0]['native_event_sequence_index'] += 900000
        with self.assertRaises(d.Refusal):
            self.joiner.row(row, prior, 'direct-commitText.rows.jsonl.gz')
        row, prior = self.row()
        row['selected_actual_native_completions'][0]['method'] = 'BaseInputConnection.commitTextWithAttributes'
        row['selected_immutable_event_points'][0]['native_event']['method'] = 'BaseInputConnection.commitTextWithAttributes'
        row['selected_actual_call_pairs'][0]['method'] = 'BaseInputConnection.commitTextWithAttributes'
        with self.assertRaises(d.Refusal):
            self.joiner.row(row, prior, 'direct-commitText.rows.jsonl.gz')

    def test_missing_and_no_selected_credit(self):
        name = 'boundary-000.rows.jsonl.gz'
        row, prior = self.row(name)
        out = self.joiner.row(row, prior, name)
        self.assertTrue(out['missing_selected_native_completion'])
        self.assertEqual(out['native_completions'], [])
        self.assertIsNone(out['public_result'])
        name = 'direct-commitText.rows.jsonl.gz'
        row, prior = self.row(name, 2)
        out = self.joiner.row(row, prior, name)
        self.assertFalse(out['missing_selected_native_completion'])
        self.assertEqual(out['native_completions'], [])

    def test_historical_and_direct_close_void_are_distinct(self):
        for name in ['boundary-000.rows.jsonl.gz', 'direct-close.rows.jsonl.gz']:
            row, prior = self.row(name)
            out = self.joiner.row(row, prior, name)
            self.assertEqual(out['qualification_status'], 'pending-original-required-cases-and-outcomes')
            if name.startswith('boundary-'):
                self.assertEqual(out['historical_enclosing_outcome'], {'kind': 'void'})
                self.assertIsNone(out['public_result'])
            else:
                self.assertEqual(out['public_result']['binding']['descriptor'], '()V')
                self.assertTrue(out['missing_selected_native_completion'])

    def test_strict_json_and_type_equality(self):
        for text in ['{"a":1,"a":2}', '{"x":NaN}', '{"x":Infinity}']:
            with self.assertRaises(d.Refusal):
                d.loads(text)
        self.assertFalse(d.same({'x': True}, {'x': 1}))
        self.assertFalse(d.same([1], [1.0]))

    def test_exact_manifest_refuses_unreleased_input(self):
        with self.assertRaises(d.Refusal):
            self.joiner.inputs.read(Path('STATUS.md'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
