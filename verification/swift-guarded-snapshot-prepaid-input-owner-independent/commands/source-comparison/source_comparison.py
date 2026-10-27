"""Read-only source comparison; no Rust parsing/compilation or product execution."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
provider = ROOT / "verification/swift-guarded-snapshot-owned-binding-provider"
base = ROOT / "verification/swift-guarded-snapshot-scoped-binding-source"
manifest = json.loads((provider / "proposed-source-manifest.json").read_bytes())
custody = json.loads((provider / "proposed-source-custody.json").read_bytes())
prior = json.loads((base / "source-manifest.json").read_bytes())
old = {row["path"]: row for row in prior["members"]}
assert len(custody) == len(old) == manifest["member_count"] == 146
assert manifest["tree_sha256"] == "acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d"
changed = []
for row in custody:
    raw = (ROOT / row["origin"]).read_bytes()
    assert (len(raw), hashlib.sha256(raw).hexdigest()) == (row["bytes"], row["sha256"])
    if row["sha256"] != old[row["path"]]["sha256"]:
        oldraw = (base / "source/vm" / row["path"]).read_bytes()
        assert raw.startswith(oldraw)
        changed.append({"path": row["path"], "original_prefix_bytes": len(oldraw),
                        "append_bytes": len(raw) - len(oldraw), "original_prefix_identical": True,
                        "origin": row["origin"], "sha256": row["sha256"]})
assert len(changed) == 1
assert changed[0]["path"] == "src/experimental_swift_reactor/cache/initial_profile_v1.rs"
source = (base / "source/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs").read_text()
control = (base / "source/vm/src/experimental_swift_reactor/control.rs").read_text()
budgetbody = control.split("pub struct SwiftRunBudget {", 1)[1].split("\n}", 1)[0]
fields = [line.strip().removeprefix("pub ").split(":", 1)[0] for line in budgetbody.splitlines() if ":" in line]
expected = ["source_bytes", "metadata_bytes", "cache_bytes", "cache_entry_bytes", "cache_entries",
            "active_pins", "cache_work", "frames", "values", "controls", "memory_pages", "state_bytes",
            "combined_bytes", "instruction_fuel", "execution_work", "host_calls", "deadline_ms"]
assert fields == expected
claimsbody = source.split("struct UnverifiedProfileDigestBytesV1 {", 1)[1].split("\n}", 1)[0]
claims = [piece.strip().split(":", 1)[0] for piece in claimsbody.split(",") if ":" in piece]
assert claims == ["baseline", "candidate", "original_input", "event_schema", "profile_adapter_binary",
                  "layout_receipt", "original_validated_snapshot", "profile_row_body"]
claimcopy = source.split("fn copy_claims_v1(", 1)[1].split("fn run_prepaid_fixture_v1", 1)[0]
for claim in claims:
    assert claim + ": claims." + claim in claimcopy
account = (base / "source/vm/src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs").read_text()
assert "Err(RefusalV1::RootPolicyPending)" in account
assert "Err(RefusalV1::WholeQuotePending)" in account
assert "Err(BindingSelectionRefusalV1::ImmutableBindingAndP0ReviewPending)" in source
fixture = ROOT / "verification/swift-real-profile-loader-binding/source-preimages/genuine.wasm"
raw = fixture.read_bytes()
assert (len(raw), hashlib.sha256(raw).hexdigest()) == (1947, "9804738523f3053f2b7a0093ecd5b324ecf54b1d43094993cdb2ee7d63747806")
print(json.dumps({"source146_tree": manifest["tree_sha256"], "source_members_rehashed": len(custody),
    "unchanged_members": 145, "changed": changed, "actual_budget_fields": fields,
    "actual_unverified_claims": claims, "all_eight_copy_claims_preserved": True,
    "all_three_selectors": "Pending", "fixture_source_bytes": len(raw),
    "fixture_source_sha256": hashlib.sha256(raw).hexdigest(),
    "scope": "exact byte/source comparison only; no compiler, native/host execution, selection or GA"}, indent=2))
