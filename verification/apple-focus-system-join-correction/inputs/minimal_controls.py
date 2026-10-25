#!/usr/bin/env python3
"""Tighter independent reproductions; never edits the producer or oracle."""
import copy
import hashlib
import importlib.util
import json
import pathlib
import sys
from decimal import Decimal as D

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("review_fixture_support", HERE / "review.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)
o = review.imported("bounded_observation_for_minimal_controls", review.PRODUCER / "observation.py")
sha = lambda value: hashlib.sha256(o.encoded(value)).hexdigest()
outputs = []

# Positive control retains every original endpoint and original observation.
values = review.fixture(o)
fingerprints = [sha(value) for value in values]
positive = o.join(*values)
assert positive["supplemental"]["captureStatus"] == "complete"
assert positive["supplemental"]["nativePass"] is False
assert fingerprints == [sha(value) for value in values]
outputs.append({"control": "unchanged original positive join", "result": positive["supplemental"]})

# The supplemental diagnostic and every witness/binding field stay unchanged.
values = review.fixture(o)
original = copy.deepcopy(values[0])
original.pop("focusSystemDiagnostic")
old_focused = values[0]["state"]["focused"]
values[0]["state"]["focused"] = not old_focused
altered = copy.deepcopy(values[0])
altered.pop("focusSystemDiagnostic")
result = o.join(*values)
assert sha(original) != sha(altered)
assert result["supplemental"]["captureStatus"] == "complete"
assert result["supplemental"]["nativePass"] is False and result["originalVerdict"]["passed"] is False
outputs.append({"control": "F1 original app observation substitution", "mutation": {
    "path": "before.state.focused", "before": old_focused, "after": not old_focused},
    "expected": "incomplete: immutable diagnostic-excluded original before observation differs",
    "trustedOriginalBeforeObservationSHA256": sha(original),
    "suppliedBeforeObservationSHA256": sha(altered), "result": result["supplemental"]})

# Change only the two middle callback references and their own intervals.
# Leave all later rows, both frozen observations, witness and binding intact.
values = review.fixture(o)
rows = values[1]["focusSystemDiagnostic"]["entries"]
before_rows = copy.deepcopy(rows)
rows[2]["contextSequence"], rows[3]["contextSequence"] = 3, 2
rows[2]["startedUptime"] = values[1]["focusContexts"][2]["uptime"] + D(".00001")
rows[2]["finishedUptime"] = rows[2]["startedUptime"] + D(".000001")
rows[3]["startedUptime"] = rows[2]["finishedUptime"] + D(".000001")
rows[3]["finishedUptime"] = rows[3]["startedUptime"] + D(".000001")
assert rows[:2] == before_rows[:2] and rows[4:] == before_rows[4:]
result = o.join(*values)
assert result["supplemental"]["captureStatus"] == "complete"
assert result["supplemental"]["nativePass"] is False and result["originalVerdict"]["passed"] is False
outputs.append({"control": "F2 minimal callback revision substitution", "expected": "incomplete: callback references must be in original append order",
    "expectedReferences": [1, 2, 3, 4], "observedReferences": [row["contextSequence"] for row in rows if row["site"] != "snapshot"],
    "changedRows": [{key: row[key] for key in ("sequence", "contextSequence", "startedUptime", "finishedUptime")} for row in rows[2:4]],
    "otherRowsUnchanged": True, "result": result["supplemental"]})

packet = {"schema": 1, "scope": "Three finite independent controls; synthetic diagnostics only; no runtime evidence",
          "controlsPassed": 3, "nativeAccepted": False, "controls": outputs}
(HERE / "minimal-reproductions.json").write_bytes(o.encoded(packet) + b"\n")
print(json.dumps({"controlsPassed": 3, "findingsReproduced": ["F1", "F2"], "nativeAccepted": False}, sort_keys=True))
