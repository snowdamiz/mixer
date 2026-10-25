import copy
import struct
import unittest
from codec_model import CAP, FOOTER, HEADER, KINDS, NONE, decode, encode, encode_record, event, replay


def cold(function=1, op=1, slot=0, pin_slot=0, nonce=1, start=1):
    kinds = ('begin', 'lookup', 'plan_begin', 'plan_end', 'miss_ready', 'build_begin', 'build_ready', 'pin')
    out = [event(k, start + i, op=op, function=function, work=start + i) for i, k in enumerate(kinds)]
    out[-1].update(slot=slot, pin_slot=pin_slot, nonce=nonce, a=1, b=100, c=1)
    return out


class CodecTests(unittest.TestCase):
    def test_fixed_width_and_maximum_file_arithmetic(self):
        self.assertEqual((HEADER.size, FOOTER.size), (512, 512))
        self.assertEqual(len(encode_record(event('begin', 1))), 128)
        self.assertEqual(1024 + CAP * 128, 536_871_936)

    def test_lossless_roundtrip_and_actual_publication(self):
        events = cold()
        decoded, flags = decode(encode(events))
        self.assertEqual(decoded, events)
        self.assertEqual(flags, 0)
        self.assertEqual(replay(decoded)['decodes'], 1)

    def test_exact_cap_and_overflow_keep_contiguous_prefix(self):
        events = cold()
        for cap in range(9):
            decoded, flags = decode(encode(events, cap=cap))
            self.assertEqual(decoded, events[:cap])
            self.assertEqual(bool(flags & 1), cap < len(events))
            self.assertEqual(len(encode(events, cap=cap)), 1024 + 128 * min(cap, 8))
            if cap < 8:
                self.assertEqual(replay(decoded, truncated=True)['coverage'], 'prefix')

    def test_cap_only_flag_requires_declared_cap_was_reached(self):
        encoded = bytearray(encode(cold(), cap=7))
        struct.pack_into('<Q', encoded, 24, 32)
        with self.assertRaises(ValueError):
            decode(encoded)
        records, flags = decode(encode(cold(), cap=7))
        self.assertEqual((len(records), flags), (7, 1))

    def test_missing_partial_and_extra_wire_rejected(self):
        good = encode(cold())
        for bad in (b'', good[:-1], good[:-512], good + b'x', good[:520] + good[521:]):
            with self.assertRaises(ValueError):
                decode(bad)

    def test_context_reserved_and_finalization_rejected(self):
        good = bytearray(encode(cold()))
        for offset in (0, 32, 100, len(good) - 1):
            bad = good.copy(); bad[offset] ^= 1
            with self.assertRaises(ValueError):
                decode(bad)
        with self.assertRaises(ValueError):
            decode(encode(cold(), finalized=0))

    def test_closed_integer_types_and_ranges(self):
        for name, value in (('work', True), ('work', 1.0), ('work', -1), ('seq', NONE + 1),
                            ('kind', 99), ('phase', 6), ('function', 80_000), ('slot', 64)):
            x = event('begin', 1); x[name] = value
            with self.assertRaises(ValueError):
                encode_record(x)
        x = event('begin', 1); x['unknown'] = 0
        with self.assertRaises(ValueError):
            encode_record(x)

    def test_gaps_duplicates_and_monotonicity(self):
        for i, name, value in ((1, 'seq', 1), (1, 'seq', 3), (4, 'work', 0), (4, 'instructions', 0)):
            events = cold()
            for e in events: e['instructions'] = e['seq']
            events[i][name] = value
            with self.assertRaises(ValueError):
                decode(encode(events))

    def test_nonzero_original_cleanup_does_not_become_complete(self):
        for i in range(4):
            final = [0] * 4; final[i] = 1
            with self.assertRaises(ValueError):
                decode(encode(cold(), final=final))

    def test_io_context_counter_errors_never_qualify_complete(self):
        for flag in (2, 4, 8):
            _, flags = decode(encode(cold(), flags=flag))
            self.assertNotEqual(flags, 0)
        with self.assertRaises(ValueError):
            decode(encode(cold(), flags=16))

    def test_terminal_counter_regression_rejected(self):
        with self.assertRaises(ValueError):
            decode(encode(cold(), terminal_work=0))

    def test_successful_release_and_hit_preserve_identity(self):
        events = cold()
        events.append(event('release', 9, work=9, function=1, slot=0, pin_slot=0, nonce=1, a=0))
        events += [event('begin', 10, work=10, function=1, op=2),
                   event('lookup', 11, work=11, function=1, op=2, slot=0, a=1),
                   event('pin', 12, work=12, function=1, op=2, slot=0, pin_slot=0, nonce=2, b=100, c=1)]
        state = replay(decode(encode(events))[0])
        self.assertEqual((state['hits'], state['misses'], state['decodes'], state['releases']), (1, 1, 1, 1))

    def test_stale_duplicate_and_wrong_identity_pins_rejected(self):
        good = cold() + [event('release', 9, function=1, slot=0, pin_slot=0, nonce=1)]
        for field, value in (('nonce', 2), ('function', 2), ('slot', 1), ('a', 1)):
            bad = copy.deepcopy(good); bad[-1][field] = value
            with self.assertRaises(ValueError): replay(bad)
        with self.assertRaises(ValueError): replay(good + [dict(good[-1], seq=10)])

    def test_eviction_commit_prefix_is_not_rollback(self):
        events = cold() + [event('release', 9, function=1, slot=0, pin_slot=0, nonce=1)]
        events += [event('begin', 10, op=2, function=2), event('lookup', 11, op=2, function=2),
                   event('evict_begin', 12, op=2, function=2, slot=0, a=100),
                   event('evict_taken', 13, op=2, function=2, slot=0),
                   event('evict_commit', 14, op=2, function=2, slot=0),
                   event('build_begin', 15, op=2, function=2), event('failure', 16, op=2, function=2)]
        state = replay(events)
        self.assertEqual((state['evictions'], state['resident_entries'], state['decodes']), (1, 0, 1))
        with self.assertRaises(ValueError):
            replay(events[:7 + 7] + [event('evict_commit', 15, op=2, function=2, slot=0)])

    def test_eviction_take_before_drop_failure_is_retained(self):
        events = cold() + [event('release', 9, function=1, slot=0, pin_slot=0, nonce=1)]
        events += [event('begin', 10, op=2, function=2), event('lookup', 11, op=2, function=2),
                   event('evict_begin', 12, op=2, function=2, slot=0, a=100),
                   event('evict_taken', 13, op=2, function=2, slot=0),
                   event('failure', 14, op=2, function=2)]
        state = replay(events)
        self.assertEqual((state['evictions'], state['resident_entries']), (0, 0))

    def test_pinned_eviction_missing_begin_and_duplicate_commit_rejected(self):
        events = cold() + [event('begin', 9, op=2, function=2), event('lookup', 10, op=2, function=2)]
        with self.assertRaises(ValueError): replay(events + [event('evict_begin', 11, op=2, function=2, slot=0, a=100)])
        with self.assertRaises(ValueError): replay(events + [event('evict_commit', 11, op=2, function=2, slot=0)])

    def test_missing_publication_build_and_unclosed_operation_rejected(self):
        with self.assertRaises(ValueError): replay(cold()[:-1])
        bad = cold(); bad.pop(6)
        with self.assertRaises(ValueError): replay(bad)
        state = replay(cold()[:-1], truncated=True)
        self.assertTrue(state['pending_operation'])
        self.assertEqual(state['resident_entries'], 0)

    def test_every_synthetic_failure_prefix_retains_completed_effects(self):
        full = cold()
        for end in range(1, 8):
            prefix = full[:end] + [event('failure', end + 1, op=1, function=1)]
            state = replay(prefix)
            self.assertEqual((state['decodes'], state['resident_entries'], state['active_pins']), (0, 0, 0))

    def test_terminal_failure_without_pin_context_and_optional_cursor(self):
        for function in (NONE, 12):
            terminal = event('failure', 1, op=0, function=function)
            self.assertEqual(replay(decode(encode([terminal]))[0])['active_pins'], 0)
            with self.assertRaises(ValueError):
                replay([terminal, event('begin', 2, op=1, function=1)])
        events = cold() + [event('failure', 9, op=0, function=NONE)]
        self.assertEqual(replay(events)['active_pins'], 1)
        self.assertEqual(replay(events)['resident_entries'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
