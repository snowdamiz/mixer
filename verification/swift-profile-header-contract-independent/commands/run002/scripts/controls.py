#!/usr/bin/env python3
"""Independent design controls, never product, compiler, File-custody or authority tests.

The synthetic records below are deliberately forgeable Python values. Their role
is to show requirements and information loss, not simulate Rust access control.
No producer script or Rust source is imported or executed.
"""
from pathlib import Path
import copy
import hashlib
import json
import struct
import unittest

P = Path(__file__).resolve().parent
PREP = P.parent / 'swift-profile-header-preparation'
C = json.loads((PREP / 'contract.json').read_bytes())
D = json.loads((PREP / 'closure-comparison.json').read_bytes())
U64 = 2**64 - 1
U32 = 2**32 - 1
FIELDS = ('source_bytes', 'metadata_bytes', 'cache_bytes', 'cache_entry_bytes',
          'cache_entries', 'active_pins', 'cache_work', 'frames', 'values',
          'controls', 'memory_pages', 'state_bytes', 'combined_bytes',
          'instruction_fuel', 'execution_work', 'host_calls', 'deadline_ms')
MAXIMA = (67108864, 16777216, 16777216, 8388608, 64, 64, 64000000,
          64, 16384, 4096, 768, 134217728, 268435456, 100000000,
          1000000000, 32768, 30000)


def add(a, b, maximum=U64):
    if not 0 <= a <= maximum or not 0 <= b <= maximum or a > maximum - b:
        raise ValueError('arithmetic')
    return a + b


def mul(a, b, maximum=U64):
    if not 0 <= a <= maximum or not 0 <= b <= maximum or (b and a > maximum // b):
        raise ValueError('arithmetic')
    return a * b


def layout(cache, proof, cleanup, plan, slot, pin, patch, slots, pins, maximum=U64):
    # These supplied numbers are arbitrary arithmetic witnesses, never ABI facts.
    if not 0 <= proof <= cache <= maximum:
        raise ValueError('subtraction')
    h = add(add(add(cache - proof, cleanup, maximum), 192, maximum),
            mul(512, plan, maximum), maximum)
    b = add(add(add(h, mul(slots, slot, maximum), maximum),
                mul(pins, pin, maximum), maximum), mul(512, patch, maximum), maximum)
    return h, b


def budgets_match(actual, selected):
    return (selected is not None and tuple(actual) == FIELDS and tuple(selected) == FIELDS
            and all(type(actual[n]) is int and type(selected[n]) is int
                    and 0 <= actual[n] == selected[n] <= m
                    for n, m in zip(FIELDS, MAXIMA)))


def model():
    budget = dict(zip(FIELDS, MAXIMA))
    budget['cache_entries'] = 2
    budget['active_pins'] = 3
    h, base = layout(997, 601, 53, 17, 31, 23, 11, 2, 3)
    return {
        'policy': 'swift-reactor-experiment-v1', 'validator': 1, 'decoder': 1,
        'imports': 34, 'defined': 9, 'validated': 9, 'types': 2, 'source': 1500,
        'budget': budget, 'selected': dict(budget),
        'cache_runtime_owner': 17, 'control_owner': 17,
        'wasi_owner': 17, 'wasi_instance': 'wasi-A', 'construction_wasi_instance': 'wasi-A',
        'header_ticket': True, 'slots_len': 2, 'slots_cap': 2,
        'pins_len': 3, 'pins_cap': 3, 'patches_len': 512, 'patches_cap': 512,
        'index_len': 192, 'index_cap': 192, 'plans_len': 512, 'plans_cap': 512,
        'nonce': 1, 'slots': [(None, 0, 0)] * 2, 'pins': [(0, 0)] * 3,
        'index': [0] * 192, 'plans': [None] * 512,
        'resident': 0, 'pinned': 0, 'construction': 0,
        'peak_resident': 0, 'peak_pinned': 0, 'peak_construction': 0, 'active_pins': 0,
        'live_cache_entries': 0, 'live_pins': 0,
        'hits': 0, 'misses': 0, 'decodes': 0, 'evictions': 0,
        'fixed': base, 'cache_current': base, 'cache_base': base,
        'cache_work': 4800 + 2 + 3, 'first_failure': None,
        'cache_attempts': 0, 'unrelated_zero_cache_tickets': 0,
        'runtime_state_live': 7, 'runtime_state_bytes': 100,
        'same_build_shape': (997, 601, 53, 17, 31, 23, 11),
        'external_build_attestation': 'unavailable',
        'snapshot_owner_identity': 'sealed-owner-A',
        'h_model_only': h,
    }


def stated_cache_shape(s):
    b = s['budget']
    slots = min(b['cache_entries'], s['defined'])
    return (1 <= slots <= 64 and 1 <= b['active_pins'] <= 64
            and s['slots_len'] == s['slots_cap'] == slots
            and s['pins_len'] == s['pins_cap'] == b['active_pins']
            and s['nonce'] == 1
            and all(v == (None, 0, 0) for v in s['slots'])
            and all(v == (0, 0) for v in s['pins'])
            and all(v == 0 for v in s['index'])
            and all(v is None for v in s['plans'])
            and all(s[n] == 0 for n in ['resident', 'pinned', 'construction',
                                       'peak_resident', 'peak_pinned', 'peak_construction', 'active_pins',
                                       'live_cache_entries', 'live_pins', 'hits',
                                       'misses', 'decodes', 'evictions']))


def common_owner_preflight_projection(s):
    # Existing owner checks establish this relation, never historical WASI identity.
    return (s['header_ticket'] and s['cache_runtime_owner'] != 0
            and s['cache_runtime_owner'] == s['control_owner']
            and (s['wasi_owner'] is None or s['wasi_owner'] == s['control_owner']))


def reservation_projection(s):
    return s['resident'] == 0 and s['fixed'] == s['cache_base'] == s['cache_current'] <= s['budget']['cache_bytes']


def snapshot_admissible(s):
    try:
        total = add(s['imports'], s['defined'])
    except ValueError:
        return False
    return (s['policy'] == 'swift-reactor-experiment-v1' and s['validator'] == 1
            and s['decoder'] == 1 and s['imports'] == 34
            and s['validated'] == s['defined'] and total <= 80000
            and 0 <= s['types'] <= U32)


def modeled_header(s, claims):
    if not stated_cache_shape(s) or not reservation_projection(s):
        raise ValueError('model shape/reservation')
    if len(claims) != 8 or any(type(x) is not bytes or len(x) != 32 for x in claims):
        raise ValueError('digest extent')
    words = (1, 512, 32, 80000, s['source'], s['types'], s['slots_len'],
             s['pins_len'], 1, s['cache_base'], s['budget']['cache_bytes'],
             s['budget']['cache_entry_bytes'], 0, 0, 0)
    if any(not 0 <= x <= U64 for x in words):
        raise ValueError('narrowing')
    if not 0 <= s['types'] <= U32:
        raise ValueError('types')
    # Independent byte assembly deliberately does not use the producer pack format.
    out = bytearray(512)
    out[0:8] = b'MIXPRF01'
    for i, word in enumerate(words, 1):
        out[i * 8:(i + 1) * 8] = word.to_bytes(8, 'little')
    for i, claim in enumerate(claims):
        out[128 + i * 32:160 + i * 32] = claim
    return bytes(out)


def load_source(name):
    return (PREP / 'inputs/vm' / name).read_text()


class IndependentControls(unittest.TestCase):
    def test_01_contract_map_matches_independent_expected_coordinates(self):
        expected = ('magic', 'version', 'header_bytes', 'row_bytes', 'rows',
                    'source_extent', 'type_count', 'slot_limit', 'pin_limit',
                    'initial_nonce', 'cache_base', 'cache_capacity', 'entry_limit',
                    'reserved_13', 'reserved_14', 'reserved_15')
        self.assertEqual([(r['name'], r['offset']) for r in C['header']['words']],
                         list(zip(expected, range(0, 128, 8))))

    def test_02_golden_bytes_independent_reverse_decoder(self):
        s = model(); s['source'] = 0x0102030405060708
        claims = [bytes(range(i * 32, (i + 1) * 32)) for i in range(8)]
        raw = modeled_header(s, claims)
        self.assertEqual(len(raw), 512)
        self.assertEqual(raw[:8], b'MIXPRF01')
        self.assertEqual(raw[40:48], bytes.fromhex('0807060504030201'))
        self.assertEqual(struct.unpack_from('<8Q', raw, 8),
                         (1, 512, 32, 80000, s['source'], 2, 2, 3))
        self.assertEqual(raw[104:128], bytes(24))
        self.assertEqual(raw[384:], bytes(128))
        self.assertEqual(raw[128:384], bytes(range(256)))

    def test_03_all_eight_digest_positions_are_distinct_and_unverified(self):
        self.assertEqual([r['name'] for r in C['header']['digests']],
                         ['baseline', 'candidate', 'original_input', 'event_schema',
                          'profile_adapter_binary', 'layout_receipt',
                          'original_validated_snapshot', 'profile_row_body'])
        self.assertEqual([r['offset'] for r in C['header']['digests']], list(range(128, 384, 32)))
        self.assertTrue(all(r['verified_by_encoding'] is False for r in C['header']['digests']))

    def test_04_digest_bytes_include_zero_and_arbitrary_content_without_authority(self):
        for claims in [[bytes(32)] * 8, [bytes([255]) * 32] * 8, [b'\x80' * 32] * 8]:
            self.assertEqual(len(modeled_header(model(), claims)), 512)
        self.assertTrue(all(v is False for v in C['authority'].values()))

    def test_05_digest_extent_refuses_every_bad_slot(self):
        for i in range(8):
            for length in [0, 31, 33]:
                claims = [bytes(32)] * 8; claims[i] = bytes(length)
                with self.assertRaises(ValueError): modeled_header(model(), claims)
        for count in [0, 7, 9]:
            with self.assertRaises(ValueError): modeled_header(model(), [bytes(32)] * count)

    def test_06_complete_budget_order_and_source_ceiling_values(self):
        self.assertEqual(C['canonical_budget_field_order'], list(FIELDS))
        self.assertEqual(C['canonical_budget_maxima'], dict(zip(FIELDS, MAXIMA)))
        self.assertIsNone(C['selected_invocation_budget'])
        self.assertFalse(C['historical_invocation_candidate']['new_execution_selected'])

    def test_07_budget_one_field_drift_refused_for_each_17_field(self):
        s = model(); self.assertTrue(budgets_match(s['budget'], s['selected']))
        for name in FIELDS:
            selected = dict(s['selected']); selected[name] -= 1
            self.assertFalse(budgets_match(s['budget'], selected), name)

    def test_08_budget_missing_extra_reordered_and_bool_refused(self):
        s = model()
        for name in FIELDS:
            selected = dict(s['selected']); del selected[name]
            self.assertFalse(budgets_match(s['budget'], selected), name)
        selected = dict(s['selected']); selected['authority'] = True
        self.assertFalse(budgets_match(s['budget'], selected))
        self.assertFalse(budgets_match(s['budget'], dict(reversed(list(s['selected'].items())))))
        selected = dict(s['selected']); selected['source_bytes'] = True
        self.assertFalse(budgets_match(s['budget'], selected))
        self.assertFalse(budgets_match(s['budget'], None))

    def test_09_budget_ceiling_and_zero_narrowing(self):
        for name, maximum in zip(FIELDS, MAXIMA):
            high = dict(zip(FIELDS, MAXIMA)); high[name] = maximum + 1
            self.assertFalse(budgets_match(high, high), name)
            low = dict(zip(FIELDS, MAXIMA)); low[name] = 0
            self.assertTrue(budgets_match(low, low), name)

    def test_10_equal_header_subset_cannot_bind_other_budget_fields(self):
        base = model(); first = modeled_header(base, [bytes(32)] * 8)
        header_names = {'cache_bytes', 'cache_entry_bytes', 'cache_entries', 'active_pins'}
        for name in set(FIELDS) - header_names:
            drift = copy.deepcopy(base); drift['budget'][name] -= 1
            self.assertEqual(first, modeled_header(drift, [bytes(32)] * 8), name)
            self.assertFalse(budgets_match(drift['budget'], base['selected']), name)

    def test_11_equal_header_can_hide_different_raw_cache_entries(self):
        s = model(); s['defined'] = 1; s['slots_len'] = s['slots_cap'] = 1
        s['slots'] = [(None, 0, 0)]
        a = modeled_header(s, [bytes(32)] * 8)
        other = copy.deepcopy(s); other['budget']['cache_entries'] = 64
        self.assertEqual(a, modeled_header(other, [bytes(32)] * 8))
        self.assertFalse(budgets_match(other['budget'], s['selected']))

    def test_12_defined_and_budget_minimum_and_maximum_slots(self):
        for defined in [1, 2, 63, 64, 65, 79966]:
            for entries in [1, 2, 63, 64]:
                s = model(); s['defined'] = s['validated'] = defined
                s['budget']['cache_entries'] = entries
                n = min(defined, entries); s['slots_len'] = s['slots_cap'] = n
                s['slots'] = [(None, 0, 0)] * n
                self.assertTrue(stated_cache_shape(s), (defined, entries))
                self.assertEqual(int.from_bytes(modeled_header(s, [bytes(32)] * 8)[56:64], 'little'), n)

    def test_13_pins_independent_from_slots_all_4096_pairs(self):
        for slots in range(1, 65):
            for pins in range(1, 65):
                s = model(); s['defined'] = s['validated'] = slots
                s['budget']['cache_entries'] = 64; s['slots_len'] = s['slots_cap'] = slots
                s['slots'] = [(None, 0, 0)] * slots
                s['budget']['active_pins'] = pins; s['pins_len'] = s['pins_cap'] = pins
                s['pins'] = [(0, 0)] * pins
                self.assertTrue(stated_cache_shape(s))

    def test_14_unsupported_zero_counts_are_not_clamped(self):
        for field in ['defined', 'budget.cache_entries', 'budget.active_pins']:
            s = model()
            if field.startswith('budget.'):
                s['budget'][field.split('.')[1]] = 0
            else: s[field] = 0
            self.assertFalse(stated_cache_shape(s), field)

    def test_15_actual_length_and_capacity_drift_refused(self):
        for key in ['slots_len', 'slots_cap', 'pins_len', 'pins_cap']:
            for delta in [-1, 1]:
                s = model(); s[key] += delta
                self.assertFalse(stated_cache_shape(s), (key, delta))

    def test_16_hidden_slot_resident_pin_or_recency_refused(self):
        for value in [('resident', 0, 0), (None, 1, 0), (None, 0, 1)]:
            s = model(); s['slots'][0] = value
            self.assertFalse(stated_cache_shape(s), value)

    def test_17_free_pin_record_requires_both_default_fields(self):
        for record in [(1, 0), (0, 1), (1, 1)]:
            s = model(); s['pins'][0] = record
            self.assertFalse(stated_cache_shape(s), record)

    def test_18_all_plan_index_cells_checked(self):
        for kind, count, value in [('index', 192, 1), ('plans', 512, 'occupied')]:
            for i in range(count):
                s = model(); s[kind][i] = value
                self.assertFalse(stated_cache_shape(s), (kind, i))

    def test_19_nonce_and_every_initial_cache_counter_checked(self):
        for n in [0, 2, U64]:
            s = model(); s['nonce'] = n; self.assertFalse(stated_cache_shape(s))
        for name in ['resident', 'pinned', 'construction', 'live_cache_entries',
                     'live_pins', 'peak_resident', 'peak_pinned', 'peak_construction',
                     'active_pins', 'hits', 'misses', 'decodes', 'evictions']:
            s = model(); s[name] = 1; self.assertFalse(stated_cache_shape(s), name)

    def test_20_other_runtime_state_is_not_unnecessarily_zeroed(self):
        s = model(); self.assertGreater(s['runtime_state_live'], 0)
        self.assertTrue(stated_cache_shape(s)); self.assertTrue(reservation_projection(s))

    def test_21_common_control_refuses_foreign_runtime_wasi_or_missing_header(self):
        s = model(); self.assertTrue(common_owner_preflight_projection(s))
        for key, value in [('cache_runtime_owner', 0), ('control_owner', 18),
                           ('wasi_owner', 18), ('header_ticket', False)]:
            q = copy.deepcopy(s); q[key] = value
            self.assertFalse(common_owner_preflight_projection(q), key)

    def test_22_counterexample_same_control_different_wasi_instance(self):
        q = model(); q['wasi_instance'] = 'wasi-B'
        self.assertTrue(common_owner_preflight_projection(q))
        self.assertNotEqual(q['wasi_instance'], q['construction_wasi_instance'])

    def test_23_counterexample_optional_wasi_history_is_not_checked(self):
        q = model(); q['wasi_owner'] = None; q['wasi_instance'] = None
        self.assertTrue(common_owner_preflight_projection(q))
        self.assertIsNotNone(q['construction_wasi_instance'])

    def test_24_counterexample_failed_imported_acquire_retains_all_cache_shape(self):
        before = model(); after = copy.deepcopy(before)
        # Literal source order: work(1), function(0) => None, latch failure.
        after['cache_work'] += 1; after['cache_attempts'] = 1
        after['first_failure'] = 'not_defined_function'
        self.assertTrue(stated_cache_shape(before)); self.assertTrue(stated_cache_shape(after))
        self.assertTrue(common_owner_preflight_projection(after))
        self.assertTrue(reservation_projection(after))
        self.assertEqual(modeled_header(before, [bytes(32)] * 8), modeled_header(after, [bytes(32)] * 8))
        self.assertNotEqual(before['cache_attempts'], after['cache_attempts'])

    def test_25_constructor_cache_work_cannot_be_required_zero(self):
        self.assertEqual(model()['cache_work'], 4805)
        self.assertTrue(stated_cache_shape(model()))

    def test_26_counterexample_zero_byte_unrelated_ticket_keeps_B_equality(self):
        a = model(); b = copy.deepcopy(a); b['unrelated_zero_cache_tickets'] = 1
        self.assertTrue(reservation_projection(b))
        self.assertEqual(a['cache_current'], b['cache_current'])
        self.assertNotEqual(a['unrelated_zero_cache_tickets'], b['unrelated_zero_cache_tickets'])

    def test_27_counterexample_same_structural_layout_different_external_identity(self):
        a = model(); b = copy.deepcopy(a); b['external_build_attestation'] = 'a different unverified claim'
        self.assertEqual(a['same_build_shape'], b['same_build_shape'])
        self.assertEqual(modeled_header(a, [bytes(32)] * 8), modeled_header(b, [bytes(32)] * 8))
        self.assertNotEqual(a['external_build_attestation'], b['external_build_attestation'])

    def test_28_counterexample_second_owner_rows_can_share_same_header(self):
        a = model(); b = copy.deepcopy(a); b['snapshot_owner_identity'] = 'sealed-owner-B'
        self.assertEqual(modeled_header(a, [bytes(32)] * 8), modeled_header(b, [bytes(32)] * 8))
        self.assertNotEqual(a['snapshot_owner_identity'], b['snapshot_owner_identity'])

    def test_29_H_B_exact_arithmetic_no_duplicate_plan_index(self):
        h, b = layout(997, 601, 53, 17, 31, 23, 11, 2, 3)
        self.assertEqual(h, 9345)
        self.assertEqual(b, 15108)
        self.assertEqual(b - h, 2 * 31 + 3 * 23 + 512 * 11)
        self.assertNotEqual(b, h + 192 + 512 * 17 + 2 * 31 + 3 * 23 + 512 * 11)

    def test_30_every_arithmetic_boundary_checked(self):
        self.assertEqual(add(U64, 0), U64); self.assertEqual(mul(U64, 1), U64)
        for call in [lambda: add(U64, 1), lambda: mul(U64, 2), lambda: add(-1, 0),
                     lambda: layout(1, 2, 0, 0, 0, 0, 0, 1, 1),
                     lambda: layout(U64, 0, 1, 0, 0, 0, 0, 1, 1),
                     lambda: layout(1, 1, 0, U64, 0, 0, 0, 1, 1),
                     lambda: layout(1, 1, 0, 0, U64, 0, 0, 2, 1),
                     lambda: layout(1, 1, 0, 0, 0, U64, 0, 1, 2),
                     lambda: layout(1, 1, 0, 0, 0, 0, U64, 1, 1)]:
            with self.assertRaises(ValueError): call()
        with self.assertRaises(ValueError): layout(2**32 - 1, 0, 1, 0, 0, 0, 0, 1, 1, 2**32 - 1)

    def test_31_reservation_current_fixed_resident_and_capacity(self):
        for key, delta in [('fixed', 1), ('cache_base', 1), ('cache_current', 1), ('resident', 1)]:
            s = model(); s[key] += delta; self.assertFalse(reservation_projection(s), key)
        s = model(); s['budget']['cache_bytes'] = s['cache_base'] - 1
        self.assertFalse(reservation_projection(s))
        s['budget']['cache_bytes'] = s['cache_base']; self.assertTrue(reservation_projection(s))

    def test_32_entry_limit_zero_or_above_capacity_stays_supported_by_encoding(self):
        for entry in [0, 1, 1000000]:
            s = model(); s['budget']['cache_bytes'] = 20000; s['budget']['cache_entry_bytes'] = entry
            self.assertTrue(reservation_projection(s))
            self.assertEqual(int.from_bytes(modeled_header(s, [bytes(32)] * 8)[96:104], 'little'), entry)

    def test_33_header_profile_and_row_error_coordinates(self):
        self.assertEqual(80000 * 32, 2560000)
        self.assertEqual(512 + 2560000, 2560512)
        self.assertEqual(4096 // 32, 128); self.assertEqual(80000 // 128, 625)
        self.assertEqual(625 * 32, 20000)
        self.assertEqual(79999 * 32, 2559968)
        self.assertEqual(512 + 79999 * 32, 2560480)

    def test_34_header_first_file_is_refused_by_unchanged_row_admission(self):
        # Pure predicate model; no File or kernel behavior is exercised here.
        admission = lambda length, offset, regular: regular and length == 0 and offset == 0
        self.assertTrue(admission(0, 0, True))
        for length, offset in [(512, 512), (512, 0), (0, 512)]:
            self.assertFalse(admission(length, offset, True))
        self.assertFalse(admission(0, 0, False))

    def test_35_composition_subrange_and_wrong_body_detection_are_separate(self):
        # Small synthetic body: establishes byte/digest algebra, no real profile.
        body = b'row-owner-A' * 7
        header = modeled_header(model(), [bytes(32)] * 7 + [hashlib.sha256(body).digest()])
        joined = header + body
        self.assertEqual(hashlib.sha256(joined[512:]).digest(), joined[352:384])
        wrong = header + b'row-owner-B' * 7
        self.assertNotEqual(hashlib.sha256(wrong[512:]).digest(), wrong[352:384])
        self.assertNotEqual(hashlib.sha256(joined).digest(), hashlib.sha256(body).digest())

    def test_36_no_digest_cycle_with_external_final_selection(self):
        # Value means canonical artifact dependencies, never verified provenance.
        graph = {'source_manifest': (), 'input': (), 'schema': (), 'binary': (),
                 'layout': ('binary', 'source_manifest'), 'snapshot_record': ('input', 'source_manifest'),
                 'body': ('snapshot_record', 'binary'),
                 'header': ('source_manifest', 'input', 'schema', 'binary', 'layout', 'snapshot_record', 'body'),
                 'profile': ('header', 'body'), 'selection': ('profile', 'binary', 'layout')}
        def visit(n, active, done):
            if n in active: raise ValueError('digest cycle')
            if n in done: return
            for dependency in graph[n]: visit(dependency, active | {n}, done)
            done.add(n)
        visit('selection', set(), set())
        graph['header'] += ('selection',)
        with self.assertRaises(ValueError): visit('selection', set(), set())
        self.assertFalse(C['header']['final_selection_digest_included'])

    def test_37_embedding_own_binary_digest_or_reciprocal_layout_digest_cycles(self):
        # A measured shape can be embedded; an exact final executable hash cannot
        # be embedded into that same executable by calling it an attestation.
        dependencies = {'binary': ['layout_receipt'], 'layout_receipt': ['binary']}
        self.assertIn('binary', dependencies['layout_receipt'])
        self.assertIn('layout_receipt', dependencies['binary'])
        receipt_only = {'binary': [], 'layout_receipt': ['binary']}
        self.assertEqual(receipt_only['binary'], [])

    def test_38_fresh_source_closure_has_at_least_134_paths(self):
        self.assertEqual(len(D['canonical_members']), 132)
        self.assertEqual(len(D['row_added']), 2)
        self.assertEqual(len(D['canonical_members']) + len(D['row_added']), 134)
        self.assertNotEqual(134, 132)
        self.assertEqual(len(D['completion_changed']), 4)
        self.assertEqual(D['row_missing'], ['include/mixer_vm.h', 'include/mixer_vm_capability.h', 'include/mixer_vm_guest_ui.h'])

    def test_39_source_witness_pairing_is_not_historical_instance_identity(self):
        cache = load_source('src/experimental_swift_reactor/cache.rs')
        wasi = load_source('src/experimental_wasi/accounted.rs')
        self.assertIn('wasi.map(|w| w.checked_usage(control, cursor)).transpose()', cache)
        self.assertIn('control.check_reservation_owner(header, cursor, observation)?;', wasi)
        fields = cache.split('pub(crate) struct SwiftFunctionCache {', 1)[1].split('\n}', 1)[0]
        self.assertNotIn('wasi', fields)
        self.assertIn('wasi: Option<&\'a AccountedWasi>', cache)

    def test_40_source_witness_failed_acquire_precedes_cache_mutation(self):
        generic = load_source('src/experimental/cache/borrowed.rs')
        pin = generic.split('pub(crate) fn pin<M: CacheMode>(', 1)[1].split('pub(crate) struct CacheFields', 1)[0]
        self.assertLess(pin.index('meter.work(1)?;'), pin.index('.function(function)'))
        self.assertLess(pin.index('"not_defined_function"'), pin.index('meter.acquire_pin()?'))
        self.assertNotIn('.miss(', pin); self.assertNotIn('.hit(', pin)
        cache = load_source('src/experimental_swift_reactor/cache.rs')
        check = cache.split('fn check_header(', 1)[1].split('\n    }', 1)[0]
        self.assertNotIn('check_with_wasi', check)
        self.assertIn('check_reservation_owner', check)

    def test_41_source_witness_zero_byte_tickets_and_global_only_count(self):
        control = load_source('src/experimental_swift_reactor/control.rs')
        admit = control.split('pub(crate) fn admit_with_wasi(', 1)[1].split('/// Aggregate locals', 1)[0]
        self.assertIn('self.reservations.live_tickets += 1;', admit)
        self.assertNotIn('bytes == 0', admit)
        usage = control.split('pub struct SwiftReservationUsage {', 1)[1].split('\n}', 1)[0]
        self.assertIn('pub current: usize', usage); self.assertNotIn('tickets', usage)

    def test_42_source_witness_owned_immutable_snapshot_and_same_owner_row_requirement(self):
        swift = load_source('src/experimental/swift.rs')
        self.assertIn('source: Box<[u8]>', swift)
        self.assertIn('pub fn source(&self) -> &[u8]', swift)
        row = (PREP / 'inputs/verification/swift-cache-state-profile-adapter/source/vm/src/experimental_swift_reactor/diagnostic_profile.rs').read_text()
        self.assertIn('pub(crate) fn write_profile_row_body_v1(\n    snapshot: &ValidatedSwiftReactor,', row)
        self.assertIn('metadata.len() != 0 || position != 0', row)

    def test_43_root_accepted_row_totals_are_not_new_allowances(self):
        a = json.loads((PREP / 'inputs/verification/swift-semantic-adapter-root-review/profile-adapter-acceptance.json').read_bytes())
        self.assertTrue(a['implementation_accepted']); self.assertFalse(a['canonical_integration_selected'])
        self.assertEqual(a['accounting']['adapter_caller_callee_union_bytes'], 11912)
        self.assertEqual(a['accounting']['including_constructor_and_owner_fixed_places_bytes'], 13904)
        self.assertEqual(a['accounting']['source_action_plus_cumulative_requested_IO_byte_bound'], 450652288)
        self.assertFalse(a['accounting']['VM_credit_or_CPU_or_RSS_or_stack_bound'])
        self.assertFalse(C['combined_analyzer_accounting_accepted'])

    def test_44_literal_false_fixture_authority_remains_source_only(self):
        f = (PREP / 'inputs/verification/swift-cache-state-ci/pack/source/library/cache_state.rs').read_text()
        for name in ['stored_prefix_validated', 'full_replay_accepted', 'semantic_metrics_valid', 'real_binding_verified']:
            self.assertIn(f'pub const fn {name}(&self) -> bool {{\n        false\n    }}', f)
        self.assertFalse(C['context']['fixture_can_gain_real_authority'])
        self.assertFalse(C['context']['real_schema_selected'])

    def test_45_missing_real_dependencies_and_context_partition_remain_explicit(self):
        self.assertEqual(C['context']['bytes'], 8192)
        self.assertEqual((C['context']['selection_bytes'], C['context']['original_result_bytes'], C['context']['custody_bytes']), (4096, 2048, 2048))
        self.assertEqual(4096 + 2048 + 2048, 8192)
        snapshot = C['header']['digests'][6]
        self.assertIn('currently unavailable', snapshot['preimage'])
        self.assertTrue(any('complete17-field invocation budget' in x for x in C['pending_dependencies']))

    def test_46_supported_snapshot_policy_revision_body_and_type_predicates(self):
        self.assertTrue(snapshot_admissible(model()))
        for key, value in [('policy', 'unselected'), ('validator', 2), ('decoder', 2),
                           ('imports', 33), ('imports', 35), ('validated', 8),
                           ('types', U32 + 1), ('types', -1)]:
            s = model(); s[key] = value
            self.assertFalse(snapshot_admissible(s), (key, value))
        for types in [0, 1, U32]:
            s = model(); s['types'] = types; self.assertTrue(snapshot_admissible(s))

    def test_47_total_row_boundary_and_checked_import_defined_addition(self):
        for defined, accepted in [(0, True), (79966, True), (79967, False), (U64, False)]:
            s = model(); s['defined'] = s['validated'] = defined
            self.assertEqual(snapshot_admissible(s), accepted, defined)
        # Zero defined is admissible to the row component but unsupported by
        # the existing profile/cache fixture grammar. Do not alter VM admission.
        s = model(); s['defined'] = s['validated'] = 0
        self.assertTrue(snapshot_admissible(s)); self.assertFalse(stated_cache_shape(s))

    def test_48_each_digest_slot_swap_is_opaque_encoding_not_a_verified_join(self):
        claims = [bytes([i]) * 32 for i in range(8)]
        expected = modeled_header(model(), claims)
        for i in range(7):
            swapped = list(claims); swapped[i], swapped[i + 1] = swapped[i + 1], swapped[i]
            raw = modeled_header(model(), swapped)
            self.assertNotEqual(raw, expected)
            self.assertEqual(len(raw), 512)
        self.assertTrue(all(v is False for v in C['authority'].values()))


if __name__ == '__main__':
    unittest.main()
