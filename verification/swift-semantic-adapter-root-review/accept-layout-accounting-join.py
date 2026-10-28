"""Accept the finite source/data join while retaining every unpriced obligation."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
DEST = Path(__file__).with_name("layout-accounting-join-acceptance.json")

def read(path):
    return json.loads(path.read_bytes())

def row(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

def verify(path, digest, count):
    assert row(path)["sha256"] == digest
    value = read(path)
    members = value.get("members", value.get("files"))
    assert len(members) == count
    for expected in members:
        actual = row(path.parent / expected["path"])
        assert actual["bytes"] == expected["bytes"] and actual["sha256"] == expected["sha256"]

assert not DEST.exists(), "One-shot; do not replay"
lane = ROOT / "verification/swift-root-bound-layout-accounting-join"
independent = ROOT / "verification/swift-root-bound-layout-accounting-join-independent"
verify(lane / "seal.json", "8a3fd8e76d2826e53aecdf0399773d03c301e2610714d3ebb11f50b949ed0520", 17)
verify(independent / "review-seal.json", "c634b0f7d5a755c794e8b21c9f2b2176a9a9d9f5fb86fd946ba18a784c1528ca", 5)
verify(independent / "preaccess-seal.json", "985a3b2b07a2a8eaaf74d488059d06c38be9a2fceb4f6048bbc791950f317adf", 13)
counts = read(lane / "inventory-place-join.json")["counts"]
assert counts == {"actual_closure_roles": 2, "arguments": 65, "locals_returns": 580,
                  "named_shape_roles": 97, "total_roles": 645, "unbound_roles": 546}
obligations = read(lane / "obligation-dispositions.json")
assert obligations["fully_closed_storage_charge_obligations"] == 0
assert obligations["storage_obligations"] == obligations["work_obligations"] == 12
controls = read(lane / "controls-result.json")
assert controls["controls_passed"] == 21 and controls["numeric_storage_charge_obligations_closed"] == 0
info = {"status": "accepted-finite-source-data-layout-accounting-prerequisite",
        "producer_seal": row(lane / "seal.json"), "independent_preaccess": row(independent / "preaccess-seal.json"),
        "independent_review": row(independent / "review-seal.json"), "counts": counts,
        "producer_integrity_controls": 21, "independent_integrity_controls": 34,
        "representation_differences_checked": 14, "prospective_unexecuted_controls": 16,
        "finite_type_spellings": 179, "general_type_normalizer_qualified": False,
        "scope": "Exact pinned source/target/compiler/config roster only; coverage links and static representation differences are not additive charges or runtime calls",
        "open_work_obligations": 12, "open_storage_obligations": 12, "closed_storage_charge_obligations": 0,
        "next_contract": row(lane / "next-contract.json"),
        "next": "Dispatch, returned-child and destruction representation/lifetime contract; no numeric charge until every region, interval, backing capacity and retained quote term is resolved",
        "new_compiler_or_runtime_replays": 0, "work_prices_storage_charges_backing_peaks_funding_ownership_GA_accepted": False}
w = read(ROOT / "work-graph.json")
g = read(ROOT / "gates/ga.json")
c = w["packages"][7]["fixtureCacheStateContractCandidate"]
assert c == g["gates"][1]["fixtureCacheStateContractCandidate"]
b = c["scalar_cursor_host_acceptance"]["real_profile_adapter_preparation"]["next_header_preparation"]["retained_profile_composition_preparation"]["real_binding_preparation"]["real_profile_loader_binding"]["next_adoption_lane"]["guarded_snapshot_export_contract_review"]["composition_source_preparation"]["bootstrap_host_boundary"]
b["actual_owner_Rust_selection"]["correction"]["IR02_source_repair"]["work_storage_delta"]["layout_accounting_join"] = copy.deepcopy(info)
g["gates"][1]["fixtureCacheStateContractCandidate"] = copy.deepcopy(c)
addition = " The finite accounting join now has independent acceptance: all 645 roles are retained, with 97 named-layout links, two exact dispatch-closure links and 546 unbound roles. All twelve work and twelve storage obligations remain open; the next source contract concerns dispatch, returned-child and destruction lifetimes without selecting a numeric grant."
marker = "No second compiler run, numerical work/storage price, aggregate peak, backing or root funding is accepted."
for name in ["PLAN.md", "STATUS.md"]:
    path = ROOT / name
    text = path.read_text()
    assert text.count(marker) == 1 and addition not in text
    path.write_text(text.replace(marker, marker + addition))
for name, value in [("work-graph.json", w), ("gates/ga.json", g)]:
    (ROOT / name).write_text(json.dumps(value, indent=2) + "\n")
with DEST.open("x") as handle:
    json.dump({"schema": 1, "at": datetime.now(timezone.utc).isoformat(), "acceptance": info,
               "GA_verified": 0, "metadata": [row(ROOT / n) for n in ["PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"]]}, handle, indent=2)
    handle.write("\n")
print(json.dumps({"accepted_finite_roles": 645, "open_obligations": 24, "numeric_grants_selected": 0, "GA_verified": 0}))
