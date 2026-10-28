"""Select only the reviewed isolated event/region model, without a product grant."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
DEST = Path(__file__).with_name("dispatch-region-model-selection.json")

def row(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

def verify(path, digest, count):
    assert row(path)["sha256"] == digest
    value = json.loads(path.read_bytes())
    members = value.get("members", value.get("files"))
    assert len(members) == count
    for expected in members:
        actual = row(path.parent / expected["path"])
        assert actual["bytes"] == expected["bytes"] and actual["sha256"] == expected["sha256"]

assert not DEST.exists(), "One-shot; do not replay"
contract = ROOT / "verification/swift-root-bound-dispatch-lifetime-contract"
review = ROOT / "verification/swift-root-bound-dispatch-lifetime-contract-independent"
verify(contract / "seal.json", "1ce05f8759b634e7a8c651a88ea4290b69ba8fde5bb100ed86802a0a5599a882", 12)
verify(review / "seal.json", "ea02c82bb26690ac3d1b3dd5692b0b649b4f737b6bfde59c882e177fdde0f3d6", 10)
info = {"status": "reviewed-source-contract-selected-isolated-model-implementation",
        "contract_seal": row(contract / "seal.json"), "review_seal": row(review / "seal.json"),
        "implementation_specification": row(contract / "IMPLEMENTATION.md"),
        "event_families": 22, "semantic_ownership_regions": 9, "backing_groups": 8,
        "retained_quote_partitions": 10, "prospective_test_families": 20,
        "implementation_files": ["verification/swift-root-bound-dispatch-region-model/source/model.rs",
                                 "verification/swift-root-bound-dispatch-region-model/source/tests.rs"],
        "required": ["Closed typed state with separate internal normal and unwind phases; invalid transitions are atomic refusals",
                     "Physical declarations and capacity evidence remain separate from semantic ownership",
                     "Checked inline unions, once-per-backing ownership and complete acquisition/P0/C0-C5 coverage",
                     "Missing physical/capacity facts refuse; work units and byte units remain distinct",
                     "Every outcome is model_only, even with reviewed-looking or synthetic fitting inputs; no product grant or ReviewedWholeQuote"],
        "canonical_product_changes_authorized": False, "compiler_or_runtime_released": False,
        "current_production_selectors_remain_pending": True,
        "physical_capacity_prices_funding_full_ownership_GA_accepted": False}
w = json.loads((ROOT / "work-graph.json").read_bytes())
g = json.loads((ROOT / "gates/ga.json").read_bytes())
c = w["packages"][7]["fixtureCacheStateContractCandidate"]
assert c == g["gates"][1]["fixtureCacheStateContractCandidate"]
b = c["scalar_cursor_host_acceptance"]["real_profile_adapter_preparation"]["next_header_preparation"]["retained_profile_composition_preparation"]["real_binding_preparation"]["real_profile_loader_binding"]["next_adoption_lane"]["guarded_snapshot_export_contract_review"]["composition_source_preparation"]["bootstrap_host_boundary"]
b["actual_owner_Rust_selection"]["correction"]["IR02_source_repair"]["work_storage_delta"]["dispatch_lifetime_contract"] = copy.deepcopy(info)
g["gates"][1]["fixtureCacheStateContractCandidate"] = copy.deepcopy(c)
for name, value in [("work-graph.json", w), ("gates/ga.json", g)]:
    (ROOT / name).write_text(json.dumps(value, indent=2) + "\n")
with DEST.open("x") as handle:
    json.dump({"schema": 1, "at": datetime.now(timezone.utc).isoformat(), "selection": info,
               "GA_verified": 0, "metadata": [row(ROOT / "work-graph.json"), row(ROOT / "gates/ga.json")]}, handle, indent=2)
    handle.write("\n")
print(json.dumps({"isolated_model_files_selected": 2, "runtime_released": False, "GA_verified": 0}))
