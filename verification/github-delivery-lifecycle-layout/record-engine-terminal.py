"""Record terminal Engine success alongside the preserved Phoenix fixture failure."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
DEST = OUT / "terminal-ci.json"

def read(path):
    return json.loads(path.read_bytes())

def row(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

assert not DEST.exists(), "One-shot; do not replay"
r = read(OUT / "ci-jobs-6.stdout")
assert r["headSha"] == "fd92138ac0b8c4ecd0d872a9050204da5ceb5d2f"
assert r["status"] == "completed" and r["conclusion"] == "success" and r["attempt"] == 1
assert len(r["jobs"]) == 6
steps = [step for job in r["jobs"] for step in job["steps"]]
assert len(steps) == 64 and all(step["conclusion"] == "success" for step in steps)
info = {"status": "Engine-passed-Phoenix-failed-six-existing-fixture-teardowns",
        "commit": r["headSha"], "Engine": {"run": r["databaseId"], "url": r["url"], "attempt": 1,
        "jobs_passed": 6, "steps_passed": 64, "steps_skipped": 0, "observation": row(OUT / "ci-jobs-6.stdout")},
        "Phoenix": read(OUT / "phoenix-failure.json")["terminal"], "all_workflows_passed": False,
        "GA_accepted": False}
w = read(ROOT / "work-graph.json")
g = read(ROOT / "gates/ga.json")
for target in [w["packages"][13], g["gates"][21]]:
    target["fixedWorkspaceDispatcher"]["key_owner_supervised_lifecycle"]["acceptance"]["delivery"].update({"status": info["status"], "terminal_CI": copy.deepcopy(info)})
c = w["packages"][7]["fixtureCacheStateContractCandidate"]
assert c == g["gates"][1]["fixtureCacheStateContractCandidate"]
b = c["scalar_cursor_host_acceptance"]["real_profile_adapter_preparation"]["next_header_preparation"]["retained_profile_composition_preparation"]["real_binding_preparation"]["real_profile_loader_binding"]["next_adoption_lane"]["guarded_snapshot_export_contract_review"]["composition_source_preparation"]["bootstrap_host_boundary"]
b["actual_owner_Rust_selection"]["correction"]["IR02_source_repair"]["work_storage_delta"]["layout_probe"]["retrospective_layout_observation_acceptance"]["delivery"].update({"status": info["status"], "terminal_CI": copy.deepcopy(info)})
g["gates"][1]["fixtureCacheStateContractCandidate"] = copy.deepcopy(c)
old = "An explicit fixture-ownership correction is in preparation; Engine CI is still running."
new = "An explicit fixture-ownership correction is in preparation. Engine CI passes all six jobs and 64 steps on attempt one, with no skipped steps."
for name in ["PLAN.md", "STATUS.md"]:
    path = ROOT / name
    text = path.read_text()
    assert text.count(old) == 1
    path.write_text(text.replace(old, new))
for name, value in [("work-graph.json", w), ("gates/ga.json", g)]:
    (ROOT / name).write_text(json.dumps(value, indent=2) + "\n")
with DEST.open("x") as handle:
    json.dump({"schema": 1, "at": datetime.now(timezone.utc).isoformat(), "terminal": info,
               "GA_verified": 0, "metadata": [row(ROOT / n) for n in ["PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"]]}, handle, indent=2)
    handle.write("\n")
print(json.dumps({"Engine_jobs_passed": 6, "Engine_steps_passed": 64, "Phoenix_failed": 6, "GA_verified": 0}))
