"""One-shot root selection of the reviewed source146 interface amendment."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SOURCE = "690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185"
HOST = "027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2"

def read(path):
    return json.loads((ROOT / path).read_text())

def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()

def write_new(path, value):
    with (ROOT / path).open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")

def packet(name, expected):
    path = "verification/" + name
    assert digest(path + "/seal.json") == expected
    seal = read(path + "/seal.json")
    names = set()
    total = 0
    for row in seal["members"]:
        relative = Path(row["path"])
        assert not relative.is_absolute() and ".." not in relative.parts
        assert row["path"] not in names
        names.add(row["path"])
        member = ROOT / path / relative
        assert member.is_file() and not member.is_symlink()
        data = member.read_bytes()
        assert len(data) == row["bytes"]
        assert hashlib.sha256(data).hexdigest() == row["sha256"]
        total += len(data)
    actual = {str(p.relative_to(ROOT / path)) for p in (ROOT / path).rglob("*")
              if p.is_file() and p.name != "seal.json"}
    assert actual == names
    assert len(names) == seal["member_count"] and total == seal["bytes"]
    return {"path": path, "seal_sha256": expected, "members": len(names), "bytes": total}

prefix = "verification/swift-semantic-adapter-root-review/"
amendment_path = prefix + "guarded-snapshot-remaining-work-contract-amendment.json"
acceptance_path = prefix + "guarded-snapshot-remaining-work-host-acceptance.json"
terminal_path = "verification/github-delivery-host-ci-repairs/terminal-ci-status.json"
for path in (amendment_path, acceptance_path, terminal_path):
    assert not (ROOT / path).exists(), "completed selection must not be replayed"

producer = packet("swift-guarded-snapshot-remaining-work-interfaces",
                  "e644f57466368837445abd57506edeab9ab87135571b354be4ee772e31ddf23a")
independent = packet("swift-guarded-snapshot-remaining-work-independent",
                     "a0b564bca8d18d8e13ed861120e2720b14628265986b11cac02a4b203af39ec8")
proposal_path = producer["path"] + "/amendment-proposal.json"
review_path = independent["path"] + "/review.json"
assert digest(proposal_path) == "27bc104ac566d848a4054531e7cd90d4868a76a521b5c835650bab0595017489"
assert digest(review_path) == "28e02bc3bee200e8654237e2b6a1205dc4f588bc0326ebc44b21b85d3b56c7eb"
proposal, review = read(proposal_path), read(review_path)
assert proposal["source_tree_sha256"] == review["source_tree_sha256"] == SOURCE
assert proposal["host_tree_sha256"] == review["host_tree_sha256"] == HOST
assert review["no_blocking_findings"] and review["assertions"] == 3374
assert len(proposal["exact_proposed_symbol_scope"]) == 14
assert len(set(proposal["exact_proposed_symbol_scope"])) == 14
assert len(proposal["callee_boundary_rows"]) == 12
assert len(proposal["whole_leaf_boundary_rows"]) == 2
allocations = proposal["constructor_allocation_requests"]
assert [x["max_requested_bytes"] for x in allocations] == [8704, 1024, 16384, 192, 28672]
for row in allocations:
    assert row["max_calls"] == row["logical_interface_events"] == 1
    assert sum(row["native_fields"].values()) == 80
    assert row["supplement"] == row["max_requested_bytes"] + 81
supplement = sum(row["supplement"] for row in allocations)
assert supplement == proposal["constructor_allocation_supplement"] == review["constructor_supplement"] == 55381
assert review["conditional_fixed"] == 895084428322997895 + supplement
assert review["candidate_unresolved"] == len(review["candidate_expression"]["terms"]) == 12
assert review["accepted_only_unresolved"] == 26 and review["original_symbols"] == 35
assert proposal["logical_atomic_callback"]["pure"]
assert proposal["logical_atomic_callback"]["count"] == 1
assert not proposal["logical_atomic_callback"]["dynamic_retry_or_CPU_claim"]
assert not proposal["frozen_35_symbol_interface_rewritten"]

now = datetime.now(timezone.utc).isoformat()
amendment = {
    "schema": 1, "at": now,
    "status": "root-selected-source146-fourteen-logical-interface-clarifications",
    "source_tree_sha256": SOURCE, "host_tree_sha256": HOST,
    "proposal": proposal_path, "proposal_sha256": digest(proposal_path),
    "independent_review": review_path, "independent_review_sha256": digest(review_path),
    "exact_symbol_scope": proposal["exact_proposed_symbol_scope"],
    "earlier_nine_amendment_sha256": proposal["selected_nine_receipt_sha256"],
    "unit": proposal["unit"], "outside_unit": proposal["outside_unit"],
    "constructor_request_supplement": supplement, "supplement_occurrences": 1,
    "supplement_phase": "P4", "requested_backing_bytes": 54976,
    "allocation_requests": allocations,
    "logical_atomic_callback": proposal["logical_atomic_callback"],
    "selection": "The exact fourteen interfaces are covered by their retained authored events, scalar/native operands, callback multiplicities, imported typed payload/resource frontiers and the separate five constructor requests. No arbitrary private zero/one price, aggregate product credit, subtraction or physical implementation bound is selected.",
    "phase_qualification": "Exact positive SnapshotAdoptionV1 policy only: generic ordinary-zero-policy bb20 is unreachable; shared bb3/bb69 remain conservatively double charged. Before-store normalization removes only the generic Copy Result destructor adapter, retaining authored operations/native roles and every owned frontier.",
    "candidate_expression": review["candidate_expression"],
    "remaining_inputs": 12,
    "frozen_35_symbol_model_rewritten": False,
    "new_outer_parent_tree_rebound": False,
    "complete_source_binary_correspondence": False,
    "actual_root_policy_or_grant": False, "native_runtime_or_GA": False,
    "limits": review["limits"],
}
write_new(amendment_path, amendment)
acceptance = {
    "schema": 1, "at": now,
    "status": "bounded-source146-remaining-work-interface-host-acceptance",
    "producer": producer, "independent": independent,
    "independent_assertions": 3374, "independent_input_files_rehashed": 425,
    "independent_control_methods": 6, "independent_adverse_cases": 366,
    "producer_reproduction": review["producer_claims_reproduced_by_separate_command"],
    "amendment": amendment_path, "amendment_sha256": digest(amendment_path),
    "selected_clarifications": 14, "conditional_fixed_work": review["conditional_fixed"],
    "remaining_external_inputs": 12,
    "constructor_supplement_once_P4": supplement,
    "original_failures_preserved": True,
    "independent_failed_checker_attempts": 5,
    "independent_exploratory_read_failures": 3,
    "root_validation": "Complete exact producer and independent seals rehashed; exact proposal/review source bindings, all five request equations and composed fixed arithmetic independently checked.",
    "source_tree_sha256": SOURCE, "host_tree_sha256": HOST,
    "limits": review["limits"],
    "whole_host_bound_or_operational_grant": False, "native_runtime_or_GA": False,
}
write_new(acceptance_path, acceptance)

old_path = "verification/github-delivery-host-ci-repairs/ci-jobs-4.stdout"
old = read(old_path)
assert old["headSha"] == "37804cf297b0fb5881ef25986a53aaa2cfe01bff"
assert old["status"] == "completed" and old["conclusion"] == "failure"
assert len(old["jobs"]) == 6 and sum(j["conclusion"] == "success" for j in old["jobs"]) == 5
terminal = {
    "schema": 1, "at": now, "run": old["databaseId"], "attempt": old["attempt"],
    "commit": old["headSha"], "status": old["status"], "conclusion": old["conclusion"],
    "url": old["url"], "jobs_total": 6, "jobs_passed": 5, "jobs_failed": 1,
    "evidence": old_path, "evidence_sha256": digest(old_path),
    "jobs": [{"name": j["name"], "status": j["status"], "conclusion": j["conclusion"],
              "failed_steps": [s["name"] for s in j["steps"] if s["conclusion"] == "failure"]}
             for j in old["jobs"]],
    "GA_accepted": False,
}
write_new(terminal_path, terminal)

w, g = read("work-graph.json"), read("gates/ga.json")
c = w["packages"][7]["fixtureCacheStateContractCandidate"]
assert c == g["gates"][1]["fixtureCacheStateContractCandidate"]
b = c["scalar_cursor_host_acceptance"]["real_profile_adapter_preparation"]["next_header_preparation"]["retained_profile_composition_preparation"]["real_binding_preparation"]["real_profile_loader_binding"]["next_adoption_lane"]["guarded_snapshot_export_contract_review"]["composition_source_preparation"]["bootstrap_host_boundary"]
b["remaining_work_interfaces"].update({
    "status": "bounded-host-accepted-fourteen-amendment-selected",
    "accepted": True, "acceptance": acceptance_path, "acceptance_sha256": digest(acceptance_path),
    "producer_seal_sha256": producer["seal_sha256"],
    "independent_seal_sha256": independent["seal_sha256"],
    "selected_amendment": amendment_path, "selected_amendment_sha256": digest(amendment_path),
    "conditional_fixed_work": review["conditional_fixed"], "remaining_inputs": 12,
    "whole_host_bound_or_operational_grant": False,
})
b["outer_parent_source"].update({
    "status": "frozen-private-source-independent-review-active",
    "producer_seal_sha256": "3936c73a0f3558000834c92c3ade9822465069492740a954765cb775684bcb57",
    "release": prefix + "guarded-snapshot-outer-parent-frozen-release.json",
    "independent_owner": "/root/swift_outer_parent_independent",
    "independent_ownership": "verification/swift-guarded-snapshot-outer-parent-independent",
    "producer_compiler_terminal_status": "unknown-receipt-writer-failed",
    "new_outer_work_storage_and_binding_pending": True,
})
b["native_open_binary_closure"] = {
    "status": "source-compiled-correspondence-candidate-active",
    "owner": "/root/swift_native_open_binary_closure",
    "ownership": "verification/swift-guarded-snapshot-native-open-binary-closure",
    "accepted": False, "runtime_selected": False,
}
old_delivery = c["guarded_snapshot_host_ci_repair_delivery"]
old_delivery["CI"].update({"status": "completed", "conclusion": "failure", "terminal": True,
                            "evidence": old_path, "jobs_passed": 5, "jobs_failed": 1,
                            "terminal_receipt": terminal_path, "terminal_receipt_sha256": digest(terminal_path)})
old_delivery["followup_preparation_correction"].update({"fresh_CI_pending": False,
    "fixed_job_passed_on_run": 40514213881, "full_followup_CI_pending": True})
latest_path = "verification/github-delivery-host-ci-directory-fix/ci-jobs-4.stdout"
latest = read(latest_path)
assert latest["headSha"] == "975b2e3ef25255a882e7476780caa2e844ce928d"
qualified_path = "verification/swift-host-resource-ci-remote-qualification/qualification.json"
qualified = read(qualified_path)
assert qualified["commands_output_pairs_rehashed"] == 103 and qualified["runner_controls"] == 29
assert qualified["compiler"]["release"] == "1.98.1" and qualified["cleanup_confirmed"]
latest_delivery = c["guarded_snapshot_host_ci_directory_delivery"]
latest_delivery["CI"].update({"status": latest["status"], "conclusion": latest["conclusion"],
    "terminal": latest["status"] == "completed", "evidence": latest_path,
    "jobs_passed": sum(j["conclusion"] == "success" for j in latest["jobs"]),
    "jobs_running": [j["name"] for j in latest["jobs"] if j["status"] != "completed"]})
latest_delivery["remote_cache_qualification"] = {
    "receipt": qualified_path, "receipt_sha256": digest(qualified_path),
    "source_commit": qualified["source_commit"], "source_tree": qualified["source_tree"],
    "commands": 103, "runner_controls": 29, "rust": "1.98.1", "artifact": 12737724911,
    "elapsed_seconds": qualified["elapsed_seconds"], "cleanup_confirmed": True,
    "historical_local_run_not_used_as_remote_evidence": True,
}
g["gates"][1]["fixtureCacheStateContractCandidate"] = copy.deepcopy(c)
assert len(w["packages"]) == 18 and len(g["gates"]) == 38
assert w["packages"][4]["privateOwnerEffectContractCandidate"] == g["gates"][4]["privateOwnerEffectContractCandidate"]
for path, value in (("work-graph.json", w), ("gates/ga.json", g)):
    (ROOT / path).write_text(json.dumps(value, indent=2) + "\n")

first = "CI evidence-directory correction `975b2e3` is pushed with 75 selected paths. Its complete cache fixture now passes on Rust 1.98.1: root verifies all 103 command output pairs, 29 controls and 86 pack members against this exact commit, with cleanup confirmed. The retained artifact also contains older local evidence, which is explicitly excluded from remote qualification. [CI](https://github.com/snowdamiz/mixer/actions/runs/40514213881) has four passing jobs and two Swift jobs running on attempt one; the Swift selection step passes. The workflow preserves existing evidence parents and still requires fresh per-run output. Canonical product source remains at `b4a9fd4`; whole-host funding, actual fixture/writer execution, native runtime and GA remain pending."
followon = "Root selects the fourteen remaining source146 logical-interface clarifications after complete producer/reviewer custody checks, 3,374 independent assertions and 366 adverse controls. Five fresh constructor allocation requests add 55,381 once in P4; the amended conditional expression retains twelve required external inputs. The original 35-symbol model and its failures remain unchanged. The private outer caller is frozen for independent source/lifetime review; its producer compiler receipt failure remains unqualified. Complete string provenance and compiled native-open correspondence are active. New outer work/storage, immutable binding and operational authority remain pending."
for path in ("PLAN.md", "STATUS.md"):
    text = (ROOT / path).read_text()
    start = text.index("CI evidence-directory correction `975b2e3`")
    end = text.index("\n\n", start)
    text = text[:start] + first + "\n\n" + followon + text[end:]
    text = text.replace("Other jobs were still running at the observation; remote Rust 1.98.1 is not yet requalified.", "That run is now terminal with five jobs passing and the setup job failing. The corrected 975b2e3 run separately requalifies the complete cache fixture on Rust 1.98.1; its full CI result is still pending.", 1)
    text = text.replace("Three active lanes close remaining work interfaces, string provenance and the private outer parent.", "The remaining-work interface amendment is selected; string provenance, outer-parent review and compiled native-open correspondence continue.", 1)
    (ROOT / path).write_text(text)
print(json.dumps({"accepted": acceptance_path, "acceptance_sha256": digest(acceptance_path),
                  "amendment_sha256": digest(amendment_path), "terminal_ci_sha256": digest(terminal_path),
                  "remote_cache_qualification_sha256": digest(qualified_path),
                  "producer_members": 103, "independent_members": 75,
                  "remaining_inputs": 12, "whole_host_grant": False}))
