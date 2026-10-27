"""Remove exact owned build/copied inputs and record returned review scope."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE / "witness-source"
BUILD = HERE / "witness-build"
def sha(data):
    return hashlib.sha256(data).hexdigest()
manifest = json.loads((HERE / "witness-source-manifest.json").read_bytes())
removed = []
preserve = "vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs"
for entry in manifest["after"]:
    path = WORK / entry["path"]
    data = path.read_bytes()
    assert len(data) == entry["bytes"] and sha(data) == entry["sha256"]
    if entry["path"] != preserve:
        removed.append({**entry, "path": "witness-source/" + entry["path"]})
        path.unlink()
assert len(removed) == 156
run_plan = json.loads((HERE / "commands/witness-run-001/plan.json").read_bytes())
for path in sorted(BUILD.rglob("*")):
    if path.is_file():
        data = path.read_bytes()
        entry = {"path": str(path.relative_to(HERE)), "bytes": len(data), "sha256": sha(data)}
        if path.name == "independent-tests-debug":
            assert entry["sha256"] == run_plan["tool_sha256"]
        removed.append(entry)
        path.unlink()
for base in (WORK, BUILD):
    for path in sorted((p for p in base.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        if not any(path.iterdir()):
            path.rmdir()
    if not any(base.iterdir()):
        base.rmdir()
commands = []
for name in ("preparation-001", "source-mir-001", "prepare-witness-001", "witness-build-001", "witness-run-001"):
    receipt = json.loads((HERE / "commands" / name / "receipt.json").read_bytes())
    assert receipt["waited"] and receipt["owned_process_group_absent"]
    commands.append({"name": name, "pid": receipt["pid"], "pgid": receipt["pgid"], "waited": True, "group_absent_at_terminal_receipt": True, "exit_code": receipt["exit_code"]})
assert not BUILD.exists()
assert [p for p in WORK.rglob("*") if p.is_file()] == [WORK / preserve]
result = {"schema": 1, "status": "owned-build-products-and-156-unchanged-source-copies-removed", "removed": removed, "retained_injected_source": {"path": "witness-source/" + preserve, "sha256": sha((WORK / preserve).read_bytes())}, "commands": commands, "compiler_lane_released": True, "further_compiler_or_test_runs": 0, "native_or_UI_processes_started": False, "global_process_inventory": False}
(HERE / "cleanup.json").write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
disposition = {"schema": 1, "status": "return-for-required-IR01-correction", "candidate_accepted": False, "IR01_desired_property_passed": False, "independent_fresh_Debug_builds": 1, "independent_exact_host_runs": 1, "fresh_full_matrix": False, "preaccess_vector_matrix": "not run against this returned candidate", "H09_H10": "corrections confirmed by source and retained producer evidence; no fresh independent full replay", "compiler_subcases": "see compiler-coverage-review.json", "scope": "actual copied host/source/generic core only; current concrete File release path remains fail closed", "native_FieldLog_OTA_GA": "Pending"}
(HERE / "disposition.json").write_text(json.dumps(disposition, indent=2, sort_keys=True)+"\n")
print(json.dumps({"removed_files": len(removed), "commands_terminal": len(commands), "retained_witness": preserve, "candidate_accepted": False, "IR01": "required correction"}, sort_keys=True))
