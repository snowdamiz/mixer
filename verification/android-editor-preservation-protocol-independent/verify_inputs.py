"""Hash only the assigned immutable packet and the necessary frozen source."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
PROTOCOL = ROOT / "verification/android-editor-preservation-completion/protocol-1"
PRODUCT = ROOT / "verification/android-editor-focus-history-correction"
REVIEW = ROOT / "verification/android-editor-focus-history-independent/actual-review"


def digest(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


expected = {
    PROTOCOL / "seal.json": "e575641c10d690bf4b6e02843355a60d5b3077233c94fc5cb443be7f490584bd",
    PRODUCT / "seal.json": "2ebf7634886be778b06ecdfa0ab2a9ac69d14a473b88a7f6ea623ccddfcd5af8",
    REVIEW / "review-seal.json": "69e1f6a02702e5a4181cbb6ff76263301d499e8853115c7059bb39e0c393dcb8",
    ROOT / "verification/android-editor-boundary-root-review/preservation-completion-requirements.md": "91159240131bc0a107f321e3571345755c24c9651ed8ad7b3cc63ba784103187",
}
verified = []
for path, sha in expected.items():
    identity = digest(path)
    assert identity["sha256"] == sha, str(path)
    verified.append({"path": str(path.relative_to(ROOT)), **identity})

protocol = json.loads((PROTOCOL / "seal.json").read_text())
assert protocol["member_count"] == len(protocol["members"]) == 44
assert protocol["member_bytes"] == sum(m["bytes"] for m in protocol["members"]) == 862128
for member in protocol["members"]:
    assert digest(PROTOCOL / member["path"]) == {k: member[k] for k in ("bytes", "sha256")}, member["path"]

product = json.loads((PRODUCT / "seal.json").read_text())
product_map = {m["path"]: m for m in product["members"]}
source_checks = []
for path in sorted((PROTOCOL / "inputs/source").glob("*.java")):
    relative = "source/" + path.name
    actual = digest(PRODUCT / relative)
    assert actual == {k: product_map[relative][k] for k in ("bytes", "sha256")}
    assert actual == digest(path)
    source_checks.append({"path": relative, **actual})
assert len(source_checks) == 16
source_map = {Path(m["path"]).name: {k: m[k] for k in ("bytes", "sha256")} for m in source_checks}
computed_product_tree = hashlib.sha256(json.dumps(source_map, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
assert computed_product_tree == product["product_source_tree_digest"]
root_requirements = next(p for p in expected if p.name == "preservation-completion-requirements.md")
assert digest(PROTOCOL / "inputs/contracts/preservation-completion-requirements.md") == digest(root_requirements)

review = json.loads((REVIEW / "review-seal.json").read_text())
assert review["member_count"] == len(review["members"]) == 1151
assert review["member_bytes"] == sum(m["bytes"] for m in review["members"]) == 10030967
review_map = {m["path"]: m for m in review["members"]}
for name in ("findings.md", "seal.json"):
    relative = "findings-1/" + name
    expected_member = {k: review_map[relative][k] for k in ("bytes", "sha256")}
    assert digest(REVIEW / relative) == expected_member
    assert digest(PROTOCOL / "inputs/findings-1" / name) == expected_member

receipt = {
    "schema": 1,
    "verified_seals_and_root_requirements": verified,
    "protocol_members_rehashed": 44,
    "protocol_member_bytes": 862128,
    "necessary_frozen_product_source_rehashed": source_checks,
    "product_source_tree_digest": product["product_source_tree_digest"],
    "independently_computed_product_source_tree_digest": computed_product_tree,
    "product_full_member_count_from_sealed_metadata_only": len(product["members"]),
    "review_full_member_count_from_sealed_metadata_only": 1151,
    "review_full_member_bytes_from_sealed_metadata_only": 10030967,
    "review_members_rehashed": ["findings-1/findings.md", "findings-1/seal.json"],
    "full_product_or_review_custody_reexecution_claimed": False,
    "root_supplied_full_custody_reference_not_reexecuted": "5534268752893a9df3fb391b6b720fd027b75edb3190db6eb3bd7fc2bb317121",
    "success": True,
}
(OWN / "input-custody.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"success": True, "protocol_members": 44,
                  "source_files": 16, "review_findings_members": 2}))
