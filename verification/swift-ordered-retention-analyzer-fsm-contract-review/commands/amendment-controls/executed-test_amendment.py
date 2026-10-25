"""Independent regression controls for R1/R2/R3 on frozen amendment only."""
from dataclasses import replace
import json
import os
from pathlib import Path
import unittest

from test_frozen_contract import model, wire, to_producer
from test_oracle import at, event
from oracle import Envelope, MAX, Stage, step

OWN = Path(__file__).resolve().parent
MAX32 = (1 << 32) - 1


class AmendmentControls(unittest.TestCase):
    def test_01_u32_width_every_full_body_kind_and_release(self):
        self.assertEqual(os.environ.get("FSM_REVIEW_FREEZE"), "producer-freeze-2")
        cases = ((Stage.Acquire, 2), (Stage.Miss, 3), (Stage.Scan, 4),
                 (Stage.Plan, 5), (Stage.Ready, 6), (Stage.EvictBegin, 7),
                 (Stage.EvictTaken, 8), (Stage.Ready, 9), (Stage.Build, 10),
                 (Stage.Hit, 11), (Stage.Built, 11), (Stage.Idle, 12))
        for stage, kind in cases:
            s = at(stage)
            w = list(wire(event(s, kind, variant=int(stage == Stage.Built))))
            for typ in (0, MAX32 - 1, MAX32, MAX32 + 1, MAX - 1, MAX):
                w[9] = typ
                self.assertEqual(model.shape(w), typ <= MAX32, (stage, kind, typ))
                reply = model.observe(to_producer(s), w)
                self.assertEqual(reply.reason == "Observed", typ <= MAX32)
                self.assertFalse(reply.storedPrefixValidated or reply.fullReplayAccepted or reply.semanticMetricsValid)

    def test_02_exact_frozen_width_reproductions_now_refuse(self):
        rows = json.loads((OWN / "findings-freeze1-reproductions.json").read_text())
        count = 0
        for row in rows:
            if "words" not in row:
                continue
            count += 1
            s = at(Stage.Acquire if row["kind"] == 2 else Stage.Idle)
            reply = model.observe(to_producer(s), row["words"])
            self.assertEqual(reply.reason, "Shape")
            self.assertEqual(reply.state, to_producer(s))
        self.assertEqual(count, 4)

    def test_03_retained_candidate_repeated_calls_no_implicit_zero_or_move(self):
        owner = model.FixtureEnvelope.create(expected=49)
        candidate = owner._candidate
        self.assertEqual(len(candidate), 2048)
        self.assertEqual(candidate, bytes(2048))
        s = Envelope()
        path = (1, 2, 3, 4, 5, 9, 10, 11, 12, 1, 2, 11, 12, 13, 13)
        for position, kind in enumerate(path):
            variant = 1 if (kind == 11 and s.stage == Stage.Built) or (kind == 2 and position == 10) else 0
            kwargs = {"function": 34}
            if kind == 13:
                kwargs = {"phase": 4 if position == 13 else 5}
            e = event(s, kind, variant=variant, **kwargs)
            before = bytes(candidate)
            reply = owner.step(wire(e))
            self.assertEqual(reply.reason, "Observed")
            s = step(s, e)
            self.assertIs(owner._candidate, candidate)
            self.assertEqual(candidate[:888], bytes(888))
            self.assertEqual(candidate[984:], bytes(2048 - 984))
            for i, name in enumerate(model.CELLS):
                observed = int.from_bytes(candidate[888 + 8*i:896 + 8*i], "little")
                self.assertEqual(observed, getattr(reply.state, name))
            if s.phase < 5:
                # A refused operation cannot change owner identity or candidate.
                wrong = list(wire(event(s, 1, function=34))); wrong[3] = MAX
                saved = bytes(candidate)
                refusal = owner.step(wrong)
                self.assertNotEqual(refusal.reason, "Observed")
                self.assertEqual(bytes(candidate), saved)
                self.assertIs(owner._candidate, candidate)
        self.assertEqual(owner.finish(False), "ClosedEnvelopeObserved")
        self.assertEqual(owner.finish(True), "CapCutUnknownTail")

    def test_04_setup_and_record_debit_admission(self):
        self.assertEqual(model.CANDIDATE_SETUP_DEBIT, 534)
        for left in (0, 533):
            self.assertIsNone(model.FixtureEnvelope.create(49, left))
        for mask in (0, 1, 32, 64, True):
            self.assertIsNone(model.FixtureEnvelope.create(mask, 534))
        for additional in (0, 1, 127, 128):
            owner = model.FixtureEnvelope.create(49, 534 + additional)
            candidate = owner._candidate
            w = wire(event(Envelope(), 1, function=34))
            reply = owner.step(w)
            self.assertEqual(reply.reason, "Observed" if additional == 128 else "Steps")
            self.assertEqual(reply.steps, 128 if additional == 128 else 0)
            self.assertIs(owner._candidate, candidate)
            self.assertEqual(owner._remaining, 0 if additional == 128 else additional)

    def test_05_poison_precedes_cap_and_absent_or_stale_state(self):
        original = to_producer(at(Stage.Acquire))
        poisoned = model.observe(original, wire(event(at(Stage.Acquire), 14)), fault="commit")
        self.assertEqual(poisoned.reason, "InternalPoisoned")
        for cap in (False, True):
            for value in (None, poisoned, model.Reply("InternalPoisoned", original, 128),
                          model.Reply("Observed", None, 128)):
                self.assertEqual(model.finish(value, cap), "InternalPoisoned")
            self.assertEqual(model.finish(object(), cap), "UnavailableState")
        for left in (0, 127, 128):
            reply = model.observe(None, (), left)
            self.assertEqual((reply.reason, reply.state, reply.steps), ("InternalPoisoned", None, 0))

    def test_06_poisoned_owner_cannot_resume_and_close_is_unavailable(self):
        owner = model.FixtureEnvelope.create(49)
        candidate = owner._candidate
        initial = Envelope()
        e = event(initial, 1, function=34)
        reply = owner.step(wire(e), fault="commit")
        self.assertEqual(reply.reason, "InternalPoisoned")
        self.assertIsNone(owner._state)
        for cap in (False, True):
            self.assertEqual(owner.finish(cap), "InternalPoisoned")
        saved = bytes(candidate)
        for kind in range(1, 15):
            reply = owner.step(wire(event(initial, kind, function=34)))
            self.assertEqual((reply.reason, reply.steps, reply.state), ("InternalPoisoned", 0, None))
            self.assertEqual(bytes(candidate), saved)
            self.assertFalse(reply.storedPrefixValidated or reply.fullReplayAccepted or reply.semanticMetricsValid)
        owner.close()
        self.assertIsNone(owner._candidate)
        for cap in (False, True):
            self.assertEqual(owner.finish(cap), "UnavailableState")
        with self.assertRaises(ValueError):
            owner.step(wire(e))

    def test_07_complete_init_and_call_role_arithmetic(self):
        initialization = (2048, 2048, 16, 32, 16, 16, 24, 16, 384, 128)
        record_call = (2048, 136, 32, 32, 16, 96, 96, 128, 128, 128,
                       128, 128, 32, 384, 256, 768)
        self.assertEqual(sum(initialization), 4728)
        self.assertEqual(sum(record_call), 4536)
        self.assertEqual(5120 - max(sum(initialization), sum(record_call)), 392)
        self.assertEqual(5120, 2048 + 3072)
        self.assertLessEqual(3072, 8192)
        self.assertEqual(256 + 256 + 12 + 2 + 4 + 4, 534)
        self.assertLess(534, 65536)
        self.assertEqual(model.RECORD_DEBIT, 128)
        self.assertEqual(model.LIMIT, 268435456)

    def test_08_candidate_refusal_and_cleanup_paths(self):
        owner = model.FixtureEnvelope.create()
        candidate = owner._candidate
        e = event(Envelope(), 1, function=34)
        for mode in ("shape", "preflight"):
            w = list(wire(e))
            if mode == "shape":
                w[1] = 0
            reply = owner.step(w, fault="preflight" if mode == "preflight" else None)
            self.assertNotEqual(reply.reason, "Observed")
            self.assertEqual(reply.state.accepted, 0)
            self.assertEqual(candidate, bytes(2048))
            self.assertIs(candidate, owner._candidate)
        owner.close()
        self.assertIsNone(owner._candidate)
        self.assertEqual(owner.finish(False), "UnavailableState")


if __name__ == "__main__":
    unittest.main(verbosity=2)
