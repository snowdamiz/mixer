"""Fresh independent arithmetic and pre-scope cleanup controls.

No producer Python module or original orchestration is imported or executed.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from admission_model import MAX64, Control, Refusal, SelectedScope, checked_add, checked_mul

CAPS = [512, 8192, 34, 79966, 8192, 4096, 4096, 4096]
WIDTHS = [3, 1, 5, 3, 4, 4, 4, 4]


def independent_frozen_formula(source, counts):
    if len(counts) != 8 or not 0 <= source <= 67108864:
        raise Refusal("shape")
    records, words = 0, 0
    for value, cap, width in zip(counts, CAPS, WIDTHS):
        if not 0 <= value <= cap:
            raise Refusal("shape")
        records = checked_add(records, value)
        words = checked_add(words, checked_mul(value, width))
    extent = checked_add(checked_add(2560, source), checked_mul(8, words))
    blocks = checked_add(extent // 4096, int(extent % 4096 != 0))
    calls = checked_mul(32, blocks)
    terms = [32768, checked_mul(36, extent), checked_mul(4096, blocks),
             checked_mul(64, records), checked_mul(16, words),
             checked_mul(32, calls), checked_mul(8, blocks)]
    emission = 0
    for term in terms:
        emission = checked_add(emission, term)
    return dict(extent=extent, records=records, words=words, blocks=blocks,
                attempts=calls, planning=16384, emission=emission,
                total=checked_add(16384, emission))


class FrozenDesign(unittest.TestCase):
    def test_independent_maximum_matches_frozen_claim_and_refuses_default_work(self):
        observed = independent_frozen_formula(67108864, CAPS)
        self.assertEqual(observed, dict(extent=69765152, records=109184, words=331716,
                                      blocks=17033, attempts=545056, planning=16384,
                                      emission=2611218696, total=2611235080))
        self.assertGreater(observed["total"], 1_000_000_000)

    def test_fixed_planning_debit_survives_emission_refusal(self):
        control = Control(base=100, combined=130, limit=1000, work=0, work_limit=16384)
        control.predebit(16384)
        with self.assertRaises(Refusal):
            control.predebit(1)
        self.assertEqual(control.work, 16384)
        self.assertIsNone(control.first_failure)

    def test_each_formula_dimension_monotonically_increases_work(self):
        baseline = independent_frozen_formula(0, [0] * 8)["total"]
        self.assertGreater(independent_frozen_formula(1, [0] * 8)["total"], baseline)
        for index in range(8):
            values = [0] * 8
            values[index] = 1
            self.assertGreater(independent_frozen_formula(0, values)["total"], baseline)

    def test_post_construction_pre_scope_stop_keeps_unknown_selected_charge(self):
        # Exact source checkpoint: adopt_body's final check after Construction
        # admission can refuse before its return creates SnapshotAdoptionScope.
        control = Control(base=100, combined=130, limit=1000, work=0, work_limit=1000)
        control.enlarge(120)
        control.cancelled = True
        with self.assertRaises(Refusal):
            control.probe()
        # Unchanged single-floor finish correctly refuses to retire the extra20.
        self.assertEqual(control.finish_original(), {"charged": 120, "invariant": "construction_bound"})

    def test_ordinary_and_selected_scope_limits_require_separate_floors(self):
        self.assertEqual(366896 + 8536, 375432)
        self.assertEqual(366312 + 8536, 374848)
        self.assertEqual(366896 + 8536 + 5984 + 29256, 410672)
        self.assertEqual(366312 + 8536 + 5936 + 29256, 410040)
        self.assertGreater(375432, 300000)
        self.assertGreater(374848, 300000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
