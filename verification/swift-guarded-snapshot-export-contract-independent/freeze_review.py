#!/usr/bin/env python3
"""Verify released immutable inputs and seal independent required failures."""
import hashlib
import json
from pathlib import Path
import shutil
from datetime import datetime, timezone

OWN = Path(__file__).resolve().parent
REPO = OWN.parents[1]

def digest(data):
    return hashlib.sha256(data).hexdigest()

def identity(path, name):
    assert path.is_file() and not path.is_symlink(), path
    data = path.read_bytes()
    return {"path": name, "bytes": len(data), "sha256": digest(data)}

def inventory(root, excluded=None):
    paths = sorted(root.rglob("*"))
    assert not any(p.is_symlink() for p in paths)
    return [identity(p, p.relative_to(root).as_posix()) for p in paths if p.is_file() and p != excluded]

def verify(root, expected):
    seal = identity(root / "seal.json", "seal.json")
    assert seal["sha256"] == expected
    declared = json.loads((root / "seal.json").read_text())
    actual = inventory(root, root / "seal.json")
    assert actual == declared["members"] and len(actual) == declared["member_count"]
    total = sum(m["bytes"] for m in actual)
    assert total == declared.get("bytes", declared.get("member_bytes"))
    if declared.get("tree_digest_algorithm") == "sha256 of sorted per-member lines: sha256 SPACE decimal-bytes SPACE relative-path LF":
        tree = digest("".join(m["sha256"] + " " + str(m["bytes"]) + " " + m["path"] + "\n" for m in actual).encode())
    else:
        assert "tree_digest_algorithm" not in declared
        tree = digest(json.dumps(actual, sort_keys=True, separators=(",", ":")).encode())
    if "tree_sha256" in declared:
        assert tree == declared["tree_sha256"]
    return {"seal": seal, "members": len(actual), "bytes": total, "tree_sha256": tree}

def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

assert not (OWN / "seal.json").exists(), "Do not rewrite a frozen review"
assert not (OWN / "owned-work").exists()
preaccess = identity(OWN / "preaccess-freeze.json", "preaccess-freeze.json")
assert preaccess["sha256"] == "716d8c93a5f5dd3ee7e0b5caafb1848e1c4697e2e21a03a77f5ded6ddab4a893"
pre = json.loads((OWN / "preaccess-freeze.json").read_text())
assert identity(OWN / "preaccess-requirements.md", pre["requirements"]["path"]) == pre["requirements"]
producer = verify(OWN / "candidate", "7787c8bbd9164ebdd360186f79c5d696739e89d6b08cd2f7cfbc71e9c156a1fe")
assert producer == verify(REPO / "verification/swift-guarded-snapshot-export-preparation", producer["seal"]["sha256"])
controls = json.loads((OWN / "controls-result.json").read_text())
assert controls["group_count"] == 12 and controls["passed_groups"] == 10
assert controls["failed_groups"] == ["F03", "F05"]
assert controls["runner_sha256"] == digest((OWN / "review_controls.py").read_bytes())
failed = [c["name"] for g in controls["groups"] for c in g["subcases"] if not c["expectation_met"]]
assert failed == ["bad-memory-minimum-duplicate", "bad-memory-host-duplicate", "bad-table-minimum-duplicate", "bad-table-max-option-duplicate", "bad-runtime-type-count-duplicate"]
released = json.loads((OWN / "released-peer-inputs.json").read_text())
assert all(p["explicitly_released"] for p in released)
peers = []
for peer in released:
    root = REPO / peer["path"]
    verified = verify(root, peer["seal_sha256"])
    destination = OWN / "peer-inputs" / root.name
    assert not destination.exists()
    shutil.copytree(root, destination)
    assert verify(destination, peer["seal_sha256"]) == verified
    peers.append({"path": peer["path"], "verified": verified, "fresh_main_controls": False})
write(OWN / "review-result.json", {
    "schema": 1, "at": datetime.now(timezone.utc).isoformat(),
    "status": "contract-corrections-required-before-root-implementation-selection",
    "root_is_final_selector": True, "producer": producer, "preaccess": preaccess,
    "source_revision_context": "606c42876855897c315ee279dcd38fabaeb561ad",
    "accepted_source_tree_sha256": "9fbdabbc5122f71809483b3b0a0e95a71b9813def61572f366bcebc8ac6d08fb",
    "fresh_control_groups": 12, "fresh_subcases": 37, "passed_groups": 10,
    "failed_groups": controls["failed_groups"], "failed_subcases": failed,
    "ordinary_production_builds": 2, "external_expected_negative_compilations": 9,
    "findings": [
        {"id": "R1", "priority": 1, "scope": "explicit duplicated immutable-field joins missing from proposed decoder; five genuine failures retained"},
        {"id": "R2", "priority": 2, "scope": "actual MIXLSE01 first section is Source File identity; correct prose only"},
        {"id": "R3", "priority": 2, "scope": "existing cache prepare generic entry incorrectly marked absent/planned in source roster"}],
    "peer_packets": peers,
    "executed_command": {"argv": ["python3", "-B", "verification/swift-guarded-snapshot-export-contract-independent/review_controls.py"], "cwd": str(REPO), "exit_code": 1, "reason": "required F03/F05 refusal expectations failed; no other subcase failed"},
    "read_attempt_failures_retained": [{"command": "cat binding-review README.md and guessed review-result.json", "exit_code": 1, "output": "README was read; review-result.json absent", "resolution": "Read exact audit-result.json named in released README; no peer mutation."}],
    "pending_before_implementation_selection": ["exact pre-guard work allowance", "read-only deadline/cancellation and failure observation", "complete outer result and source-place roster", "actual same-owner runtime/WASI observation", "fresh actual unit/production layout and simultaneous admission measurements", "separate exact-floor host-only positive grant"],
    "not_accepted": ["working exporter", "original all-eight behavior and partial output", "operational loader/output storage admission", "actual File-close/name/hash custody", "semantic context/FSM/full workload", "canonical product integration", "native/device/FieldLog package", "OTA/store/customer/operational/GA"],
    "canonical_product_changed": False, "GA_gates_verified": 0,
    "cleanup": controls["cleanup"], "producer_or_peer_wrappers_replayed": False,
})
(OWN / "README.md").write_text("# Frozen independent guarded snapshot export contract review\n\nRead review.md and review-result.json. Contract corrections R1/R2/R3 are required\nbefore root implementation selection. Fresh controls retain 12 groups/37\nsubcases: ten groups pass; F03/F05 retain five genuine contradictory-fixture\nfailures. Baseline ordinary-production privacy passes; no exporter or native\nruntime acceptance follows. The original producer is unchanged.\n\npreaccess-freeze.json was frozen before producer release. candidate-custody.json\nrecords the released 639-member producer copy. Released peer packets are copied\nunder peer-inputs/ with separate scope and are not counted as fresh main controls.\nThe seal covers all owned files except itself; no compiler products or scratch remain.\n")
members = inventory(OWN, OWN / "seal.json")
seal = {"schema": 1, "scope": "frozen independent guarded snapshot export contract review; required corrections and genuine failed controls retained; no implementation acceptance", "member_count": len(members), "bytes": sum(m["bytes"] for m in members), "tree_sha256": digest(json.dumps(members, sort_keys=True, separators=(",", ":")).encode()), "members": members}
write(OWN / "seal.json", seal)
print(json.dumps({"seal": identity(OWN / "seal.json", "seal.json"), "members": seal["member_count"], "bytes": seal["bytes"], "tree_sha256": seal["tree_sha256"]}, sort_keys=True))
