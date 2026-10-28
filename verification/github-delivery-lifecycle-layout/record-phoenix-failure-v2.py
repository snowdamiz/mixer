"""Preserve the remote fixture teardown failures and pending correction."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
DEST = OUT / "phoenix-failure.json"

def read(path):
    return json.loads(path.read_bytes())

def row(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

assert not DEST.exists(), "One-shot; do not replay"
job = read(OUT / "ci-jobs-3.stdout")
assert job["headSha"] == "fd92138ac0b8c4ecd0d872a9050204da5ceb5d2f"
assert job["status"] == "completed" and job["conclusion"] == "failure" and job["attempt"] == 1
remote = OUT / "phoenix-remote-artifact"
r = read(remote / "receipt.json")
assert r["status"] == "failed" and r["cleanup"] == {"postgres_stopped": True, "scratch_removed": True}
assert (remote / "revision.log").read_text().strip() == job["headSha"]
assert (remote / "format.log").stat().st_size == 0
assert (remote / "compile.log").read_text().strip() == "Compiling 95 files (.ex)\nGenerated mixer_hosted app"
test_log = (remote / "tests.log").read_text()
assert "Result: 684/690 passed, 2 skipped" in test_log and "Failed: 6 tests" in test_log
failures = re.findall(r"^\s*\d+\) test (.+) \(MixerHosted.Identity.KeyOwnerTest\)$", test_log, re.MULTILINE)
assert len(failures) == 6
canonical = ["hosted/lib/mixer_hosted/identity/admission.ex", "hosted/lib/mixer_hosted/identity/key_owner.ex",
             "hosted/test/mixer_hosted/identity/key_owner_lifecycle_test.exs"]
for path in canonical:
    assert r["inputs"][path] == row(ROOT / path)["sha256"]
info = {"status": "Phoenix-failed-six-existing-fixture-teardown-races-Engine-pending",
        "workflow": {k: job[k] for k in ["databaseId", "headSha", "status", "conclusion", "attempt", "url"]},
        "workflow_steps": len(job["jobs"][0]["steps"]), "job_observation": row(OUT / "ci-jobs-3.stdout"),
        "artifact_selection": row(OUT / "artifact-selection.json"), "remote_receipt": row(remote / "receipt.json"),
        "remote_test_log": row(remote / "tests.log"), "source_hashes_match": canonical,
        "passed": 684, "failed": 6, "existing_skipped": 2, "failure_cases": failures,
        "all_seven_new_lifecycle_cases_passed": True, "format_and_compile_passed": True,
        "cleanup": r["cleanup"], "correction_lane": "verification/console-key-owner-fixture-cleanup-ci-correction",
        "diagnosis": "Existing direct-linked fixture owner races its test-parent shutdown against on_exit GenServer.stop after trap_exit is enabled. Explicit test-supervisor ownership is selected for correction; no production behavior is relaxed.",
        "local_broad_harness_replay_authorized": False, "GA_accepted": False}
w = read(ROOT / "work-graph.json")
g = read(ROOT / "gates/ga.json")
for target in [w["packages"][13], g["gates"][21]]:
    delivery = target["fixedWorkspaceDispatcher"]["key_owner_supervised_lifecycle"]["acceptance"]["delivery"]
    delivery.update({"status": info["status"], "phoenix_terminal": copy.deepcopy(info)})
c = w["packages"][7]["fixtureCacheStateContractCandidate"]
assert c == g["gates"][1]["fixtureCacheStateContractCandidate"]
b = c["scalar_cursor_host_acceptance"]["real_profile_adapter_preparation"]["next_header_preparation"]["retained_profile_composition_preparation"]["real_binding_preparation"]["real_profile_loader_binding"]["next_adoption_lane"]["guarded_snapshot_export_contract_review"]["composition_source_preparation"]["bootstrap_host_boundary"]
b["actual_owner_Rust_selection"]["correction"]["IR02_source_repair"]["work_storage_delta"]["layout_probe"]["retrospective_layout_observation_acceptance"]["delivery"].update({"status": info["status"], "phoenix_terminal": copy.deepcopy(info)})
g["gates"][1]["fixtureCacheStateContractCandidate"] = copy.deepcopy(c)
old = "Checkpoint `fd92138a` is pushed with 1,559 selected paths: the supervised identity-owner cleanup fix, seven ordinary lifecycle tests, and independently checked diagnostic layout observations. Engine and Phoenix CI are running. Active in-flight lifecycle and accounting work were excluded; the exact historical failures and evidence remain preserved."
new = "Checkpoint `fd92138a` is pushed with 1,559 selected paths: the supervised identity-owner cleanup fix, seven ordinary lifecycle tests, and independently checked diagnostic layout observations. Phoenix compilation and formatting pass, but six existing KeyOwnerTest teardown callbacks fail; 684 tests pass, including all seven new lifecycle cases, and two existing tests are skipped. PostgreSQL and scratch cleanup complete. An explicit fixture-ownership correction is in preparation; Engine CI is still running. Active in-flight lifecycle and accounting work were excluded from this checkpoint."
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
print(json.dumps({"Phoenix_passed": 684, "failed_teardowns": 6, "skipped": 2, "cleanup": r["cleanup"]}))
