#!/usr/bin/env python3
"""Static contract-packet verification only; never controller/runtime acceptance."""
import hashlib
import json
from pathlib import Path

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parent.parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def main():
    profile = json.loads((PACKET / "profile.json").read_text())
    required = {
        "shards": 16, "permanent_records_per_shard": 4096,
        "permanent_identity_limit": 65536, "page_record_limit": 32,
        "page_byte_limit": 65536, "pages_per_invocation": 16,
        "records_examined_per_invocation": 512, "wakes_per_invocation": 8,
        "unresolved_wakes_per_live_coordinator": 1, "invocation_budget_ms": 24000,
        "registry_rpc_wait_ms": 250, "recovery_rpc_wait_ms": 2500,
        "provider_call_wait_ms": 2000, "attention_failure_threshold": 8,
        "failure_counter_limit": 32, "skip_visits_limit": 7,
        "wall_time_slo_qualified": False, "permanent_record_deletion_allowed": False,
        "attention_records_remain_automatically_eligible": True,
        "production_clock_available": False, "production_provider_available": False,
        "restore_authority_qualified": False,
    }
    for key, value in required.items():
        assert profile[key] == value, ("profile", key)
    assert profile["shards"] * profile["permanent_records_per_shard"] == profile["permanent_identity_limit"]
    assert profile["page_record_limit"] * profile["pages_per_invocation"] == profile["records_examined_per_invocation"]
    assert profile["provider_call_wait_ms"] < profile["recovery_rpc_wait_ms"] < profile["invocation_budget_ms"]
    assert max(min(7, 2 ** min(failures, 3) - 1) for failures in range(33)) == 7

    definitions = json.loads((PACKET / "acceptance-cases.json").read_text())
    assert definitions["status"] == "definitions-only-runtime-pending"
    cases = definitions["cases"]
    ids = [case["id"] for case in cases]
    assert len(ids) == len(set(ids)) == 30
    assert {case["group"] for case in cases} == {
        "discovery", "ordering", "restore", "safety", "retention", "audit",
        "bounds", "availability", "codec", "integration",
    }
    for case in cases:
        assert set(case) == {"id", "group", "setup", "fault", "actions", "required"}
        assert case["actions"] and len(case["required"]) >= 2
        assert all(isinstance(item, str) and item for item in case["actions"] + case["required"])
    assert {
        "intent_track_crash_gap", "stop_registry_outage", "missing_positive_ledger",
        "audit_retry_attention_revisit", "capacity_exact_profile",
        "effect_barrier_final_authority", "claim_consumption_barrier",
        "page_fairness_wrap", "concurrent_audit_and_cas", "audit_unresolved_timeout",
    }.issubset(ids)

    fixtures = json.loads((PACKET / "identity-vectors.json").read_text())
    buckets = set()
    for fixture in fixtures["valid"]:
        identity = fixture["identity"]
        key_bytes = encoded([
            "mixer-worker-controller-do-v1", identity["environmentId"],
            identity["poolId"], identity["controllerId"], identity["operationId"],
        ])
        assert key_bytes.hex() == fixture["operation_key_bytes_hex"]
        assert digest(key_bytes) == identity["operationKey"]
        identity_bytes = encoded([
            "mixer-worker-pending-identity-v1", identity["namespaceGeneration"],
            identity["environmentId"], identity["poolId"], identity["controllerId"],
            identity["platform"], identity["operationKey"], identity["operationId"],
            identity["immutableSha256"],
        ])
        assert identity_bytes.hex() == fixture["identity_bytes_hex"]
        assert digest(identity_bytes) == fixture["identity_digest"]
        assert len(identity_bytes) <= profile["identity_byte_limit"]
        bucket = int(identity["operationKey"][0], 16)
        assert bucket == fixture["shard"]
        buckets.add(bucket)
    assert buckets == set(range(16))
    assert {item["reason"] for item in fixtures["invalid"]} == {
        "non_ascii_principal", "unknown_key", "uppercase_key", "oversize_principal",
    }

    bindings = json.loads((PACKET / "source-manifest.json").read_text())
    for binding in bindings["files"]:
        path = ROOT / binding["path"]
        raw = path.read_bytes()
        assert len(raw) == binding["bytes"] and digest(raw) == binding["sha256"], binding["path"]

    document = (ROOT / "docs/hosted-worker-pending-registry-contract.md").read_text()
    for name in ["public-contract.ts", "acceptance-cases.json"]:
        assert name in document
    types = (PACKET / "public-contract.ts").read_text()
    assert "WireRequest" not in types
    assert "export interface KnownOperationRecovery" in types
    assert "export interface PendingRegistry" in types
    for path in [ROOT / "docs/hosted-worker-pending-registry-contract.md"] + sorted(PACKET.iterdir()):
        if path.is_file() and path.suffix in {".json", ".py", ".ts", ".md"}:
            raw = path.read_bytes()
            assert raw.endswith(b"\n"), ("missing_final_newline", str(path))
            assert all(line.rstrip(b" \t") == line for line in raw.splitlines()), ("trailing_whitespace", str(path))
    print(json.dumps({
        "status": "passed", "scope": "static-contract-packet-only",
        "acceptance_cases_defined": len(cases), "identity_vectors_checked": len(fixtures["valid"]),
        "source_files_bound": len(bindings["files"]), "runtime_acceptance": "pending",
        "deployed_qualification": "pending", "live_source_changed": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
