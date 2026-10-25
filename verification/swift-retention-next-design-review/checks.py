#!/usr/bin/env python3
"""Independent finite result review. Imports only the sealed new Python model.

The oracle uses a fixed slot array and one sorted eviction order, rather than
the producer's dictionary/shadow/iterated-victim algorithm. It is not a VM.
"""
import copy
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "verification/swift-retention-next-design"
EXPECTED_SEAL = "9fb43c9111e0b4bf5f340358983f404087a5980e7da27c9c3e40483b1649ae57"
spec = importlib.util.spec_from_file_location("reviewed_retention_model", PACKET / "model.py")
producer = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = producer
spec.loader.exec_module(producer)
MODES = producer.MODES
COUNTS = {"oracle_requests": 0, "oracle_cases": 0, "sealed_members": 0}


def read(path):
    return json.loads((ROOT / path).read_bytes())


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def independent_sequences():
    original_warm = list(itertools.chain.from_iterable((n, n) for n in range(34, 50)))
    original = []
    mixed_warm = list(itertools.chain.from_iterable((n, n) for n in range(100, 116)))
    mixed = []
    for round_number in range(4):
        original.extend(range(100 + 128 * round_number, 228 + 128 * round_number))
        original.extend(range(34, 50))
        mixed.extend(range(200 + 128 * round_number, 328 + 128 * round_number))
        mixed.extend(range(100, 116))
    return {
        "hot16_scan128_four_rounds": (original_warm, original),
        "cyclic65_three_rounds": ([], list(range(100, 165)) * 3),
        "expensive_hot_cheap_cold": (mixed_warm, mixed),
        "cheap_hot_expensive_cold": (mixed_warm, mixed),
        "uniform_hot_cold": (mixed_warm, mixed),
        "expensive_old_to_cheap_cycle64_phase_shift": (list(range(100, 116)) * 3, list(range(200, 264)) * 12),
        "resident_hit256": (list(range(34, 98)), list(range(34, 98)) * 4),
    }


class OracleReject(Exception):
    pass


class SlotOracle:
    def __init__(self, capacity, mode, byte_limit=1 << 30):
        self.slots = [None] * capacity  # [key, priority, bytes, pins]
        self.tags = [None] * 512
        self.mode, self.limit = mode, byte_limit
        self.clock = self.hits = self.misses = self.evictions = self.added = 0
        self.plan_hits = self.plan_collisions = self.scans = 0

    def resident(self):
        return {row[0]: (row[1], row[2], row[3], index)
                for index, row in enumerate(self.slots) if row is not None}

    def request(self, key, size=1, identity=None, fail=None):
        if self.clock >= (1 << 64) - 1:
            raise OracleReject("clock exhausted")
        for index, row in enumerate(self.slots):
            if row is not None and row[0] == key:
                if not 0 <= row[1] <= self.clock:
                    raise OracleReject("future timestamp")
                if fail == "publication":
                    raise OracleReject("before hit publication")
                self.clock += 1
                row[1] = self.clock
                self.hits += 1
                return []
        tag = (key, (key, size, 0) if identity is None else identity)
        cell = key % 512
        previous = self.tags[cell]
        reused = previous is not None and previous[0] == key
        if reused:
            if previous != tag:
                raise OracleReject("immutable plan identity")
            self.plan_hits += 1
        else:
            self.plan_collisions += previous is not None
            if fail == "scan":
                raise OracleReject("scan before plan publication")
            self.tags[cell] = tag
            self.scans += 1
        if not self.slots or size > self.limit:
            raise OracleReject("capacity")
        if any(row is not None and not 0 <= row[1] <= self.clock for row in self.slots):
            raise OracleReject("future timestamp")
        vacancies = [index for index, row in enumerate(self.slots) if row is None]
        destination = vacancies[0] if vacancies else None
        needed = sum(row[2] for row in self.slots if row is not None) + size - self.limit
        eligible = sorted((row[1], index, row[0], row[2])
                          for index, row in enumerate(self.slots) if row is not None and row[3] == 0)
        victims = []
        for _, index, victim_key, victim_size in eligible:
            if destination is not None and needed <= 0:
                break
            victims.append((index, victim_key))
            destination = index
            needed -= victim_size
        if destination is None or needed > 0:
            raise OracleReject("all pinned")
        if fail == "plan":
            raise OracleReject("before resident mutation")
        for index, _ in victims:
            self.slots[index] = None
        self.evictions += len(victims)
        if fail in ("build", "publication"):
            raise OracleReject("after eviction before admission" if fail == "build" else "before admission")
        self.clock += 1
        self.misses += 1
        priority = self.clock
        if self.mode == MODES[1] or (self.mode == MODES[2] and self.misses % 32 != 0) or (self.mode == MODES[3] and not reused):
            priority = 0
        self.slots[destination] = [key, priority, size, 0]
        self.added += 0 if self.mode == MODES[0] else 8
        return [key for _, key in victims]


class Review(unittest.TestCase):
    def assert_same(self, model, oracle):
        self.assertEqual({key: (entry.stamp, entry.size, entry.pins, entry.slot)
                          for key, entry in model.resident.items()}, oracle.resident())
        self.assertEqual(model.plans, oracle.tags)
        for field in ("clock", "hits", "misses", "evictions", "added", "plan_hits", "plan_collisions", "scans"):
            self.assertEqual(getattr(model, field), getattr(oracle, field), field)
        model.invariant()

    def step(self, model, oracle, *args, **kwargs):
        outcomes = []
        for cache, rejection in ((model, producer.Rejected), (oracle, OracleReject)):
            try:
                outcomes.append(("ok", cache.request(*args, **kwargs)))
            except rejection as error:
                outcomes.append(("rejected", str(error)))
        self.assertEqual(outcomes[0], outcomes[1])
        self.assert_same(model, oracle)
        COUNTS["oracle_requests"] += 1

    def test_01_seal_and_every_owned_member(self):
        self.assertEqual(digest((PACKET / "seal.json").read_bytes()), EXPECTED_SEAL)
        self.assertEqual((PACKET / "seal.sha256").read_text(), EXPECTED_SEAL + "\n")
        seal = read("verification/swift-retention-next-design/seal.json")
        for member in seal["members"]:
            payload = (ROOT / member["path"]).read_bytes()
            self.assertEqual((len(payload), digest(payload)), (member["bytes"], member["sha256"]))
            COUNTS["sealed_members"] += 1

    def test_02_exact_132_live_source_members(self):
        expected = read("verification/swift-cost-retention-candidate/live-baseline-source-manifest.json")
        actual = {name: digest((ROOT / "vm" / name).read_bytes()) for name in expected}
        self.assertEqual(len(expected), 132)
        self.assertEqual(actual, expected)
        canonical = (json.dumps(actual, indent=2, sort_keys=True) + "\n").encode()
        self.assertEqual(digest(canonical), "16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd")

    def test_03_hand_reconstructed_trace_bytes_and_all_four_frozen_results(self):
        frozen = read("verification/swift-retention-next-design/model-attempt-1/stdout")
        serialized = read("verification/swift-retention-next-design/synthetic-traces.json")
        for name, (warm, interval) in independent_sequences().items():
            self.assertEqual((serialized[name]["warm"], serialized[name]["trace"]), (warm, interval))
            for mode in MODES:
                model, oracle = producer.Model(mode=mode), SlotOracle(64, mode)
                for key in warm:
                    self.step(model, oracle, key)
                before = {field: getattr(oracle, field) for field in producer.FIELDS}
                for key in interval:
                    self.step(model, oracle, key)
                row = frozen["traces"][name][mode]
                self.assertEqual({field: getattr(oracle, field) - before[field] for field in producer.FIELDS},
                                 {field: row[field] for field in producer.FIELDS})
                self.assertEqual(sorted(oracle.resident()), row["final_residents"])
                self.assertEqual(sum(value[0] == 0 for value in oracle.resident().values()), row["final_zero_priority_residents"])
                COUNTS["oracle_cases"] += 1

    def test_04_every_positive_capacity_collision_and_random_variable_sizes(self):
        rng = random.Random(0x726576696577)
        for capacity in range(1, 65):
            for mode in MODES:
                model = producer.Model(capacity, byte_limit=capacity * 2, mode=mode)
                oracle = SlotOracle(capacity, mode, byte_limit=capacity * 2)
                sizes = {key: 1 + rng.randrange(4) for key in range(capacity + 5)}
                for _ in range(100):
                    for key, entry in model.resident.items():
                        pins = rng.randrange(3) if rng.randrange(5) == 0 else 0
                        entry.pins = pins
                        oracle.slots[entry.slot][3] = pins
                    key = rng.randrange(capacity + 5)
                    self.step(model, oracle, key * 512, size=sizes[key])
                COUNTS["oracle_cases"] += 1

    def test_05_zero_capacity_publishes_complete_scan_then_rejects(self):
        for mode in MODES:
            model, oracle = producer.Model(0, mode=mode), SlotOracle(0, mode)
            self.step(model, oracle, 7)
            self.assertEqual(model.plans[7], (7, (7, 1, 0)))

    def test_06_original_observation_survives_later_cell_replacement(self):
        model, oracle = producer.Model(1, mode=MODES[3]), SlotOracle(1, MODES[3])
        for key in (0, 1, 0):
            self.step(model, oracle, key)
        self.assertGreater(model.resident[0].stamp, 0)
        self.step(model, oracle, 512)
        self.assertEqual(model.plans[0][0], 512)
        self.assertEqual(model.resident[512].stamp, 0)
        self.step(model, oracle, 0)
        self.assertEqual(model.plans[0][0], 0)
        self.assertEqual(model.resident[0].stamp, 0)  # not reconstructed as reused after scan

    def test_07_each_immutable_identity_component_rejects_before_replacement(self):
        for changed in ((2, 20, 3), (1, 21, 3), (1, 20, 4)):
            model = producer.Model(1, mode=MODES[3])
            model.request(5, identity=(1, 20, 3))
            model.request(6)
            before = copy.deepcopy(model.__dict__)
            with self.assertRaisesRegex(producer.Rejected, "immutable plan identity"):
                model.request(5, identity=changed)
            self.assertEqual(before, model.__dict__)

    def test_08_collision_replaces_stale_identity_but_never_claims_reuse(self):
        model, oracle = producer.Model(1, mode=MODES[3]), SlotOracle(1, MODES[3])
        self.step(model, oracle, 0, identity=(1, 2, 3))
        self.step(model, oracle, 512, identity=(8, 9, 10))
        self.step(model, oracle, 0, identity=(11, 12, 13))
        self.assertEqual(model.plan_hits, 0)
        self.assertEqual(model.resident[0].stamp, 0)

    def test_09_pin_held_through_multiple_evictions_then_release(self):
        model, oracle = producer.Model(4, byte_limit=8, mode=MODES[3]), SlotOracle(4, MODES[3], 8)
        for key in range(4):
            self.step(model, oracle, key, size=2)
        held = model.resident[0]
        held.pins = oracle.slots[held.slot][3] = 2
        self.step(model, oracle, 4, size=6)
        self.assertEqual(model.resident[0].pins, 2)
        self.assertEqual(model.resident[4].slot, 3)
        model.resident[0].pins = oracle.slots[0][3] = 0
        self.step(model, oracle, 5, size=8)
        self.assertEqual(set(model.resident), {5})

    def test_10_failed_scan_and_plan_preserve_required_boundaries(self):
        for failure in ("scan", "plan"):
            model, oracle = producer.Model(2, mode=MODES[3]), SlotOracle(2, MODES[3])
            for key in (0, 1):
                self.step(model, oracle, key)
            before = copy.deepcopy(model.resident)
            self.step(model, oracle, 512, fail=failure)
            self.assertEqual(model.resident, before)
            self.assertEqual(model.plans[0][0], 0 if failure == "scan" else 512)

    def test_11_partial_build_and_publication_failure_keep_evictions_and_scan(self):
        for failure in ("build", "publication"):
            model, oracle = producer.Model(4, byte_limit=8, mode=MODES[3]), SlotOracle(4, MODES[3], 8)
            for key in range(4):
                self.step(model, oracle, key, size=2)
            model.resident[0].pins = oracle.slots[0][3] = 1
            self.step(model, oracle, 4, size=6, fail=failure)
            self.assertEqual(set(model.resident), {0})
            self.assertEqual((model.misses, model.evictions, model.plans[4][0]), (4, 3, 4))
            self.step(model, oracle, 4, size=6)
            self.assertGreater(model.resident[4].stamp, 0)

    def test_12_future_timestamp_and_ordinal_limit_are_finite_controls(self):
        model = producer.Model(2, mode=MODES[3])
        model.request(0)
        model.resident[0].stamp = model.clock + 1
        before = copy.deepcopy(model.resident)
        with self.assertRaisesRegex(producer.Rejected, "future timestamp"):
            model.request(1)
        self.assertEqual(model.resident, before)
        self.assertEqual(model.plans[1][0], 1)  # successful scan may precede later rejection
        model.clock = (1 << 64) - 1
        before_all = copy.deepcopy(model.__dict__)
        with self.assertRaisesRegex(producer.Rejected, "clock exhausted"):
            model.request(0)
        self.assertEqual(model.__dict__, before_all)

    def test_13_exact_phase_and_collision_regressions(self):
        cases = [
            (list(range(100, 116)) * 3, list(range(200, 264)) * 12, 64, 81),
            (list(range(64)) * 3, list(range(100, 164)) * 12, 64, 128),
            (list(range(64)) * 3, list(range(512, 576)) * 12, 64, 128),
            ([], [100 + 512 * n for n in range(65)] * 3, 195, 69),
        ]
        for warm, interval, baseline_misses, candidate_misses in cases:
            for mode, expected in ((MODES[0], baseline_misses), (MODES[3], candidate_misses)):
                model, oracle = producer.Model(mode=mode), SlotOracle(64, mode)
                for key in warm:
                    self.step(model, oracle, key)
                before = oracle.misses
                for key in interval:
                    self.step(model, oracle, key)
                self.assertEqual(oracle.misses - before, expected)
                COUNTS["oracle_cases"] += 1

    def test_14_historical_six_body_work_rows_are_different_evidence(self):
        summary = read("verification/swift-cost-retention-candidate/result-summary.json")
        raw = {}
        for kind, relative in (("baseline", "baseline-final-swift"), ("candidate", "candidate-expanded-2")):
            payload = (ROOT / f"verification/swift-cost-retention-candidate/commands/{relative}/stdout").read_text()
            raw[kind] = {row["case"]: row for line in payload.splitlines() if "COST_TRACE {" in line
                         for row in [json.loads(line.split("COST_TRACE ", 1)[1])]}
        self.assertEqual(len(summary["traces"]), 6)
        for row in summary["traces"]:
            for kind in ("baseline", "candidate"):
                self.assertEqual(row[kind], raw[kind][row["case"]])
            self.assertGreater(row["candidate"]["traceWork"], row["baseline"]["traceWork"])
        for name in ("expensive_hot_cheap_cold", "cheap_hot_expensive_cold", "uniform_hot_cold", "hot16_scan128_four_rounds"):
            self.assertEqual(raw["baseline"][name]["decodes"], 592)

    def test_15_work_estimates_are_only_arithmetic_not_vm_work(self):
        comparison = read("verification/swift-retention-next-design/comparison.json")
        for row in comparison["finite_interval_comparison"]:
            self.assertEqual(row["candidate_added_policy_estimate"], row["candidate_interval_decodes"] * 8)
        sensitivity = comparison["original_failure_sensitivity_not_prediction"]
        self.assertEqual(sensitivity["adaptive_four_credit_hit_tax"], 537576 * 4)
        self.assertEqual(sensitivity["candidate_eight_credit_tax_if_baseline_miss_count_unchanged"], 61628 * 8)
        self.assertEqual(sensitivity["candidate_tax_fraction_of_fixed_budget_if_baseline_misses_unchanged"]["decimal"], 493024 / 64000000)
        self.assertIn("hypothetical baseline miss", (ROOT / "docs/swift-retention-next-design.md").read_text())

    def test_16_memory_formula_is_prospective_and_cannot_zero_unknowns(self):
        memory = read("verification/swift-retention-next-design/comparison.json")["memory_contract"]
        self.assertEqual(memory["prospective_full_inventory_formula"], "3 * align8(3*32 + 3*R + 2*8 + 3*8 + 4*1 + 4*8) + DeltaExisting")
        self.assertIn("unmeasured", memory["R"])
        self.assertIn("cannot be zero-assumed", memory["DeltaExisting"])
        for hypothetical_result_size in (32, 40, 64, 128):
            body = 3 * 32 + 3 * hypothetical_result_size + 2 * 8 + 3 * 8 + 4 + 4 * 8
            self.assertGreaterEqual(3 * ((body + 7) // 8 * 8), 3 * body)
        # Python dict/Entry/tag/result objects and allocator capacity do not appear
        # in that Rust proposal formula; no physical-memory validation is made.

    def test_17_metadata_drift_is_historical_and_not_vm_drift(self):
        model_command = read("verification/swift-retention-next-design/model-attempt-1/command.json")
        change = read("verification/swift-retention-next-design/metadata-context-change.json")
        self.assertFalse(change["policy_retuned"])
        self.assertFalse(change["model_or_test_rerun_for_metadata_change"])
        for kind in ("model", "tests"):
            inputs = read(f"verification/swift-retention-next-design/{kind}-attempt-1/inputs.json")
            historical = next(item for item in inputs if item["path"] == "PLAN.md")
            self.assertEqual(historical["sha256"], change["changes"]["PLAN.md"]["historical_sha256"])
        self.assertEqual(model_command["source_closure"]["digest"], "16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd")
        failure = read("verification/swift-retention-next-design/seal-preflight-attempt-1/receipt.json")
        self.assertEqual(failure["exit_code"], 1)
        self.assertFalse(failure["retention_policy_or_model_changed"])

    def test_18_original_telemetry_is_aggregate_and_failure_unchanged(self):
        summary = read("verification/swift-current-attribution-runtime/result-summary.json")
        self.assertEqual((summary["instructions"], summary["cacheWorkUsed"], summary["repeatedDecodes"], summary["repeatedBuildCredits"]),
                         (23358291, 64000000, 61142, 34500496))
        self.assertFalse(summary["corpus1Passed"])
        telemetry = read("verification/swift-current-attribution-runtime/target-once-telemetry.json")
        self.assertEqual(len(telemetry["snapshots"]), 5)
        self.assertTrue(all(isinstance(row["payload"]["calls"], list) for row in telemetry["snapshots"]))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Review)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"scope": "Independent finite Python review; no product, compiler, VM, guest or target execution", "counts": COUNTS,
                      "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors)}, sort_keys=True))
    raise SystemExit(0 if result.wasSuccessful() else 1)
