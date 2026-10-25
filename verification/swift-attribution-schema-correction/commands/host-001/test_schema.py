#!/usr/bin/env python3
"""Finite in-memory strict schema controls; no guest or subprocess dispatch."""
from pathlib import Path
import copy
import importlib.util
import json
import unittest

H = Path(__file__).resolve().parent
P = H.parent / 'swift-current-attribution-full-preparation'
Q = H.parent / 'swift-current-attribution-preparation-review'
spec = importlib.util.spec_from_file_location('schema_control_classifier', H / 'telemetry.py')
telemetry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(telemetry)


class BytesPath:
    def __init__(self, data): self.data = data
    def read_bytes(self): return self.data


def encode(rows):
    return b''.join(b'MIXER_ATTRIBUTION ' + json.dumps(r, separators=(',', ':')).encode() + b'\n' for r in rows)


def zero_row(label, sequence):
    payload = {k: [0] * n for k, n in telemetry.ARRAYS.items()}
    payload.update(invalid=0, completed=0, distinct=0, repeated=0, first_rejection=None)
    return dict(lifecycle=label, sequence=sequence, reset_count=1, formatted=True,
        observer_invalid=0, invariant_mask=0, adapter_invalid=0, prior_write_failed=False,
        valid=True, cache_work=0, cache_decodes=0,
        decodes_bound_before_consumption=label == 'final_cleanup', payload=payload)


def failure_fixture(kind='WorkExhausted', resource='CacheWork'):
    failure = dict(kind=kind, resource=resource, function=None, offset=None, attempted=1, limit=0)
    original = [{'event': 'constructed', 'payload': {'usage': {'cache_work': 0}, 'cache': {'decodes': 0}}},
                {'event': 'runtime_failure', 'payload': failure},
                {'event': 'final_cleanup_usage', 'payload': {'cache_work': 0}}]
    rows = [zero_row('constructed', 1), zero_row('final_cleanup', 2)]
    return original, rows


def rejection():
    return dict(site=15, requested=1, cursor_function=telemetry.U64, cursor_offset=telemetry.U64,
                kind='WorkExhausted', resource='Some(CacheWork)', function=telemetry.U64,
                offset=telemetry.U64, attempted=1, limit=0)


class TypedSchemaControls(unittest.TestCase):
    def classify(self, rows, original=None):
        if original is None: original, _ = failure_fixture()
        before = copy.deepcopy(original)
        result = telemetry.classify(BytesPath(encode(rows)), original)
        self.assertEqual(original, before)
        self.assertFalse(result['originalResultReplaced'])
        self.assertFalse(result['cleanupTruthInferredFromTelemetry'])
        return result

    def invalid(self, rows, original=None, issue=None):
        result = self.classify(rows, original)
        self.assertEqual(result['status'], 'invalid_or_missing', result)
        if issue: self.assertIn(issue, result['issues'])

    def test_exact_six_independent_reproductions(self):
        original = json.loads((Q / 'parser-original-events.json').read_bytes())
        for path in sorted((Q / 'parser-reproductions').glob('*.stdout')):
            with self.subTest(fixture=path.name):
                before = copy.deepcopy(original)
                result = telemetry.classify(path, original)
                self.assertEqual(result['status'], 'invalid_or_missing', result)
                self.assertEqual(original, before)
                self.assertFalse(result['originalResultReplaced'])
                self.assertFalse(result['cleanupTruthInferredFromTelemetry'])
        self.assertEqual(len(list((Q / 'parser-reproductions').glob('*.stdout'))), 6)

    def test_both_exact_real_finite_producer_outputs_remain_valid(self):
        for name in ('control-001', 'control-002'):
            with self.subTest(producer=name):
                original = json.loads((P / (name + '-events.json')).read_bytes())
                before = copy.deepcopy(original)
                result = telemetry.classify(P / (name + '.stdout'), original)
                self.assertEqual(result['status'], 'valid', result['issues'])
                self.assertEqual(original, before)
                self.assertEqual(result, json.loads((P / (name + '-telemetry.json')).read_bytes()))

    def test_closed_field_sets_at_every_object(self):
        _, rows = failure_fixture()
        rows[-1]['payload']['first_rejection'] = rejection()
        for location in ('envelope', 'aggregate', 'rejection'):
            base = rows[0] if location == 'envelope' else (rows[-1]['payload'] if location == 'aggregate' else rows[-1]['payload']['first_rejection'])
            for key in list(base) + ['unrecognized']:
                changed = copy.deepcopy(rows)
                target = changed[0] if location == 'envelope' else (changed[-1]['payload'] if location == 'aggregate' else changed[-1]['payload']['first_rejection'])
                if key == 'unrecognized': target[key] = 0
                else: del target[key]
                with self.subTest(location=location, field=key): self.invalid(changed)

    def test_every_unsigned_scalar_rejects_bool_float_negative_and_overflow(self):
        _, rows = failure_fixture()
        groups = [('envelope', 'sequence', telemetry.U8), ('envelope', 'reset_count', telemetry.U8)]
        groups += [('envelope', k, telemetry.U32) for k in ('observer_invalid', 'invariant_mask', 'adapter_invalid')]
        groups += [('envelope', k, telemetry.U64) for k in ('cache_work', 'cache_decodes')]
        groups += [('aggregate', k, telemetry.U64) for k in telemetry.COUNTERS]
        groups += [('aggregate', 'invalid', telemetry.U32)]
        groups += [('rejection', k, telemetry.U64) for k in ('requested', 'cursor_offset', 'offset', 'attempted', 'limit')]
        groups += [('rejection', 'site', 15), ('rejection', 'cursor_function', telemetry.U32), ('rejection', 'function', telemetry.U32)]
        for location, key, maximum in groups:
            for value in (True, False, 0.0, -1, maximum + 1, None, '0'):
                changed = copy.deepcopy(rows)
                if location == 'envelope': target = changed[0]
                elif location == 'aggregate': target = changed[0]['payload']
                else:
                    changed[-1]['payload']['first_rejection'] = rejection()
                    target = changed[-1]['payload']['first_rejection']
                target[key] = value
                with self.subTest(location=location, key=key, value=value): self.invalid(changed)

    def test_each_fixed_array_type_length_and_unsigned_elements(self):
        _, rows = failure_fixture()
        for key, n in telemetry.ARRAYS.items():
            for value in ([0] * (n - 1), [0] * (n + 1), None, {}, [True] + [0] * (n - 1),
                          [0.0] + [0] * (n - 1), [-1] + [0] * (n - 1), [telemetry.U64 + 1] + [0] * (n - 1)):
                changed = copy.deepcopy(rows); changed[0]['payload'][key] = value
                with self.subTest(array=key, value=value): self.invalid(changed)

    def test_boolean_fields_require_actual_booleans(self):
        _, rows = failure_fixture()
        for key in ('formatted', 'prior_write_failed', 'valid', 'decodes_bound_before_consumption'):
            for value in (0, 1, 'false', None, [], {}):
                changed = copy.deepcopy(rows); changed[0][key] = value
                with self.subTest(field=key, value=value): self.invalid(changed)

    def test_nested_shapes_and_closed_enum_forms(self):
        _, rows = failure_fixture()
        for value in ([], 'bad', 0, True):
            changed = copy.deepcopy(rows); changed[0]['payload'] = value; self.invalid(changed)
            changed = copy.deepcopy(rows); changed[-1]['payload']['first_rejection'] = value; self.invalid(changed)
        for key in ('kind', 'resource'):
            for value in ('', 'NewVariant', 'Some(Some(CacheWork))', 'Reservation(Cache)', 1, True, [], None):
                changed = copy.deepcopy(rows); changed[-1]['payload']['first_rejection'] = rejection()
                changed[-1]['payload']['first_rejection'][key] = value
                with self.subTest(enum=key, value=value): self.invalid(changed)

    def test_source_width_boundaries_and_optional_sentinels(self):
        for maximum in (telemetry.U8, telemetry.U32, telemetry.U64):
            self.assertTrue(telemetry.uint(0, maximum)); self.assertTrue(telemetry.uint(maximum, maximum))
            self.assertFalse(telemetry.uint(maximum + 1, maximum)); self.assertFalse(telemetry.uint(True, maximum))
        r = rejection()
        for field in ('cursor_function', 'function'):
            for value in (0, telemetry.U32, telemetry.U64):
                r[field] = value; self.assertTrue(telemetry.rejection_schema(r))
            r[field] = telemetry.U32 + 1; self.assertFalse(telemetry.rejection_schema(r)); r[field] = telemetry.U64
        for field in ('cursor_offset', 'offset', 'requested', 'attempted', 'limit'):
            r[field] = telemetry.U64; self.assertTrue(telemetry.rejection_schema(r))
        for resource in telemetry.RESOURCES:
            r['resource'] = resource; self.assertTrue(telemetry.rejection_schema(r))
        for kind in telemetry.KINDS:
            r['kind'] = kind; self.assertTrue(telemetry.rejection_schema(r))
        payload = zero_row('constructed', 1)['payload']
        for key in telemetry.ARRAYS: payload[key] = [telemetry.U64] * len(payload[key])
        for key in telemetry.COUNTERS: payload[key] = telemetry.U64
        payload['invalid'] = telemetry.U32
        self.assertTrue(telemetry.aggregate_schema(payload))  # Typed bounds, not a valid aggregate claim.

    def test_consistent_u64_max_credit_boundary_remains_valid(self):
        original, rows = failure_fixture()
        for row in rows:
            row['cache_work'] = telemetry.U64; row['payload']['credits'][0] = telemetry.U64
        original[0]['payload']['usage']['cache_work'] = telemetry.U64
        original[-1]['payload']['cache_work'] = telemetry.U64
        self.assertEqual(self.classify(rows, original)['status'], 'valid')

    def test_rejected_work_record_is_optional_and_bound_to_original_failure(self):
        original, rows = failure_fixture()
        self.assertEqual(self.classify(rows, original)['status'], 'valid')
        rows[-1]['payload']['first_rejection'] = rejection()
        self.assertEqual(self.classify(rows, original)['status'], 'valid')
        changed = copy.deepcopy(original); changed[1]['payload']['attempted'] = 2
        self.invalid(rows, changed, 'rejection_original_failure_mismatch')
        self.invalid(rows, [original[0], original[-1]], 'rejection_original_failure_mismatch')
        # Sticky failures keep original failure identity while later work has another cursor.
        rows[-1]['payload']['first_rejection'].update(cursor_function=79999, cursor_offset=123)
        self.assertEqual(self.classify(rows, original)['status'], 'valid')

    def test_first_rejection_cannot_change_or_disappear(self):
        original, rows = failure_fixture()
        original.insert(-1, {'event': 'before_cleanup', 'payload': copy.deepcopy(original[0]['payload'])})
        rows.insert(-1, zero_row('before_cleanup', 2)); rows[-1]['sequence'] = 3
        for row in rows[1:]: row['payload']['first_rejection'] = rejection()
        self.assertEqual(self.classify(rows, original)['status'], 'valid')
        for value in (None, {**rejection(), 'requested': 2}):
            changed = copy.deepcopy(rows); changed[-1]['payload']['first_rejection'] = value
            self.invalid(changed, original, 'first_rejection_not_sticky')
        changed = copy.deepcopy(rows); changed[0]['payload']['first_rejection'] = rejection()
        self.invalid(changed, original, 'rejection_original_failure_mismatch')

    def test_phase_sequence_reset_and_cumulative_protocol(self):
        original = json.loads((P / 'control-001-events.json').read_bytes())
        rows = json.loads((P / 'control-001-telemetry.json').read_bytes())['snapshots']
        for key, value in (('sequence', 0), ('sequence', 255), ('reset_count', 0), ('reset_count', 2),
                           ('decodes_bound_before_consumption', True)):
            changed = copy.deepcopy(rows); changed[0][key] = value; self.invalid(changed, original)
        for changed in (rows[::-1], rows + [rows[0]], rows[:-1]): self.invalid(changed, original)
        changed = copy.deepcopy(rows); changed[-1]['payload']['calls'][0] -= 1
        self.invalid(changed, original, 'cumulative_counter_regression')

    def test_aggregate_invariants_and_original_bindings(self):
        original, rows = failure_fixture()
        for field in ('credits', 'scan_credits', 'scan_calls', 'scan_published', 'build_credits', 'build_calls'):
            changed = copy.deepcopy(rows); changed[0]['payload'][field][0] = 1
            self.invalid(changed, original)
        for key, value in (('invalid', 1), ('completed', 1), ('distinct', 1), ('repeated', 1)):
            changed = copy.deepcopy(rows); changed[0]['payload'][key] = value; self.invalid(changed, original)
        for key in ('cache_work', 'cache_decodes'):
            changed = copy.deepcopy(rows); changed[-1][key] = 1; self.invalid(changed, original)

    def test_invalidity_and_formatter_failures_require_discarded_payload(self):
        _, rows = failure_fixture()
        for key, value in (('formatted', False), ('observer_invalid', 1), ('invariant_mask', 1),
                           ('adapter_invalid', 1), ('prior_write_failed', True), ('valid', False)):
            changed = copy.deepcopy(rows); changed[0][key] = value
            self.invalid(changed, issue='invalid_payload_not_discarded')
            changed[0].update(valid=False, payload=None); self.invalid(changed)
        changed = copy.deepcopy(rows); changed[0]['payload'] = None; self.invalid(changed, issue='missing_payload')

    def test_nonfinite_floats_duplicates_malformed_and_non_object_json(self):
        original, rows = failure_fixture()
        data = encode(rows)
        for token in (b'NaN', b'Infinity', b'-Infinity', b'1.0', b'1e999'):
            changed = data.replace(b'"reset_count":1', b'"reset_count":' + token, 1)
            self.assertEqual(telemetry.classify(BytesPath(changed), original)['status'], 'invalid_or_missing')
        changed = data.replace(b'"reset_count":1', b'"reset_count":1,"reset_count":1', 1)
        self.assertIn('malformed_telemetry', telemetry.classify(BytesPath(changed), original)['issues'])
        for suffix in (b'null', b'[]', b'true', b'0', b'{broken', b'"text"'):
            result = telemetry.classify(BytesPath(b'MIXER_ATTRIBUTION ' + suffix + b'\n'), original)
            self.assertEqual(result['status'], 'invalid_or_missing')
            self.assertFalse(any(i.startswith('telemetry_parser_error') for i in result['issues']))

    def test_empty_missing_truncated_and_output_boundaries(self):
        original, rows = failure_fixture()
        self.assertEqual(telemetry.classify(BytesPath(b''), [{'event': 'validation_failure', 'payload': {}}])['status'], 'not_started')
        self.assertEqual(telemetry.classify(BytesPath(b''), original)['status'], 'invalid_or_missing')
        self.assertIn('truncated_telemetry_line', telemetry.classify(BytesPath(encode(rows)[:-1]), original)['issues'])
        line = encode(rows[:1])
        for n in (telemetry.ENVELOPE, telemetry.ENVELOPE + 1):
            padded = line[:-1] + b' ' * (n - len(line)) + b'\n' + encode(rows[1:])
            result = telemetry.classify(BytesPath(padded), original)
            self.assertEqual('envelope_overflow' in result['issues'], n > telemetry.ENVELOPE)
        self.assertIn('lifetime_output_overflow', telemetry.classify(BytesPath(encode(rows) * 4), original)['issues'])


if __name__ == '__main__': unittest.main(verbosity=2)
