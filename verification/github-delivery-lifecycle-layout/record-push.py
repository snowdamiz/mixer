"""Record the exact delivered checkpoint and initial CI, preserving scoped gates."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
DEST = OUT / "post-push-metadata.json"

def read(path):
    return json.loads(path.read_bytes())

def row(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

assert not DEST.exists(), "One-shot; do not replay"
r = read(OUT / "receipt.json")
assert r["commit"] == "fd92138ac0b8c4ecd0d872a9050204da5ceb5d2f" and r["pushed"] and not r["force"]
assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, timeout=10).strip() == r["commit"]
runs = read(OUT / "ci-runs-1.stdout")
assert len(runs) == 2 and all(x["headSha"] == r["commit"] for x in runs)
d = {"status": "pushed-Engine-and-Phoenix-CI-pending", "commit": r["commit"], "tree": r["tree"],
     "changed_paths": r["committed_paths"], "canonical_paths": r["canonical_paths"],
     "receipt": row(OUT / "receipt.json"), "manifest": r["manifest"], "initial_CI": row(OUT / "ci-runs-1.stdout"),
     "runs": runs, "pushed": True, "force": False, "active_inflight_lifecycle_and_accounting_join_lanes_excluded": True,
     "GA_accepted": False}
w = read(ROOT / "work-graph.json")
g = read(ROOT / "gates/ga.json")
assert w["packages"][13]["fixedWorkspaceDispatcher"] == g["gates"][21]["fixedWorkspaceDispatcher"]
for target in [w["packages"][13], g["gates"][21]]:
    target["fixedWorkspaceDispatcher"]["key_owner_supervised_lifecycle"]["acceptance"].update({"delivery_pending": False, "delivery": copy.deepcopy(d)})
c = w["packages"][7]["fixtureCacheStateContractCandidate"]
assert c == g["gates"][1]["fixtureCacheStateContractCandidate"]
b = c["scalar_cursor_host_acceptance"]["real_profile_adapter_preparation"]["next_header_preparation"]["retained_profile_composition_preparation"]["real_binding_preparation"]["real_profile_loader_binding"]["next_adoption_lane"]["guarded_snapshot_export_contract_review"]["composition_source_preparation"]["bootstrap_host_boundary"]
b["actual_owner_Rust_selection"]["correction"]["IR02_source_repair"]["work_storage_delta"]["layout_probe"]["retrospective_layout_observation_acceptance"].update({"delivery_pending": False, "delivery": copy.deepcopy(d)})
g["gates"][1]["fixtureCacheStateContractCandidate"] = copy.deepcopy(c)
paragraph = "Checkpoint `fd92138a` is pushed with 1,559 selected paths: the supervised identity-owner cleanup fix, seven ordinary lifecycle tests, and independently checked diagnostic layout observations. Engine and Phoenix CI are running. Active in-flight lifecycle and accounting work were excluded; the exact historical failures and evidence remain preserved."
for name in ["PLAN.md", "STATUS.md"]:
    path = ROOT / name
    text = path.read_text()
    assert paragraph not in text
    if name == "PLAN.md":
        marker = "## Resumed checkpoint\n\n"
        assert text.count(marker) == 1
        text = text.replace(marker, marker + paragraph + "\n\n", 1)
    else:
        pos = text.index("\n\n") + 2
        text = text[:pos] + paragraph + "\n\n" + text[pos:]
    path.write_text(text)
for name, value in [("work-graph.json", w), ("gates/ga.json", g)]:
    (ROOT / name).write_text(json.dumps(value, indent=2) + "\n")
assert w["packages"][13]["fixedWorkspaceDispatcher"] == g["gates"][21]["fixedWorkspaceDispatcher"]
assert w["packages"][4]["privateOwnerEffectContractCandidate"] == g["gates"][4]["privateOwnerEffectContractCandidate"]
assert sum(x["status"] == "running" for x in g["gates"]) == 8
assert sum(x["status"] == "planned" for x in g["gates"]) == 30
for path, digest in r["protected_work_unchanged"].items():
    assert row(ROOT / path)["sha256"] == digest
assert not subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=ROOT, timeout=10)
subprocess.run(["git", "diff", "--check", "--", *["PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"]], cwd=ROOT, check=True, timeout=10)
with DEST.open("x") as handle:
    json.dump({"schema": 1, "at": datetime.now(timezone.utc).isoformat(), "delivery": d,
               "metadata_files": [row(ROOT / n) for n in ["PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"]],
               "packages": 18, "gates": 38, "GA_verified": 0}, handle, indent=2)
    handle.write("\n")
print(json.dumps({"pushed": r["commit"], "paths": r["committed_paths"], "CI_pending": 2, "GA_verified": 0}))
