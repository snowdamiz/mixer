import unittest
from model import Resident, Replay, Budget, Plans, MAX, plan, classify, reuse, interval
from interface_schema import SCALARS, REPORT_HEADER, REPORT_REGIONS, HOST_REGIONS, offsets

class FiniteContract(unittest.TestCase):
    def test_fixed_interface_names_and_offsets(self):
        self.assertEqual(len(SCALARS), 512); self.assertEqual(len(set(SCALARS)), 512)
        self.assertEqual(len(REPORT_HEADER), 32)
        self.assertEqual(sum(length for _, length in REPORT_REGIONS), 49152)
        self.assertEqual(sum(length for _, length in HOST_REGIONS), 8192)
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

if __name__ == "__main__": unittest.main(verbosity=2)
