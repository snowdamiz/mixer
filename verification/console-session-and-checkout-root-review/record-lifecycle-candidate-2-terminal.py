"""Record the failed formatting qualification without converting tests into acceptance."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
DEST = OUT / "key-owner-lifecycle-candidate-2-terminal.json"

def read(path):
    return json.loads(path.read_bytes())

def row(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}

assert not DEST.exists(), "One-shot; do not replay"
lane = ROOT / "verification/console-key-owner-lifecycle-implementation"
execution = lane / "executions/candidate-2"
receipt = read(execution / "receipt.json")
observations = read(execution / "observations.json")
assert receipt["status"] == "failed"
assert receipt["errors"] == ["RuntimeError: phase failed: corrected"]
assert not receipt["cleanup_errors"] and not receipt["observed_signals_at_cutoff"]
assert observations["phases"] == [
    {"id": "original", "returncode": 0, "output_bytes": 134},
    {"id": "corrected", "returncode": 1, "output_bytes": 603}]
assert observations["scratch_removed"] and observations["all_original_pins_rechecked"]
assert not observations["original_changes"] and not observations["cleanup_errors"]
assert len(observations["owned_processes"]) == 2
assert all(p["direct_child_reaped"] and p["group_absent"] for p in observations["owned_processes"])
artifacts = observations["artifacts"]
assert len(artifacts) == 13
assert artifacts["corrected/exunit-result.json"] == {"total": 7, "failures": 0, "skipped": 0, "excluded": 0}
assert all(v is True for v in artifacts["original/original-regression.json"].values())
assert "read-only formatting equality failed: hosted/lib/mixer_hosted/identity/admission.ex" in (execution / "corrected/stdout.txt").read_text()
info = {
    "status": "original-defect-reproduced-seven-tests-pass-formatting-failed",
    "plan": row(lane / "prepared-2/execution-plan.json"),
    "release": row(OUT / "key-owner-lifecycle-candidate-2-release.json"),
    "review": row(ROOT / "verification/console-key-owner-lifecycle-independent/review-2/review-seal.json"),
    "receipt": row(execution / "receipt.json"),
    "execution_members": [row(p) for p in sorted(execution.rglob("*")) if p.is_file()],
    "original_defect_reproduced": True,
    "corrected_tests": artifacts["corrected/exunit-result.json"],
    "compiled_identity_modules_per_phase": 19,
    "compile_warnings": 0,
    "formatting_qualification_passed": False,
    "cleanup": observations["owned_processes"],
    "scratch_removed": True,
    "all_original_source_tool_pins_rechecked": True,
    "elapsed_seconds": observations["elapsed_seconds"],
    "product_implementation_accepted": False,
    "next": "One formatting-only pass then separate frozen prepared-3 review and root release; no candidate-2 replay",
    "scope": receipt["scope"]}
w = read(ROOT / "work-graph.json")
g = read(ROOT / "gates/ga.json")
assert w["packages"][13]["fixedWorkspaceDispatcher"] == g["gates"][21]["fixedWorkspaceDispatcher"]
state = w["packages"][13]["fixedWorkspaceDispatcher"]["key_owner_supervised_lifecycle"]
state.update({"status": info["status"], "candidate_2_terminal": copy.deepcopy(info),
              "runtime_released": False, "product_implementation_accepted": False,
              "pending": ["Formatting correction and separately reviewed host execution",
                          "KOL08/KOL09 real flight and TLS drain including worker-supervisor death",
                          "Application/provider/HTTP/browser/session/operational/GA qualification"]})
g["gates"][21]["fixedWorkspaceDispatcher"] = copy.deepcopy(w["packages"][13]["fixedWorkspaceDispatcher"])
old = "The next ordinary identity-owner slice selects graceful supervised Admission cleanup with an expected-table/creator guard and seven socket-free lifecycle cases; implementation and runtime acceptance remain pending. Existing forced-death denial and real TLS drain retain separate scope."
new = "The ordinary identity-owner correction now reproduces the original graceful-stop defect and passes seven socket-free lifecycle tests with zero warnings or skips, but its first complete host qualification fails formatting. Both VMs are reaped, their groups are absent and scratch is removed. A separate formatting correction and reviewed rerun remain required before implementation acceptance. Real in-flight TLS drain, worker-supervisor fault and application/provider integration retain separate scope."
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
    json.dump({"schema": 1, "at": datetime.now(timezone.utc).isoformat(),
               "terminal": info, "GA_verified": 0,
               "metadata_files": [row(ROOT / n) for n in ["PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"]]}, handle, indent=2)
    handle.write("\n")
print(json.dumps({"tests_passed": 7, "formatting_passed": False, "cleanup_complete": True, "GA_verified": 0}))
