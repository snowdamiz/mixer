#!/usr/bin/env python3
"""Bind root's scoped acceptance to executed logs and immutable source inputs."""
from pathlib import Path
import datetime
import hashlib
import json
import tarfile

root = Path(__file__).resolve().parents[2]
base = root / "verification/phoenix-foundation"
bindings = {}


def bind(path, expected=None):
    path = Path(path)
    if not path.is_absolute():
        path = root / path
    name = str(path.relative_to(root))
    value = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected is not None:
        assert value == expected, name
    bindings[name] = value
    return path


candidate = json.loads(bind(base / "candidate-5/receipt.json").read_text())
assert candidate["status"] == "passed"
assert candidate["cleanup"] == {"postgres_stopped": True, "scratch_removed": True}
manifest = candidate["inputs"]
assert hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == candidate["source_tree_sha256"]
archive = bind(base / "candidate-5/source.tar.gz", candidate["source_archive_sha256"])
with tarfile.open(archive) as source:
    assert set(source.getnames()) == set(manifest)
    for member in source.getmembers():
        assert member.isfile()
        assert hashlib.sha256(source.extractfile(member).read()).hexdigest() == manifest[member.name]
        bind(root / "hosted" / member.name, manifest[member.name])
for command in candidate["commands"]:
    bind(base / "candidate-5" / command["log"], command["sha256"])
    assert command["exit_code"] == command.get("expected_exit_code", 0)
assert "Result: 8 passed" in (base / "candidate-5/tests.log").read_text()

review_base = root / "verification/phoenix-foundation-review"
review = json.loads(bind(review_base / "receipt.json").read_text())
assert review["status"] == "passed"
assert all(review["cleanup"].values())
for command in review["commands"]:
    bind(command["output"], command["sha256"])
    assert command["exit_code"] == command["expected_exit_code"]
assert "Result: 5 passed" in (review_base / "commands/adversarial-tests.log").read_text()
summary = json.loads(bind(review_base / "review-summary.json").read_text())
for artifact in summary["artifacts"]:
    bind(artifact["path"], artifact["sha256"])
bind("docs/phoenix-foundation-review.md", "58edd4081ca8717a33e38fb69fcea8abdc9d7bf59921a232d011505ab04dfd8f")

identity_base = root / "verification/hosted-identity-contract"
identity = json.loads(bind(identity_base / "receipt.json").read_text())
assert identity["all_expected_results"]
for command in identity["commands"]:
    assert command["passed"] and not command["timed_out"]
    assert command["exit_code"] == command["expected_exit_code"]
    for stream in ["stdout", "stderr"]:
        bind(command[stream], command[stream + "_sha256"])
for artifact in identity["artifacts"]:
    bind(artifact["path"], artifact["sha256"])
bind("mixer-product-plan.md", "b797eb9f4b4106fe85acbd29481270ecb0fae0f2c5d3bbf3fa85e0bed8b7836d")

inventory = json.loads(bind(base / "dependencies.json").read_text())
bind("hosted/mix.lock", inventory["lock_sha256"])
assert len(inventory["dependencies"]) == 19
for dependency in inventory["dependencies"]:
    for path, expected in dependency["notice_files"].items():
        bind(path, expected)

for path in ["docs/phoenix-foundation.md", ".github/workflows/hosted.yml", "THIRD_PARTY.yml", __file__]:
    bind(path)

receipt = {
    "schema": 1,
    "recorded_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "accepted-scoped-foundation-and-identity-design",
    "source_tree_sha256": candidate["source_tree_sha256"],
    "reviewer": "root",
    "executed_by_root": "Eight host tests, packaged release build and exact missing-setting rejection; all logs and archived source rechecked.",
    "independent_review": "Five actual host adversarial tests; frozen candidate-2 production inputs equal candidate-5. Root audited retained source and command bindings; no third replay claimed.",
    "identity_design_decision": "Accept six-role ceilings, explicit environment grants, authoritative membership/transaction locking and revocation ordering, trusted-API RLS boundary, and artifact-only first slice. Declaration checks are not authentication implementation.",
    "limitations": candidate["limitations"] + [
        "No product release routes, real identity, restricted-role RLS, cloud deployment, global quotas, fences, external effects, protocol migration parity or GA acceptance.",
        "Four Hex packages need upstream notice collection before distribution; inventory is not license release approval.",
        "New Linux workflow is pending its first hosted run. All mobile runtime and computer-use tests remain paused."
    ],
    "bindings": bindings
}
(base / "root-acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n")
identity_acceptance = {
    "schema": 1, "status": "accepted-implementation-design-only", "reviewer": "root",
    "decision": receipt["identity_design_decision"],
    "contract_sha256": bindings["docs/hosted-identity-contract.md"],
    "evidence_receipt_sha256": bindings["verification/hosted-identity-contract/receipt.json"],
    "root_receipt": "verification/phoenix-foundation/root-acceptance.json",
    "limitations": "No provider/library choice, authentication/authorization implementation, hosted qualification or GA pass."
}
(identity_base / "root-acceptance.json").write_text(json.dumps(identity_acceptance, indent=2) + "\n")
print(json.dumps({"status": receipt["status"], "bindings": len(bindings), "source_tree_sha256": candidate["source_tree_sha256"]}))
