"""Preserved independently encoded contract counterexamples; exits nonzero."""
import json
from pathlib import Path
from test_frozen_contract import model, wire, to_producer
from test_oracle import at, event
from oracle import Stage

OWN = Path(__file__).resolve().parent
rows = []
for stage, kind in ((Stage.Acquire, 2), (Stage.Idle, 12)):
    s = at(stage)
    for typ in (1 << 32, (1 << 64) - 2):
        w = list(wire(event(s, kind)))
        w[9] = typ
        r = model.observe(to_producer(s), w)
        rows.append({"kind": kind, "type": typ, "words": w,
                     "shape": model.shape(w), "reason": r.reason,
                     "source_type_width": "u32",
                     "finding": "R1 closed source scalar domain widened"})
s = at(Stage.Acquire)
r = model.observe(to_producer(s), wire(event(s, 14)), fault="commit")
boundary = model.finish(r.state, True)
rows.append({"reason": r.reason, "poisoned_state": r.state,
             "finish_cap_boundary": boundary,
             "fullReplayAccepted": r.fullReplayAccepted,
             "storedPrefixValidated": r.storedPrefixValidated,
             "finding": "R3 poison not propagated through finish boundary"})
(OWN / "findings-freeze1-reproductions.json").write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n")
print(json.dumps(rows, indent=2, sort_keys=True))
assert not any(row.get("shape") for row in rows), "R1: unsupported u64 type passes shape and envelope"
assert boundary != "CapCutUnknownTail", "R3: poisoned reply names normal CAP fixture boundary"
