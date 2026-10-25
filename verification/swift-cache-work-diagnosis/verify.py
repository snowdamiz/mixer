#!/usr/bin/env python3
"""Read-only bindings and narrow arithmetic checks; no compile or execution."""
from pathlib import Path
import hashlib
import json

packet = Path(__file__).resolve().parent
root = packet.parent.parent
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
seal = json.loads((packet / "seal.json").read_text())
for relative, expected in seal["files"].items():
    assert sha(packet / relative) == expected, relative
for relative, expected in seal["externalFiles"].items():
    assert sha(root / relative) == expected, relative
inputs = json.loads((packet / "input-bindings.json").read_text())
for relative, expected in inputs.items():
    assert sha(root / relative) == expected, relative
baseline = root / "verification/swift-exact-reactor-after-observer/baseline-manifest.json"
assert sha(baseline) == "f2682c6a2fd6f6e74bd00a2394ff32b704aa1e2ed3d2373ef95cdee29fa7eb2c"
manifest = json.loads(baseline.read_text())
assert len(manifest) == 132
for relative, expected in manifest.items():
    assert sha(root / "vm" / relative) == expected, relative
rows = []
for line in (packet / "fixture.stdout").read_text().splitlines():
    if "DIAG " in line:
        rows.append(json.loads(line.split("DIAG ", 1)[1]))
observations = json.loads((packet / "fixture-observations.json").read_text())
assert rows == observations["observations"]
for row in rows[:2]:
    assert sum(row["cold_steps"]) == row["cold_work"]
    assert row["cold_steps"][2] == row["cold_steps"][4] == 512
    assert sum(row["hit_steps"]) == row["hit_work"] == 3
    assert row["hit_steps"][2] == row["hit_steps"][4] == 0
row = rows[2]
assert sum(row["steps"]) == row["work"] == 164008
assert row["steps"][2] == row["steps"][4] == 130 * 512
assert (row["decodes"], row["misses"], row["hits"], row["evictions"]) == (130, 130, 0, 66)
assert rows[3] == {"cleanup": "all_three_actual_owners_drained"}
arithmetic = json.loads((packet / "arithmetic.json").read_text())
assert arithmetic["compulsoryResetCreditsFromCompletedDecodes"] == 24054 * 1024 == 24631296
assert arithmetic["compulsoryResetCreditsAfterInitialize"] == 23919 * 1024 == 24493056
command = json.loads((packet / "fixture-command.json").read_text())
assert command["exitCode"] == 0 and not command["timedOut"]
assert sha(packet / "fixture.stdout") == command["stdoutSHA256"]
assert sha(packet / "fixture.stderr") == command["stderrSHA256"]
assert sha(packet / "copied-source-manifest.json") == command["sourceManifestSHA256"]
cleanup = json.loads((packet / "cleanup.json").read_text())
assert cleanup["ownedPathsAbsent"] and cleanup["live132SourceHashesUnchanged"]
assert cleanup["processGroupMembers"] == [] and cleanup["signalsSent"] == []
assert all(not (packet / name).exists() for name in ("scratch", "target", "tmp"))
receipt = json.loads((packet / "receipt.json").read_text())
assert receipt["fixturePassed"] and not receipt["optimizationImplemented"]
assert not receipt["targetExecuted"] and not receipt["targetHotspotMeasured"]
print(f"Verified {len(seal['files'])} packet members, {len(inputs)} input references, 132 live source bindings and fixture arithmetic; no execution.")
