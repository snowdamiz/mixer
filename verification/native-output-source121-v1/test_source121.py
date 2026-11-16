#!/usr/bin/env python3
"""Process-free controls for exact source121 admission and the immutable119 inverse."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('source121_authority', HERE/'adopt_envelope.py')
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)
guard_spec = importlib.util.spec_from_file_location('source121_guard', ROOT/'verification/envelope-rust-1991-default-ci-adoption/offline_guard.py')
guard = importlib.util.module_from_spec(guard_spec)
guard_spec.loader.exec_module(guard)
metadata_guard = A.module('source121_metadata_guard', ROOT/A.OLD/'metadata_guard.py')
metadata_guard.install(guard, HERE/'control-scratch')


class Source121Controls(unittest.TestCase):
    def setUp(self):
        self.binding = A.load_json(HERE/'binding.json')
        self.selected = A.load_json(HERE/'current-source-inputs.json')

    def test_actual_owning_roster_and_all_original_guards(self):
        proof = A.verify(True)
        self.assertEqual(proof['source_count'], 121)
        self.assertEqual(proof['predecessor_source_count'], 119)
        self.assertEqual(proof['historical119']['source_count'], 119)

    def test_complete119_inverse_and_unaffected_rows(self):
        before = A.inverse121(self.binding, self.selected)
        self.assertEqual(before, A.load_json(ROOT/A.OLD/'current-source-inputs.json'))
        changed = self.binding['native_output_transition']['changes']
        for path in set(before)-set(changed):
            self.assertEqual(before[path], self.selected[path])
        self.assertEqual(len(set(self.selected)-set(before)), 2)

    def test_count_is_not_a_compiler_or_android_profile_version(self):
        self.assertEqual(self.binding['type'], 'EXACT_NATIVE_OUTPUT_SOURCE121_AND_CALLER_SUCCESSOR')
        old = A.load_json(ROOT/A.OLD/'binding.json')
        self.assertEqual(self.binding['profile'], old['profile'])
        self.assertEqual(self.binding['renderer_pair21_transition'], old['renderer_pair21_transition'])
        self.assertIs(self.binding['provenance']['CLI120_selected'], False)

    def test_transition_type_number_aliases_and_unknown_fields_refuse(self):
        for key, value in [('schema', True), ('sourceCountBefore', True),
                ('sourceCountAfter', True), ('sourceCountAfter', 120),
                ('qualification', 0), ('type', 'CLI120'), ('unknown', False)]:
            forged = copy.deepcopy(self.binding)
            forged['native_output_transition'][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(RuntimeError):
                A.inverse121(forged, self.selected)

    def test_source_mutation_unknown_path_and_missing_path_refuse(self):
        mutants = []
        p = next(iter(self.selected))
        m = copy.deepcopy(self.selected); m[p]['sha256'] = '0'*64; mutants.append(m)
        m = dict(self.selected); m.pop(p); mutants.append(m)
        m = dict(self.selected); m['cli/Sources/MixerBuild/Unknown.swift'] = self.selected[p]; mutants.append(m)
        for forged in mutants:
            with self.assertRaises(RuntimeError): A.inverse121(self.binding, forged)

    def test_inverse_predecessor_change_and_partial_delta_refuse(self):
        for p in self.binding['native_output_transition']['changes']:
            forged = copy.deepcopy(self.binding)
            change = forged['native_output_transition']['changes'][p]
            change['before'] = {'bytes':1,'sha256':'0'*64}
            with self.assertRaises(RuntimeError): A.inverse121(forged, self.selected)

    def test_ordinary_test_binding_and_campaign_exclusion(self):
        test = self.binding['ordinary_test']
        self.assertEqual(test['actual_self_contained_tests'], 18)
        self.assertEqual(test['ordinary_cases_root_verified'], 382)
        self.assertEqual(A.row(A.read(ROOT/test['path'])), test['identity'])
        self.assertIs(test['new_fixture_copies'], False)
        for name in ['NativeProductCaptureTests.swift','PublicNativeOutputTests.swift']:
            self.assertFalse((ROOT/'cli/Tests/MixerBuildTests'/name).exists())

    def test_root_selection_and_all_acceptance_gates_remain_false(self):
        self.assertEqual(set(self.binding['root_gates']), {'manifest_fix','posix_scope',
            'ordinary382','independent_packet_review','explicit_successor_selection'})
        for v in self.binding['root_gates'].values(): self.assertIs(v, False)
        for k in ('aggregate','adoption','activation','GA'): self.assertIs(self.binding[k], False)

    def test_duplicate_keys_and_path_escape_refuse(self):
        with self.assertRaises(RuntimeError): A.unique([('schema',1),('schema',1)])
        for name in ['../bad','/bad','x/../bad','x\\bad','.git/HEAD','x\0bad']:
            with self.assertRaises(RuntimeError): A.relative(name)


if __name__ == '__main__':
    unittest.main()
