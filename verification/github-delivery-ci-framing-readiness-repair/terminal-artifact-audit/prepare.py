"""Copy reviewed data-only auditors into this fresh, bounded evidence folder."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SOURCE = REPO / "verification/github-delivery-membership-review-checkpoint/terminal-artifact-audit"
OLD_SHA = "62db9518c0c108cb44b81455c9be239df4ee00db"
SHA = "a9ea84aa33320cadaed2340fe637324b694a917f"
OLD_TREE = "7b9034a6ec66e310b21be570d1df5d5b9b67ceab"
TREE = "52e887a6a99623b6a2f6f2c5e9788147e0fb91fd"
OLD_RUN = "40400072603"
RUN = "40410911137"
OLD_FIXTURE = "verification/github-delivery-membership-review-checkpoint/fixture-artifact-audit/acceptance.json"
FIXTURE = "verification/github-delivery-ci-framing-readiness-repair/fixture-artifact-audit/acceptance.json"
OLD_FIXTURE_SHA256 = "4a88d30911f0c5ac13bbcba8d7d8e09f71a68f3dda53e502ab2c21f866eef4ea"
FIXTURE_SHA256 = "f8a67c214a903018dba3acb99cb88f0885895ebdaa6fd96032978311df31b0cd"
SEAL = REPO / "verification/github-delivery-ci-framing-readiness-repair/fixture-artifact-audit/seal.json"
CUSTODY = REPO / "verification/github-delivery-ci-framing-readiness-repair/fixture-audit-root-custody.json"


def digest(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


assert __debug__ and not (HERE / "preparation.json").exists()
assert digest((REPO / FIXTURE).read_bytes())["sha256"] == FIXTURE_SHA256
assert digest(SEAL.read_bytes())["sha256"] == "cc80a8da335e59246a56649e72e2afd2d03930843d7ffe2fde46cd2be7c9d019"
assert digest(CUSTODY.read_bytes())["sha256"] == "e347e60794b620b657808a49f93e319805093c88b43275a8c65a500ccb0b6191"
records = []
for name in ("audit.py", "capability_review.py", "collect-and-review.py", "freeze.py", "run-reviewed.py"):
    target = HERE / name
    assert not target.exists()
    original = (SOURCE / name).read_bytes()
    adapted = original.decode()
    changes = []
    for old, new in ((OLD_SHA, SHA), (OLD_TREE, TREE), (OLD_RUN, RUN),
                     (OLD_FIXTURE, FIXTURE), (OLD_FIXTURE_SHA256, FIXTURE_SHA256)):
        count = adapted.count(old)
        if count:
            adapted = adapted.replace(old, new)
            changes.append({"old": old, "new": new, "occurrences": count})
    target.write_bytes(adapted.encode())
    records.append({"source": str((SOURCE / name).relative_to(REPO)),
                    "target": str(target.relative_to(REPO)),
                    "source_digest": digest(original), "adapted_digest": digest(target.read_bytes()),
                    "literal_adaptations": changes})
receipt = {
    "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "argv": sys.argv, "python": sys.version,
    "source_revision": SHA, "source_tree": TREE, "run_id": int(RUN), "run_attempt": 1,
    "review": "Read all five prior auditor scripts before copying; subprocesses limited to read-only gh/git and new data-only local auditor children, each with 60 second child timeout. No old one-shot script executed.",
    "adaptation_scope": "Only current source SHA/tree/run and separate current fixture acceptance path/hash literals changed; capability auditor copied byte-for-byte.",
    "fixture_acceptance": {"path": FIXTURE, **digest((REPO / FIXTURE).read_bytes())},
    "fixture_seal": {"path": str(SEAL.relative_to(REPO)), **digest(SEAL.read_bytes())},
    "root_fixture_custody": {"path": str(CUSTODY.relative_to(REPO)), **digest(CUSTODY.read_bytes())},
    "scripts": records,
    "scope": "Fresh terminal six-job CI and selected core/JVM/capability retained artifact audit preparation only. No success claim before terminal CI and independent data audit.",
    "cleanup": {"native_or_capture_processes_started_or_queried": False,
                "artifact_code_extracted_or_executed": False, "git_mutations": False, "network_mutations": False},
}
(HERE / "preparation.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"status": "prepared", "scripts": len(records), "source_revision": SHA, "source_tree": TREE, "run_id": int(RUN)}))
