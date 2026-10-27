"""Accept only the reviewed accessible-result lifetime repair, retaining open gates."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DEST = OUT / "guarded-snapshot-root-result-lifetime-acceptance.json"
PRODUCER = ROOT / "verification/swift-guarded-snapshot-root-result-lifetime-implementation"
REVIEW = ROOT / "verification/swift-guarded-snapshot-root-result-lifetime-independent"
CI = ROOT / "verification/github-delivery-fixed-dispatcher-android-checkout"


def row(path):
    assert path.is_file() and not path.is_symlink()
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def read(path):
    return json.loads(path.read_bytes())


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


assert not DEST.exists(), "One-shot; do not replay"
packets = []
for directory, digest, count in [
    (PRODUCER, "7efe39286257be85d0e91f4bdd80b6098d24d7d2f446dcdc2e8dd7adb0159fa4", 336),
    (REVIEW, "dc67bbd36e630f23e3eba9b3068c0f0e0a52aba44d9ec21fb5ffb925e874b76c", 253),
]:
    seal_path = directory / "seal.json"
    assert row(seal_path)["sha256"] == digest
    seal = read(seal_path)
    names = {"seal.json"}
    for expected in seal["members"]:
        name = expected["path"]
        assert not Path(name).is_absolute() and ".." not in Path(name).parts and name not in names
        actual = row(directory / name)
        assert actual["bytes"] == expected["bytes"] and actual["sha256"] == expected["sha256"], name
        names.add(name)
    assert len(seal["members"]) == count
    assert names == {str(p.relative_to(directory)) for p in directory.rglob("*") if p.is_file()}
    packets.append({"directory": str(directory.relative_to(ROOT)), "seal": row(seal_path),
                    "members_verified": count, "member_bytes": sum(x["bytes"] for x in seal["members"])})
p = read(PRODUCER / "result.json"); r = read(REVIEW / "result.json")
assert p["host_passed_each"] == 38 and p["host_failed"] == 0 and p["negative_intended_boundaries"] == 18
assert p["compiler_commands"] == 21 and p["host_runs"] == 2 and p["retries"] == 0
assert r["disposition"] == "recommend-accept-selected-minimum-accessible-original-root-result-lifetime-source-slice"
assert not r["concrete_source_defects_found"]
assert r["passed_per_mode"] == 42 and r["independent_compiler_commands"] == 11
assert r["independent_semantic_negatives"] == 6 and r["host_runs"] == 2
assert r["new_host_tests"] == 4 and r["new_finite_host_subcases_per_mode"] == 22
for command in r["independent_commands"]:
    receipt = read(REVIEW / command["receipt"]["path"])
    assert receipt["success"] and receipt["child_reaped"] and receipt["exact_owned_group_absent"]
    assert receipt["postrun_pins_verified"] and command["owned_group_absent_rechecked"]
cleanup = read(REVIEW / "generated-artifact-cleanup.json")
assert cleanup["build_directory_empty"] and cleanup["all_13_owned_groups_rechecked_absent_before_removal"]
mir = read(REVIEW / "mir-evidence-review.json")
assert mir["contiguous_top_level_item_hashes_verified"] == 4237
assert mir["complete_decompressed_bytes"] == 84594785
assert len(mir["selected_complete_body_items"]) == 42
value = {"schema": 1, "at": datetime.now(timezone.utc).isoformat(),
         "command": [sys.executable, "-B", str(Path(__file__).relative_to(ROOT))], "python": sys.version,
         "status": "accepted-minimum-accessible-original-root-result-lifetime-source-slice-only",
         "packets": packets, "source146_tree": r["source146_tree_sha256"],
         "instrumented_test_tree": r["instrumented_test_only_source_tree_sha256"],
         "host11_tree": r["host11_tree_sha256"], "producer_result": row(PRODUCER / "result.json"),
         "independent_result": row(REVIEW / "result.json"), "independent_cleanup": row(REVIEW / "generated-artifact-cleanup.json"),
         "producer_host_methods_per_mode": 38, "producer_negative_compiler_probes": 18,
         "independent_host_methods_per_mode": 42, "fresh_independent_methods": 4,
         "fresh_independent_finite_subcases_per_mode": 22, "independent_negative_compiler_probes": 6,
         "accepted_scope": r["accepted_evidence_scope"], "private_boundary_limit": r["private_N12_N13"],
         "historical_signature_disposition": r["historical_signature"],
         "root_review": "Verified both complete packet seals and all command outcomes. Reviewed original-source lifetime propagation, short diagnostic views, fixed private consuming frame, child/root separation, exact independent positive and negative probes and raw semantic diagnostics. Complete production MIR is independently verified and 42 complete relevant bodies reviewed. Privacy/source closure is not an intrinsic lifetime guarantee for raw internal File payloads.",
         "producer_46_vector_loop_not_historical_460_rerun": True,
         "canonical_source_integrated": False, "root_runtime_replay": False,
         "full_ownership_or_durable_funding_accepted": False, "new_prices_or_layouts_accepted": False,
         "pending": r["still_pending"], "GA_accepted": False}
ci = read(CI / "ci-jobs-6.stdout")
assert ci["headSha"] == "d04fd5cc71bc72061f18203e414b90869129b4ca"
assert ci["databaseId"] == 40567963687 and ci["attempt"] == 1 and ci["conclusion"] == "success"
assert len(ci["jobs"]) == 6
steps = [s for j in ci["jobs"] for s in j["steps"]]
assert len(steps) == 64 and all(s["conclusion"] == "success" for s in steps)
terminal = {"schema": 1, "at": datetime.now(timezone.utc).isoformat(),
            "commit": ci["headSha"], "run_id": ci["databaseId"], "url": ci["url"], "attempt": 1,
            "conclusion": "success", "jobs_passed": 6, "steps_passed": 64, "steps_skipped": 0,
            "raw_observation": row(CI / "ci-jobs-6.stdout"),
            "scope": "Existing exact d04fd5cc Engine host checks, including accepted Android sparse checkout. New capability checkout and isolated IR02 source/review are excluded.",
            "native_or_GA_acceptance": False}
w = read(ROOT / "work-graph.json"); g = read(ROOT / "gates/ga.json")
c = w["packages"][7]["fixtureCacheStateContractCandidate"]
assert c == g["gates"][1]["fixtureCacheStateContractCandidate"]
assert w["packages"][4]["privateOwnerEffectContractCandidate"] == g["gates"][4]["privateOwnerEffectContractCandidate"]
b = c["scalar_cursor_host_acceptance"]["real_profile_adapter_preparation"]["next_header_preparation"]["retained_profile_composition_preparation"]["real_binding_preparation"]["real_profile_loader_binding"]["next_adoption_lane"]["guarded_snapshot_export_contract_review"]["composition_source_preparation"]["bootstrap_host_boundary"]
save(DEST, value); save(CI / "terminal-engine-attempt1.json", terminal)
correction = b["actual_owner_Rust_selection"]["correction"]
correction.update({"status": "IR01-retention-and-minimum-accessible-result-lifetime-accepted-full-ownership-pending",
                   "root_result_lifetime_accepted": True, "root_result_lifetime_accepted_scope": value["accepted_scope"],
                   "implementation_accepted": False})
repair = correction["IR02_source_repair"]
repair.update({"status": value["status"], "root_acceptance": row(DEST),
               "implementation_accepted": True, "accepted_scope": value["accepted_scope"],
               "independent_review_status": "accepted-bounded-source-compiler-and-generic-core-host-slice",
               "producer_host_methods_per_mode": 38, "independent_host_methods_per_mode": 42,
               "fresh_independent_methods": 4, "fresh_finite_subcases_per_mode": 22,
               "producer_result": value["producer_result"], "independent_result": value["independent_result"],
               "independent_execution_release": row(OUT / "guarded-snapshot-root-result-lifetime-independent-execution-release.json"),
               "canonical_source_integrated": False, "full_funding_or_ownership_accepted": False,
               "new_work_storage_delta_ownership": "verification/swift-root-bound-work-storage-delta",
               "new_work_storage_delta_status": "source-offline-preparation-only", "pending": value["pending"]})
correction["scoped_review_delivery"].update({"status": "pushed-Engine-passed-Phoenix-format-failed",
    "terminal_Engine": row(CI / "terminal-engine-attempt1.json"),
    "terminal_Phoenix": row(CI / "terminal-phoenix-format-failure.json")})
g["gates"][1]["fixtureCacheStateContractCandidate"] = copy.deepcopy(c)
for target, key in [(w["packages"][13], "fixedWorkspaceDispatcher"), (g["gates"][21], "fixedWorkspaceDispatcher"),
                    (w["packages"][4], "ownerHostSparseCheckout"), (g["gates"][4], "ownerHostSparseCheckout")]:
    target[key]["delivery"].update({"status": "pushed-Engine-passed-Phoenix-format-failed",
                                   "terminal_Engine": row(CI / "terminal-engine-attempt1.json")})
for name, data in [("work-graph.json", w), ("gates/ga.json", g)]:
    (ROOT / name).write_text(json.dumps(data, indent=2) + "\n")
for name in ["PLAN.md", "STATUS.md"]:
    path = ROOT / name; text = path.read_text()
    old = "full Engine remains pending. Phoenix fails its formatter gate"
    assert text.count(old) == 1
    text = text.replace(old, "Engine passes all six jobs and 64 steps on attempt one without skips. Phoenix fails its formatter gate")
    old = "A separate IR02 finding shows owned results can outlive the original ledger; current outer-caller order is safe, but full root/result lifetime remains unproved."
    assert text.count(old) == 1
    text = text.replace(old, "A separate IR02 review found that the prior owned results could outlive the original ledger, despite safe current outer-caller ordering.")
    old = "The isolated two-file source is frozen and its exact 21 compiler, two filtered host and one version commands are released under a hardened bounded runner. Fresh independent source review is active; compiler/host results and implementation acceptance remain pending."
    new = "The isolated two-file repair now has bounded accessible-result lifetime acceptance: producer checks pass 38 host methods in each mode and eighteen intended compiler refusals; independent checks pass 42 methods in each mode, with four fresh methods / 22 finite subcases and six semantic compiler refusals. Two positive companions compile, and the historical signature correctly inherits the original root through lifetime elision. The independent reviewer verifies all 4,237 complete MIR items and reviews 42 relevant complete bodies; root verifies all 589 producer/reviewer packet members. Generated compiler outputs are removed. Canonical integration, actual File/VM leaf execution and full ownership remain pending. New work/storage accounting is being prepared offline."
    assert text.count(old) == 1
    path.write_text(text.replace(old, new))
assert sum(x["status"] == "running" for x in g["gates"]) == 8
assert sum(x["status"] == "planned" for x in g["gates"]) == 30
subprocess.run(["git", "diff", "--check", "--", "PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"], cwd=ROOT, check=True, timeout=10)
print(json.dumps({"minimum_accessible_result_lifetime_accepted": True, "packet_members": 589,
                  "producer_per_mode": 38, "independent_per_mode": 42, "Engine_jobs_passed": 6,
                  "full_ownership_or_GA_accepted": False}))
