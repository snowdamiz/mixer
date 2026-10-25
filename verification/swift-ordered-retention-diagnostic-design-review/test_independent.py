"""Independent finite protocol review; imports only the frozen synthetic codec.

This is deliberately not a Rust observer, target driver, or full event schema.
The named incomplete-model cases preserve the limit of the producer evidence.
"""
import copy
import importlib.util
from pathlib import Path
import struct
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('reviewed_codec', HERE / 'inputs/producer/codec_model.py')
MODEL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODEL)
GATE_SPEC = importlib.util.spec_from_file_location('reviewed_finalization', HERE / 'inputs/producer/finalization_model.py')
GATE_MODEL = importlib.util.module_from_spec(GATE_SPEC)
GATE_SPEC.loader.exec_module(GATE_MODEL)

ABSENT = 2**64 - 1
WORD = struct.Struct('<16Q')
HEADER = struct.Struct('<8sQQQ32s448s')
FOOTER = struct.Struct('<8s18Q360s')
FIELDS = ('seq', 'kind', 'phase', 'op', 'work', 'instructions', 'function',
          'body_offset', 'body_len', 'type_index', 'slot', 'pin_slot', 'nonce', 'a', 'b', 'c')
KIND = dict(begin=1, lookup=2, plan_begin=3, plan_end=4, miss_ready=5,
            evict_begin=6, evict_commit=7, build_begin=8, build_ready=9,
            pin=10, release=11, phase=12, failure=13, evict_taken=14)


def row(kind, **kwargs):
    x = dict.fromkeys(FIELDS, 0)
    x.update(kind=KIND[kind], slot=ABSENT, pin_slot=ABSENT)
    x.update(kwargs)
    return x


def numbered(rows):
    out = copy.deepcopy(rows)
    for number, x in enumerate(out, 1):
        x.update(seq=number, work=number*7, instructions=number*3)
    return out


def miss(function=1, op=1, slot=0, pin_slot=0, nonce=1, size=100):
    rows = [row(k, op=op, function=function) for k in
            ('begin', 'lookup', 'plan_begin', 'plan_end', 'miss_ready', 'build_begin', 'build_ready')]
    rows += [row('pin', op=op, function=function, slot=slot, pin_slot=pin_slot,
                 nonce=nonce, a=1, b=size, c=1)]
    return rows


def release(function=1, slot=0, pin_slot=0, nonce=1, remaining=0):
    return row('release', function=function, slot=slot, pin_slot=pin_slot,
               nonce=nonce, a=remaining)


def hit(function=1, op=2, slot=0, pin_slot=1, nonce=2, size=100, count=2):
    return [row('begin', op=op, function=function),
            row('lookup', op=op, function=function, slot=slot, a=1),
            row('pin', op=op, function=function, slot=slot, pin_slot=pin_slot,
                nonce=nonce, b=size, c=count)]


def pack(rows, flags=0, attempted=None, final=(0, 0, 0, 0), cap=32):
    """Independent byte encoder for tiny fixed synthetic records."""
    rows = numbered(rows)
    count = len(rows)
    last = rows[-1] if rows else dict(seq=0, work=0, instructions=0, op=0)
    footer_words = (1, count, flags, count if attempted is None else attempted,
                    last['seq'], last['work'], last['instructions'], last['work'],
                    last['instructions'], *final, 0, last['op'], 49, 1, 0)
    return (HEADER.pack(b'MXORD001', 1, 128, cap, b'x'*32, bytes(448)) +
            b''.join(WORD.pack(*(x[k] for k in FIELDS)) for x in rows) +
            FOOTER.pack(b'MXEND001', *footer_words, bytes(360)))


def independent_state(rows):
    """Tiny resident/pin oracle, independently organized as resident and token tables.

    Called only for the constructed valid traces below, not schema admission.
    """
    residents, tokens = {}, {}
    totals = dict(hits=0, misses=0, decodes=0, evictions=0, releases=0)
    for x in rows:
        k = x['kind']
        if k == KIND['lookup']:
            totals['hits' if x['a'] else 'misses'] += 1
        elif k == KIND['pin']:
            if x['a']:
                residents[x['slot']] = [x['function'], x['b'], 0]
                totals['decodes'] += 1
            residents[x['slot']][2] += 1
            tokens[(x['pin_slot'], x['nonce'])] = x['slot']
        elif k == KIND['release']:
            residents[tokens.pop((x['pin_slot'], x['nonce']))][2] -= 1
            totals['releases'] += 1
        elif k == KIND['evict_taken']:
            del residents[x['slot']]
        elif k == KIND['evict_commit']:
            totals['evictions'] += 1
    totals.update(resident_entries=len(residents), active_pins=len(tokens),
                  resident_bytes=sum(x[1] for x in residents.values()))
    return totals


def classify_tiny(data):
    rows, flags = MODEL.decode(data)
    # This required caller ordering is explicit; replay itself is not a classifier.
    if flags & ~1:
        return 'invalid'
    state = MODEL.replay(rows, truncated=bool(flags & 1))
    return 'truncated-prefix' if flags & 1 else state['coverage']


class IndependentReview(unittest.TestCase):
    def test_header_record_footer_and_cap_arithmetic(self):
        self.assertEqual((HEADER.size, WORD.size, FOOTER.size), (512, 128, 512))
        self.assertEqual(512 + 4194304*128 + 512, 536871936)
        hits, misses, evictions = 537576, 61628, 61564
        projected = 4*(hits+misses) + 5*misses + 3*evictions + 8
        self.assertEqual((projected, projected*128), (2889656, 369875968))
        self.assertLess(projected, 4194304)
        self.assertEqual((131072+2)*32, 4194368)

    def test_independent_wire_encoding_roundtrips_without_producer_encoder(self):
        expected = numbered(miss())
        decoded, flags = MODEL.decode(pack(miss()))
        self.assertEqual((decoded, flags), (expected, 0))

    def test_nested_held_pin_and_release_after_other_operation(self):
        rows = miss() + hit() + miss(function=2, op=3, slot=1, pin_slot=2, nonce=3, size=140)
        rows += [release(nonce=1, remaining=1), release(function=2, slot=1, pin_slot=2, nonce=3),
                 release(pin_slot=1, nonce=2)]
        state = MODEL.replay(numbered(rows))
        for key, value in independent_state(rows).items():
            self.assertEqual(state[key], value)
        self.assertEqual((state['resident_entries'], state['active_pins']), (2, 0))

    def test_two_victim_removals_one_acquisition(self):
        rows = miss() + [release()] + miss(function=2, op=2, slot=1, nonce=2, size=150)
        rows += [release(function=2, slot=1, nonce=2), row('begin', op=3, function=3),
                 row('lookup', op=3, function=3)]
        for slot, size in ((0, 100), (1, 150)):
            rows += [row('evict_begin', op=3, function=3, slot=slot, a=size),
                     row('evict_taken', op=3, function=3, slot=slot),
                     row('evict_commit', op=3, function=3, slot=slot)]
        rows += [row('build_begin', op=3, function=3), row('build_ready', op=3, function=3),
                 row('pin', op=3, function=3, slot=1, pin_slot=0, nonce=3, a=1, b=260, c=1)]
        state = MODEL.replay(numbered(rows))
        for key, value in independent_state(rows).items():
            self.assertEqual(state[key], value)
        self.assertEqual((state['evictions'], state['resident_bytes']), (2, 260))

    def test_every_eviction_failure_boundary_preserves_only_actual_effect(self):
        prefix = miss() + [release(), row('begin', op=2, function=2), row('lookup', op=2, function=2)]
        transition = [row('evict_begin', op=2, function=2, slot=0, a=100),
                      row('evict_taken', op=2, function=2, slot=0),
                      row('evict_commit', op=2, function=2, slot=0),
                      row('build_begin', op=2, function=2), row('build_ready', op=2, function=2)]
        for count in range(6):
            rows = prefix + transition[:count] + [row('failure', op=2, function=2)]
            state = MODEL.replay(numbered(rows))
            for key, value in independent_state(rows).items():
                self.assertEqual(state[key], value)
            self.assertEqual(state['resident_entries'], int(count < 2))
            self.assertEqual(state['evictions'], int(count >= 3))

    def test_all_tiny_record_cut_positions_are_explicitly_prefix(self):
        rows = miss()
        for n in range(len(rows)):
            data = pack(rows[:n], flags=1, attempted=len(rows), cap=n)
            self.assertEqual(classify_tiny(data), 'truncated-prefix')
        self.assertEqual(classify_tiny(pack(rows)), 'complete-records')

    def test_cap_flag_before_declared_cap_is_rejected(self):
        with self.assertRaises(ValueError):
            MODEL.decode(pack(miss()[:7], flags=1, attempted=8, cap=32))

    def test_sticky_errors_must_be_classified_before_replay(self):
        for flag in (2, 4, 8, 2|4|8):
            self.assertEqual(classify_tiny(pack(miss(), flags=flag)), 'invalid')

    def test_malformed_framing_count_and_raw_tail_rejected(self):
        data = pack(miss())
        bads = [data[:-1], data + bytes(128), data[:512] + data[640:], bytes(len(data))]
        for offset in (0, 8, 16, 32, 64, len(data)-1):
            bad = bytearray(data); bad[offset] ^= 0x80; bads.append(bytes(bad))
        for bad in bads:
            with self.assertRaises((ValueError, struct.error)):
                MODEL.decode(bad)

    def test_every_original_final_ledger_dimension_cannot_qualify(self):
        for i in range(4):
            final = [0]*4; final[i] = 1
            with self.assertRaises(ValueError):
                MODEL.decode(pack(miss(), final=final))

    def test_footer_zero_ledger_never_zeroes_replayed_held_pin(self):
        decoded, flags = MODEL.decode(pack(miss(), final=(0, 0, 0, 0)))
        state = MODEL.replay(decoded)
        self.assertEqual(flags, 0)
        self.assertEqual((state['resident_entries'], state['active_pins'], state['resident_bytes']), (1, 1, 100))

    def test_pin_corruption_is_rejected(self):
        rows = miss() + [release()]
        for key, value in (('nonce', 7), ('function', 2), ('slot', 1), ('pin_slot', 1), ('a', 1)):
            changed = copy.deepcopy(rows); changed[-1][key] = value
            with self.assertRaises(ValueError):
                MODEL.replay(numbered(changed))

    def test_partial_schema_limitations_are_retained_as_pending(self):
        # These admissible corruptions establish limits, not full protocol passes.
        mutations = []
        for key, value in (('body_offset', ABSENT), ('body_len', ABSENT), ('b', 77), ('c', 99)):
            changed = miss(); changed[0][key] = value; mutations.append(changed)
        changed = miss(); changed[3]['phase'] = 5; mutations.append(changed)
        changed = miss(); changed[3]['a'] = 99; mutations.append(changed)
        for changed in mutations:
            decoded, flags = MODEL.decode(pack(changed))
            self.assertEqual(flags, 0)
            self.assertEqual(MODEL.replay(decoded)['coverage'], 'complete-records')
        # Full scan state remains intentionally absent.
        no_scan = [x for x in miss() if x['kind'] not in (KIND['plan_begin'], KIND['plan_end'])]
        self.assertEqual(MODEL.replay(numbered(no_scan))['decodes'], 1)

    def test_independent_single_wrong_callback_end_linearizations(self):
        for end_position in range(4):
            gate = GATE_MODEL.Gate()
            token = None
            steps = ['enter', 'check', 'leave']
            steps.insert(end_position, 'end')
            for step in steps:
                if step == 'end':
                    gate.end()
                elif step == 'enter':
                    token = gate.enter(owner=False)
                elif token is not None and step == 'check':
                    gate.check_owner(token)
                elif token is not None and step == 'leave':
                    gate.leave(token)
            if end_position == 0:
                self.assertEqual(gate.footer, 0)
            elif end_position == 3:
                self.assertEqual(gate.footer, 4)
            else:
                self.assertTrue(gate.end_refused)
                self.assertIsNone(gate.footer)

    def test_finite_callback_capacity_and_refused_end_do_not_make_footer(self):
        gate = GATE_MODEL.Gate()
        tokens = [gate.enter() for _ in range(64)]
        self.assertTrue(all(x is not None for x in tokens))
        self.assertIsNone(gate.enter(owner=False))
        self.assertEqual(gate.flags, 4)
        self.assertIsNone(gate.end())
        self.assertTrue(gate.end_refused)
        for token in reversed(tokens):
            gate.leave(token)
        self.assertIsNone(gate.footer)
        self.assertIsNone(gate.enter())
        with self.assertRaises(ValueError):
            gate.end()

    def test_terminal_failure_outside_pin_and_no_later_acquisition(self):
        for cursor in (ABSENT, 12):
            rows = [row('failure', op=0, function=cursor)]
            decoded, _ = MODEL.decode(pack(rows))
            self.assertEqual(MODEL.replay(decoded)['active_pins'], 0)
            with self.assertRaises(ValueError):
                MODEL.replay(numbered(rows + miss()))
        rows = miss() + [row('failure', op=0, function=ABSENT)]
        self.assertEqual(MODEL.replay(numbered(rows))['active_pins'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
