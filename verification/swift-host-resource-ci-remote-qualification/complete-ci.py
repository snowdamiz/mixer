"""Record the retained terminal workflow result without rerunning any job."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = "verification/github-delivery-host-ci-directory-fix/ci-jobs-5.stdout"
raw = (ROOT / evidence).read_bytes()
data = json.loads(raw)
assert data["headSha"] == "975b2e3ef25255a882e7476780caa2e844ce928d"
assert data["databaseId"] == 40514213881 and data["attempt"] == 1
assert data["status"] == "completed" and data["conclusion"] == "success"
assert len(data["jobs"]) == 6
assert all(j["status"] == "completed" and j["conclusion"] == "success" for j in data["jobs"])
steps = [s for j in data["jobs"] for s in j["steps"]]
assert len(steps) == 64 and all(s["conclusion"] == "success" for s in steps)
path = "verification/github-delivery-host-ci-directory-fix/terminal-ci-status.json"
receipt = {
    "schema": 1, "at": datetime.now(timezone.utc).isoformat(),
    "run": data["databaseId"], "attempt": 1, "commit": data["headSha"],
    "status": "completed", "conclusion": "success", "url": data["url"],
    "jobs_total": 6, "jobs_passed": 6, "steps_passed": 64,
    "evidence": evidence, "evidence_sha256": hashlib.sha256(raw).hexdigest(),
    "jobs": [{"name": j["name"], "status": j["status"], "conclusion": j["conclusion"]}
             for j in data["jobs"]],
    "remote_cache_qualification": "verification/swift-host-resource-ci-remote-qualification/qualification.json",
    "historical_failed_runs_preserved": True,
    "native_runtime_or_GA_accepted": False,
}
with (ROOT / path).open("x") as stream:
    json.dump(receipt, stream, indent=2)
    stream.write("\n")
sha = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
w = json.loads((ROOT / "work-graph.json").read_text())
g = json.loads((ROOT / "gates/ga.json").read_text())
c = w["packages"][7]["fixtureCacheStateContractCandidate"]
assert c == g["gates"][1]["fixtureCacheStateContractCandidate"]
c["guarded_snapshot_host_ci_directory_delivery"]["CI"].update({
    "status": "completed", "conclusion": "success", "terminal": True,
    "evidence": evidence, "jobs_passed": 6, "steps_passed": 64, "jobs_running": [],
    "terminal_receipt": path, "terminal_receipt_sha256": sha,
})
c["guarded_snapshot_host_ci_repair_delivery"]["followup_preparation_correction"]["full_followup_CI_pending"] = False
b = c["scalar_cursor_host_acceptance"]["real_profile_adapter_preparation"]["next_header_preparation"]["retained_profile_composition_preparation"]["real_binding_preparation"]["real_profile_loader_binding"]["next_adoption_lane"]["guarded_snapshot_export_contract_review"]["composition_source_preparation"]["bootstrap_host_boundary"]
b["string_provenance"].update({
    "status": "frozen-source-candidate-independent-review-active",
    "producer_seal_sha256": "b228f62a0751e6d1b45e27edabe500cc5e52449db1d33ee59abca0f695b6fa2f",
    "release": "verification/swift-semantic-adapter-root-review/guarded-snapshot-string-provenance-frozen-release.json",
    "independent_owner": "/root/swift_string_provenance_independent",
    "independent_ownership": "verification/swift-guarded-snapshot-string-provenance-independent",
    "candidate_L_str": 5080, "accepted": False,
})
g["gates"][1]["fixtureCacheStateContractCandidate"] = copy.deepcopy(c)
for name, value in (("work-graph.json", w), ("gates/ga.json", g)):
    (ROOT / name).write_text(json.dumps(value, indent=2) + "\n")
for name in ("PLAN.md", "STATUS.md"):
    text = (ROOT / name).read_text()
    old = "has four passing jobs and two Swift jobs running on attempt one; the Swift selection step passes."
    assert old in text
    text = text.replace(old, "passes all six jobs and 64 steps on attempt one, including the repaired Swift selection and cache fixture steps.", 1)
    text = text.replace("its full CI result is still pending.", "all six corrected-run jobs and 64 steps now pass.", 1)
    text = text.replace("Complete string provenance and compiled native-open correspondence are active.", "The string-provenance candidate is frozen for independent review; compiled native-open correspondence is active.", 1)
    (ROOT / name).write_text(text)
print(json.dumps({"terminal_receipt": path, "sha256": sha, "jobs": 6, "steps": 64, "native_or_GA": False}))
