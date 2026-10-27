"""Focused tests for root-selected F1/F2/F3 and explicit contextual limits."""
import copy
import unittest

import check_descriptor_joins as d


def replace_exact(value, replacements):
    if isinstance(value, dict):
        return {key: replace_exact(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [replace_exact(item, replacements) for item in value]
    return replacements.get(value, value) if isinstance(value, str) else value


class SelectedCorrectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.joiner = d.Joiner(d.Inputs())

    def test_coherent_invokespecial_hook_receiver_unknown_stays_unresolved(self):
        j = self.joiner
        file = next(x for x in j.ledger['files'] if x['file'] == 'boundary-162.rows.jsonl.gz')
        rows = [d.loads(line) for line in j.inputs.read(file['input_path'] + '.compact.jsonl').splitlines()]
        for number in (6, 7):
            with self.subTest(row=number):
                original = rows[number - 1]
                observed = original['selected_actual_native_completions'][0]
                binding = next(x for x in original['native_receiver_bindings'] if x['global_identity'] == observed['receiver_identity'])
                row = replace_exact(copy.deepcopy(original), {binding['global_identity']: 'missing.NativeSwitch@999', binding['row_identity']: 'missing.NativeSwitch@row-' + str(binding['ordinal'])})
                changed = next(x for x in row['native_receiver_bindings'] if x['global_identity'] == 'missing.NativeSwitch@999')
                changed['class'] = 'missing.NativeSwitch'
                result = j.row(row, file['rows'][number - 1], file['file'])['native_completions'][0]
                self.assertEqual(result['receiver']['status'], 'unresolved')
                self.assertTrue(result['status'].startswith('unresolved-'))
                self.assertFalse(result['status'].startswith('joined-'))
                self.assertEqual(result['value']['normal_return'], 'pending')
                self.assertEqual(result['value']['actual']['identity'], observed['original_exception_identity'])
                self.assertEqual(result['parameter_contexts']['symbolic_callee']['evidence']['opcode'], 183)

    def test_specification_valid_class_name_segments(self):
        for name in ['pkg/Foo(Bar', 'pkg/Foo)Bar', 'pkg/Foo Bar', 'foo/(Bar', 'pkg/\tName', 'pkg/\nName', 'pkg/Name\x00']:
            with self.subTest(name=name):
                self.assertEqual(d.descriptor('()L' + name + ';')[1], 'L' + name + ';')
                d.descriptor('(L' + name + ';[L' + name + ';)V', receiver_units=1)

    def test_actual_jvms_name_exclusions_and_complete_input_still_reject(self):
        for text in ['()L;', '()Lfoo//Bar;', '()L/foo;', '()Lfoo/;', '()Lfoo.Bar;', '()Lfoo[Bar;', '()Lfoo;Bar;', '(I))V', '()Lfoo;extra']:
            with self.subTest(text=text):
                with self.assertRaises(d.Refusal):
                    d.descriptor(text)

    def test_default_none_is_grammar_only_never_contextually_passed(self):
        text = '(' + 'I' * 255 + ')V'
        d.descriptor(text)
        for context in ({}, {'opcode': 186}, {'opcode': 0}):
            with self.subTest(context=context):
                result = d.descriptor_context(text, **context)
                self.assertEqual(result['status'], 'unresolved-receiver-context')
                self.assertIsNone(result['receiver_units'])
                self.assertTrue(result['reason'])

    def test_static255_and_instance254_explicit_units(self):
        instance = '(' + 'I' * 254 + ')V'
        static = '(' + 'I' * 255 + ')V'
        for opcode in (182, 183, 185):
            with self.subTest(opcode=opcode):
                result = d.descriptor_context(instance, opcode=opcode, access=1)
                self.assertEqual(result['total_parameter_units'], 255)
                self.assertEqual(result['receiver_units'], 1)
                with self.assertRaises(d.Refusal):
                    d.descriptor_context(static, opcode=opcode, access=1)
        result = d.descriptor_context(static, opcode=184, access=9)
        self.assertEqual(result['total_parameter_units'], 255)
        self.assertEqual(result['receiver_units'], 0)

    def test_wide_units_and_arrays(self):
        for text, accepted in [('(' + 'J' * 127 + ')V', True), ('(' + 'D' * 127 + ')V', True), ('(' + 'J' * 127 + 'I)V', False), ('(' + '[J' * 254 + ')V', True), ('(' + '[D' * 255 + ')V', False)]:
            with self.subTest(text=text[:40], accepted=accepted):
                if accepted:
                    self.assertEqual(d.descriptor_context(text, access=1)['status'], 'passed')
                else:
                    with self.assertRaises(d.Refusal):
                        d.descriptor_context(text, access=1)

    def test_access_and_invocation_receiver_metadata_must_agree(self):
        for access, opcode in [(8, 185), (1, 184), (8, 183), (8, 182)]:
            with self.subTest(access=access, opcode=opcode):
                with self.assertRaises(d.Refusal):
                    d.descriptor_context('()V', access=access, opcode=opcode)
        for units in (True, False, -1, 2, '1'):
            with self.assertRaises(d.Refusal):
                d.descriptor('()V', receiver_units=units)

    def test_retained_compiled_declarations_are_context_checked(self):
        self.assertTrue(self.joiner.methods)
        for key, method in self.joiner.methods.items():
            context = method['parameter_context']
            self.assertEqual(context['status'], 'passed', key)
            self.assertEqual(context['receiver_units'], 0 if method['access'] & 8 else 1, key)
            self.assertEqual(context['evidence']['access'], method['access'], key)


if __name__ == '__main__':
    unittest.main(verbosity=2)
