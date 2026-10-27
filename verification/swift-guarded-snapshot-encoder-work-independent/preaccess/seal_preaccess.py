#!/usr/bin/env python3
"""Seal independent criteria without touching producer audit or composition."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]
ENCODER = REPO / "verification/swift-guarded-snapshot-encoder-implementation"
EXPECTED = {
    "verification/swift-guarded-snapshot-encoder-implementation/seal.json": "eadbe533d23459573ead21c7a9bac54ae929b98cdbc76dd47aebe34b5ceb2b1f",
    "verification/swift-semantic-adapter-root-review/guarded-snapshot-encoder-host-acceptance.json": "4d0eb23c7306e4d63d039f989391e59e45a928be98ece531f69f543952eb15cb",
    "verification/swift-guarded-snapshot-encoder-implementation/host/encoder.rs": "8e1eb4a6670ea4d6d408c4b527a777cd70ef821f625175ad6be037f890b9df27",
    "verification/swift-guarded-snapshot-encoder-implementation/source/vm/src/experimental/swift.rs": "dedb226175ec45b9c724a6bec6c8a9b43ed02c7de72970ea3f0cb7c5bc0d208f",
    "verification/swift-guarded-snapshot-encoder-implementation/source/vm/src/experimental_swift_reactor/control.rs": "c1d71faf33efe1264d4267623d19fe356aafc5a98e9a7871024e22682139776f",
    "verification/swift-guarded-snapshot-encoder-implementation/final-source-manifest.json": "1d4c432a2cbfa7ef8af7fc8e7c13df263a0275296a5fe11a412715c3cd580e46",
}


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2) + "\n")


def member(path, rel):
    data = path.read_bytes()
    return {"path": rel, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


if __name__ == "__main__":
    assert not (BASE / "seal.json").exists(), "preaccess seal is immutable; do not overwrite"
    inputs = []
    for rel, expected in EXPECTED.items():
        row = member(REPO / rel, rel)
        assert row["sha256"] == expected, (rel, row)
        row["expected_sha256_matches"] = True
        inputs.append(row)
    seal = json.loads((ENCODER / "seal.json").read_bytes())
    manifest = json.loads((ENCODER / "final-source-manifest.json").read_bytes())
    assert seal["member_count"] == len(seal["members"]) == 1256
    assert manifest["member_count"] == len(manifest["members"]) == 144
    assert manifest["tree_sha256"] == "447719d8fef2928674d9d196266408ca72c70ce152cf0251807d2c3bcd7e7c43"
    host = (ENCODER / "host/encoder.rs").read_bytes()
    swift = (ENCODER / "source/vm/src/experimental/swift.rs").read_bytes()
    assert swift.count(host) == 1
    line = swift[:swift.index(host)].count(b"\n") + 1
    assert line == 732
    results = json.loads((BASE / "arithmetic-results.json").read_bytes())
    assert results["status"] == "pass" and all(row["pass"] for row in results["checks"])
    dump(BASE / "source-custody.json", {
        "schema": 1, "inputs": inputs,
        "candidate_members_metadata_verified": 1256,
        "candidate_member_bytes_all_reverified": False,
        "source_members_metadata_verified": 144,
        "source_tree_declared_sha256": manifest["tree_sha256"],
        "host_encoder_exact_embedding_occurrences": 1,
        "host_encoder_first_embedded_line": line,
        "preaccess_producer_work_audit_read": False,
        "preaccess_active_composition_read": False,
        "preaccess_other_engine_bodies_read": [],
        "read_engine_bodies": ["host/encoder.rs", "source/vm/src/experimental/swift.rs (encoder embedding)", "source/vm/src/experimental_swift_reactor/control.rs (ExecutionWork semantics)"],
        "helper_body_coverage_pending": True,
    })
    dump(BASE / "receipt.json", {
        "schema": 1, "at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "python_version": sys.version,
        "commands": [
            "python3 verification/swift-guarded-snapshot-encoder-work-independent/preaccess/arithmetic_controls.py > verification/swift-guarded-snapshot-encoder-work-independent/preaccess/arithmetic-results.json",
            "python3 verification/swift-guarded-snapshot-encoder-work-independent/preaccess/seal_preaccess.py",
        ],
        "arithmetic_check_count": results["check_count"],
        "arithmetic_output": "arithmetic-results.json",
        "status": "criteria-and-independent-arithmetic-sealed-before-producer-access",
        "work_floor_selected": False,
        "operational_grant_selected": False,
        "writer_vm_compiler_executed": False,
        "native_runtime_ui_capture_process_inventory": "not started or inspected; paused",
        "cleanup": "No native instances, capture, VM, compiler, writer or child-process harnesses started by this lane. Only short host source/arithmetic commands ran. No broader process cleanup claimed.",
        "pending": ["released frozen producer audit", "exact helper and branch primitive coverage review", "complete work admission", "native and GA qualification"],
        "earlier_evidence": "Initial source/plan display exceeded tool display budget and was truncated; subsequent bounded reads and hashes establish the source actually used. No encoder/VM test failure was relabeled or retried.",
    })
    members = [member(p, str(p.relative_to(BASE))) for p in sorted(BASE.rglob("*")) if p.is_file()]
    preimage = json.dumps(members, sort_keys=True, separators=(",", ":")).encode()
    dump(BASE / "seal.json", {"schema": 1, "scope": "independent immutable preaccess criteria and arithmetic only", "members": members, "member_count": len(members), "bytes": sum(m["bytes"] for m in members), "tree_sha256": hashlib.sha256(preimage).hexdigest(), "tree_preimage": "UTF-8 JSON of members, sorted keys, compact separators; member paths sorted"})
    print(json.dumps(member(BASE / "seal.json", str((BASE / "seal.json").relative_to(REPO)))))
    print(json.dumps({"status": results["status"], "arithmetic_check_count": results["check_count"], "member_count": len(members)}))
