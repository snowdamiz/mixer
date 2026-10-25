#!/usr/bin/env python3
"""Finite reference/invariant/evidence checks; imports only this lane's model."""
import copy
import hashlib
import json
from pathlib import Path
import random
import unittest

from model import Model, MODES, Rejected, U64_MAX, compare, traces

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def load(path):
    return json.loads((ROOT / path).read_bytes())


def snapshot(model):
    return copy.deepcopy(model.resident)


def reference(mode, capacity, requests):
    """Separate sorted-list model; it has no production/model Entry or eviction loop."""
    rows, tags = [], {}
    misses = hits = 0
    for ordinal, key in enumerate(requests, 1):
        found = next((r for r in rows if r[0] == key), None)
        if found is not None:
            found[1] = ordinal
            hits += 1
            continue
        reused = tags.get(key & 511) == key
        tags[key & 511] = key
        free = sorted(set(range(capacity)) - {r[2] for r in rows})
        if free:
            slot = free[0]
        else:
            rows.sort(key=lambda r: (r[1], r[2]))
            slot = rows.pop(0)[2]
        misses += 1
        cold = mode == "always-cold-insertion" or (mode == MODES[2] and misses % 32) or (mode == MODES[3] and not reused)
        rows.append([key, 0 if cold else ordinal, slot])
    return hits, misses, sorted((r[0], r[1], r[2]) for r in rows)


class PolicyTests(unittest.TestCase):
    def test_all_65_capacities_and_four_policies(self):
        for capacity in range(65):
            for mode in MODES:
                model = Model(capacity, mode=mode)
                if not capacity:
                    with self.assertRaisesRegex(Rejected, "capacity"):
                        model.request(0)
                else:
                    for n in range(4 * capacity + 3):
                        model.request(n % (capacity + 1))
                        model.invariant()

    def test_independent_sorted_reference_48_cases(self):
        randomizer = random.Random(0x4d49584552)
        for capacity in (1, 2, 3, 7, 16, 64):
            for mode in MODES:
                for collision in (False, True):
                    keys = [randomizer.randrange(capacity + 5) * (512 if collision else 1) for _ in range(180)]
                    model = Model(capacity, mode=mode)
                    for key in keys:
                        model.request(key)
                    hits, misses, residents = reference(mode, capacity, keys)
                    self.assertEqual((model.hits, model.misses), (hits, misses))
                    self.assertEqual(sorted((k, e.stamp, e.slot) for k, e in model.resident.items()), residents)

    def test_original_baseline_counts_match_two_sealed_evidence_packets(self):
        adaptive = load("verification/swift-adaptive-retention-design/stdout.json")["traces"]
        engine = {r["case"]: r["baseline"] for r in load("verification/swift-cost-retention-candidate/result-summary.json")["traces"]}
        for name, case in traces().items():
            row = compare(case["warm"], case["trace"])["baseline-lru"]
            old = adaptive[name]["lru_model"]
            self.assertEqual((row["hits"], row["misses"], row["evictions"]), (old["hits"], old["decodes"], old["evictions"]))
            if name in engine:
                warm = Model()
                for key in case["warm"]:
                    warm.request(key)
                self.assertEqual(row["misses"] + warm.misses, engine[name]["decodes"])
                self.assertEqual(row["hits"] + warm.hits, engine[name]["hits"])

    def test_primary_saved_results_remain_exact_first_frozen_run(self):
        output = json.loads((HERE / "model-attempt-1/stdout").read_bytes())
        for name, case in traces().items():
            self.assertEqual(compare(case["warm"], case["trace"]), output["traces"][name])

    def test_resident_hit256_no_added_policy_credit(self):
        row = compare(list(range(64)), list(range(64)) * 4)[MODES[3]]
        self.assertEqual((row["misses"], row["hits"], row["added"]), (0, 256, 0))

    def test_all_successful_primary_misses_charge_complete_eight(self):
        for case in traces().values():
            row = compare(case["warm"], case["trace"])[MODES[3]]
            self.assertEqual(row["added"], 8 * row["misses"])

    def test_warmup_excluded_equally(self):
        case = traces()["expensive_hot_cheap_cold"]
        row = compare(case["warm"], case["trace"])[MODES[3]]
        self.assertEqual((row["misses"], row["hits"]), (512, 64))
        self.assertEqual(len(case["trace"]), 576)

    def test_phase_regression_is_retained_not_hidden(self):
        case = traces()["expensive_old_to_cheap_cycle64_phase_shift"]
        result = compare(case["warm"], case["trace"])
        self.assertEqual(result[MODES[0]]["misses"], 64)
        self.assertEqual(result[MODES[3]]["misses"], 81)
        self.assertEqual(result[MODES[3]]["avoided_decodes"], -17)

    def test_full_old_set_phase_regression_and_eventual_turnover(self):
        result = compare(list(range(64)) * 3, list(range(100, 164)) * 12)
        self.assertEqual(result[MODES[3]]["misses"], 128)
        self.assertEqual(result[MODES[3]]["final_residents"], list(range(100, 164)))
        self.assertEqual(result[MODES[1]]["misses"], 768)

    def test_exact_plan_collision_is_not_false_reuse(self):
        model = Model(2, mode=MODES[3])
        for key in (0, 512, 1024):
            model.request(key)
        self.assertEqual(model.plan_hits, 0)
        self.assertEqual(model.plan_collisions, 2)
        self.assertEqual(model.plans[0][0], 1024)
        self.assertTrue(all(e.stamp == 0 for e in model.resident.values()))

    def test_same_key_wrong_immutable_identity_fails_closed(self):
        model = Model(1, mode=MODES[3])
        model.request(10, identity=(1, 2, 3))
        model.request(11)
        before = copy.deepcopy(model.__dict__)
        with self.assertRaisesRegex(Rejected, "immutable plan identity"):
            model.request(10, identity=(1, 2, 4))
        self.assertEqual(model.__dict__, before)

    def test_same_key_valid_plan_gets_normal_priority(self):
        model = Model(1, mode=MODES[3])
        for key in (10, 11, 10):
            model.request(key)
        self.assertEqual(model.plan_hits, 1)
        self.assertGreater(model.resident[10].stamp, 0)

    def test_first_hit_promotes_without_new_state(self):
        model = Model(2, mode=MODES[3])
        model.request(10)
        model.request(11)
        self.assertEqual(model.resident[10].stamp, 0)
        added = model.added
        model.request(10)
        self.assertGreater(model.resident[10].stamp, 0)
        self.assertEqual(model.added, added)
        self.assertEqual(model.request(12), [11])

    def test_equal_stamp_uses_lower_slot_not_key(self):
        model = Model(3, mode=MODES[3])
        for key in (9, 8, 7):
            model.request(key)
        self.assertEqual(model.request(6), [9])

    def test_pin_and_variable_size_three_victims(self):
        model = Model(4, byte_limit=8, mode=MODES[3])
        for key in range(4):
            model.request(key, size=2)
        model.resident[0].pins = 1
        before = copy.deepcopy(model.resident[0])
        self.assertEqual(model.request(4, size=6), [1, 2, 3])
        self.assertEqual(model.resident[0], before)
        model.invariant()

    def test_all_pinned_preserves_residents_after_baseline_scan(self):
        model = Model(3, mode=MODES[3])
        for key in range(3):
            model.request(key)
            model.resident[key].pins = 1
        before = snapshot(model)
        with self.assertRaisesRegex(Rejected, "all pinned"):
            model.request(4)
        self.assertEqual(model.resident, before)
        self.assertEqual(model.plans[4][0], 4)

    def test_plan_failure_preserves_residents_but_not_successful_scan(self):
        model = Model(2, mode=MODES[3])
        model.request(0)
        model.request(1)
        before = snapshot(model)
        with self.assertRaisesRegex(Rejected, "before resident mutation"):
            model.request(2, fail="plan")
        self.assertEqual(model.resident, before)
        self.assertEqual(model.plans[2][0], 2)

    def test_build_failure_retains_exact_committed_evictions(self):
        model = Model(2, mode=MODES[3])
        model.request(0)
        model.request(1)
        with self.assertRaisesRegex(Rejected, "after eviction"):
            model.request(2, fail="build")
        self.assertEqual(set(model.resident), {1})
        self.assertEqual(model.evictions, 1)
        self.assertEqual(model.misses, 2)
        model.invariant()

    def test_count_plan_is_prior_scan_not_prior_completed_build(self):
        model = Model(1, mode=MODES[3])
        model.request(0)
        with self.assertRaises(Rejected):
            model.request(1, fail="build")
        self.assertNotIn(1, model.resident)
        model.request(1)
        self.assertGreater(model.resident[1].stamp, 0)
        self.assertEqual(model.plan_hits, 1)

    def test_failed_scan_cannot_publish_plan(self):
        model = Model(1, mode=MODES[3])
        with self.assertRaisesRegex(Rejected, "scan before plan publication"):
            model.request(0, fail="scan")
        self.assertIsNone(model.plans[0])
        self.assertEqual(model.resident, {})

    def test_future_stamp_rejection_has_no_resident_mutation(self):
        model = Model(1, mode=MODES[3])
        model.request(0)
        model.resident[0].stamp = model.clock + 1
        before = snapshot(model)
        with self.assertRaisesRegex(Rejected, "future timestamp"):
            model.request(0)
        self.assertEqual(model.resident, before)

    def test_finite_clock_boundary_is_not_a_work_budget_claim(self):
        model = Model(1, mode=MODES[3])
        model.clock = U64_MAX - 1
        model.request(0)
        self.assertEqual(model.clock, U64_MAX)
        before = copy.deepcopy(model.__dict__)
        with self.assertRaisesRegex(Rejected, "clock exhausted"):
            model.request(0)
        self.assertEqual(model.__dict__, before)

    def test_selected_prior_packet_member_hashes(self):
        cost = load("verification/swift-cost-retention-candidate/seal.json")
        for name in ("common-tests.rs", "result-summary.json", "commands/baseline-final-swift/stdout", "commands/candidate-expanded-2/stdout"):
            payload = (ROOT / "verification/swift-cost-retention-candidate" / name).read_bytes()
            self.assertEqual(hashlib.sha256(payload).hexdigest(), cost["members"][name]["sha256"])
            self.assertEqual(len(payload), cost["members"][name]["bytes"])
        adaptive = load("verification/swift-adaptive-retention-design/seal.json")
        for member in adaptive["members"]:
            payload = (ROOT / member["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(payload).hexdigest(), member["sha256"])
            self.assertEqual(len(payload), member["bytes"])
        for name in ("target-once-events.json", "target-once-telemetry.json", "result-summary.json"):
            seal = load("verification/swift-current-attribution-runtime/result-seal.json")
            payload = (ROOT / "verification/swift-current-attribution-runtime" / name).read_bytes()
            self.assertEqual(hashlib.sha256(payload).hexdigest(), seal["files"][name])
        runtime = load("verification/swift-retention-runtime/seal.json")
        selected = {"verification/swift-retention-runtime/result-summary.json", "verification/swift-retention-runtime/target-once-events.json", "verification/swift-retention-runtime/target-once-result.json"}
        for member in runtime["files"]:
            if member["path"] in selected:
                self.assertEqual(hashlib.sha256((ROOT / member["path"]).read_bytes()).hexdigest(), member["sha256"])

    def test_retained_engine_work_comparison_is_not_model_work(self):
        raw = (ROOT / "verification/swift-cost-retention-candidate/commands/baseline-final-swift/stdout").read_text()
        producer = (ROOT / "verification/swift-cost-retention-candidate/commands/candidate-expanded-2/stdout").read_text()
        def rows(text):
            return {row["case"]: row for line in text.splitlines() if "COST_TRACE {" in line
                    for row in [json.loads(line[line.index("COST_TRACE ") + 11:]) ]}
        baseline, candidate = rows(raw), rows(producer)
        self.assertEqual(len(baseline), 6)
        self.assertEqual(set(baseline), set(candidate))
        for name in baseline:
            self.assertEqual(baseline[name]["instructions"], 0)
            self.assertGreater(candidate[name]["traceWork"], baseline[name]["traceWork"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
