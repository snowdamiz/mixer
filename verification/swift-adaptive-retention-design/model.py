#!/usr/bin/env python3
"""Finite policy specification model; never loads or executes the Mixer VM.

Python objects are not the proposed Rust representation or reservation evidence.
No timings or CacheWork totals are inferred from this model.
"""
import copy
import json
from pathlib import Path

U64_MAX = (1 << 64) - 1


class Rejected(Exception):
    pass


class Policy:
    def __init__(self, capacity=64, byte_limit=1 << 30, adaptive=True):
        self.c = capacity
        self.byte_limit = byte_limit
        self.adaptive = adaptive
        self.resident = {}  # key -> [recency, repeated, bytes, pin count, slot]
        self.ghost = [None] * capacity  # eviction history, not a Python cache
        self.hand = 0
        self.p = 0
        self.clock = 0
        self.hits = self.misses = self.evictions = self.feedback = 0
        self.hit_policy_work = self.miss_policy_work = 0

    def ghost_lookup_cost(self, key):
        # Authored schedule estimate, assuming a valid complete hash chain.
        bucket = ((key * 0x9e3779b9) & 0xffffffff) >> 25
        return 2 + 4 * sum(g is not None and (((g[0] * 0x9e3779b9) & 0xffffffff) >> 25) == bucket for g in self.ghost)

    def invariant(self):
        assert 0 <= self.p <= self.c <= 64
        assert len(self.resident) <= self.c
        assert len({r[4] for r in self.resident.values()}) == len(self.resident)
        assert all(0 <= r[4] < self.c for r in self.resident.values())
        assert sum(x[2] for x in self.resident.values()) <= self.byte_limit
        assert self.hand == 0 if self.c == 0 else 0 <= self.hand < self.c
        keys = [g[0] for g in self.ghost if g is not None]
        assert len(keys) == len(set(keys)) <= self.c
        assert not set(keys) & self.resident.keys()
        assert all(0 <= r[0] <= self.clock <= U64_MAX for r in self.resident.values())

    def request(self, key, size=1, fail=None):
        """fail=plan is before resident mutation; fail=build follows evictions.

        In the product, existing work/statistics failure observations are sticky;
        this model isolates retention and ownership, excluding those counters.
        """
        before = copy.deepcopy(self)
        if self.clock == U64_MAX:
            raise Rejected("checked clock exhaustion")
        now = self.clock + 1
        if key in self.resident:
            r = self.resident[key]
            if r[0] > self.clock:
                raise Rejected("future recency")
            if fail == "plan":
                raise Rejected("before hit publication")
            r[0], r[1] = now, self.adaptive or r[1]
            self.clock = now
            self.hits += 1
            self.hit_policy_work += 4 if self.adaptive else 0
            self.invariant()
            return []
        if not self.c or size > self.byte_limit:
            raise Rejected("capacity")
        shadow = copy.deepcopy(self)
        hits = [(i, g) for i, g in enumerate(shadow.ghost) if g and g[0] == key]
        assert len(hits) <= 1
        feedback = hits[0][1][1] if hits and self.adaptive else None
        b1 = sum(g is not None and not g[1] for g in shadow.ghost)
        b2 = sum(g is not None and g[1] for g in shadow.ghost)
        target = self.p
        estimated = 60 + 16 + len(self.resident) + shadow.ghost_lookup_cost(key)
        if feedback is False:
            target = min(self.c, target + max(1, b2 // b1))
        elif feedback is True:
            target = max(0, target - max(1, b1 // b2))
        order = []
        target_slot = min(set(range(self.c)) - {r[4] for r in self.resident.values()}, default=None)
        if any(r[0] > self.clock for r in shadow.resident.values()):
            raise Rejected("future recency")
        while len(shadow.resident) >= self.c or sum(r[2] for r in shadow.resident.values()) + size > self.byte_limit:
            recent = sum(not r[1] for r in shadow.resident.values())
            prefer_recent = recent > target or (feedback is True and recent == target and recent > 0)
            eligible = [(k, r) for k, r in shadow.resident.items() if r[3] == 0]
            if not eligible:
                raise Rejected("all entries pinned")
            preferred = [(k, r) for k, r in eligible if not self.adaptive or (not r[1]) == prefer_recent]
            estimated += 4 + self.c * (1 if preferred else 3)
            k, r = min(preferred or eligible, key=lambda item: (item[1][0], item[1][4]))
            order.append(k)
            target_slot = r[4]
            del shadow.resident[k]
            if self.adaptive:
                old = shadow.ghost[shadow.hand]
                estimated += 8 + 10 + 2
                if old is not None:
                    estimated += shadow.ghost_lookup_cost(old[0]) + 2
                    shadow.ghost[shadow.hand] = None
                estimated += shadow.ghost_lookup_cost(k)
                shadow.ghost[shadow.hand] = (k, r[1])
                shadow.hand = 0 if shadow.hand + 1 == self.c else shadow.hand + 1
        if fail == "plan":
            assert self.__dict__ == before.__dict__
            raise Rejected("before eviction mutation")
        # Commit actual evictions; p and the attempted incoming classification wait.
        self.resident, self.ghost, self.hand = shadow.resident, shadow.ghost, shadow.hand
        self.evictions += len(order)
        self.invariant()
        if fail == "build":
            raise Rejected("after committed evictions, before admission")
        estimated += 4 + 6 + self.ghost_lookup_cost(key)
        self.ghost = [None if g and g[0] == key else g for g in self.ghost]
        self.p = target
        self.feedback += int(feedback is not None)
        self.resident[key] = [now, feedback is not None, size, 0, target_slot]
        self.clock = now
        self.misses += 1
        self.miss_policy_work += estimated if self.adaptive else 0
        self.invariant()
        return order


def run_trace(warm, trace):
    result = {}
    for label, adaptive in [("lru_model", False), ("adaptive_model", True)]:
        p = Policy(adaptive=adaptive)
        for f in warm:
            p.request(f)
        before = (p.hits, p.misses, p.evictions, p.feedback, p.hit_policy_work, p.miss_policy_work)
        for f in trace:
            p.request(f)
        result[label] = dict(zip(("hits", "decodes", "evictions", "ghost_feedback_events", "estimated_added_hit_policy_credits", "estimated_added_miss_policy_credits"),
                                [n - b for n, b in zip((p.hits, p.misses, p.evictions, p.feedback, p.hit_policy_work, p.miss_policy_work), before)]))
        result[label]["final_recent_target"] = p.p
    avoided = result["lru_model"]["decodes"] - result["adaptive_model"]["decodes"]
    added = result["adaptive_model"]["estimated_added_hit_policy_credits"] + result["adaptive_model"]["estimated_added_miss_policy_credits"]
    result["avoided_decodes"] = avoided
    result["estimated_added_policy_credits"] = added
    result["policy_only_break_even_credits_per_avoided_decode"] = round(added / avoided, 3) if avoided > 0 else None
    return result


def checks():
    count = 0
    for c in [0, 1, 2, 3, 7, 16, 48, 64]:
        p = Policy(c)
        if c:
            for f in range(8 * c + 3):
                p.request(f % (c + 1))
                p.invariant()
        else:
            try:
                p.request(0)
            except Rejected:
                pass
            else:
                raise AssertionError("zero capacity accepted")
        count += 1
    p = Policy(4, 8)
    for f in range(4):
        p.request(f, 2)
    p.resident[0][3] = 1
    assert p.request(4, 6) == [1, 2, 3]
    assert 0 in p.resident
    count += 1
    p = Policy(2)
    for f in range(3):
        p.request(f)
    assert p.ghost[0] == (0, False)
    try:
        p.request(0, fail="build")
    except Rejected:
        pass
    assert p.p == 0 and 0 not in p.resident and p.ghost[0] == (0, False)
    p.invariant()
    count += 1
    p = Policy(3)
    for f in [9, 8, 7]:
        p.request(f)
    for r in p.resident.values():
        r[0] = 1
    assert p.request(6) == [9]  # lower stable slot, independent of function key
    count += 1
    p = Policy(3)
    for f in range(3):
        p.request(f)
    frozen = copy.deepcopy(p.__dict__)
    try:
        p.request(4, fail="plan")
    except Rejected:
        pass
    assert p.__dict__ == frozen
    count += 1
    old_p = p.p
    try:
        p.request(4, fail="build")
    except Rejected:
        pass
    assert p.p == old_p and 4 not in p.resident and len(p.resident) == 2
    p.invariant()
    count += 1
    p = Policy(3)
    for f in range(3):
        p.request(f)
    for r in p.resident.values():
        r[3] = 1
    frozen = copy.deepcopy(p.__dict__)
    try:
        p.request(4)
    except Rejected:
        pass
    assert p.__dict__ == frozen
    count += 1
    p = Policy(2)
    p.request(1)
    p.resident[1][0] = p.clock + 1
    frozen = copy.deepcopy(p.__dict__)
    try:
        p.request(1)
    except Rejected:
        pass
    assert p.__dict__ == frozen
    count += 1
    p = Policy(2)
    p.clock = U64_MAX
    frozen = copy.deepcopy(p.__dict__)
    try:
        p.request(1)
    except Rejected:
        pass
    assert p.__dict__ == frozen
    count += 1
    # Deterministic phase change, bounded ring turnover, and both feedback directions.
    p = Policy(8)
    for f in [f for _ in range(8) for f in range(10)]:
        p.request(f)
    assert p.feedback > 0
    for f in [f for _ in range(8) for f in range(20, 28)]:
        p.request(f)
    assert set(p.resident) == set(range(20, 28))
    p.invariant()
    count += 1
    return count


def main():
    warm = [f for f in range(34, 50) for _ in range(2)]
    hot_scan = [f for r in range(4) for f in list(range(100 + 128*r, 228 + 128*r)) + list(range(34, 50))]
    phase_warm = [f for _ in range(3) for f in range(100, 116)]
    traces = {
        "hot16_scan128_four_rounds": run_trace(warm, hot_scan),
        "cyclic65_three_rounds": run_trace([], list(range(100, 165)) * 3),
        "expensive_hot_cheap_cold": run_trace([f for f in range(100, 116) for _ in range(2)], [f for r in range(4) for f in list(range(200 + 128*r, 328 + 128*r)) + list(range(100, 116))]),
        "cheap_hot_expensive_cold": run_trace([f for f in range(100, 116) for _ in range(2)], [f for r in range(4) for f in list(range(200 + 128*r, 328 + 128*r)) + list(range(100, 116))]),
        "uniform_hot_cold": run_trace([f for f in range(100, 116) for _ in range(2)], [f for r in range(4) for f in list(range(200 + 128*r, 328 + 128*r)) + list(range(100, 116))]),
        "expensive_old_to_cheap_cycle64_phase_shift": run_trace(phase_warm, list(range(200, 264)) * 12),
        "resident_hit256": run_trace(list(range(34, 98)), list(range(34, 98)) * 4),
    }
    result = {
        "scope": "Finite Python policy model; no VM, decode work, wall-time, Rust inventory, hash-index, or product qualification evidence.",
        "checks_passed": checks(),
        "traces": traces,
        "work_estimate_scope": "Added retention-policy work schedule only, with valid-chain hash occupancy. Excludes existing lookup, scans, index edits, decoding/building, allocation, reservation, cleanup, and machine time. Break-even only divides new policy cost by avoided decodes; it is not net CacheWork.",
        "parent_supplied_original_failure_sensitivity": {
            "baseline_hits": 537576,
            "four_credits_per_hit": 2150304,
            "percent_of_64000000_work_budget": 3.35985,
            "repeated_build_work": 34500496,
            "repeated_build_count": 61142,
            "mean_repeated_build_work": 34500496 / 61142,
            "repeat_builds_to_cover_hit_charge_at_that_mean": 2150304 / (34500496 / 61142),
            "limitation": "Sensitivity using baseline observations at failure, not a candidate target prediction. New misses and new hit counts remain unknown.",
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
