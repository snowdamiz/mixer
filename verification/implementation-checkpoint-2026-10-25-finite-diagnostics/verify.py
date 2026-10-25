#!/usr/bin/env python3
"""Verify this finite evidence selection without inspecting unrelated packets."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
selected = json.loads((HERE / "selected-files.json").read_text())
for name, expected in selected.items():
    path = ROOT / name
    assert path.is_file() and not path.is_symlink(), name
    data = path.read_bytes()
    assert len(data) == expected["bytes"], name
    assert hashlib.sha256(data).hexdigest() == expected["sha256"], name

tracked = ["STATUS.md", "PLAN.md", "work-graph.json", "gates/ga.json"]
subprocess.run(["git", "diff", "--check", "--", *tracked], cwd=ROOT, check=True)
base = json.loads(subprocess.check_output(
    ["git", "show", "4ffd5ecf974c3ac8c8a052e9a533fcd7b244f545:gates/ga.json"], cwd=ROOT))
current = json.loads((ROOT / "gates/ga.json").read_text())
gate_states = lambda value: [(x["id"], x["status"], x["reviewer"]) for x in value["gates"]]
assert gate_states(base) == gate_states(current), "gate promotion"
graph = json.loads((ROOT / "work-graph.json").read_text())
assert len({x["id"] for x in graph["packages"]}) == len(graph["packages"])
for package in graph["packages"]:
    if package["id"] in {"W04", "W08", "W12"}:
        for name in package["evidence"]:
            assert (ROOT / name).exists(), name
print(json.dumps({"selectedFiles": len(selected), "hashesExact": True,
                  "rootDiffCheck": True, "gateStatesAndReviewersUnchanged": True,
                  "activeReviewLanesExcluded": True,
                  "liveEngineOrNativeAcceptance": False}))
