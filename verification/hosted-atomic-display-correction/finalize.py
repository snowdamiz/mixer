#!/usr/bin/env python3
"""Freeze only this bounded correction packet after observed local executions."""
import datetime
import hashlib
import json
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DOCUMENT = ROOT / "docs/hosted-atomic-display-correction.md"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def observe(argv):
    before = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, check=True)
    return {"argv": argv, "cwd": str(ROOT), "started_utc": before,
            "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr,
            "stdout_sha256": sha(result.stdout.encode()), "stderr_sha256": sha(result.stderr.encode())}


upstream_check = observe(["python3", "-B", "verification/hosted-atomic-storage-correction-review/check.py"])
write(HERE / "upstream-validation.json", upstream_check)
assert json.loads(upstream_check["stdout"])["bindings"] == 213
oracles = [observe(["python3", "-B", "verification/hosted-atomic-display-correction/row-oracle.py", run]) for run in ["run-3", "run-4"]]
write(HERE / "row-oracle-results.json", oracles)
attempts = [read(path / "receipt.json") for path in sorted(HERE.glob("run-*")) if path.is_dir()]
assert len(attempts) == 4
full = attempts[2]
assert full["passed"] and full["test_summary"] == {"total": 88, "failures": 0, "skipped": 0, "excluded": 0}
assert attempts[3]["passed"] and attempts[3]["test_summary"] == {"total": 88, "failures": 0, "skipped": 0, "excluded": 83}
commands = read(HERE / "run-3/commands.json")
versions = [item for item in commands if item["argv"] in [["python3", "--version"], ["elixir", "--version"], ["mix", "--version"], ["postgres", "--version"], ["pg_ctl", "--version"], ["psql", "--version"], ["go", "version"]]]
receipt = {
    "schema": 1,
    "status": "isolated-display-correction-passed-independent-review-pending",
    "frozen_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "scope": "Local synthetic atomic-storage exact display formatter correction only; no live hosted code or GA acceptance",
    "selection": "docs/hosted-atomic-display-correction-contract.md",
    "root_direction": "verification/hosted-atomic-storage-root-review/display-correction-direction.json",
    "upstream_bindings_verified": len(read(HERE / "upstream-inputs.json")["files"]),
    "upstream_final_review_receipt_sha256": "b361c631907be071f36bbe9c702ea160918a6ea08c3289cd2dd01a3a3d8989a9",
    "upstream_final_review_seal_sha256": "4950c4faa49d7c017841329e9473db2dcc0983b11d3166fd3ec4d77547ebc28b",
    "upstream_final_review_bindings_freshly_verified": 213,
    "upstream_producer_receipt_sha256": "863b10881f8133e83dd54610e03c39dea46cbf7fa750fe6e456c2339396c51a7",
    "upstream_producer_seal_sha256": "496220a8e0713844adb38b339785d1cba4ae082fcf66d2b74b05d47c8d96dbff",
    "frozen_base": "verification/hosted-atomic-storage-corrected-preflight/run-6/inputs",
    "observed_execution_head": full["observed_head"],
    "baseline_failure_run": "run-1", "baseline_failures": ["I02", "I03"],
    "first_expanded_run": "run-2",
    "first_expanded_failure": "D05 new assertion expected false; unchanged SQL row_valid correctly raises P0001 for corrupted exact display bytes. Only this new assertion was corrected.",
    "full_passing_run": "run-3", "full_summary": full["test_summary"],
    "focused_passing_run": "run-4", "focused_summary": attempts[3]["test_summary"],
    "original_assertions_preserved": 83, "added_assertions": 5,
    "new_actual_postgresql_parity_cases": 56,
    "new_complete_uploaded_replayed_rows": 56,
    "original_reviewer_uploaded_replayed_rows": 8,
    "additional_stored_byte_boundary_rows": 2,
    "stdlib_cross_checked_complete_rows": 64,
    "unchanged_installed_catalog_sha256": full["installed_catalog_sha256"],
    "catalog_scope": "Equality to frozen synthetic specimen only; not production startup inspector/trigger-enabled/internal-FK/persistence qualification",
    "implementation_delta": ["probe/lib/codec.ex: PostgreSQL source-string formatter only"],
    "sql_catalog_cbor_and_storage_code_byte_identical": True,
    "all_83_original_assertion_bodies_unchanged": True,
    "exact_equality_unchanged": True,
    "literal_escape_and_utf8_bytes_preserved": True,
    "nul_and_malformed_unicode_explicit_invalid_storage": True,
    "full_source_and_runner_digest": full["probe_source_tree_digest"],
    "tool_versions": versions,
    "dependency_baseline": "bc45a20298533b70808607b8228473b1d1efa81d",
    "dependency_source_closure": "Each run archives accepted lock and per-package source manifest; archive inner/outer checksums and every copied source member verified; no dependency added",
    "legacy_source_closure": "Frozen legacy-services plus exact per-run source copies and manifests, used offline in disposable Go caches",
    "all_attempts": attempts,
    "all_owned_cleanup_verified": all(all(attempt["cleanup"][key] for key in ["owned_proxy_stopped", "owned_postgres_stopped", "owned_scratch_removed", "owned_socket_removed"]) for attempt in attempts),
    "document_sha256": sha(DOCUMENT.read_bytes()),
    "independent_review_pending": True, "root_acceptance": False,
    "repository_acceptance": False, "full_as05_acceptance": False,
    "product_implementation": False, "migration": False,
    "provider_or_ga_acceptance": False, "native_or_physical_runs": False,
    "dependency_additions": False, "commits_created": False,
    "limitations": [
        "Fresh independent review and root acceptance remain required before integration.",
        "Synthetic fixed policy/clock/tenant/target; no complete authoritative credential/profile/membership resolver or five-lock product seam.",
        "No live product migration/helper ACL manifest/startup inspector/repository/HTTP/signed-admission composition.",
        "Catalog equality does not qualify production trigger-enabled/internal FK states or UNLOGGED persistence drift hardening.",
        "No Neon/R2/Cloudflare/Linux service/Oban lifecycle/provider/operational/customer/FieldLog/GA acceptance.",
        "Bounded adjacent-edge checks and cached semantic linkage do not prove whole-history or original-key provenance against privileged coherent offline rewrite.",
        "Known completed-COMMIT acknowledgement loss/restart/replay is preserved; arbitrary cancellation/provider/WAL timing and already-sent COMMIT-after-expiry remain outside this guarantee.",
        "No native tests; physical phones remain disconnected/deferred; no other-project processes touched."
    ]
}
write(HERE / "receipt.json", receipt)
files = [DOCUMENT] + sorted(path for path in HERE.rglob("*") if path.is_file() and path not in {HERE / "artifact-manifest.json", HERE / "seal.json"})
manifest = {"schema": 1, "files": [{"path": str(path.relative_to(ROOT)), "sha256": sha(path.read_bytes()), "bytes": path.stat().st_size} for path in files]}
write(HERE / "artifact-manifest.json", manifest)
write(HERE / "seal.json", {"schema": 1, "bindings": len(files), "manifest_sha256": sha((HERE / "artifact-manifest.json").read_bytes()), "receipt_sha256": sha((HERE / "receipt.json").read_bytes()), "independent_review_pending": True, "root_acceptance": False, "repository_acceptance": False, "full_as05_acceptance": False})
print(json.dumps({"bindings": len(files), "receipt_sha256": sha((HERE / "receipt.json").read_bytes()), "seal_sha256": sha((HERE / "seal.json").read_bytes()), "status": receipt["status"]}))
