#!/usr/bin/env python3
"""Freeze the independent documentation review and ordinary contract models.

No database, product compilation, BEAM dependency, provider, native runtime,
browser, capture, broad hosted harness, or foreign-lane runner is executed.
"""

import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import uuid


ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = pathlib.Path(__file__).resolve().parent
PRODUCER = ROOT / "verification/hosted-browser-callback-claim"
PRODUCT = [
    "hosted/lib/mixer_hosted/browser_auth/runtime_owner.ex",
    "hosted/lib/mixer_hosted/browser_auth/preauth_draft.ex",
    "hosted/lib/mixer_hosted/browser_auth/store.ex",
    "hosted/lib/mixer_hosted/browser_auth/protocol.ex",
    "hosted/lib/mixer_hosted/browser_auth/config.ex",
    "hosted/lib/mixer_hosted/browser_auth/runtime_config.ex",
    "hosted/lib/mixer_hosted/browser_auth/vault.ex",
    "hosted/lib/mixer_hosted/browser_auth/stored_snapshot.ex",
    "hosted/lib/mixer_hosted/browser_auth/lifecycle_repo.ex",
    "hosted/lib/mixer_hosted/browser_auth/storage_schema.ex",
    "hosted/lib/mixer_hosted/browser_auth/activation_preparation.ex",
    "hosted/lib/mixer_hosted/browser_auth/activation_preparation_schema.ex",
    "hosted/lib/mixer_hosted/identity/key_owner.ex",
]
CONTEXT = [
    "AGENTS.md",
    "mixer-product-plan.md",
    "docs/hosted-browser-lifecycle-runtime-contract.md",
    "docs/hosted-browser-begin-login.md",
    "docs/hosted-browser-begin-login-review.md",
    "docs/hosted-browser-callback-claim.md",
    "verification/hosted-browser-callback-claim/contract.json",
    "verification/hosted-browser-callback-claim/run.py",
    "verification/hosted-browser-callback-claim/handoff.json",
    "verification/hosted-browser-callback-claim/handoff.sha256",
    "verification/hosted-browser-callback-claim-review/contract_model.py",
    "verification/hosted-browser-callback-claim-review/run_review.py",
]
ACCEPTED = {
    PRODUCT[0]: "007ab3e8445820318ed503337b0c2693d0e703227eb8b0202d21cd1330666580",
    PRODUCT[1]: "143f34f3c0810e290b4ccfa4460b86fee0482b33573a6fc604aeeac27498cbbd",
    PRODUCT[2]: "6c02fff8454790449b3ebe70695fc3adfd537d899b24411ee6585171578c8e43",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def serial(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def command(argv):
    completed = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=30)
    return {
        "argv": argv,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def git_text(*args):
    result = command(["git", *args])
    if result["exit_code"]:
        raise RuntimeError("git command failed")
    return result["stdout"].decode().strip()


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    attempt = BASE / "attempts" / (stamp + "-" + uuid.uuid4().hex[:8])
    attempt.mkdir(parents=True, exist_ok=False)
    inputs = {}
    for name in PRODUCT + CONTEXT:
        data = (ROOT / name).read_bytes()
        target = attempt / "inputs" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        inputs[name] = {"bytes": len(data), "sha256": digest(data)}

    handoff_data = (PRODUCER / "handoff.json").read_bytes()
    handoff = json.loads(handoff_data)
    contract = json.loads((PRODUCER / "contract.json").read_bytes())
    selected_receipt_path = handoff["selected_attempt"] + "/receipt.json"
    selected_receipt_data = (ROOT / selected_receipt_path).read_bytes()
    selected_receipt = json.loads(selected_receipt_data)
    target = attempt / "inputs" / selected_receipt_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(selected_receipt_data)
    inputs[selected_receipt_path] = {"bytes": len(selected_receipt_data), "sha256": digest(selected_receipt_data)}

    checks = {}
    checks["producer_handoff_sha256_matches"] = digest(handoff_data) == (PRODUCER / "handoff.sha256").read_text().strip()
    checks["producer_selected_receipt_matches_manifest"] = inputs[selected_receipt_path] == handoff["members"][selected_receipt_path]
    checks["producer_selected_receipt_passed_structure_only"] = selected_receipt["exit_code"] == 0 and handoff["runtime_security_pass_claim"] is False
    checks["producer_current_document_and_contract_match"] = all(
        inputs[name] == handoff["members"][name]
        for name in (
            "docs/hosted-browser-callback-claim.md",
            "verification/hosted-browser-callback-claim/contract.json",
            "verification/hosted-browser-callback-claim/run.py",
        )
    )
    checks["accepted_begin_source_hashes_unchanged"] = all(inputs[name]["sha256"] == expected for name, expected in ACCEPTED.items())
    checks["all_producer_runtime_cases_remain_pending"] = len(contract["runtime_matrix"]) >= 37 and all(case["status"] == "pending" for case in contract["runtime_matrix"])
    checks["storage_prerequisite_has_no_public_claim_or_provider_effect"] = contract["scope"]["claim_publication_in_a"] is False and contract["scope"]["provider_exchange"] is False and contract["scope"]["application_wiring"] is False
    checks["no_schema_or_catalog_change_authorized"] = contract["sql_changes_required"] == [] and contract["catalog_changes_required"] == []
    checks["one_combined_cap_and_original_lifetimes"] = contract["limits"]["combined_operations_and_claims"] == 32 and contract["limits"]["pool_size"] == 2 and contract["limits"]["operation_ms"] == 5000 and contract["limits"]["maximum_claim_ms_from_original_entry"] == 60000 and contract["limits"]["queue"] is False and contract["limits"]["retry"] is False

    result = command([sys.executable, "-B", str(attempt / "inputs/verification/hosted-browser-callback-claim-review/contract_model.py")])
    (attempt / "model.stdout.txt").write_bytes(result["stdout"])
    (attempt / "model.stderr.txt").write_bytes(result["stderr"])
    checks["independent_contract_models_pass"] = result["exit_code"] == 0 and b"Ran 14 tests" in result["stderr"] and result["stderr"].rstrip().endswith(b"OK")
    checks["all_selected_product_and_context_inputs_stable"] = all(digest((ROOT / name).read_bytes()) == record["sha256"] for name, record in inputs.items())
    summary = {
        "evidence_kind": "independent_source_review_and_contract_models_only",
        "checks": checks,
        "passed": all(checks.values()),
        "contract_model_methods_passed": 14 if checks["independent_contract_models_pass"] else 0,
        "product_runtime_cases_passed": 0,
        "producer_runtime_cases_pending": len(contract["runtime_matrix"]),
    }
    (attempt / "summary.json").write_bytes(serial(summary))
    source_tree = {name: inputs[name] for name in PRODUCT}
    receipt = {
        "schema": 1,
        "scope": "Independent callback contract review; ordinary Python model tests only. No product implementation or runtime security acceptance.",
        "requested_agent": {"model": "gpt-6.1-sol", "reasoning_effort": "xhigh", "context": "fresh", "evidence": "parent dispatch"},
        "command": [sys.executable, "-B", str(pathlib.Path(__file__).resolve())],
        "model_command": result["argv"],
        "working_directory": str(ROOT),
        "revision": git_text("rev-parse", "HEAD"),
        "git_tree": git_text("rev-parse", "HEAD^{tree}"),
        "selected_source_tree_sha256": digest(serial(source_tree)),
        "producer_handoff_sha256": digest(handoff_data),
        "producer_selected_attempt": handoff["selected_attempt"],
        "inputs": inputs,
        "tools": {"python": sys.version, "git": git_text("--version")},
        "dependencies": "Python standard library only; no BEAM/product/runtime dependencies executed",
        "outputs": {name: {"bytes": (attempt / name).stat().st_size, "sha256": digest((attempt / name).read_bytes())} for name in ("model.stdout.txt", "model.stderr.txt", "summary.json")},
        "exit_code": 0 if summary["passed"] else 1,
        "cleanup": {
            "owned_runtime_or_scratch_created": [],
            "owned_database_started": False,
            "owned_beam_started": False,
            "native_or_capture_started": False,
            "browser_or_ui_used": False,
            "provider_or_customer_network_used": False,
            "unrelated_process_discovery_used": False,
            "product_sources_edited": [],
            "cleanup_required": False,
            "retained_artifacts": "Only immutable owned review evidence; -B suppresses Python bytecode scratch.",
        },
    }
    receipt_data = serial(receipt)
    (attempt / "receipt.json").write_bytes(receipt_data)
    (attempt / "receipt.sha256").write_text(digest(receipt_data) + "\n")
    selected = {"attempt": str(attempt.relative_to(ROOT)), "receipt_sha256": digest(receipt_data), "producer_handoff_sha256": digest(handoff_data), "passed": summary["passed"], "evidence_kind": summary["evidence_kind"]}
    (BASE / "selected.json").write_bytes(serial(selected))
    print(json.dumps(selected, sort_keys=True))
    return receipt["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
