"""Accept the independently reviewed socket-free ordinary lifecycle slice only."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
DEST = OUT / "key-owner-lifecycle-acceptance.json"

def read(path):
    return json.loads(path.read_bytes())

def row(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}

def seal(path, digest):
    assert row(path)["sha256"] == digest
    value = read(path)
    members = value.get("members", value.get("files"))
    for expected in members:
        actual = row(path.parent / expected["path"])
        assert actual["bytes"] == expected["bytes"] and actual["sha256"] == expected["sha256"]
    return len(members)

assert not DEST.exists(), "One-shot; do not replay"
lane = ROOT / "verification/console-key-owner-lifecycle-implementation"
prepared = lane / "prepared-3"
execution = lane / "executions/candidate-3"
review = ROOT / "verification/console-key-owner-lifecycle-independent/terminal-review-3/review-seal.json"
assert seal(prepared / "freeze.json", "fc4f644bccc627470bdb027a65d2e4d80cde51ca32c684b23a85fd6c1e80e307") == 253
assert seal(review, "0db8ab61df2215357b04f3f63a92f4b53561715f1184841c1e2c1a14fd1e8d68") == 3
plan = read(prepared / "execution-plan.json")
assert row(prepared / "execution-plan.json")["sha256"] == "80d718131fd6b0ba48d6c7e4b9a6eb7c9d704eee95f4b91555a82dc944acd4fd"
for expected in plan["canonical_inputs"]:
    actual = row(ROOT / expected["path"])
    assert actual["bytes"] == expected["bytes"] and actual["sha256"] == expected["sha256"]
receipt = read(execution / "receipt.json")
observations = read(execution / "observations.json")
assert receipt["status"] == "passed" and not receipt["errors"] and not receipt["cleanup_errors"]
assert not receipt["observed_signals_at_cutoff"]
assert observations["scratch_removed"] and observations["all_original_pins_rechecked"]
assert not observations["original_changes"] and not observations["cleanup_errors"]
assert len(observations["owned_processes"]) == 2
assert all(p["direct_child_reaped"] and p["group_absent"] for p in observations["owned_processes"])
assert all(p["returncode"] == 0 for p in observations["phases"])
artifacts = observations["artifacts"]
assert len(artifacts) == 13
assert artifacts["corrected/exunit-result.json"] == {"total": 7, "failures": 0, "skipped": 0, "excluded": 0}
assert all(v is True for v in artifacts["original/original-regression.json"].values())
assert "FORMAT CHECK 3 authored canonical files; unchanged=3" in (execution / "corrected/stdout.txt").read_text()
assert read(lane / "executions/candidate-2/receipt.json")["status"] == "failed"
canonical = ["hosted/lib/mixer_hosted/identity/admission.ex", "hosted/lib/mixer_hosted/identity/key_owner.ex",
             "hosted/test/mixer_hosted/identity/key_owner_lifecycle_test.exs"]
info = {
    "status": "accepted-bounded-socket-free-ordinary-supervised-lifecycle",
    "accepted_scope": "KOL01-KOL07 for serial atom-registered ordinary KeyOwnerSupervisor and Admission with disabled profiles",
    "selected_changes": ["Trap parent exit before Admission publication so normal supervisor shutdown invokes termination",
                         "Close only the current published table while its ETS creator is the caller"],
    "atomic_compare_and_erase_claim": False,
    "canonical_sources": [row(ROOT / p) for p in canonical],
    "prepared_plan": row(prepared / "execution-plan.json"), "prepared_seal": row(prepared / "freeze.json"),
    "prepared_members_verified": 253, "canonical_inputs_verified": len(plan["canonical_inputs"]),
    "root_release": row(OUT / "key-owner-lifecycle-candidate-3-release.json"),
    "independent_terminal_review": row(review),
    "execution_members": [row(p) for p in sorted(execution.rglob("*")) if p.is_file()],
    "runtime": artifacts["corrected/runtime.json"],
    "original_defect_reproduced": True, "corrected_tests": artifacts["corrected/exunit-result.json"],
    "compiled_identity_modules_per_phase": 19, "compile_warnings": 0, "formatting_files_passed": 3,
    "elapsed_seconds": observations["elapsed_seconds"], "cleanup": observations["owned_processes"],
    "scratch_removed": True, "all_source_tool_posthashes_passed": True,
    "prior_failed_formatting_run": row(OUT / "key-owner-lifecycle-candidate-2-terminal.json"),
    "independent_runtime_replay_claim": False, "delivery_pending": True,
    "pending": ["KOL08 active TLS flight drain and KOL09 active-flight worker-supervisor death",
                "Application/provider/HTTP/browser/session integration and production operation",
                "Paused native/device checks and every GA gate"],
    "GA_accepted": False}
w = read(ROOT / "work-graph.json")
g = read(ROOT / "gates/ga.json")
assert w["packages"][13]["fixedWorkspaceDispatcher"] == g["gates"][21]["fixedWorkspaceDispatcher"]
state = w["packages"][13]["fixedWorkspaceDispatcher"]["key_owner_supervised_lifecycle"]
state.update({"status": info["status"], "acceptance": copy.deepcopy(info), "runtime_released": False,
              "product_implementation_accepted": True, "pending": info["pending"]})
g["gates"][21]["fixedWorkspaceDispatcher"] = copy.deepcopy(w["packages"][13]["fixedWorkspaceDispatcher"])
old = "The ordinary identity-owner correction now reproduces the original graceful-stop defect and passes seven socket-free lifecycle tests with zero warnings or skips, but its first complete host qualification fails formatting. Both VMs are reaped, their groups are absent and scratch is removed. A separate formatting correction and reviewed rerun remain required before implementation acceptance. Real in-flight TLS drain, worker-supervisor fault and application/provider integration retain separate scope."
new = "The ordinary identity-owner correction now has independently reviewed host acceptance for seven socket-free lifecycle cases: normal supervisor shutdown clears its Admission pointer, and close requires the current table and its creator. The original defect reproduces; all seven corrected tests, zero-warning compilation and three formatting checks pass. Both VMs and scratch are cleaned up. The earlier formatting failure is preserved. Active TLS drain, worker-supervisor faults with active flights and application/provider integration remain pending."
for name in ["PLAN.md", "STATUS.md"]:
    path = ROOT / name
    text = path.read_text()
    assert text.count(old) == 1
    path.write_text(text.replace(old, new))
for name, value in [("work-graph.json", w), ("gates/ga.json", g)]:
    (ROOT / name).write_text(json.dumps(value, indent=2) + "\n")
assert sum(t["status"] == "running" for t in g["gates"]) == 8
assert sum(t["status"] == "planned" for t in g["gates"]) == 30
with DEST.open("x") as handle:
    json.dump({"schema": 1, "at": datetime.now(timezone.utc).isoformat(), "acceptance": info,
               "GA_verified": 0, "metadata_files": [row(ROOT / n) for n in ["PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"]]}, handle, indent=2)
    handle.write("\n")
print(json.dumps({"accepted": "socket-free KOL01-KOL07", "tests_passed": 7, "GA_verified": 0}))
