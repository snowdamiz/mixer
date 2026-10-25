#!/usr/bin/env python3
"""Source-bound documentation checker only; no runtime/security acceptance."""

import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import uuid


ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = pathlib.Path(__file__).resolve().parent
DOCUMENT = "docs/hosted-browser-callback-claim.md"
CONTRACT = "verification/hosted-browser-callback-claim/contract.json"
SEMANTIC = [
    "hosted/lib/mixer_hosted/browser_auth/preauth_draft.ex",
    "hosted/lib/mixer_hosted/browser_auth/runtime_owner.ex",
    "hosted/lib/mixer_hosted/browser_auth/store.ex",
    "hosted/lib/mixer_hosted/browser_auth/protocol.ex",
    "hosted/lib/mixer_hosted/browser_auth/vault.ex",
    "hosted/lib/mixer_hosted/browser_auth/stored_snapshot.ex",
    "hosted/lib/mixer_hosted/browser_auth/storage_schema.ex",
    "hosted/lib/mixer_hosted/browser_auth/catalog.ex",
    "hosted/lib/mixer_hosted/browser_auth/relation_catalog.ex",
    "hosted/lib/mixer_hosted/browser_auth/lifecycle_repo.ex",
    "hosted/lib/mixer_hosted/browser_auth/runtime_config.ex",
    "hosted/lib/mixer_hosted/browser_auth/custody.ex",
    "hosted/lib/mixer_hosted/browser_auth/configuration_digest.ex",
    "hosted/lib/mixer_hosted/browser_auth/config.ex",
]
CONTEXT = [
    "AGENTS.md",
    "PLAN.md",
    "mixer-product-plan.md",
    "docs/hosted-browser-auth-protocol.md",
    "docs/hosted-browser-lifecycle-runtime-contract.md",
    "docs/hosted-browser-preauth-store.md",
    "docs/hosted-browser-begin-login.md",
    "docs/hosted-browser-begin-login-review.md",
]
ACCEPTED = {
    SEMANTIC[0]: "143f34f3c0810e290b4ccfa4460b86fee0482b33573a6fc604aeeac27498cbbd",
    SEMANTIC[1]: "007ab3e8445820318ed503337b0c2693d0e703227eb8b0202d21cd1330666580",
    SEMANTIC[2]: "6c02fff8454790449b3ebe70695fc3adfd537d899b24411ee6585171578c8e43",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def serial(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def git(*args):
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    attempt = BASE / "attempts" / (stamp + "-" + uuid.uuid4().hex[:8])
    attempt.mkdir(parents=True, exist_ok=False)
    invocation = [sys.executable, str(pathlib.Path(__file__).resolve())]
    inputs = {}
    selected = SEMANTIC + CONTEXT + [DOCUMENT, CONTRACT, str(pathlib.Path(__file__).relative_to(ROOT))]
    for name in selected:
        data = (ROOT / name).read_bytes()
        target = attempt / "inputs" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        inputs[name] = {"sha256": digest(data), "bytes": len(data)}

    document = (attempt / "inputs" / DOCUMENT).read_text()
    contract = json.loads((attempt / "inputs" / CONTRACT).read_text())
    checks = []

    def require(name, condition):
        checks.append({"name": name, "passed": bool(condition)})

    require("contract is proposed and product edits are not authorized", contract["status"] == "proposed_for_independent_contract_review" and contract["scope"]["product_implementation_authorized"] is False)
    require("fresh Sol xhigh dispatch recorded", contract["delegation"]["requested_model"] == "gpt-6.1-sol" and contract["delegation"]["requested_reasoning_effort"] == "xhigh" and contract["delegation"]["context"] == "fresh")
    require("all parent accepted begin sources exactly match", all(inputs[name]["sha256"] == value for name, value in ACCEPTED.items()))
    require("no schema or catalog change proposed", contract["sql_changes_required"] == [] and contract["catalog_changes_required"] == [])
    require("A has only three fixed typed Store operations", contract["interfaces"]["unit_a"] == ["Store.discover_callback(%CallbackDraft.Discovery{})", "Store.claim(%CallbackDraft.Claim{}, metadata)", "Store.provider_reject(%CallbackDraft.Reject{}, metadata)"])
    require("no opaque claim or provider or Application effect in A", contract["scope"]["claim_publication_in_a"] is False and contract["scope"]["provider_exchange"] is False and contract["scope"]["application_wiring"] is False)
    require("actual pool and aggregate cap stay fixed", contract["limits"]["pool_size"] == 2 and contract["limits"]["combined_operations_and_claims"] == 32 and contract["limits"]["queue"] is False and contract["limits"]["retry"] is False)
    require("operation and claim deadlines retain original entry", contract["limits"]["operation_ms"] == 5000 and contract["limits"]["maximum_claim_ms_from_original_entry"] == 60000 and "initial** operation sample" in document)
    require("all 37 explicitly named runtime cases are pending", len(contract["runtime_matrix"]) == 37 and len({case["id"] for case in contract["runtime_matrix"]}) == 37 and all(case["status"] == "pending" and case["assertion"] for case in contract["runtime_matrix"]))
    require("A has exact pending active and full-output predicates", all(term in document for term in ["Active snapshots fail closed", "entire rediscovered StoredSnapshot", "only audit_sequence + 1", "attempt_envelope is nil", "provider_rejected", "no nil-success"]))
    require("fixed raw parsing and cookie binding are explicit", all(term in document for term in ["raw_cookie, raw_headers, raw_query, raw_body, metadata", "Protocol.parse_session_cookie(raw_headers)", "Protocol.parse_callback(lease.runtime.browser_config, raw_query, raw_body)"]))
    require("supervision and transfer keep real ownership", all(term in document for term in ["RuntimeOwner.enable_claims/0", "restart: :temporary", "at most 32 children", "retained original lease", "does **not** call ordinary finish/release", "late startup"]))
    require("timer and crash do not invent authorized failure", contract["scope"]["automatic_failure_sql_on_expiry_or_crash"] is False and "do **not** automatically" in document and "no stronger current-generation API" in document)
    require("product code has not gained proposed A interfaces", all(term not in (attempt / "inputs" / SEMANTIC[2]).read_text() for term in ["def discover_callback(", "def claim(", "def provider_reject("]))
    require("selected product sources stable throughout checker", all(digest((ROOT / name).read_bytes()) == inputs[name]["sha256"] for name in SEMANTIC))

    output = {
        "evidence_kind": "documentation_source_binding_only",
        "checks": checks,
        "passed": all(item["passed"] for item in checks),
        "runtime_cases_passed": 0,
        "runtime_cases_pending": len(contract["runtime_matrix"]),
    }
    stdout = serial(output)
    (attempt / "stdout.json").write_bytes(stdout)
    (attempt / "stderr.txt").write_bytes(b"")
    selected_tree = {name: inputs[name] for name in SEMANTIC}
    receipt = {
        "schema": 1,
        "scope": "contract/source review only; no product compile or runtime/security test",
        "command": invocation,
        "working_directory": str(ROOT),
        "revision": git("rev-parse", "HEAD"),
        "tools": {"python": sys.version, "git": git("--version")},
        "inputs": inputs,
        "semantic_source_tree_sha256": digest(serial(selected_tree)),
        "dependencies": "Python standard library only; no runtime dependency imported",
        "outputs": {"stdout.json": digest(stdout), "stderr.txt": digest(b"")},
        "exit_code": 0 if output["passed"] else 1,
        "cleanup": {
            "owned_database_started": False,
            "owned_beam_started": False,
            "owned_native_started": False,
            "capture_or_ui_started": False,
            "provider_or_customer_network_used": False,
            "unrelated_process_discovery_used": False,
            "temporary_runtime_resources_created": [],
            "cleanup_required": False,
        },
    }
    receipt_bytes = serial(receipt)
    (attempt / "receipt.json").write_bytes(receipt_bytes)
    (attempt / "receipt.sha256").write_text(digest(receipt_bytes) + "\n")
    members = [ROOT / DOCUMENT]
    members += [path for path in BASE.rglob("*") if path.is_file() and path.name not in {"handoff.json", "handoff.sha256"} and "__pycache__" not in path.parts]
    manifest = {str(path.relative_to(ROOT)): {"sha256": digest(path.read_bytes()), "bytes": path.stat().st_size} for path in sorted(members)}
    handoff = {
        "version": 1,
        "status": "proposed_contract_only",
        "selected_attempt": str(attempt.relative_to(ROOT)),
        "source_tree_sha256": receipt["semantic_source_tree_sha256"],
        "document_sha256": inputs[DOCUMENT]["sha256"],
        "contract_sha256": inputs[CONTRACT]["sha256"],
        "members": manifest,
        "runtime_security_pass_claim": False,
    }
    handoff_bytes = serial(handoff)
    (BASE / "handoff.json").write_bytes(handoff_bytes)
    (BASE / "handoff.sha256").write_text(digest(handoff_bytes) + "\n")
    print(json.dumps({"attempt": str(attempt.relative_to(ROOT)), "documentation_checks_passed": sum(item["passed"] for item in checks), "documentation_checks_total": len(checks), "runtime_cases_passed": 0, "runtime_cases_pending": len(contract["runtime_matrix"]), "passed": output["passed"], "handoff_sha256": digest(handoff_bytes)}, sort_keys=True))
    return receipt["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
