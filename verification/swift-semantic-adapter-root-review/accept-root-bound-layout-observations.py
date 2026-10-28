"""Accept the separately amended, independently checked diagnostic layouts only."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
DEST = OUT / "root-bound-layout-observation-acceptance.json"

def read(path):
    return json.loads(path.read_bytes())

def row(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}

def verify(path, digest, count):
    assert row(path)["sha256"] == digest
    value = read(path)
    members = value.get("members", value.get("files"))
    assert len(members) == count
    for expected in members:
        actual = row(path.parent / expected["path"])
        assert actual["bytes"] == expected["bytes"] and actual["sha256"] == expected["sha256"]

assert not DEST.exists(), "One-shot; do not replay"
lane = ROOT / "verification/swift-root-bound-layout-observation-amendment-v2"
review = ROOT / "verification/swift-root-bound-work-storage-layout-preaccess"
warning = ROOT / "verification/swift-root-bound-layout-warning-classification"
verify(lane / "seal.json", "409a1e4fcea8ac54cd7e96b4ab179bab397f4e49c19d019b1751307ab8e3d8a3", 16)
verify(review / "independent-amended-terminal-seal.json", "746be02f13acdce47dfe5ea24e80bef7658f62030c7f30886009b90a5337fbd7", 6)
verify(warning / "seal.json", "39976085aa6fd3cebf5c12bb6376358c46b11223df8347b8fb70ef12c20be5ab", 9)
candidate = read(lane / "actual/candidate-observation.json")
receipt = read(lane / "actual/receipt.json")
independent = read(review / "independent-amended-saved-observation.json")
terminal = read(review / "independent-amended-terminal-review.json")
assert receipt["candidate_emitted"] and receipt["error"] is None
assert receipt["actual_saved_raw_parser_calls"] == 1 and receipt["compiler_invocations"] == 0
assert receipt["bounded_input_memory_sha256_verified_before_parser"]
assert terminal["root_retrospective_offline_layout_observation_acceptance_recommended"]
assert terminal["actual_independent_amended_saved_raw_parser_calls"] == 1
assert terminal["custody_unchanged"] and terminal["error"] is None
assert terminal["new_compiler_runtime_native_ui_capture_child_process_queries"] == 0
assert len(candidate["named_layout_candidates"]) == 28
assert candidate["named_layout_candidates"] == independent["named_layouts"]
assert candidate["actual_closure_candidate"] == independent["actual_closure"] == {"size": 48, "align": 8, "source_bits": 384, "wrapper_bits": 448}
assert candidate["source_spans_verified"] == independent["source_geometries_verified"] == 346
assert candidate["primary_E0308"] == 56 and candidate["primary_E0512"] == 2
assert candidate["exact_source_bound_warnings"] == candidate["summaries"] == 3
assert not candidate["original_contract_accepted"] and not independent["original_oracle_accepted"]
original = ROOT / "verification/swift-root-bound-work-storage-layout-probe-v3"
assert row(original / "command/stderr")["sha256"] == "05c526210b4c07779c09c33f1944ffaa06d8012c57a57e3ad05f68ee34106635"
old_receipt = read(original / "command/receipt.json")
assert not old_receipt["accepted_diagnostic_observation"] and old_receipt["compiler_invocations"] == 1
info = {
    "status": "accepted-retrospective-source-tool-target-bound-diagnostic-layout-observations",
    "scope": terminal["acceptance_scope"],
    "retrospective_policy": True, "original_contract_accepted": False,
    "source146_tree": candidate["source146_tree"], "diagnostic146_tree": candidate["diagnostic146_tree"],
    "historical_query_plan": row(original / "plan.json"),
    "historical_query_receipt": row(original / "command/receipt.json"),
    "saved_stderr": candidate["saved_stderr"],
    "warning_provenance_seal": row(warning / "seal.json"),
    "warnings": "Exactly three complete pre-existing source warnings remain visible; no warning-free build claim",
    "amendment_plan": row(lane / "plan.json"), "amendment_seal": row(lane / "seal.json"),
    "root_release": row(OUT / "root-bound-layout-observation-amendment-release.json"),
    "candidate": row(lane / "actual/candidate-observation.json"), "offline_receipt": row(lane / "actual/receipt.json"),
    "independent_terminal_seal": row(review / "independent-amended-terminal-seal.json"),
    "independent_observation": row(review / "independent-amended-saved-observation.json"),
    "independent_terminal_review": row(review / "independent-amended-terminal-review.json"),
    "named_layouts": candidate["named_layout_candidates"], "actual_closure": candidate["actual_closure_candidate"],
    "full_stream": terminal["full_stream"], "historical_compiler_invocations": 1,
    "new_compiler_invocations": 0, "producer_offline_saved_raw_calls": 1, "independent_offline_saved_raw_calls": 1,
    "all_original_failures_preserved": True, "delivery_pending": True,
    "pending": ["Incremental work/storage prices, coexistence and aggregate peaks, dynamic backing and capacity",
                "Root funding and complete ownership", "Canonical integration and paused native/device qualification",
                "FieldLog immutable distribution, OTA and every GA gate"],
    "prices_backing_peaks_funding_full_ownership_GA_accepted": False}
w = read(ROOT / "work-graph.json")
g = read(ROOT / "gates/ga.json")
c = w["packages"][7]["fixtureCacheStateContractCandidate"]
assert c == g["gates"][1]["fixtureCacheStateContractCandidate"]
b = c["scalar_cursor_host_acceptance"]["real_profile_adapter_preparation"]["next_header_preparation"]["retained_profile_composition_preparation"]["real_binding_preparation"]["real_profile_loader_binding"]["next_adoption_lane"]["guarded_snapshot_export_contract_review"]["composition_source_preparation"]["bootstrap_host_boundary"]
layout = b["actual_owner_Rust_selection"]["correction"]["IR02_source_repair"]["work_storage_delta"]["layout_probe"]
layout.update({"status": info["status"], "retrospective_layout_observation_acceptance": copy.deepcopy(info),
               "diagnostic_layout_observations_accepted": True, "numeric_prices_accepted": False,
               "original_v3_policy_accepted": False, "compiler_lane_released": False})
layout["v3_execution"]["independent_terminal_review_pending"] = False
layout["v3_execution"]["independent_terminal_review"] = row(review / "terminal-v3-review-seal.json")
g["gates"][1]["fixtureCacheStateContractCandidate"] = copy.deepcopy(c)
old = "The original and second Swift layout runners remain unexecuted after parsing, cleanup and final-publication review findings. The independently reviewed third runner completed one compiler-only query in 2.26 seconds with confirmed child/group and build cleanup, but its frozen policy rejects two unused-import and one deprecation warnings. The raw 58 intended errors and three warnings are preserved for separate offline classification; no compiler retry, layout, price or funding is accepted."
new = "The Swift layout lane now accepts 28 named size/alignment observations and the actual closure at 48 bytes with alignment 8, limited to the exact isolated source, compiler, target and configuration. One compiler query was followed by separately reviewed retrospective parsing of its saved diagnostics; both producer and independent parsers agree on all values and 346 source spans. The original warning-policy rejection is preserved, and all three baseline warnings remain visible. No second compiler run, numerical work/storage price, aggregate peak, backing or root funding is accepted."
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
print(json.dumps({"accepted_named_layouts": 28, "actual_closure": info["actual_closure"], "new_compiler_invocations": 0, "GA_verified": 0}))
