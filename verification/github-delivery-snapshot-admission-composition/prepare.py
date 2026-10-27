"""Prepare an exact, one-shot delivery selection; never invoke an older wrapper."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import stat
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = "32b5075a5f203cb25ae357492b70f0f724f3ea19"
PARENT = ROOT / "verification/github-delivery-snapshot-funding-retention"


def identity(path):
    assert stat.S_ISREG(path.lstat().st_mode), path
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def save(path, value, exclusive=True):
    with path.open("x" if exclusive else "w") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


assert not (OUT / "release-selection.json").exists(), "Preparation is one-shot"
work = json.loads((ROOT / "work-graph.json").read_bytes())
gates = json.loads((ROOT / "gates/ga.json").read_bytes())
candidate = work["packages"][7]["fixtureCacheStateContractCandidate"]
contract = candidate["scalar_cursor_host_acceptance"]["real_profile_adapter_preparation"]["next_header_preparation"]["retained_profile_composition_preparation"]["real_binding_preparation"]["real_profile_loader_binding"]["next_adoption_lane"]["guarded_snapshot_export_contract_review"]
boundary = contract["composition_source_preparation"]["bootstrap_host_boundary"]
boundary["host_account_entry"].update({
    "status": "frozen-root-custody-verified-independent-contract-and-inventory-reviews-active",
    "producer_seal_sha256": "6e8c8e2d8dde62e2e35fe2e8fb1a851a342d8d95f8c71facd938416ac3e153e3",
    "producer_members_verified": 136, "producer_bytes_verified": 3432402,
    "source_tree_sha256": "5cd522af7e126d88496b5aefee722ff481821f0cf5babdbdbd7fbeba646c380b",
    "source_basis": "funding144 plus bootstrap leaf and private account include; distinct from combined145",
    "producer_host_tests_each_mode": 11, "producer_negative_compile_controls": 3,
    "new_functions": 19, "new_MIR_roles": 396, "new_logical_source_object_bytes": 311071,
    "superseded_394_role_claim_preserved": True,
    "root_policy_whole_quote_fixture_binding_pending": True,
    "independent_contract_review_owner": "/root/swift_snapshot_host_account_independent",
    "independent_inventory_review_owner": "/root/swift_snapshot_host_account_inventory",
    "included_in_admission_composition_delivery": False,
})
boundary["loader_work"].update({
    "status": "active-MIR-operation-and-validator-credit-bridge-review",
    "producer_compiler_complete": True,
    "independent_preaccess_seal_sha256": "37aaa40dcfa3cf599d35f3466d12dffc7431c5c53d689ebe7e4f388958834fa2",
    "independent_preaccess_checks": 315,
    "independent_preaccess_source_members": 11,
    "producer_coefficient_review_pending": True,
})
candidate["guarded_snapshot_admission_composition_delivery"] = {
    "status": "prepared-exact-allowlist-delivery",
    "base": BASE,
    "packets": 7,
    "canonical_product_changed": False,
    "scope": "Bounded private-core work admission with common-storage correction and combined-source interaction acceptance; frozen bootstrap source preparation remains unqualified.",
    "excluded": ["host-account source and reviews", "active loader-work candidate and preaccess review", "protected hosted changes"],
    "native_OTA_GA_accepted": False,
}
gates["gates"][1]["fixtureCacheStateContractCandidate"] = candidate
save(ROOT / "work-graph.json", work, exclusive=False)
save(ROOT / "gates/ga.json", gates, exclusive=False)
old = "The fresh private host-bootstrap leaf is frozen; enforcing host-account source and the loader work bound are active. These follow-ons remain excluded from the pushed checkpoint."
new = "The fresh private host-bootstrap leaf is frozen. The enforcing host-account source is also frozen with eleven pure account tests per host mode and three negative compiler controls; separate contract and source-inventory reviews are active. Its corrected inventory has 396 roles and 311,071 logical bytes. The loader work bound has compiled its exact source model and is undergoing operation and credit-cut review; 315 independent preaccess model cases pass. These follow-ons remain excluded from the pushed checkpoint."
for name in ("PLAN.md", "STATUS.md"):
    path = ROOT / name
    text = path.read_text()
    assert text.count(old) == 1, name
    path.write_text(text.replace(old, new))

seals = {
    "work-admission": "e8fe23ee4800a76ac6ca1486604b98b114a1f4dbdec1a25f520641c4e9951940",
    "work-admission-independent": "68619807028aec0ac511a287ebcc33f9788e22860b0e39bb0fc6daee0620956a",
    "work-common-correction": "c679b12e5a82c5cd6746f87d8615cb19c6cba00f1d72625cad334bb11adc1422",
    "work-common-independent": "fd628a9e7617eb962876219383b7a551c22fa55202664bd8e1addbcda9652d69",
    "combined-source": "2eb3dab82f2b492b491e9f80e1d05fb0f8745e41c452f4f3bc777a33b62e8bdc",
    "combined-independent": "4162045924b38f67feea2b6a44b5914d141270ae4dca79a99469315c7b21338e",
    "bootstrap-host-boundary": "00f5bf754a13317ac18dd9959a1db4a9b025b16c72fc99a9d4cfddfcc7cb4dba",
}
packets = []
for suffix, digest in seals.items():
    name = "swift-guarded-snapshot-" + suffix
    folder = ROOT / "verification" / name
    assert identity(folder / "seal.json")["sha256"] == digest
    seal = json.loads((folder / "seal.json").read_bytes())
    for row in seal["members"]:
        observed = identity(folder / row["path"])
        assert all(observed[key] == row[key] for key in ("bytes", "sha256"))
    packets.append({"path": name, "seal_sha256": digest})

root_receipts = {
    "guarded-snapshot-work-admission-independent-release.json": "e902912c64ecb585782fd92e164377e46aefa3c3c1e7771ce0760655c3316e3d",
    "guarded-snapshot-work-admission-review-finding.json": "6664555f320e78995c8e0eed9766308bfc43240bfd0cbf21bf0c1ab8db05b894",
    "guarded-snapshot-work-common-independent-release.json": "a57e64c32beaa2b472e8148772d66633f9214754e414e25088ed0e2cdcab93f9",
    "guarded-snapshot-work-admission-host-acceptance.json": "c08376ad082af1b12fed92571d23f2544d52dad389096b62790a4073b7b3a8b3",
    "guarded-snapshot-bootstrap-next-source-release.json": "92889d223971bf99c3a7fdf9d2afe8d0491d02273f62d922ee78010f38ae9164",
    "guarded-snapshot-combined-independent-release.json": "6f27017ee31d9d4bc6b2866920313440d5f0fe88524dcf875e02a38e43478885",
    "guarded-snapshot-combined-host-acceptance.json": "f522358c5c3f474b2c10f23c7710e4296d9e287001eae09a50eeb591ba3f68b2",
}
rows = []
for name, digest in root_receipts.items():
    row = identity(ROOT / "verification/swift-semantic-adapter-root-review" / name)
    assert row["sha256"] == digest
    rows.append(row)
rows.append(identity(Path(__file__)))
parent_files = [identity(path) for path in sorted(PARENT.rglob("*")) if path.is_file()]
terminal = json.loads((PARENT / "terminal-ci-status.json").read_bytes())
assert terminal["commit"] == BASE and terminal["conclusion"] == "success"
assert terminal["jobs_passed"] == 6 and terminal["steps_passed"] == 64

script = (PARENT / "deliver.py").read_text()
replacements = {
    '"""One-shot delivery of accepted funding, retention, work interface and descriptor preparation."""': '"""One-shot delivery of bounded work admission, composition and bootstrap preparation."""',
    'BASE = "9a8e8f78b97cb5c7c9c44c88b69c961aa4906c21"': f'BASE = "{BASE}"',
    'assert len(release["packets"]) == 10': 'assert len(release["packets"]) == 7',
    'verification/github-delivery-snapshot-storage-accounting/': 'verification/github-delivery-snapshot-funding-retention/',
    '"verification/swift-guarded-snapshot-work-admission/",\n    "verification/swift-guarded-snapshot-work-admission-independent/",\n    "verification/swift-guarded-snapshot-work-common-correction/",\n    "verification/swift-guarded-snapshot-bootstrap-host-boundary/",': '"verification/swift-guarded-snapshot-host-account-entry/",\n    "verification/swift-guarded-snapshot-host-account-independent/",\n    "verification/swift-guarded-snapshot-host-account-inventory-independent/",\n    "verification/swift-guarded-snapshot-loader-work/",\n    "verification/swift-guarded-snapshot-loader-work-independent/",',
    'Integrate isolated snapshot funding and lifetime retention': 'Record reviewed snapshot admission and source composition',
    'active_admission_correction_and_bootstrap_lanes_excluded': 'host_account_and_loader_work_lanes_excluded',
}
for old_value, new_value in replacements.items():
    assert script.count(old_value) == 1, old_value
    script = script.replace(old_value, new_value)
ast.parse(script)
with (OUT / "deliver.py").open("x") as stream:
    stream.write(script)
save(OUT / "release-selection.json", {
    "schema": 1, "ready": True, "base": BASE, "packets": packets,
    "root_and_source_files": rows, "parent_delivery_files": parent_files,
    "canonical_paths": [],
    "scope": "Accepted private-core work prepayment with common-storage correction and accepted combined145 synthetic interaction; original findings retained. Bootstrap leaf is frozen preparation only. No canonical product change, real loader/writer dispatch, full host funding, healthy cleanup, native, OTA, FieldLog or GA acceptance.",
})
assert [p["id"] for p in work["packages"]] == [f"W{i:02}" for i in range(1, 19)]
assert [g["id"] for g in gates["gates"]] == [f"G{i:02}" for i in range(1, 39)]
assert sum(g["status"] == "running" for g in gates["gates"]) == 8
assert sum(g["status"] == "planned" for g in gates["gates"]) == 30
assert work["packages"][4]["privateOwnerEffectContractCandidate"] == gates["gates"][4]["privateOwnerEffectContractCandidate"]
assert work["packages"][7]["fixtureCacheStateContractCandidate"] == gates["gates"][1]["fixtureCacheStateContractCandidate"]
assert all(f"D{i}" in (ROOT / "mixer-product-plan.md").read_text() for i in range(9))
save(OUT / "metadata-validation.json", {
    "schema": 1, "at": datetime.now(timezone.utc).isoformat(), "passed": True,
    "python": sys.version, "command": "python3 verification/github-delivery-snapshot-admission-composition/prepare.py",
    "scope": "Exact frozen member custody, W01-W18/G01-G38/D0-D8 identities, mirrors, eight running/thirty planned/no passed gates, source exclusions and authored wrapper syntax; no runtime or broad scan",
    "metadata_files": [identity(ROOT / name) for name in ("PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json")],
    "packages": 18, "gates": 38, "dogfood_milestones": 9,
})
print(json.dumps({"prepared_packets": len(packets), "parent_files": len(parent_files), "canonical_paths": []}))
