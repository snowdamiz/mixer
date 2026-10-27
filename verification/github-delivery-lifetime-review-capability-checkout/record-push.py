"""Record the exact push and initial CI state without extending qualification."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DEST = OUT / "post-push-metadata.json"


def read(path):
    return json.loads(path.read_bytes())


def row(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


assert not DEST.exists(), "One-shot; do not replay"
r = read(OUT / "receipt.json")
assert r["commit"] == "6f116c6a41994fcab5fa0d203198dc139dae9829" and r["pushed"] and not r["force"]
assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, timeout=10).strip() == r["commit"]
runs = read(OUT / "ci-runs-1.stdout")
assert len(runs) == 2 and all(x["headSha"] == r["commit"] for x in runs)
delivery = {"status": "pushed-Engine-and-Phoenix-CI-pending", "commit": r["commit"], "tree": r["tree"],
            "changed_paths": r["committed_paths"], "canonical_paths": r["canonical_paths"],
            "receipt": row(OUT / "receipt.json"), "manifest": row(OUT / "manifest.json"),
            "initial_CI": row(OUT / "ci-runs-1.stdout"), "runs": runs, "pushed": True, "force": False,
            "active_authority_and_work_storage_lanes_excluded": True, "GA_accepted": False}
w = read(ROOT / "work-graph.json"); g = read(ROOT / "gates/ga.json")
for target in [w["packages"][7], g["gates"][1]]:
    target["capabilityHostSparseCheckout"].update({"delivery_pending": False, "delivery": copy.deepcopy(delivery)})
for target in [w["packages"][13], g["gates"][21]]:
    target["fixedWorkspaceDispatcher"]["format_correction"].update({"delivery_pending": False, "delivery": copy.deepcopy(delivery)})
    target["fixedWorkspaceDispatcher"]["default_authority_candidate"] = {
        "status": "source-only-preparation-runtime-not-released",
        "ownership": "verification/console-dispatcher-default-authority-slice",
        "independent_preaccess": "verification/console-dispatcher-authority-preaccess",
        "scope": "Actual default verifier and restricted default Repo via dedicated local identity TLS fixture and isolated database; ordinary private dispatch only",
        "candidate_1_runtime_started": False,
        "candidate_1_preexecution_cleanup_and_time_bound_corrections_pending": True,
        "actual_default_Repo_success_accepted": False, "GA_accepted": False}
c = w["packages"][7]["fixtureCacheStateContractCandidate"]
assert c == g["gates"][1]["fixtureCacheStateContractCandidate"]
b = c["scalar_cursor_host_acceptance"]["real_profile_adapter_preparation"]["next_header_preparation"]["retained_profile_composition_preparation"]["real_binding_preparation"]["real_profile_loader_binding"]["next_adoption_lane"]["guarded_snapshot_export_contract_review"]["composition_source_preparation"]["bootstrap_host_boundary"]
b["actual_owner_Rust_selection"]["correction"]["IR02_source_repair"]["scoped_source_review_delivery"] = copy.deepcopy(delivery)
g["gates"][1]["fixtureCacheStateContractCandidate"] = copy.deepcopy(c)
for name, data in [("work-graph.json", w), ("gates/ga.json", g)]:
    (ROOT / name).write_text(json.dumps(data, indent=2) + "\n")
for name in ["PLAN.md", "STATUS.md"]:
    path = ROOT / name; text = path.read_text()
    old = "The reviewed patch is applied locally. Delivery, remote checkout duration, dependency resolution and complete job outcomes remain pending."
    new = "The accepted checkout and dispatcher formatting correction are pushed as `6f116c6a` with 773 selected paths, including the frozen bounded IR02 repair/review. Engine and Phoenix CI are pending. Active default-authority and work/storage lanes are excluded; remote checkout duration, dependency resolution and complete job outcomes remain pending."
    assert text.count(old) == 1
    text = text.replace(old, new)
    old = "preserves all six parsed ASTs; delivery and new CI remain pending."
    new = "preserves all six parsed ASTs. The correction is pushed in `6f116c6a`; new CI remains pending."
    assert text.count(old) == 1
    path.write_text(text.replace(old, new))
assert w["packages"][4]["privateOwnerEffectContractCandidate"] == g["gates"][4]["privateOwnerEffectContractCandidate"]
assert sum(x["status"] == "running" for x in g["gates"]) == 8
assert sum(x["status"] == "planned" for x in g["gates"]) == 30
for path, digest in r["protected_work_unchanged"].items():
    assert row(ROOT / path)["sha256"] == digest
assert not subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=ROOT, timeout=10)
subprocess.run(["git", "diff", "--check", "--", "PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"], cwd=ROOT, check=True, timeout=10)
with DEST.open("x") as stream:
    json.dump({"schema": 1, "at": datetime.now(timezone.utc).isoformat(), "delivery": delivery,
               "metadata_files": [row(ROOT / name) for name in ["PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"]],
               "packages": 18, "gates": 38, "W08_G02_equal": True, "W05_G05_equal": True, "GA_verified": 0}, stream, indent=2)
    stream.write("\n")
print(json.dumps({"pushed": r["commit"], "changed_paths": r["committed_paths"], "CI_runs_pending": 2, "GA_verified": 0}))
