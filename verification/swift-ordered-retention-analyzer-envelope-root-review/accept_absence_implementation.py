"""Accept the exact isolated fixture-envelope scope after independent evidence."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
REVIEW = ROOT / "verification/swift-envelope-absent-state-behavior-review/final-review"


def identity(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


packets = []
for name, digest, count, size in [
    ("verification/swift-envelope-absent-state-correction/proposal-1/seal.json", "3da07ea9c308c9bee798cf7c891a8f9dfd2a170e85b43341c30caa38cdb9b04c", 35, 205372),
    ("verification/swift-envelope-absent-state-accounting-review/seal.json", "c9191a26ed0c5081e9c2ad97082fc61cee3f6eeb94ea49c4be5028b0f54536e4", 22, 119706),
    ("verification/swift-envelope-absent-state-correction/implementation/seal.json", "1e45ae55b5a159fd2c384bfdbbc520467e467b391af9f6a1d655e8ab67f0012a", 120, 8532453),
    ("verification/swift-envelope-absent-state-behavior-review/preaccess-seal.json", "e24d3bd09fd5bf07e5df86a03df2ca285eaea5837245666b3718c33b15fc56a4", 5, 21178),
    ("verification/swift-envelope-absent-state-behavior-review/preaccess-correction/seal.json", "485346537ab2c34bfeb14ff630c07bb9be7cd7fe3a9a7bceae59dcb1679debfd", 5, 22215),
    ("verification/swift-envelope-absent-state-behavior-review/final-review/seal.json", "84f93960a58b6f5fe04a3e1a95211e6c1e5b2bc38c58752e6703f83b3184d2f8", 220, 1331015),
]:
    assert identity(ROOT / name)["sha256"] == digest
    members = json.loads((ROOT / name).read_text())["members"]
    if isinstance(members, dict):
        members = [{"path": path, **row} for path, row in members.items()]
    assert len(members) == count and sum(row["bytes"] for row in members) == size
    for row in members:
        path = Path(row["path"])
        assert not path.is_absolute() and ".." not in path.parts
        assert identity(ROOT / path) == {k: row[k] for k in ("bytes", "sha256")}, str(path)
    packets.append({"seal": name, "sha256": digest, "members": count, "bytes": size})

final = json.loads((REVIEW / "final-receipt.json").read_text())
coverage = json.loads((REVIEW / "coverage.json").read_text())
assert final["candidate_defects_observed_in_scope"] == coverage["new_candidate_mismatches_found"] == 0
assert final["exact_source_methods_passed"] == coverage["exact_source_unique_methods_passed"] == 14
assert final["overlay_methods_passed"] == coverage["test_only_overlay_methods_passed"] == 2
assert final["API_positive"] == 1 and final["API_expected_negative"] == 8
assert coverage["API_intended_reasons_verified"]
assert coverage["R2_original_expected_and_actual_debits"] == [0] * 10
assert coverage["observed_layouts"] == 32
assert final["all_direct_children_reaped"] and final["all_owned_groups_absent"] and final["all_scratch_run_directories_removed"]
assert final["original10members_preserved"] and final["candidate_or_compiler_timeouts"] == 0
assert len(final["commands"]) == final["commands_count"] == 41
timeout_controls = 0
for row in final["commands"]:
    path = REVIEW / row["path"]
    receipt = json.loads(path.read_text())
    assert receipt["direct_child_reaped"] and receipt["owned_group_absent"]
    assert receipt["deadline_seconds"] <= 120
    assert row["returncode"] == receipt["returncode"] and row["timed_out"] == receipt["timed_out"]
    if receipt["timed_out"]:
        assert "runner-timeout-qualification" in row["path"]
        timeout_controls += 1
    for stream in ("stdout", "stderr"):
        assert identity(path.parent / (stream + ".bin")) == receipt[stream]
assert timeout_controls == 3
for name, expected in final["selected_source_pair"].items():
    assert identity(REVIEW / "source" / name) == expected
    assert identity(ROOT / "verification/swift-envelope-absent-state-correction/proposal-1/src" / name) == expected
instrumentation = json.loads((REVIEW / "instrumentation-binding.json").read_text())
selected = (REVIEW / "source/envelope.rs").read_text()
replacement = instrumentation["single_replacement"]
assert selected.count(replacement["from"]) == 1
derived = selected.replace(replacement["from"], replacement["to"]) + instrumentation["appended_suffix"]
assert {"bytes": len(derived.encode()), "sha256": hashlib.sha256(derived.encode()).hexdigest()} == instrumentation["derivative_source"]
preflight = json.loads((OUT / "absence-implementation-preflight.json").read_text())
assert preflight["qualification_commands"] == 27 and preflight["raw_streams_verified"] == 54
selection = json.loads((OUT / "absence-correction-selection.json").read_text())
accounting = json.loads((ROOT / "verification/swift-envelope-absent-state-accounting-review/findings.json").read_text())
assert accounting["blocking_accounting_findings"] == []
result = {
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(Path(__file__).resolve())],
    "python_version": sys.version,
    "checker": identity(Path(__file__)),
    "context_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "status": "accepted-isolated-fixture-envelope-host-implementation",
    "packets": packets,
    "root_verified_members": 407,
    "root_verified_bytes": 10231939,
    "root_verified_commands": {"producer": 27, "independent": 41},
    "root_verified_raw_streams": 136,
    "candidate_source_sha256": selection["candidate_source_sha256"],
    "parent_source_sha256": selection["parent_source_sha256"],
    "source_pair": selection["source_pair"],
    "root_selection": identity(OUT / "absence-correction-selection.json"),
    "accepted_scope": "Exact fixture-only safe-File framing/envelope API, independently authored canonical private leaf and corrected absence-before-funding/caller debit behavior, under the selected bounded accounting contract. No engine integration or real source authority adapter.",
    "producer": {"unchanged_methods": 70, "focused_methods": 8, "fresh_candidate_comparisons_against_reused_oracle": 21714, "fresh_model_execution": False, "actual_host_layouts": 32, "API_positive": 1, "API_expected_negative": 8},
    "independent": {"exact_source_methods": 14, "separate_test_overlay_methods": 2, "actual_host_layouts": 32, "API_positive": 1, "API_expected_negative": 8, "R2_original10_debits": [0] * 10, "absent_boundary_cases": 15, "readable_underfunding_cases": 1700, "caller_poststate_cases": 19, "candidate_mismatches_in_scope": 0},
    "selected_amounts": selection["selected"],
    "selected_guard_scope": selection["explicit_G_ownership_amendment"],
    "accounting": {"independent_offline_checks": 352, "rows": 121, "transfer_edges": 108, "logical_bytes": 24656, "reserved_bytes": 41984, "ceiling_bytes": 65536},
    "public_debit": "534*S_paid + 47*F_paid + 425*N_B; zero-call581; no main-paid425 refund",
    "historical_failures_preserved": "Old undercount/latch and funded-absence failures remain rejected historical packets. New producer test-expectation failure, four preaccess reviewer model errors, three reviewer execution errors and one repaired cleanup-retention gap remain retained. No single all-green attempt is claimed.",
    "receipt_precedence": "Independent final-receipt.json and coverage.json are terminal; execution-receipt.json remains a preserved intermediate not-complete placeholder.",
    "limitations": [
        "Poststate debit coherence is not a historical-budget, arbitrary reply-shape or authority validator. Fabricated paid status1/reason1 may schedule; canonical helper provenance excludes that form.",
        "Direct private short-arena absence and composed test-only counter overlays are not natural end-to-end public safe-File absence faults. Actual File construction uses full Arena.",
        "Overlay two-method evidence is separate from the fourteen byte-identical-source methods; compared matrices overlap and are not additive product features.",
        "Observed Rust1.99 aarch64-apple-darwin layout/evidence only. No Linux/compiler-target/native/device qualification.",
        "Runtime tests validate behavior; step/memory bounds derive from the separately selected operation/transfer/lifetime ledger, not timings.",
        "Historical full packets remain local unless separately delivered; this receipt does not claim their remote publication."
    ],
    "implementation_accepted": True,
    "fullReplayAccepted": False,
    "storedPrefixValidated": False,
    "semanticMetricsValid": False,
    "native_runtime_or_capture_started": False,
    "GA_qualified": False,
    "pending": ["Narrow selected-source CI and delivery closure", "Semantic replay/real source adapters/custody", "Live VM/CLI/target integration", "Native/device/compiler/signing/store/customer/operational and immutable published FieldLog gates", "Accountable GA review"],
    "errors": [],
}
assert sum(p["members"] for p in packets) == result["root_verified_members"]
assert sum(p["bytes"] for p in packets) == result["root_verified_bytes"]
(OUT / "absence-implementation-acceptance.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: result[k] for k in ("status", "root_verified_members", "root_verified_bytes", "implementation_accepted")}))
