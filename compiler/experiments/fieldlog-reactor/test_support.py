import json
import unittest
from pathlib import Path
from support import ROOT, descriptors, observations, source_mapping
from qualification_support import model_observations

HERE = Path(__file__).resolve().parent


class QualificationChecks(unittest.TestCase):
    def test_source_mapping_rejects_changed_assertion_receipt_and_duplicate_body(self):
        corpus = (ROOT / 'compiler/Fixtures/FieldLogCorpus/main.swift').read_bytes()
        wrapper = (HERE / 'FieldLogReactor.swift').read_bytes()
        self.assertTrue(source_mapping(corpus, wrapper)['exactBodyBytes'])
        for altered in [wrapper.replace(b'== 5000', b'== 4000'),
                        wrapper.replace(b'let reportIncludesEntry: Bool', b'let reportIncludesEntry: Int'),
                        wrapper + b'private func runFieldLogCorpus() throws {\n']:
            with self.assertRaises(ValueError):
                source_mapping(corpus, altered)

    def test_observation_parity_requires_two_complete_duplicate_free_objects(self):
        value = dict(status='passed', taskCount=1000, completionBasisPoints=5000,
                     codableRoundTrip=True, unicodePreserved=True, reordered=True,
                     committedEntries=1, pendingChanges=1503, emptyTitleRejected=True,
                     repeatedCommitRejected=True, reportIncludesEntry=True)
        model_observations(value)
        line = json.dumps(value)
        self.assertEqual(observations(line + '\n' + line + '\n', 2, value), [value, value])
        wrong = dict(value, unicodePreserved=False)
        duplicate = line[:-1] + ', "status":"passed"}'
        for altered in [line, line + '\n' + line + '\n' + line,
                        line + '\n' + json.dumps(wrong), line + '\n' + duplicate,
                        line + '\n' + json.dumps(dict(value, taskCount=True))]:
            with self.assertRaises(ValueError):
                observations(altered, 2, value)

    def test_descriptor_resolves_actual_function_type_and_rejects_truncation(self):
        # Independent scalar Wasm descriptor control; no executable body.
        source = (b'\0asm\x01\0\0\0' + b'\x01\x08\x02\x60\x00\x00\x60\x00\x01\x7f'
                  + b'\x03\x03\x02\x00\x01' + b'\x07\x09\x02\x01a\x00\x00\x01b\x00\x01')
        value = descriptors(source)
        self.assertEqual(value['exports'][0]['signature'], dict(parameters=[], results=[]))
        self.assertEqual(value['exports'][1]['signature'], dict(parameters=[], results=['i32']))
        for altered in [source[:-1], source + b'\x03\x01\x00',
                        source.replace(b'\x03\x03\x02\x00\x01', b'\x03\x03\x02\x00\x02')]:
            with self.assertRaises(ValueError):
                descriptors(altered)


if __name__ == '__main__':
    unittest.main(verbosity=2)
