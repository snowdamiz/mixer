"""Independent cross-checks of frozen finite model; no product/target imports."""
import importlib.util
import json
import os
from pathlib import Path
import unittest
from dataclasses import replace

from oracle import Envelope, MAX, Stage, Symbol, Refused, step
from test_oracle import at, event, matrix

OWN = Path(__file__).resolve().parent
PRODUCER = (OWN / os.environ.get("FSM_REVIEW_FREEZE", "producer-freeze-1") / "repository" /
            "verification/swift-ordered-retention-analyzer-fsm-contract")
spec = importlib.util.spec_from_file_location("frozen_fsm_model", PRODUCER / "model.py")
model = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = model
spec.loader.exec_module(model)


def to_producer(s):
    return model.State(accepted=s.sequence, work=s.work, instructions=s.instructions,
                       operation=s.operation, phase=s.phase, mask=s.mask, expected=49,
                       state=int(s.stage), active_op=s.operation,
                       function=s.requested, terminal=int(s.terminal_failed),
                       failed=int(s.pin_failed))


def wire(e):
    """Independent raw encoder; not the frozen producer's builder."""
    w = [e.sequence, e.kind, e.phase, e.operation, e.work, e.instructions,
         e.function, 100, 7, 2, MAX, MAX, 0, 0, 0, 0]
    k = e.kind
    if k == 1:
        w[7:10] = [MAX] * 3
    elif k == 2:
        w[10], w[13] = (0 if e.variant else MAX), e.variant
    elif k == 3:
        w[15] = e.function & 511
    elif k == 4:
        w[14:16] = [MAX, e.function & 511]
    elif k == 5:
        w[13:16] = [8, 16, 64]
    elif k in (6, 7, 8):
        w[10], w[13] = 0, 8
    elif k in (9, 10):
        w[13] = 8
    elif k == 11:
        w[10:16] = [0, 0, 1, e.variant, 8, 1]
    elif k == 12:
        w[8], w[10:16] = MAX, [0, 0, 1, 8, 0, 0]
    elif k == 13:
        w[6:10], w[13] = [MAX] * 4, e.phase
    elif k == 14:
        w[7:10], w[13:16] = [MAX] * 3, [2, 1, 2]
    return tuple(w)


class FrozenContractCrossChecks(unittest.TestCase):
    def compare(self, s, e):
        try:
            expected = step(s, e)
        except Refused:
            expected = None
        p = to_producer(s)
        r = model.observe(p, wire(e))
        self.assertEqual(r.reason == "Observed", expected is not None, (s, e, r))
        self.assertFalse(r.fullReplayAccepted or r.storedPrefixValidated or r.semanticMetricsValid)
        if expected is None:
            self.assertEqual(r.state, p)
        else:
            self.assertEqual((r.state.state, r.state.phase, r.state.mask,
                              r.state.operation, r.state.accepted,
                              r.state.work, r.state.instructions,
                              bool(r.state.failed), bool(r.state.terminal)),
                             (expected.stage, expected.phase, expected.mask,
                              expected.operation, expected.sequence,
                              expected.work, expected.instructions,
                              expected.pin_failed, expected.terminal_failed))
        return r

    def test_01_preaccess_154_vectors(self):
        frozen = json.loads((OWN / "preaccess-vectors.json").read_text())
        self.assertEqual(frozen, matrix())
        for row in frozen:
            self.compare(at(Stage(row["state"])), Symbol(**row["event"]))

    def test_02_failure_forms_every_stage_cursor_and_wrong_operation(self):
        for stage in Stage:
            s = at(stage)
            for cursor in (MAX, 0, 33, 34, 35, 79_999):
                for op in (0, 1, 6, 7, 8, MAX):
                    self.compare(s, event(s, 14, operation=op, function=cursor))

    def test_03_normal_stage_all_wrong_joins(self):
        for stage in Stage:
            s = at(stage)
            for kind in range(2, 12):
                for op in (0, 6, 7, 8, MAX):
                    for fn in (0, 33, 34, 35, 79_999):
                        self.compare(s, event(s, kind, operation=op, function=fn,
                                              variant=int(stage == Stage.Built)))

    def test_04_phase_and_release_cross_product(self):
        for phase in range(6):
            for stage in Stage:
                for pin, terminal in ((False, False), (True, False), (False, True), (True, True)):
                    s = at(stage, phase=phase, pin_failed=pin, terminal_failed=terminal)
                    self.compare(s, event(s, 12))
                    for new_phase in range(6):
                        self.compare(s, event(s, 13, phase=new_phase))

    def test_05_failure_resumption_cross_product(self):
        for stage in list(Stage)[1:]:
            s = at(stage)
            failed = step(s, event(s, 14))
            for kind in range(1, 15):
                self.compare(failed, event(failed, kind))
        s = at(Stage.Idle, terminal_failed=True)
        for kind in range(1, 15):
            self.compare(s, event(s, kind))

    def test_06_variants(self):
        for stage in Stage:
            s = at(stage)
            for kind in (2, 11):
                for variant in (0, 1, 2, MAX):
                    self.compare(s, event(s, kind, variant=variant))

    def test_07_atomic_budget_preflight_poison(self):
        for stage in Stage:
            s = at(stage)
            e = event(s, 14, operation=0 if stage == Stage.Idle else s.operation)
            p, w = to_producer(s), wire(e)
            for remaining in (0, 1, 127):
                r = model.observe(p, w, remaining)
                self.assertEqual((r.reason, r.steps, r.state), ("Steps", 0, p))
            r = model.observe(p, w, 128)
            self.assertEqual((r.reason, r.steps), ("Observed", 128))
            r = model.observe(p, w, 128, fault="preflight")
            self.assertEqual((r.reason, r.steps, r.state), ("CheckedAccess", 128, p))
            r = model.observe(p, w, 128, fault="commit")
            self.assertEqual((r.reason, r.steps, r.state), ("InternalPoisoned", 128, None))
            self.assertFalse(r.fullReplayAccepted or r.storedPrefixValidated or r.semanticMetricsValid)

    def test_08_cap_no_state_or_phase_mutation(self):
        for stage in Stage:
            p = to_producer(at(stage))
            before = vars(p).copy()
            self.assertEqual(model.finish(p, True), "CapCutUnknownTail")
            self.assertEqual(vars(p), before)
            self.assertEqual(model.finish(p, False), "IncompleteEnvelope")

    def test_09_cells_against_accepted_names(self):
        expected = {"accepted": (7, "control.accepted_records"),
                    "work": (9, "control.last_work"),
                    "instructions": (10, "control.last_instructions"),
                    "operation": (11, "control.last_operation"),
                    "phase": (12, "control.current_phase"),
                    "mask": (13, "control.observed_mask"),
                    "expected": (14, "control.expected_mask"),
                    "state": (64, "active.state"),
                    "active_op": (65, "active.operation"),
                    "function": (66, "active.function"),
                    "terminal": (160, "lifecycle.terminal_seen"),
                    "failed": (161, "lifecycle.pin_failure_seen")}
        source = OWN / "inputs/verification__swift-ordered-retention-analyzer-design__interface_schema.py"
        space = {}
        exec(compile(source.read_bytes(), str(source), "exec"), space)
        for name, (index, symbolic) in expected.items():
            self.assertEqual(model.CELLS[name], index)
            self.assertEqual(space["SCALARS"][index], symbolic)
        self.assertEqual(len(set(model.CELLS.values())), 12)

    def test_10_shape_independent_scalar_boundaries(self):
        for stage, kind in ((Stage.Idle, 1), (Stage.Acquire, 2), (Stage.Miss, 3),
                            (Stage.Scan, 4), (Stage.Plan, 5), (Stage.Ready, 6),
                            (Stage.EvictBegin, 7), (Stage.EvictTaken, 8),
                            (Stage.Ready, 9), (Stage.Build, 10), (Stage.Hit, 11),
                            (Stage.Idle, 12), (Stage.Idle, 13), (Stage.Acquire, 14)):
            s = at(stage)
            w = wire(event(s, kind))
            self.assertTrue(model.shape(w), (stage, kind))
            for i in range(16):
                for n in (-1, MAX + 1, True, 1.0):
                    broken = list(w)
                    broken[i] = n
                    self.assertFalse(model.shape(tuple(broken)), (kind, i, n))

    def test_11_plan_end_discriminator(self):
        s = at(Stage.Scan)
        base = list(wire(event(s, 4)))
        for a, b in ((0, MAX), (1, 35), (2, MAX)):
            w = base.copy(); w[13], w[14] = a, b
            self.assertEqual(model.observe(to_producer(s), w).reason, "Observed")
        for a, b in ((3, MAX), (1, 34), (1, MAX), (0, 0), (2, 0)):
            w = base.copy(); w[13], w[14] = a, b
            self.assertEqual(model.observe(to_producer(s), w).reason, "Shape")

    def test_12_explicit_arithmetic_ceiling(self):
        roles = (2048,136,32,32,96,96,128,128,128,128,128,32,384,256,768)
        self.assertEqual(sum(roles), 4520)
        self.assertLessEqual(sum(roles), 5120)
        self.assertEqual(2048 + 3072, 5120)
        self.assertEqual(sum((16,12,12,24,12,12,12,12,4,12)), 128)
        fixed = 1048576 + 640000 + 65536 + 263584 + 3000000
        self.assertEqual(fixed + 128 * 2889656, 374893664)
        self.assertEqual((268435456 - fixed) // 128, 2057951)
        self.assertEqual(49152 + 8192, 57344)
        self.assertLess(57344, 65536)


if __name__ == "__main__":
    unittest.main(verbosity=2)
