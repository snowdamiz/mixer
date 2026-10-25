#!/usr/bin/env python3
"""Verify the final independently reviewed local PostgreSQL slice."""
from pathlib import Path
import datetime
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SEALS = {
    "verification/hosted-customer-authorization-postgres/final-seal.json":
        "61c25aad3dc31050f6a196950a7a51fc21bad158f9f8936e884f568a36b8b6ff",
    "verification/hosted-customer-authorization-postgres-review/seal.json":
        "c51cdbe91de691a35edd387bbef0239de361f5738f58999d7e4434b3bfabfdae",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


bindings = {}
live = {}
counts = {}
for name, expected in SEALS.items():
    path = ROOT / name
    assert digest(path) == expected
    packet = json.loads(path.read_text())
    for field, collection in [("files", bindings), ("live_input_bindings", live)]:
        for member, expected_hash in packet[field].items():
            p = ROOT / member
            assert p.resolve().is_relative_to(ROOT) and not p.is_symlink()
            assert digest(p) == expected_hash, member
            if member in collection:
                assert collection[member] == expected_hash
            collection[member] = expected_hash
    counts[name] = {field: len(packet[field]) for field in ["files", "live_input_bindings"]}

summary = json.loads((ROOT / "verification/hosted-customer-authorization-postgres-review/result-summary.json").read_text())
assert summary["status"] == "accepted_finite_local_durable_lookup_and_selected_fixture_migration_integration"
assert summary["unresolved_findings"] == []
assert summary["closed_findings"] == ["AUTHZ-PG-REVIEW-001"]
assert summary["ordinary_migrations_applied"] == 5 and summary["ordinary_migration_idempotence"]
assert summary["owned_review_attempts_cleaned"] == 6
assert summary["producer_final_seal_mismatches"] == summary["producer_current_binding_mismatches"] == 0
receipt = {"schema": 1, "observedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "command": [sys.executable, str(Path(__file__).resolve())], "python": sys.version,
           "verifierSHA256": digest(Path(__file__)), "seals": SEALS, "counts": counts,
           "verifiedRetainedBindings": len(bindings), "verifiedCurrentBindings": len(live),
           "currentBindings": live, "independentRuns": summary["independent_runs"],
           "decision": "Accept finite local durable lookup and selected fixture/migration integration.",
           "pending": summary["pending"],
           "scope": "Pure policy evidence only; no protected domain authority, customer routes, deployment or GA acceptance."}
assert not (OUT / "acceptance.json").exists()
(OUT / "acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"retainedBindings": len(bindings), "currentBindings": len(live), "accepted": True}))
