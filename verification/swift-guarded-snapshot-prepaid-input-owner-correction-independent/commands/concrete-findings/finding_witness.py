"""Narrow positive reproduction of defects; exit zero is NOT acceptance."""
import json
from review_controls import complete, selected, m

root, paid, view, _, _ = complete()
result = selected(paid, view, buffer_count=3)
try:
    m.correlate_before_leaf(paid, view, result)
except m.Refused as original:
    refusal = str(original)
    assert original is paid.diagnostics[-1]
assert paid.state == "admitted" and result.owner is None
token = paid.destroy()
assert token.complete
token.release()
assert root.used_storage == 0 and result.live and all(h.live for h in result.files)
print(json.dumps({"finding": "C1-owner-escape", "first_refusal": refusal,
                  "complete_token": token.complete, "released": paid.released,
                  "remaining_storage_charge": root.used_storage,
                  "selected_live": result.live, "supplied_selected_File_owners_still_live": len(result.files),
                  "selected_in_paid_roster": result in paid.outcome.loader_results}))

_, paid, view, _, _ = complete()
bad = selected(paid, view, buffer_count=3)
try: m.correlate_before_leaf(paid, view, bad)
except m.Refused: pass
good = selected(paid, view)
answer = m.correlate_before_leaf(paid, view, good)
assert paid.effects.count("leaf-model-only") == 1
print(json.dumps({"finding": "C1-reusable-refusal", "later_leaf_count": 1, "later_result": answer}))

_, paid, view, _, _ = complete()
result = selected(paid, view)
try: m.correlate_before_leaf(paid, view, result, {})
except m.Refused: pass
m.correlate_before_leaf(paid, view, result)
assert paid.effects.count("leaf-model-only") == 1
print(json.dumps({"finding": "C1-old-API-retry", "later_leaf_count": 1}))

for name, mutate in (
    ("extent-float", lambda r: r.update(extent=float(r["extent"]))),
    ("inode-float", lambda r: r["source_identity"].update(inode=float(r["source_identity"]["inode"]))),
    ("mtime-ns-float", lambda r: r["source_identity"].update(mtime_ns=float(r["source_identity"]["mtime_ns"]))),
):
    _, paid, view, _, _ = complete(record_change=mutate)
    assert paid.state == "admitted"
    print(json.dumps({"finding": "C2-strict-session-type", "malformation": name, "admitted": True}))
