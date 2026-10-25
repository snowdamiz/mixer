import unittest
from model import (Resident, Replay, Budget, Plans, MAX, plan, classify, reuse,
                   interval, OperationGate, binding_admission, assembled_hash_units,
                   exact_context)
from interface_schema import SCALARS, REPORT_HEADER, REPORT_REGIONS, HOST_REGIONS, offsets
from interface_schema import (ACTIVE_STATES, RUST_IO_ATTEMPTS, WRAPPER_INPUT_CAPS,
                              WRAPPER_STEP_LIMIT, wrapper_budget)

class FiniteContract(unittest.TestCase):
    def test_fixed_interface_names_and_offsets(self):
        self.assertEqual(len(SCALARS), 512); self.assertEqual(len(set(SCALARS)), 512)
        self.assertEqual(len(REPORT_HEADER), 32)
        self.assertEqual(sum(length for _, length in REPORT_REGIONS), 49152)
        self.assertEqual(sum(length for _, length in HOST_REGIONS), 8192)
        self.assertEqual(offsets(HOST_REGIONS), [('header', 0, 512),
            ('custody', 512, 3840), ('digests', 4352, 512),
            ('bindings_and_result', 4864, 2048), ('observations', 6912, 1024),
            ('reserved', 7936, 256)])
        self.assertTrue(all(offset % 8 == 0 for _, offset, _ in offsets(REPORT_REGIONS)))

    def test_ties_use_lowest_slot(self):
        rows = [Resident(1, 4, 0, 7), Resident(2, 4, 0, 7)]
        self.assertEqual(plan(rows, 0, 8, 4), ((0,), (0,), 0))

    def test_selection_emission_and_destination_differ(self):
        rows = [Resident(1, 3, 0, 30), Resident(2, 3, 0, 10), Resident(3, 3, 0, 20)]
        self.assertEqual(plan(rows, 0, 9, 7), ((1, 2, 0), (0, 1, 2), 0))
        self.assertEqual(plan(rows, 0, 9, 5), ((1, 2), (1, 2), 2))

    def test_empty_slot_is_replaced_by_last_selected(self):
        rows = [None, Resident(2, 5, 0, 1), Resident(3, 5, 0, 2)]
        self.assertEqual(plan(rows, 0, 10, 6), ((1, 2), (1, 2), 2))

    def test_held_pin_blocks_eviction(self):
        rows = [Resident(1, 4, 1, 0), Resident(2, 4, 0, 1)]
        self.assertEqual(plan(rows, 0, 8, 4), ((1,), (1,), 1))
        with self.assertRaises(ValueError):
            plan([Resident(1, 4, 1, 0)], 0, 4, 4)

    def test_failure_before_take_preserves_resident(self):
        r = Replay([Resident(1, 4, 0, 0)])
        r.begin(0, 4); r.fail()
        self.assertIsNotNone(r.slots[0]); self.assertEqual(r.completed, 0)

    def test_refund_failure_preserves_taken_uncommitted(self):
        r = Replay([Resident(1, 4, 0, 0)])
        r.begin(0, 4); r.take(); r.fail()
        self.assertIsNone(r.slots[0]); self.assertEqual((r.taken, r.completed), (1, 0))
        self.assertTrue(r.pending[2])

    def test_commit_count_is_separate(self):
        r = Replay([Resident(1, 4, 0, 0)])
        r.begin(0, 4); r.take(); r.commit(); r.fail()
        self.assertEqual((r.taken, r.completed), (1, 1))

    def test_release_joins_real_nonce_and_keeps_timestamp(self):
        r = Replay([Resident(1, 4, 0, 2)])
        r.publish(0, 5, 0, 1, 20)
        with self.assertRaises(AssertionError): r.release(0, 6, 0, 1)
        with self.assertRaises(AssertionError): r.release(0, 5, 0, 1, 0)
        r.release(0, 5, 0, 1)
        self.assertEqual(r.slots[0].timestamp, 20)
        with self.assertRaises(KeyError): r.release(0, 5, 0, 1)

    def test_consuming_zeros_cannot_erase_guest_pins(self):
        r = Replay([Resident(1, 4, 0, 2)])
        r.publish(0, 1, 0, 1, 3)
        consuming_ledger = [0] * 15
        self.assertTrue(all(n == 0 for n in consuming_ledger))
        self.assertEqual(len(r.pins), 1); self.assertEqual(r.slots[0].pins, 1)

    def test_cap_never_complete_and_requires_actual_cap(self):
        self.assertEqual(classify(1, 2, 2, 4, 2, 1280), "truncated-prefix")
        self.assertEqual(classify(1, 2, 3, 4, 2, 1280), "invalid")
        self.assertEqual(classify(1, 2, 2, 2, 0, 1280), "invalid")

    def test_unknown_code_buffer_loss_and_other_flags_invalid(self):
        self.assertEqual(classify(128, 9, 100, 9, 0, 1024), "invalid")
        self.assertEqual(classify(128, 32, 100, 33, 1, 5120), "invalid")
        for flags in (2, 3, 128, 256, 512):
            self.assertEqual(classify(flags, 2, 2, 4, 2, 1280), "invalid")

    def test_context_lifecycle_and_original_are_mandatory(self):
        self.assertEqual(classify(0, 1, 2, 1, 0, 1152), "complete-records")
        for key in ("replay_ok", "bindings", "lifecycle", "original", "budget_complete"):
            self.assertEqual(classify(0, 1, 2, 1, 0, 1152, **{key: False}), "invalid")

    def test_record_reserve_exhaustion_is_before_commit(self):
        b = Budget(30, 10, 8)
        self.assertTrue(b.record(8, 1)); self.assertTrue(b.record(5, 2))
        self.assertFalse(b.record(1, 3)); self.assertEqual((b.accepted, b.state), (2, 2))
        self.assertEqual(b.remaining, 7)

    def test_exact_reserve_boundary_and_cost_contract(self):
        b = Budget(18, 10, 8)
        self.assertTrue(b.record(8, 1)); self.assertFalse(b.record(0, 2))
        with self.assertRaises(AssertionError): Budget(18, 10, 8).record(9, 1)

    def test_reuse_0_to_63_and_larger_first_separate(self):
        self.assertEqual(reuse([1, 1, 2, 1]), ["first", 0, "first", 1])
        self.assertEqual(reuse(list(range(64)) + [0])[-1], 63)
        self.assertEqual(reuse(list(range(65)) + [0])[-1], ">=64")

    def test_plan_collision_and_full_immutable_identity(self):
        p = Plans(); identity = (100, 4, 7)
        p.finish(1, identity, 0); p.finish(1, identity, 2)
        for wrong in ((101, 4, 7), (100, 5, 7), (100, 4, 8)):
            with self.assertRaises(AssertionError): p.finish(1, wrong, 2)
        p.finish(513, (200, 4, 7), 1, 1)
        with self.assertRaises(AssertionError): p.finish(1, identity, 2)
        with self.assertRaises(AssertionError): p.finish(513, (200, 4, 7), 1, 1)

    def test_completed_and_partial_credit_are_separate(self):
        self.assertEqual(interval(10, end=30), {"completed": 20, "partial": 0})
        self.assertEqual(interval(10, failure=21), {"completed": 0, "partial": 11})
        with self.assertRaises(AssertionError): interval(10, end=9)
        with self.assertRaises(AssertionError): interval(10, end=20, failure=21)

    def test_release_forbidden_in_every_open_acquisition_state(self):
        for state in ACTIVE_STATES:
            if state == 'Idle': continue
            g = OperationGate(); g.state = state
            with self.subTest(state=state), self.assertRaises(AssertionError): g.event('Release')
        g = OperationGate(); g.event('AcquireBegin'); g.event('LookupHit')
        with self.assertRaises(AssertionError): g.event('Release')
        g.event('PinPublished'); g.event('Release')

    def test_failed_operation_cannot_resume_but_idle_release_is_legal(self):
        for failure in ('PinFailure', 'TerminalFailure'):
            g = OperationGate()
            if failure == 'PinFailure': g.event('AcquireBegin')
            g.event(failure); g.event('Release')
            for kind in ('AcquireBegin', 'LookupHit', 'PlanBegin', 'PlanEnd',
                         'MissReady', 'EvictBegin', 'EvictTaken', 'EvictCommit',
                         'BuildBegin', 'BuildReady', 'PinPublished'):
                with self.subTest(failure=failure, kind=kind), self.assertRaises(AssertionError):
                    g.event(kind)

    def test_terminal_and_phase_require_idle_and_phase5_ends_events(self):
        g = OperationGate(); g.event('AcquireBegin')
        with self.assertRaises(AssertionError): g.event('TerminalFailure')
        with self.assertRaises(AssertionError): g.event('Phase', 4)
        g.event('PinFailure'); g.event('TerminalFailure'); g.event('Phase', 4)
        g.event('Release'); g.event('Phase', 5)
        for kind in ('Release', 'AcquireBegin', 'TerminalFailure', 'Phase'):
            with self.subTest(kind=kind), self.assertRaises(AssertionError): g.event(kind, 5)

    def test_context_read_reserve_and_wrapper_closed_hash_budget(self):
        self.assertEqual(RUST_IO_ATTEMPTS, 263584)
        self.assertEqual(WRAPPER_INPUT_CAPS['context'], 8192)
        self.assertEqual(wrapper_budget(), (17200432, 535808, 896, 65536))
        self.assertEqual(sum(wrapper_budget()), 17802672)
        self.assertLess(sum(wrapper_budget()), WRAPPER_STEP_LIMIT)
        self.assertEqual((5 + 4) + (1 + 3), 13)  # data owners + null stdio owners
        self.assertEqual(5 * 8 + 2 * 8 + 4, 60)  # raw custody rows, no object list

    def test_source_prerequisite_cannot_be_replaced_by_hash_syntax(self):
        self.assertFalse(binding_admission(True, False, False, True, True))
        for i in range(5):
            claims = [True] * 5; claims[i] = False
            self.assertFalse(binding_admission(*claims))
        self.assertTrue(binding_admission(True, True, True, True, True))

    def test_context_exact_length_eof_and_combined_reserve(self):
        self.assertEqual(exact_context([256] * 32, ['Interrupted'] * 31 + [0]), 64)
        for parts, eof in (([8191], [0]), ([8193], [0]), ([8192], [1]),
                           ([8192], ['Interrupted'] * 32), ([8192], ['IO'])):
            with self.subTest(parts=parts, eof=eof), self.assertRaises(AssertionError):
                exact_context(parts, eof)

    def test_short_reads_are_hashed_once_as_one_assembled_block(self):
        parts = [1] * 31 + [97]
        self.assertEqual(assembled_hash_units(parts), 2)
        self.assertEqual(sum((n + 63) // 64 for n in parts), 33)
        with self.assertRaises(AssertionError): assembled_hash_units([1] * 33)

if __name__ == "__main__": unittest.main(verbosity=2)
