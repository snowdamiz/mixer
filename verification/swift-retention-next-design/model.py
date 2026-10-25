#!/usr/bin/env python3
"""Authored finite policy model. No Mixer product code, VM or guest is loaded.

Timestamp ordinals preserve order, not original CacheWork distances. Entries are
unit sized except explicit controls. Plan tags model only exact body identity and
512-cell replacement; actual parsing, Counts, proof and decoder remain absent.
"""
from dataclasses import dataclass
import copy
import json

U64_MAX = (1 << 64) - 1
MODES = ("baseline-lru", "always-cold-insertion",
         "cold-insertion-mru-every-32nd-successful-miss", "plan-aware-cold-insertion")


class Rejected(Exception):
    pass


@dataclass
class Entry:
    stamp: int
    size: int
    pins: int
    slot: int


class Model:
    def __init__(self, capacity=64, byte_limit=1 << 30, mode="baseline-lru"):
        assert 0 <= capacity <= 64 and mode in MODES
        self.c, self.byte_limit, self.mode = capacity, byte_limit, mode
        self.resident = {}
        self.plans = [None] * 512
        self.clock = 0
        self.hits = self.misses = self.evictions = self.added = 0
        self.plan_hits = self.plan_collisions = self.scans = 0

    def invariant(self):
        assert len(self.resident) <= self.c
        assert len({e.slot for e in self.resident.values()}) == len(self.resident)
        assert all(0 <= e.slot < self.c and 0 <= e.stamp <= self.clock and e.pins >= 0
                   for e in self.resident.values())
        assert sum(e.size for e in self.resident.values()) <= self.byte_limit
        assert 0 <= self.clock <= U64_MAX
        assert all(tag is None or (tag[0] & 511) == i for i, tag in enumerate(self.plans))

    def request(self, key, size=1, identity=None, fail=None):
        """Only retention state; not the product's sticky work/statistics ledger.

        Complete scan publication precedes capacity/planning rejection, as in the
        baseline. This means plan and scans may change after a planning failure.
        """
        if self.clock == U64_MAX:
            raise Rejected("clock exhausted")
        now = self.clock + 1
        if key in self.resident:
            entry = self.resident[key]
            if not 0 <= entry.stamp <= self.clock:
                raise Rejected("future timestamp")
            if fail == "publication":
                raise Rejected("before hit publication")
            entry.stamp = now
            self.clock = now
            self.hits += 1
            self.invariant()
            return []
        tag = (key, identity if identity is not None else (key, size, 0))
        old = self.plans[key & 511]
        reused = old is not None and old[0] == key
        if reused and old != tag:
            raise Rejected("immutable plan identity")
        if reused:
            self.plan_hits += 1
        else:
            if old is not None:
                self.plan_collisions += 1
            if fail == "scan":
                raise Rejected("scan before plan publication")
            self.plans[key & 511] = tag
            self.scans += 1
        if not self.c or size > self.byte_limit:
            raise Rejected("capacity")
        if any(not 0 <= e.stamp <= self.clock for e in self.resident.values()):
            raise Rejected("future timestamp")
        shadow = copy.deepcopy(self.resident)
        destination = min(set(range(self.c)) - {e.slot for e in shadow.values()}, default=None)
        order = []
        while destination is None or sum(e.size for e in shadow.values()) + size > self.byte_limit:
            eligible = [(k, e) for k, e in shadow.items() if not e.pins]
            if not eligible:
                raise Rejected("all pinned")
            victim, entry = min(eligible, key=lambda item: (item[1].stamp, item[1].slot))
            destination = entry.slot
            del shadow[victim]
            order.append(victim)
        if fail == "plan":
            raise Rejected("before resident mutation")
        # Model commit each completed eviction. No whole-miss rollback is claimed.
        self.resident = shadow
        self.evictions += len(order)
        if fail == "build":
            raise Rejected("after eviction before admission")
        if fail == "publication":
            raise Rejected("before admission")
        cold = (self.mode == "always-cold-insertion" or
                (self.mode == "cold-insertion-mru-every-32nd-successful-miss" and (self.misses + 1) % 32 != 0) or
                (self.mode == "plan-aware-cold-insertion" and not reused))
        self.resident[key] = Entry(0 if cold else now, size, 0, destination)
        self.clock = now
        self.misses += 1
        self.added += 0 if self.mode == "baseline-lru" else 8
        self.invariant()
        return order


def traces():
    warm = [f for f in range(34, 50) for _ in range(2)]
    hot = [f for r in range(4) for f in list(range(100 + 128*r, 228 + 128*r)) + list(range(34, 50))]
    warm2 = [f for f in range(100, 116) for _ in range(2)]
    hot2 = [f for r in range(4) for f in list(range(200 + 128*r, 328 + 128*r)) + list(range(100, 116))]
    cases = {
        "hot16_scan128_four_rounds": (warm, hot),
        "cyclic65_three_rounds": ([], list(range(100, 165)) * 3),
        "expensive_hot_cheap_cold": (warm2, hot2),
        "cheap_hot_expensive_cold": (warm2, hot2),
        "uniform_hot_cold": (warm2, hot2),
        "expensive_old_to_cheap_cycle64_phase_shift": ([f for _ in range(3) for f in range(100, 116)], list(range(200, 264)) * 12),
        "resident_hit256": (list(range(34, 98)), list(range(34, 98)) * 4),
    }
    return {name: {"provenance": "synthetic finite sequence from sealed common-tests.rs; body work is not executed",
                   "warm": warm, "trace": trace} for name, (warm, trace) in cases.items()}


FIELDS = ("hits", "misses", "evictions", "added", "plan_hits", "plan_collisions", "scans")


def compare(warm, trace, capacity=64):
    results = {}
    for mode in MODES:
        model = Model(capacity, mode=mode)
        for key in warm:
            model.request(key)
        before = {f: getattr(model, f) for f in FIELDS}
        for key in trace:
            model.request(key)
        row = {f: getattr(model, f) - before[f] for f in FIELDS}
        row["final_residents"] = sorted(model.resident)
        row["final_zero_priority_residents"] = sum(e.stamp == 0 for e in model.resident.values())
        results[mode] = row
    baseline = results["baseline-lru"]["misses"]
    for row in results.values():
        row["avoided_decodes"] = baseline - row["misses"]
        row["policy_only_break_even_per_avoided_decode"] = row["added"] / row["avoided_decodes"] if row["avoided_decodes"] > 0 else None
    return results


def main():
    cases = {name: compare(case["warm"], case["trace"]) for name, case in traces().items()}
    warm = [f for f in range(100, 116) for _ in range(2)]
    adversarial = {
        "colliding_65_cycle": compare([], [100 + 512*i for i in range(65)] * 3),
        "cold_phase64_after_64_hot": compare(list(range(64)) * 3, list(range(100, 164)) * 12),
        "cold_phase64_after_16_hot_long": compare(warm, list(range(200, 264)) * 64),
        "scan640_then_hot": compare(warm, list(range(200, 840)) + list(range(100, 116))),
        "reused64_collide_then_phase": compare(list(range(64)) * 3, list(range(512, 576)) * 12),
        "hotset64_followed_by_once_only64": compare(list(range(64)) * 2, list(range(100, 164))),
    }
    print(json.dumps({"scope": "Finite independently authored Python policy model; no VM, Counts, byte decoding, actual CacheWork, CPU time or native/full target",
                      "traces": cases, "adversarial_synthetic": adversarial}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
