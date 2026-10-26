#!/usr/bin/env python3
"""Record exact immutable packet custody; does not execute product code."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


def verify(relative, expected):
    raw = (ROOT / relative).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected, relative
    data = json.loads(raw)
    rows = data.get("files") or {row["path"]: row for row in data["members"]}
    total = 0
    for name, row in rows.items():
        value = (ROOT / name).read_bytes()
        assert len(value) == row["bytes"], name
        assert hashlib.sha256(value).hexdigest() == row["sha256"], name
        total += len(value)
    assert len(rows) == data.get("member_count", data.get("members"))
    assert total == data.get("member_bytes", data.get("bytes"))
    return {"path": relative, "sha256": expected, "members": len(rows), "bytes": total}


def write(relative, value):
    path = ROOT / relative
    assert not path.exists(), "One-shot receipt already exists"
    path.write_text(json.dumps(value, indent=2) + "\n")
    print(relative, hashlib.sha256(path.read_bytes()).hexdigest())


common = {
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(pathlib.Path(__file__).resolve())],
    "python": sys.version,
    "builder_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
    "head_context_only": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "native_UI_capture_or_inventory": False,
    "GA_qualified": False,
}
swift = verify(
    "verification/swift-cache-state-implementation/correction-3/candidate-repo-seal.json",
    "7044a00eef658d8c729e7301c0923ed193ec405c6c6009989a964b3159bad12f",
)
android = verify(
    "verification/android-private-owner-independent-review/implementation-review-3/manifest.json",
    "f4afff4105d08642e74f1e5a3255015828e57c2a703b023bdd91ce709be18bc2",
)
proposal = verify(
    "verification/android-private-owner-effect-integration-root-review/candidate5-proposal/manifest.json",
    "22a119f096db3da04efdbde6b2f6d6c1a2402e22bfc4bac9a0a26fa8687ccf89",
)
write("verification/swift-semantic-adapter-root-review/correction3-host-results.json", {
    **common,
    "status": "Fresh isolated correction3 host evidence accepted; complete implementation acceptance pending",
    "candidate": swift,
    "cache_state_sha256": "0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8",
    "host_tool": "Rust 1.99.0 b940084d7eb6a299eb4bfeb8e34901bc051e7ac4; arm64 macOS; debug and -O",
    "methods_per_mode": {"distinct": 122, "new": 30, "inherited_producer": 78, "inherited_independent": 14, "binary_counts_overlap": [84, 108, 98]},
    "API_dispositions_per_mode": 25,
    "complete_layouts_per_mode": 23,
    "public_Result_bytes": 488,
    "fresh_four_File_cases_per_mode": {"public": 29, "public_complete32": 27, "public_outer_error_no_aggregate": 2, "private_poison_complete32": 2},
    "fresh_guard_full32_methods_per_mode": 5,
    "owned_children_observed_exited": 72,
    "owned_products_hashed_removed": 14,
    "candidate_byte_comparisons": 6144,
    "source_change": "Only selected sixteen anonymous 128-byte clear statements; all twelve restores and private fault suffix unchanged",
    "selected_clear_block_groups": 189,
    "pending": ["Complete G6 source ledger independent review", "G3/G4 source work bounds", "Complete 29344-byte role/lifetime union", "Independent correction3 implementation replay"],
    "full_G6_accepted": False,
    "whole_lifetime_accepted": False,
    "implementation_accepted": False,
    "new_sort_design": "Source-only byte-index proposal within existing Candidate regions assigned; no contract amendment or product change selected",
})
write("verification/android-private-owner-effect-integration-root-review/candidate4-final-review-and-candidate5-selection.json", {
    **common,
    "review": android,
    "status": "Candidate4 rejected for F09; exact narrow candidate5 repair selected after full immutable review seal",
    "finding": "Collect coordinator retained primary and firstFatal before remembering the caught disposal throwable; retain earlier outer owner primary/fatal",
    "original_mixed_matrix_rows": 1323,
    "direct_qualified_rows": 1316,
    "direct_leaf_or_opaque_rows": 1295,
    "direct_helper_rows": 21,
    "pending_measure_helper_rows": 7,
    "exhaustive_callee_classification": {"platform": 174, "opaque_product_constructor": 8, "opaque_platform_constructor": 3, "actual_product_helper": 4},
    "actual_owner_core_observer": {"cases": 129, "assertions": 1787},
    "unchanged_V1_positives": 5,
    "historical_source_binding": {"groups": 35, "check_sites": 153, "reported_dynamic_vectors_pending_expansion": 447},
    "full_families_pending": ["First/middle/last current and pending cancellation rosters", "Decoder/IME refusal and forwarding families beyond observed controls"],
    "F09_input_closure": "Full review seal binds actual descriptor and base packet omitted by earlier mini; old mini scope note preserved",
    "cleanup_receipts_verified_by_reviewer": 31,
    "proposal": proposal,
    "selected_NativeOwnerV2_sha256": "056aa51d07e765b59a3859ce76090477a24211c973b63336406ff4b0d4102269",
    "owned_changes": ["native/android/app/src/dev/mixer/android/NativeOwnerV2.java", "native/android/tests/NativeOwnerV2HostTests.java", "verification/android-private-owner-integration-implementation/candidate-5/**"],
    "required": ["Fresh outer/nested identity, fatal propagation, prior outer failure precedence and repeated close controls", "Fresh bounded A/B host and relevant cross-compilation evidence", "New exact source/profile freeze and independent review", "New root adapter projection selection and CLI consumer qualification"],
    "implementation_accepted": False,
    "canonical_delivery_authorized": False,
})
