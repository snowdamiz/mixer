import copy
import os
from pathlib import Path
import tempfile
import unittest

from admission_model import (MAX64, Control, Refusal, SelectedScope, Storage,
                             blocks, checked_add, checked_mul, counted_write,
                             distinct_regular_outputs, original_order, work_bound)


class Controls(unittest.TestCase):
    def control(self, **overrides):
        values = dict(base=100, combined=130, limit=1000, work=7, work_limit=1000)
        values.update(overrides)
        return Control(**values)

    def refuses(self, code, action):
        with self.assertRaises(Refusal) as caught:
            action()
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def test_checked_arithmetic_boundaries(self):
        self.assertEqual(checked_add(MAX64, 0), MAX64)
        self.assertEqual(checked_mul(MAX64, 1), MAX64)
        self.refuses("arithmetic", lambda: checked_add(MAX64, 1))
        self.refuses("arithmetic", lambda: checked_mul(MAX64, 2))
        self.refuses("arithmetic", lambda: checked_add(-1, 1))

    def test_continuous_block_boundaries_without_roundup_overflow(self):
        self.assertEqual([blocks(x) for x in [0, 1, 4095, 4096, 4097]], [0, 1, 1, 1, 2])
        self.assertEqual(blocks(MAX64), (MAX64 // 4096) + 1)

    def test_work_terms_and_attempt_cap(self):
        self.assertEqual(work_bound(4097, 5, [2, 3], 7, 11, 9, 13), (4942, 64))
        self.refuses("arithmetic", lambda: work_bound(MAX64, 1, [], 0, 0, 0, 0))
        self.refuses("arithmetic", lambda: work_bound(1, 0, [], 0, MAX64, 0, 0))

    def test_work_floor_and_floor_minus_one(self):
        exact = self.control(work=7, work_limit=17)
        exact.predebit(10)
        self.assertEqual(exact.work, 17)
        short = self.control(work=7, work_limit=16)
        before = copy.copy(short)
        self.refuses("work", lambda: short.predebit(10))
        self.assertEqual(short, before)

    def test_overflow_refusal_does_not_commit_or_poison(self):
        control = self.control(work=MAX64, work_limit=MAX64)
        before = copy.copy(control)
        self.refuses("arithmetic", lambda: control.predebit(1))
        self.assertEqual(control, before)

    def test_actual_immutable_probe_order(self):
        marker = object()
        control = self.control(first_failure=marker, cancelled=True, expired=True)
        before = copy.copy(control)
        self.refuses("already_terminal", control.probe)
        self.assertEqual(control, before)
        self.assertIs(control.first_failure, marker)
        control.first_failure = None
        self.refuses("cancelled", control.probe)
        control.cancelled = False
        self.refuses("deadline", control.probe)
        self.assertIsNone(control.first_failure)

    def test_nonterminal_work_failure_allows_later_runtime_operation(self):
        control = self.control(work_limit=7)
        self.refuses("work", lambda: control.predebit(1))
        self.assertIsNone(control.first_failure)
        control.probe()

    def test_work_not_refunded_after_storage_refusal(self):
        control = self.control(limit=130)
        control.predebit(10)
        self.refuses("storage", lambda: control.enlarge(101))
        self.assertEqual((control.work, control.ticket_bytes, control.combined), (17, 100, 130))
        self.assertIsNone(control.first_failure)

    def test_storage_exact_total_and_minus_one(self):
        control = self.control(limit=170)
        control.enlarge(140)
        self.assertEqual((control.ticket_bytes, control.combined), (140, 170))
        short = self.control(limit=169)
        before = copy.copy(short)
        self.refuses("storage", lambda: short.enlarge(140))
        self.assertEqual(short, before)

    def test_wrong_ticket_owner_category_and_shrink_preserve_state(self):
        for code, overrides, required in [("owner", {"ticket_owner": 2}, 140),
                                           ("category", {"category": "cache"}, 140),
                                           ("shrink", {}, 99)]:
            control = self.control(**overrides)
            before = copy.copy(control)
            self.refuses(code, lambda: control.enlarge(required))
            self.assertEqual(control, before)

    def test_scope_admission_failure_has_no_early_storage_or_ledger_change(self):
        control = self.control(limit=149)
        before = copy.copy(control)
        self.refuses("storage", lambda: SelectedScope(control, 20))
        self.assertEqual(control, before)

    def test_omitted_phase_remains_charged_at_original_finish(self):
        control = self.control()
        scope = SelectedScope(control, 20)
        # A bounded synthetic phase uses 40 units; no allocation is being measured.
        phase = scope.admit_phase(40)
        self.refuses("phase_live", lambda: scope.finish(scope._early))
        self.assertTrue(phase.alive)
        self.assertEqual(control.finish_original(), {"charged": 160, "invariant": "construction_bound"})

    def test_byte_identical_foreign_storage_cannot_retire_phase(self):
        control = self.control()
        scope = SelectedScope(control, 20)
        phase = scope.admit_phase(40)
        self.refuses("foreign_storage", lambda: scope.retire_phase(Storage(40)))
        self.assertTrue(phase.alive)
        self.assertEqual(control.ticket_bytes, 160)

    def test_consuming_phase_then_early_storage_restores_only_captured_base(self):
        control = self.control()
        scope = SelectedScope(control, 20)
        early, phase = scope._early, scope.admit_phase(40)
        scope.predebit(10)
        scope.retire_phase(phase)
        self.assertFalse(phase.alive)
        self.assertEqual(control.ticket_bytes, 120)
        self.refuses("foreign_storage", lambda: scope.finish(Storage(20)))
        self.assertEqual(scope.finish(early), {"charged": 0, "invariant": None})
        self.assertFalse(early.alive)
        self.assertEqual(control.work, 17)

    def test_all_original_early_outcomes_keep_exact_payload_and_no_snapshot(self):
        for variant in range(1, 8):
            original = (variant, object())
            primary, attempt, events = original_order(original, "error")
            self.assertIs(primary, original)
            self.assertEqual((attempt, events), ("NotReached", []))

    def test_outer_refusal_preserves_success_primary_and_original_order(self):
        original = (8, object())
        for refusal in ["work", "storage", "cancelled", "deadline", "missing_provenance", "alias", "io"]:
            primary, attempt, events = original_order(original, refusal)
            self.assertIs(primary, original)
            self.assertEqual(attempt, refusal)
            self.assertEqual(events, ["inspect_success", "work_predebit", "storage_admission", "sole_guard", "snapshot", "header", "rows"])

    def test_late_original_header_refusal_preserves_snapshot_and_suppresses_rows(self):
        original = (8, object())
        primary, attempt, events = original_order(original, "partial", header_refuses=True)
        self.assertIs(primary[1], original[1])
        self.assertEqual((primary[0], attempt, events[-1]), (6, "partial", "header"))
        self.assertNotIn("rows", events)

    def test_real_kernel_metadata_rejects_all_same_inode_aliases_before_write(self):
        with tempfile.TemporaryDirectory(prefix="mixer-independent-alias-") as folder:
            source = Path(folder) / "snapshot"
            source.touch()
            hardlink, symlink = Path(folder) / "hardlink", Path(folder) / "symlink"
            os.link(source, hardlink)
            symlink.symlink_to(source)
            with source.open("r+b", buffering=0) as left:
                handles = [os.dup(left.fileno())]
                handles.extend(os.open(path, os.O_RDWR) for path in [source, hardlink, symlink])
                try:
                    for fd in handles:
                        self.refuses("alias", lambda: distinct_regular_outputs(left.fileno(), fd))
                        self.assertEqual(os.fstat(fd).st_size, 0)
                        self.assertEqual(os.lseek(fd, 0, os.SEEK_CUR), 0)
                finally:
                    for fd in handles:
                        os.close(fd)

    def test_actual_distinct_empty_outputs_accepted_and_nonempty_refused(self):
        with tempfile.TemporaryDirectory(prefix="mixer-independent-distinct-") as folder:
            with (Path(folder) / "snapshot").open("w+b") as left, (Path(folder) / "rows").open("w+b") as right:
                distinct_regular_outputs(left.fileno(), right.fileno())
                left.write(b"x")
                left.flush()
                self.refuses("output_state", lambda: distinct_regular_outputs(left.fileno(), right.fileno()))

    def test_completing_write_32_succeeds_without_write_33(self):
        calls = []
        def writer(remaining):
            calls.append(remaining)
            return "interrupted" if len(calls) < 32 else remaining
        self.assertEqual(counted_write(4096, writer), (4096, 32))
        self.assertEqual(len(calls), 32)

    def test_incomplete_write_32_refuses_with_no_write_33(self):
        calls = []
        def writer(remaining):
            calls.append(remaining)
            return 1
        error = self.refuses("attempts", lambda: counted_write(4096, writer))
        self.assertEqual((error.acknowledged, error.attempts, len(calls)), (32, 32, 32))

    def test_attempt_budget_resets_only_at_real_continuous_block_boundary(self):
        count = 0
        def writer(remaining):
            nonlocal count
            count += 1
            return "interrupted" if count % 32 else remaining
        self.assertEqual(counted_write(4097, writer), (4097, 64))

    def test_zero_overreport_and_io_keep_actual_progress(self):
        for code, value in [("zero", 0), ("overreport", 4097), ("io", "io")]:
            error = self.refuses(code, lambda: counted_write(4096, lambda _: value))
            self.assertEqual((error.acknowledged, error.attempts), (0, 1))

    def test_late_cancellation_after_full_final_write_retains_bytes_and_no_success(self):
        control = self.control()
        def writer(remaining):
            control.cancelled = True
            return remaining
        error = self.refuses("cancelled", lambda: counted_write(4096, writer, control.probe))
        self.assertEqual((error.acknowledged, error.attempts), (4096, 1))
        self.assertIsNone(control.first_failure)

    def test_interrupted_call_is_followed_by_actual_interruption_check(self):
        control = self.control()
        calls = []
        def writer(remaining):
            calls.append(remaining)
            control.expired = True
            return "interrupted"
        error = self.refuses("deadline", lambda: counted_write(4096, writer, control.probe))
        self.assertEqual((error.acknowledged, error.attempts, len(calls)), (0, 1, 1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
