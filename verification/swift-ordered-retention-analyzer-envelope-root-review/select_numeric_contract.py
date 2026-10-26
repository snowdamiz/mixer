"""Root read-only custody audit, followed by explicit isolated numeric selection."""
import datetime
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
PROPOSAL = ROOT / "verification/swift-ordered-retention-analyzer-envelope-correction/commands/operation-ledger-proposal-2"
REVIEW = ROOT / "verification/swift-ordered-retention-analyzer-envelope-correction-accounting-review-2"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2) + "\n")


audits = []
for path, expected, base, count, total in [
    (PROPOSAL / "manifest.json", "58b2fccf992baade1eee51dfdd9f5e3bd5c039cfa5b52a3a25fef8d97ff034e5", PROPOSAL, 42, 633148),
    (REVIEW / "seal.json", "c500c43ee55db92bd7a4bcaf62a90224761ee08dfbba80457069eebd7c8fd9ce", ROOT, 60, 695181),
]:
    raw = path.read_bytes()
    assert sha(raw) == expected
    members = json.loads(raw)["members"]
    actual_total = 0
    for member in members:
        rel = pathlib.PurePosixPath(member["path"])
        assert not rel.is_absolute() and ".." not in rel.parts
        data = (base / member["path"]).read_bytes()
        assert len(data) == member["bytes"] and sha(data) == member["sha256"], member["path"]
        actual_total += len(data)
    assert len(members) == count and actual_total == total
    audits.append({"path": str(path.relative_to(ROOT)), "sha256": expected, "members": count, "bytes": total})

numeric_raw = (PROPOSAL / "numeric-proposal.json").read_bytes()
assert sha(numeric_raw) == "736947e71b0fcaf102ac2c64438730afbc6d2954ac082134066f73fae8211550"
numeric = json.loads(numeric_raw)
expected_values = {"leaf": 425, "W": 24, "B": 471, "G": 112, "T": 42, "finish": 47, "F": 42,
                   "setup_selected": 534, "setup_actual_bound": 329, "F_base": 29, "F_early_error": 13}
assert numeric["proposed"] == expected_values
receipt = json.loads((REVIEW / "review-receipt.json").read_text())
assert receipt["C1_resolved"] and receipt["C2_resolved"] and receipt["findings"] == []
assert receipt["rows_checked"] == 116 and receipt["transfer_edges_checked"] == 108
assert receipt["named_logical_bytes"] == 24656 and receipt["reserved_logical_bytes"] == 41984
assert 22 + 425 + 24 == 471 <= 8192
assert 42 + 534 == 576 <= 65536
assert 47 + 112 + 42 == 201 and 6245 + 201 == 6446 <= 3000000
assert 534 + 47 == 581 and 581 + 425 == 1006
audit = {
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(pathlib.Path(__file__).resolve())],
    "python_version": sys.version,
    "checker_sha256": sha(pathlib.Path(__file__).read_bytes()),
    "packets": audits,
    "members": 102,
    "bytes": 1328329,
    "review_findings": [],
    "source_execution": False,
    "errors": [],
}
save("correction-proposal2-review-admission.json", audit)
selection = {
    "schema": 1,
    "at": audit["at"],
    "status": "proposal2-numeric-contract-selected-for-isolated-correction-implementation",
    "root_admission": "verification/swift-ordered-retention-analyzer-envelope-root-review/correction-proposal2-review-admission.json",
    "proposal_manifest": str((PROPOSAL / "manifest.json").relative_to(ROOT)),
    "proposal_manifest_sha256": audits[0]["sha256"],
    "review_seal": str((REVIEW / "seal.json").relative_to(ROOT)),
    "review_seal_sha256": audits[1]["sha256"],
    "prior_source_sha256": "e86ef43a99f99245c78308666f91f5147981859ca03fa3f97e62d46993667535",
    "parent_source_sha256": "1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b",
    "operation_ledger_sha256": "8ba395af50cd827242ce121f60dade5ebd270956602454fbd7345cf8f89c0a0f",
    "funding_table_sha256": "baec5fde93a784a20351e48f1200cb1d7378c0999f82aa4dd84e94aba897581d",
    "selected": expected_values,
    "unchanged_accepted_framing": 22,
    "public_formula": "534*S_paid + 47*F_paid + 425*N_B",
    "zero_leaf_complete_or_limited_debit_if_setup_finish_paid": 581,
    "input_error_funding": "Outer F_wrapper42 = existing base29 + dedicated F05 early13. Every returned input Err uses F05 even if finish47 was paid; unused finish credits remain unused, no refund. Input Ok implies successful walk setup and finish, so its finalizer uses finish47 and F05 stays unused. No inactive-credit reassignment or added runtime paid flag.",
    "selected_contract_amendment": "For this separate fixture-envelope correction only, replace historical leaf128/W42/B192/G36/T20/finish8/F44 with leaf425/W24/B471/G112/T42/finish47/F42. Setup534 and all global limits remain fixed. This supersedes earlier root numeric selections solely for this corrected API/packet; it does not alter accepted framing-only API, historical model or frozen evidence.",
    "cost_unit": "At most16 named bounded scalar operations OR one actual fixed copy/transfer of at most128 bytes per group. Charge each actual16-byte handle transfer once; retain full source/destination memory places while coexisting. No compiler-elision, padding, inactive branch or unassigned margin credit.",
    "limits": numeric["limits"],
    "logical_memory": {"named_upper": 24656, "reservation": 41984, "ceiling": 65536, "unassigned_margin_not_spent": 23552},
    "fixed_new_report": 201,
    "existing_plus_new_report_upper": 6446,
    "public_report_bytes_unchanged": 49152,
    "future_host_bytes_unchanged": 8192,
    "range_and_lifetime_contract": "One retained Candidate2048, payload888..98396 bytes, no move/embed/per-record rezero. Safe unrolled12 prior reads/stages/commits, checked lengths before mutations, no allocator/I/O/callback/raw pointer. Progress144 persists through report/final metadata; reply_valid only after complete actual reply. Full types and all caller/return places remain accounted.",
    "required_behavior": [
        "Reason15/status3 poison priority precedes leaf scheduling and all finalization branches. A complete private status1/reason15 reply cannot schedule another leaf.",
        "Zero actual leaf calls produce Unavailable/EnvelopeUnavailable with all extent fields0. Paid setup/finish/record counters remain truthful; setup fail0, finish fail after setup534, guard fail after setup+finish581.",
        "Private underfunding returns Refused/Steps, prior state, debit0 and no candidate/arena mutation. Prepaid main425 remains in the public counter. G112 is separately prepaid before candidate mutation and usable at most once.",
        "Each successful atomic B471 adds425 even if later decode/framing fails or leaf execution is skipped by a latched refusal/poison. Framing/input Err suppresses state fields but preserves paid debit. Outer output/allocation/report errors return no aggregate.",
        "Public signature, private fields and no constructor/Copy/Clone/raw serializer/trust bool/record exposure remain unchanged; semantic/full replay/prefix flags remainfalse.",
    ],
    "authorized_next_work": [
        "Update only existing correction packet source constants and exact reviewed operation partition, plus clearly documented tests/oracle parameter adaptation and correction documentation. Keep proposal1/proposal2 and all original/review freezes immutable. A substantive source/control-flow/owner change requires renewed accounting before replay.",
        "Run fresh bounded direct-Rust host tests, actual complete layouts, public API compile controls, selected budget/error/zero-call/poison/finite-oracle cases against final selected source. Do not execute historical unqualified128/192 source or retry original timeout closure. Preserve failures and partial streams.",
        "Keep existing accepted finite model immutable. Any local corrected test model with selected425 debit is a separate derived oracle with explicit parameter/delta evidence, not retroactive historical qualification.",
        "Use dedicated owned subprocess groups, deadlines, kill/reap on timeout, preserve partial output before cleanup; delete only owned scratch after children finish. Pin compiler argv0 correctly using known Rustup dispatch method.",
        "Freeze exact corrected source/test/model/archive/ledger/results and command/version/source-tree identities for fresh independent behavior review and final accounting review. No engine/CLI/product/CI/root metadata integration or commit/push until root acceptance.",
    ],
    "ownership": ["docs/swift-ordered-retention-analyzer-envelope-correction.md", "verification/swift-ordered-retention-analyzer-envelope-correction/** except frozen operation proposal1/proposal2 directories and retained prior attempts"],
    "numeric_contract_selected": True,
    "cost_dependent_replay_authorized_only_after_selected_constants_update": True,
    "implementation_accepted": False,
    "combined_final_source_qualified": False,
    "native_UI_capture_or_hosted_execution_authorized": False,
    "GA_qualified": False,
    "limits_of_selection": "425 is a conservative source upper, not a minimal lower bound or impossibility proof for128. Arithmetic capacity559256 is an upper bound only, not guaranteed prefix/fullcap/throughput. Logical roles are not physical stack/RSS or compiler/native performance. This remains fixture-only, no semantic replay/custody/binding/release/store/FieldLog authority.",
}
save("correction-numeric-contract-selection.json", selection)
print(json.dumps({"audited_members": 102, "bytes": 1328329,
                  "selection_sha256": sha((OUT / "correction-numeric-contract-selection.json").read_bytes()),
                  "selected": expected_values, "implementation_accepted": False}))
