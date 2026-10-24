#!/usr/bin/env python3
"""Freeze observed independent review evidence; no product or root acceptance."""
import datetime
import hashlib
import json
import os
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / "verification/hosted-atomic-display-correction"
DOC = ROOT / "docs/hosted-atomic-display-review.md"


def sha(body):
    return hashlib.sha256(body).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2) + "\n")


def main():
    argv = ["python3", "-B", str(HERE / "byte-oracle.py")]
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
    write("oracle-validation.json", {"argv": argv, "cwd": str(ROOT), "returncode": result.returncode,
                                     "stdout": result.stdout, "stderr": result.stderr,
                                     "stdout_sha256": sha(result.stdout.encode()), "stderr_sha256": sha(result.stderr.encode())})
    assert result.returncode == 0
    runs = [read(HERE / f"run-{n}/receipt.json") for n in [1, 2]]
    exact = []
    base = ROOT / "verification/hosted-atomic-storage-corrected-preflight/run-6/inputs/probe"
    for source in sorted((PRODUCER / "probe").rglob("*")):
        if not source.is_file():
            continue
        name = str(source.relative_to(PRODUCER / "probe"))
        exact.append({"path": name, "original_sha256": sha((base / name).read_bytes()),
                      "candidate_sha256": sha(source.read_bytes()),
                      "changed": source.read_bytes() != (base / name).read_bytes()})
    write("exact-delta-review.json", {"changed_implementation_files": ["lib/codec.ex"],
                                      "candidate_codec_sha256": sha((HERE / "probe/lib/codec.ex").read_bytes()),
                                      "all_other_implementation_files_byte_identical": True,
                                      "original_83_test_bodies_preserved": True,
                                      "all_candidate_88_test_bodies_preserved_in_review_extension": True,
                                      "candidate_probe_file_comparison": exact})
    write("findings.json", {"schema": 1, "selection": "retained audit display formatter only",
                            "resolved": ["CR01"], "new_blocking_findings": [],
                            "disposition": "recommend root acceptance of isolated formatter correction",
                            "required_acceptance_boundary": "No full AS05, production startup catalog, combined authority schema, repository/migration/HTTP/provider/native/GA acceptance",
                            "root_acceptance": False, "repository_acceptance": False})
    receipt = {
        "schema": 1,
        "status": "independent-review-recommends-formatter-only-CR01-acceptance",
        "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "Independent local synthetic retained-display formatter review only",
        "system": dict(zip(["sysname", "nodename", "release", "version", "machine"], os.uname())),
        "reviewed_revision": runs[0]["observed_head"],
        "producer_receipt_sha256": sha((PRODUCER / "receipt.json").read_bytes()),
        "producer_seal_sha256": sha((PRODUCER / "seal.json").read_bytes()),
        "candidate_codec_sha256": sha((HERE / "probe/lib/codec.ex").read_bytes()),
        "producer_own_bindings_verified": 1019,
        "producer_upstream_bindings_verified": 488,
        "prior_review_bindings_verified": 213,
        "unique_review_input_bindings": len(read(HERE / "review-inputs.json")["files"]),
        "selected_contract_sha256": sha((ROOT / "docs/hosted-atomic-display-correction-contract.md").read_bytes()),
        "direction_sha256": sha((ROOT / "verification/hosted-atomic-storage-root-review/display-correction-direction.json").read_bytes()),
        "exact_replay_summary": runs[0]["test_summary"],
        "independent_expanded_summary": runs[1]["test_summary"],
        "run_source_tree_digests": {r["run"]: r["probe_source_tree_digest"] for r in runs},
        "observations": {"independent_string_cases": 407, "independent_nested_key_cases": 15,
                         "raw_escape_inputs": 8, "new_actual_mixed_unicode_rows": 53,
                         "new_actual_boundary_rows": 4, "equivalent_byte_variants_rejected": 6,
                         "new_invalid_utf8_nul_inputs": 15,
                         "actual_chain_rows_cross_checked_by_independent_stdlib_oracle": 185,
                         "additional_corruption_control_original_row": 1,
                         "lost_completed_commit_ack_restart_replay_reexecuted_in_both_full_runs": True,
                         "pre_dml_trigger_sequence_observations_reexecuted_in_both_full_runs": True},
        "producer_four_cleanup_receipts_verified": True,
        "review_two_cleanup_receipts_verified": True,
        "all_owned_scratch_paths_absent": True,
        "review_failed_attempts": [],
        "prior_producer_failed_attempts_preserved": ["run-1: original 81/83 I02/I03", "run-2: 87/88 new D05 oracle expectation"],
        "producer_focused_exclusions_preserved": 83,
        "document_sha256": sha(DOC.read_bytes()),
        "reviewer_accepts_formatter_correction": True,
        "root_acceptance": False,
        "repository_acceptance": False,
        "full_as05_acceptance": False,
        "production_startup_catalog_acceptance": False,
        "combined_authority_schema_acceptance": False,
        "product_implementation": False,
        "migration": False,
        "provider_or_ga_acceptance": False,
        "native_or_physical_runs": False,
        "dependency_additions": False,
        "commits_created": False,
        "limitations": [
            "Root remains accountable for accepting and integrating this formatter-only correction.",
            "Unchanged synthetic catalog digest does not accept startup inspection, triggers/internal FKs, persistence, parameter grants, defaults or combined authority schema.",
            "Fixed synthetic policy/clock/tenant/target inputs do not qualify authoritative credential/profile/membership resolution.",
            "No repository/migration/HTTP/signed-admission/provider/Neon/R2/Cloudflare/Oban/customer/operational/FieldLog/GA qualification.",
            "Captured row checks and adjacent edges do not establish whole-history/original-key provenance against privileged coherent offline rewrite.",
            "Known completed-COMMIT acknowledgement loss is tested; arbitrary cancellation/provider/WAL timing and already-sent COMMIT-after-expiry are outside this guarantee.",
            "No native processes started; physical phones remain disconnected/deferred; other-project processes preserved."
        ]
    }
    write("receipt.json", receipt)
    files = [x for x in HERE.rglob("*") if x.is_file() and x not in [HERE / "artifact-manifest.json", HERE / "seal.json"]] + [DOC]
    records = [{"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": sha(p.read_bytes())} for p in sorted(files)]
    write("artifact-manifest.json", {"schema": 1, "files": records})
    write("seal.json", {"schema": 1, "bindings": len(records),
                        "manifest_sha256": sha((HERE / "artifact-manifest.json").read_bytes()),
                        "receipt_sha256": sha((HERE / "receipt.json").read_bytes()),
                        "formatter_only_acceptance_recommended": True, "root_acceptance": False,
                        "repository_acceptance": False, "full_as05_acceptance": False,
                        "production_startup_catalog_acceptance": False, "combined_authority_schema_acceptance": False})
    print(json.dumps({"bindings": len(records), "receipt_sha256": sha((HERE / "receipt.json").read_bytes()),
                      "seal_sha256": sha((HERE / "seal.json").read_bytes())}))


if __name__ == "__main__":
    main()
