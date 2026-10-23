import csv
from pathlib import Path
import tempfile
import unittest
from summarize import COLUMNS, SHAPE, attribute, distribution, summarize


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'rows.csv'
        self.observed = {'source_bytes': 1000, 'imports': 0, 'functions': 2, 'successful_bodies': 1,
            'maximum_parameters_plus_locals': 8, 'layout': {'instruction': 40, 'function': 64,
                'validator_control': 16, 'validator_state': 72, 'validator_operand': 1, 'decoder_control': 24}}
        base = {key: 0 for key in COLUMNS}
        first = dict(base, function=0, defined=0, body_offset=16, wire_bytes=4, raw_instructions=2,
            raw_immediate_bytes=1, raw_code_wire_bytes=3, status='decoded', error_offset='', error_message_utf8_hex='',
            instructions=2, instruction_capacity_bytes=160, retained_requested_above_baseline=272,
            peak_requested_above_baseline=300, peak_live_allocations_above_baseline=2, maximum_live_allocation_count=50)
        second = dict(base, function=1, defined=1, body_offset=64, wire_bytes=610, local_groups=1,
            declared_locals=5, parameters=3, raw_instructions=300, raw_immediate_bytes=300,
            raw_code_wire_bytes=600, raw_max_block_nesting=140, status='limit', error_offset=320,
            error_message_utf8_hex='control nesting exceeds profile'.encode().hex(),
            retained_requested_above_baseline=100, peak_requested_above_baseline=1000,
            peak_live_allocations_above_baseline=3, maximum_live_allocation_count=51)
        for key in SHAPE: second[key] = ''
        self.rows = [first, second]

    def write(self):
        with self.path.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=COLUMNS); writer.writeheader(); writer.writerows(self.rows)

    def test_rejected_shape_is_unobserved_and_raw_counts_remain_inventory(self):
        self.write(); result = summarize(self.path, self.observed)
        self.assertEqual(result['decoded_count'], 1)
        self.assertEqual(result['raw_instruction_count'], 302)
        self.assertEqual(result['successful_instruction_count'], 2)
        self.assertIsNone(result['rejections'][0]['instructions'])
        self.assertEqual(result['rejections'][0]['error_message'], 'control nesting exceeds profile')
        self.assertEqual(result['raw_control_nesting_over_existing_body_ceiling'][0]['including_function'], 141)
        self.assertFalse(result['authorization'])

    def test_fake_zero_shape_and_incomplete_rows_are_rejected(self):
        self.rows[1]['instructions'] = 0; self.write()
        with self.assertRaises(ValueError): summarize(self.path, self.observed)
        self.rows[1]['instructions'] = ''; self.rows.pop(); self.write()
        with self.assertRaises(ValueError): summarize(self.path, self.observed)

    def test_count_span_and_payload_disagreements_reject(self):
        for field, invalid in [('function', 8), ('body_offset', 1000), ('instruction_capacity_bytes', 100000), ('raw_code_wire_bytes', 9)]:
            original = self.rows[0][field]; self.rows[0][field] = invalid; self.write()
            with self.subTest(field=field), self.assertRaises(ValueError): summarize(self.path, self.observed)
            self.rows[0][field] = original

    def test_attribution_requires_exact_all_function_size_and_bias(self):
        self.write(); summary = summarize(self.path, self.observed)
        path = Path(self.directory.name) / 'map'
        good = '       - 0 0 CODE\n       - a 5         first\n       - 39 264         second\n'
        path.write_text(good)
        result = attribute(self.path, path, summary)
        self.assertEqual(result['verified_function_count'], 2)
        self.assertEqual(result['observed_link_map_offset_bias_bytes'], 5)
        path.write_text(good.replace('a 5', 'a 6'))
        with self.assertRaises(ValueError): attribute(self.path, path, summary)
        path.write_text(good + '       - ff 1         extra\n')
        with self.assertRaises(ValueError): attribute(self.path, path, summary)

    def test_quantiles_are_nearest_rank(self):
        self.assertEqual(distribution(list(range(1, 21)))['p95'], 19)
        self.assertIsNone(distribution([]))


if __name__ == '__main__': unittest.main()
