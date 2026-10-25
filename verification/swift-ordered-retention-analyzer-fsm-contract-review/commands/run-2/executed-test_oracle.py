"""Independent pre-access vectors; finite symbols only, never File replay."""
import json
import unittest
from dataclasses import asdict, replace
from pathlib import Path
from oracle import Envelope, MAX, Refused, Stage, Symbol, observation, step


def at(stage, **changes):
    return replace(Envelope(stage=stage, operation=7, requested=34), **changes)


def event(state, kind, *, variant=0, **changes):
    op = state.operation + 1 if kind == 1 else (0 if kind in (12, 13) else state.operation)
    fn = MAX if kind == 13 else state.requested
    return replace(Symbol(kind, state.phase + 1 if kind == 13 else state.phase,
                          op, fn, variant=variant,
                          sequence=state.sequence + 1, work=state.work,
                          instructions=state.instructions), **changes)


def matrix():
    rows = []
    for state in Stage:
        s = at(state)
        for kind in range(1, 15):
            e = event(s, kind, variant=int(state == Stage.Built) if kind == 11 else 0)
            try:
                after = step(s, e)
                destination = int(after.stage)
            except Refused:
                destination = None
            rows.append({"state": int(state), "kind": kind,
                         "event": asdict(e), "next_state": destination})
    return rows


class IndependentEnvelopeTests(unittest.TestCase):
    def refuse(self, old, e, **kw):
        frozen = asdict(old)
        with self.assertRaises(Refused):
            step(old, e, **kw)
        self.assertEqual(asdict(old), frozen)

    def test_01_all_11_by_14_pairs(self):
        expected = {0: {1: 1, 12: 0, 13: 0}, 1: {2: 3, 14: 0},
                    2: {11: 0, 14: 0}, 3: {3: 4, 14: 0},
                    4: {4: 5, 14: 0}, 5: {5: 6, 14: 0},
                    6: {6: 7, 9: 9, 14: 0}, 7: {7: 8, 14: 0},
                    8: {8: 6, 14: 0}, 9: {10: 10, 14: 0},
                    10: {11: 0, 14: 0}}
        rows = matrix()
        self.assertEqual(len(rows), 154)
        for row in rows:
            self.assertEqual(row["next_state"], expected[row["state"]].get(row["kind"]), row)

    def test_02_lookup_forms(self):
        s = at(Stage.Acquire)
        self.assertEqual(step(s, event(s, 2, variant=0)).stage, Stage.Miss)
        self.assertEqual(step(s, event(s, 2, variant=1)).stage, Stage.Hit)
        self.refuse(s, event(s, 2, variant=2))

    def test_03_publication_forms(self):
        for stage, form in ((Stage.Hit, 0), (Stage.Built, 1)):
            s = at(stage)
            self.assertEqual(step(s, event(s, 11, variant=form)).stage, Stage.Idle)
            for bad in (1 - form, 2, MAX):
                self.refuse(s, event(s, 11, variant=bad))

    def test_04_pin_failures_close_every_open_state(self):
        for stage in list(Stage)[1:]:
            s = at(stage)
            for cursor in (MAX, 0, 21, 34, 79_999):
                r = step(s, event(s, 14, function=cursor))
                self.assertEqual(r.stage, Stage.Idle)
                self.assertTrue(r.pin_failed)
                self.assertFalse(r.terminal_failed)

    def test_05_failure_operation_forms(self):
        idle = at(Stage.Idle)
        terminal = step(idle, event(idle, 14, operation=0))
        self.assertTrue(terminal.terminal_failed)
        self.refuse(terminal, event(terminal, 14, operation=0))
        self.refuse(idle, event(idle, 14, operation=7))
        for stage in list(Stage)[1:]:
            s = at(stage)
            for op in (0, 1, 6, 8, MAX):
                self.refuse(s, event(s, 14, operation=op))

    def test_06_terminal_after_pin_failure(self):
        s = at(Stage.Scan)
        failed = step(s, event(s, 14))
        terminal = step(failed, event(failed, 14, operation=0, function=MAX))
        self.assertTrue(terminal.pin_failed and terminal.terminal_failed)

    def test_07_no_failure_resumption(self):
        for stage in list(Stage)[1:]:
            s = at(stage)
            failed = step(s, event(s, 14))
            for kind in range(1, 12):
                self.refuse(failed, event(failed, kind, variant=1))
        terminal = step(at(Stage.Idle), event(at(Stage.Idle), 14, operation=0))
        for kind in range(1, 12):
            self.refuse(terminal, event(terminal, kind))

    def test_08_release_idle_only_including_after_failure(self):
        for phase in range(5):
            for flags in ((False, False), (True, False), (False, True), (True, True)):
                idle = at(Stage.Idle, phase=phase, pin_failed=flags[0], terminal_failed=flags[1])
                self.assertEqual(step(idle, event(idle, 12)).stage, Stage.Idle)
                self.refuse(idle, event(idle, 12, operation=7))
            for stage in list(Stage)[1:]:
                s = at(stage, phase=phase)
                self.refuse(s, event(s, 12))

    def test_09_phases_strict_idle(self):
        for phase in range(5):
            idle = at(Stage.Idle, phase=phase, mask=(1 << (phase + 1)) - 1)
            for next_phase in range(6):
                e = event(idle, 13, phase=next_phase)
                if next_phase > phase:
                    self.assertEqual(step(idle, e).phase, next_phase)
                else:
                    self.refuse(idle, e)
            for stage in list(Stage)[1:]:
                s = replace(idle, stage=stage)
                self.refuse(s, event(s, 13))

    def test_10_phase5_is_terminal_for_every_kind(self):
        for stage in Stage:
            s = at(stage, phase=5, mask=63)
            for kind in range(1, 15):
                self.refuse(s, event(s, kind, phase=5))

    def test_11_acquisition_phase_and_operation(self):
        for phase in range(4):
            s = at(Stage.Idle, phase=phase)
            self.assertEqual(step(s, event(s, 1)).operation, 8)
            for op in (0, 1, 7, 9, MAX):
                self.refuse(s, event(s, 1, operation=op))
        for phase in (4, 5):
            s = at(Stage.Idle, phase=phase)
            self.refuse(s, event(s, 1))

    def test_12_normal_stage_operation_and_requested_function_joins(self):
        cases = ((Stage.Acquire, 2), (Stage.Miss, 3), (Stage.Scan, 4),
                 (Stage.Plan, 5), (Stage.Ready, 6), (Stage.EvictBegin, 7),
                 (Stage.EvictTaken, 8), (Stage.Ready, 9), (Stage.Build, 10),
                 (Stage.Hit, 11), (Stage.Built, 11))
        for stage, kind in cases:
            s = at(stage)
            e = event(s, kind, variant=int(stage == Stage.Built))
            step(s, e)
            for wrong_op in (0, 6, 8, MAX):
                self.refuse(s, replace(e, operation=wrong_op))
            for wrong_fn in (0, 35, 80_000, MAX):
                self.refuse(s, replace(e, function=wrong_fn))

    def test_13_failure_cursor_is_independent_original_optional_cursor(self):
        for stage in Stage:
            s = at(stage)
            op = 0 if stage == Stage.Idle else 7
            for cursor in (MAX, 0, 33, 35, 79_999):
                step(s, event(s, 14, operation=op, function=cursor))
            self.refuse(s, event(s, 14, operation=op, function=80_000))

    def test_14_cap_preserves_open_stage_and_unknown_tail(self):
        for stage in Stage:
            s = at(stage)
            before = asdict(s)
            o = observation(s, cap_tail=True)
            self.assertEqual(o["acquisition_state"], stage)
            self.assertTrue(o["omitted_tail_unknown"])
            self.assertEqual(before, asdict(s))
            for key in ("storedPrefixValidated", "fullReplayAccepted", "semantic_counters_valid"):
                self.assertFalse(o[key])

    def test_15_atomic_budget_and_candidate_refusal(self):
        for row in matrix():
            if row["next_state"] is None:
                continue
            s = at(Stage(row["state"]))
            e = Symbol(**row["event"])
            self.refuse(s, e, budget=0)
            self.refuse(s, e, candidate_ok=False)
            self.assertEqual(step(s, e, budget=1, required=1).stage, row["next_state"])

    def test_16_eviction_loop_and_miss_path(self):
        s = Envelope()
        for kind in (1, 2, 3, 4, 5, 6, 7, 8, 6, 7, 8, 9, 10, 11):
            s = step(s, event(s, kind, function=34, variant=int(kind == 11)))
        self.assertEqual(s.stage, Stage.Idle)
        self.assertEqual(s.operation, 1)

    def test_17_atomic_ordering_and_coordinate_refusal(self):
        s = at(Stage.Acquire, sequence=4, work=7, instructions=11)
        for values in ({"sequence": 4}, {"sequence": 6}, {"work": 6},
                       {"instructions": 10}, {"phase": 1}, {"kind": 0}, {"kind": 15}):
            self.refuse(s, replace(event(s, 2), **values))

    def test_18_noncap_observation_grants_no_semantic_validity(self):
        s = at(Stage.Idle, phase=5, mask=33)
        o = observation(s, cap_tail=False)
        self.assertFalse(o["storedPrefixValidated"])
        self.assertFalse(o["fullReplayAccepted"])
        self.assertFalse(o["semantic_counters_valid"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
