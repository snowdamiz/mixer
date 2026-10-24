#!/usr/bin/env python3
"""Freeze only this review packet and its owned document; no producer mutation."""
import datetime
import hashlib
import json
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DOCUMENT = ROOT / "docs/hosted-atomic-storage-correction-review.md"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


oracle = subprocess.run(["python3", "-B", str(HERE / "row-oracle.py")], cwd=ROOT, capture_output=True, text=True, check=True)
(HERE / "row-oracle.log").write_text(oracle.stdout + oracle.stderr)
runs = [read(HERE / f"run-{n}/receipt.json") for n in range(1, 5)]
commands = read(HERE / "run-4/commands.json")
versions = [x for x in commands if x["argv"] in [["python3", "--version"], ["elixir", "--version"], ["mix", "--version"], ["postgres", "--version"], ["pg_ctl", "--version"], ["psql", "--version"], ["go", "version"]]]
receipt = {
    "schema": 1,
    "status": "correction-required-CR01-no-complete-AS05-acceptance",
    "frozen_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "accountable_recommendation": "Independent reviewer recommends retaining the supported synthetic mechanics while correcting exact Elixir PostgreSQL string formatting before complete AS05 or repository acceptance. Root acceptance remains separate.",
    "scope": "Independent local PostgreSQL17+Ecto synthetic atomic specimen review only",
    "producer_source_digest": "f346d03f1d279918d0b7a0ea965535bc757fa86874164dc8f14cc233642b21e1",
    "producer_document_sha256": "68f5031d8eb330cf38efeb4f4590ba9844f9121097d77568fa4e5c0134a71615",
    "producer_receipt_sha256": "863b10881f8133e83dd54610e03c39dea46cbf7fa750fe6e456c2339396c51a7",
    "producer_seal_sha256": "496220a8e0713844adb38b339785d1cba4ae082fcf66d2b74b05d47c8d96dbff",
    "producer_bindings_freshly_verified": 269,
    "observed_execution_head": runs[-1]["observed_head"],
    "original_corrected_suite_passing_run": "run-1",
    "original_corrected_suite_summary": runs[0]["test_summary"],
    "final_adversarial_run": "run-4",
    "final_adversarial_summary": runs[-1]["test_summary"],
    "final_source_and_runner_digest": runs[-1]["probe_source_tree_digest"],
    "original_cases": 41, "prior_independent_cases": 20, "correction_cases": 12, "new_independent_cases": 10,
    "new_independent_cases_passed": 8, "known_contract_failures": ["I02", "I03"], "mandatory_findings": ["CR01"],
    "canonical_suffix_rejections": 312, "valid_text_boundaries": 45, "display_counterexamples": 9, "actual_uploaded_rows_retained": 8, "actual_uploaded_valid_rows_elixir_rejects": 3,
    "installed_catalog_sha256": "5824cfe3629e65e2da8dcf4d831a10f22589a5b2bd38c02bbf58f90d23971883",
    "all_attempts": runs,
    "tool_versions": versions,
    "dependency_baseline": "bc45a20298533b70808607b8228473b1d1efa81d",
    "before_effect_nontransactional_observation": "expiry140/stale46 after confirmed final-read waits reject before any INSERT recorder is called; valid139 inserts twice and timestamps139; instrumentation dropped",
    "all_owned_cleanup_verified": all(r["cleanup"]["owned_proxy_stopped"] and r["cleanup"]["owned_postgres_stopped"] and r["cleanup"]["owned_scratch_removed"] and r["cleanup"]["owned_socket_removed"] for r in runs),
    "document_sha256": sha(DOCUMENT.read_bytes()),
    "row_oracle_command": ["python3", "-B", "verification/hosted-atomic-storage-correction-review/row-oracle.py"],
    "row_oracle_output_sha256": sha((HERE / "row-oracle.log").read_bytes()),
    "root_acceptance": False, "full_as05_acceptance": False, "repository_acceptance": False, "product_implementation": False, "migration": False, "provider_or_ga_acceptance": False, "native_or_physical_runs": False, "dependency_additions": False, "commits_created": False,
    "limitations": [
        "Synthetic fixed policy/clock/tenant/target only; no full authoritative credential/profile/membership resolver or five-lock product seam.",
        "CR01 exact-display false rejection remains open; all failed assertions retained. No SQL unauthorized-success or persistence-corruption bypass observed from CR01.",
        "No selected product migration/helper ACL manifest/startup inspector/repository/HTTP/signed-admission composition.",
        "No Neon/R2/Cloudflare/Linux service/Oban/domain jobs/multiprocess blob durability or operational/customer/FieldLog/GA acceptance.",
        "Bounded adjacent-edge checks and cached semantic linkage do not prove whole-history or original-key provenance against privileged coherent offline rewrite; independent commitment required for that stronger model.",
        "Known completed-COMMIT acknowledgement loss/restart/replay is preserved; arbitrary cancellation/provider/WAL timing and already-sent COMMIT-after-expiry remain outside this guarantee.",
        "Physical phones remain disconnected and deferred; no native instance or other-project process touched."
    ]
}
write(HERE / "receipt.json", receipt)
files = [DOCUMENT] + sorted(p for p in HERE.rglob("*") if p.is_file() and p.name not in {"artifact-manifest.json", "seal.json"})
manifest = {"schema": 1, "files": [{"path": str(p.relative_to(ROOT)), "sha256": sha(p.read_bytes()), "bytes": p.stat().st_size} for p in files]}
write(HERE / "artifact-manifest.json", manifest)
write(HERE / "seal.json", {"schema": 1, "bindings": len(files), "manifest_sha256": sha((HERE / "artifact-manifest.json").read_bytes()), "receipt_sha256": sha((HERE / "receipt.json").read_bytes()), "root_acceptance": False, "repository_acceptance": False, "full_as05_acceptance": False})
print(json.dumps({"bindings": len(files), "receipt_sha256": sha((HERE / "receipt.json").read_bytes()), "seal_sha256": sha((HERE / "seal.json").read_bytes()), "status": receipt["status"]}))
