#!/usr/bin/env python3
"""Bind selected constants and freeze preparation; never execute test sources."""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

OWN = Path(__file__).resolve().parent
BASE = OWN.parent
ROOT = BASE.parents[1]
BASE_SEAL = "582d0ab43c078caeb9142650390345eee3076c6114c35d217f1964f460e324da"
SELECTION = "verification/swift-ordered-retention-analyzer-envelope-root-review/correction-numeric-contract-selection.json"
SELECTION_SHA = "199dfa75b024d04eeef28f2f40165115797a0bbb3d09a2405426172d8339867c"

BINDINGS = {
    "E_SETUP": 534, "E_FINISH": 47, "E_LEAF": 425, "B_RECORD": 471,
    "W_RECORD": 24, "W_SETUP": 42, "W_FINISH": 42, "G": 112,
    "F_base": 29, "F05_early_error": 13,
}

DETAILS = {
    "R1-exact-original": "Status1/reason15/state999 cannot schedule another leaf. Complete CAP returns InternalPoisoned with zero extent; retain the synthetic prepaid counter supplied by the private seam.",
    "poison-cross-product": "Reason15 or status3 precedes scheduling, CAP and stale-state access. Complete poison is InternalPoisoned; successful limited poison is AnalysisLimited/InternalPoisoned. All eleven extent fields are zero.",
    "poison-later-wire-error": "A later framing error overrides retained poison. Preserve 534*S_paid+47*F_paid+425*N_B, not a leaf-execution count. Returned input Err finalizes through dedicated F05=13.",
    "absent-backing": "reply_valid0 never projects its backing, even poisoned garbage. Complete or successfully limited framing is Unavailable/EnvelopeUnavailable with zero extent and the actual paid debit.",
    "zero-actual-leaf-calls": "With setup and finish paid and N_B=0, debit581. No actual completed leaf reply means Unavailable/EnvelopeUnavailable and all eleven extent fields zero. A paid failed decode can instead leave N_B>0 without a reply; its input error still overrides.",
    "reply-valid-only-after-return": "Setup534, finish47 and G112 must precede candidate mutation. Candidate initialization does not set reply_valid. Only an actual complete returned-and-installed reply can do so; an actual Steps reply is valid.",
    "absent-prior-state-before-underfunding": "Absent state returns InternalPoisoned/debit0 before shape or funding checks. Test funds0 through425 without inventing prior extent; no arena/candidate mutation.",
    "underfunded-first-and-later": "For every remaining value0..424, first/later and valid/malformed record: actual Refused/Steps, unchanged prior state/coordinate, debit0, unchanged budget/arena/candidate. G112 is prepaid once; public main-paid425 remains reserved.",
    "exact-leaf-funding": "Funds424 => Steps/debit0/no mutation. Funds425 and426 admit the specified valid transition with debit425; remaining0 and1 respectively. No fresh replay credit is introduced.",
    "ordinary-refusal-atomic": "Every successfully charged record includes425 before decode. Paid ordinary refusals retain425, preserve the prior complete state and latch. No later leaf call resumes.",
    "last-cell-boundary": "At the last selected-cell byte boundary, check every address before any write. A fully prepaid425 call returns poison on missing required state, keeps all available arena/candidate bytes unchanged and retains425.",
    "partial-commit-fault": "If an admissible private seam exists after exact-source admission, a partial commit must poison, suppress extent and stop later calls. No rollback, fabricated prior extent or production fault API. Charge425 remains paid.",
    "complete-sole-cap-eleven-states": "All eleven supported states remain CapCutUnknownTail/Observed after complete sole-CAP framing. Debit is581+425*N_B when setup/finish succeeded. No closure or missing tail is invented.",
    "complete-noncap-finality": "Strict EOF and all final metadata are mandatory. Only supported Idle/phase5/exact mask closes. Other supported non-CAP boundaries are Refused/IncompleteBoundary. No counter changes during finalization beyond already reserved finish47.",
    "successful-limited-table": "Absent => unavailable/zero; Observed => AnalysisLimited/FramingLimited/safe extent; Refused => AnalysisLimited/first reason/safe extent; poison => AnalysisLimited/InternalPoisoned/zero. Preserve581+425*N_B after paid setup/finish.",
    "failed-limited-drain": "A failed drain is an input Err, not a partial envelope. Input BINDING/BUDGET/other maps to reason16/18/17; extent is zero and paid debit survives. F05=13 funds this error path even if finish47 was paid.",
    "invalid-private-values": "Unsupported values/flag combinations fail closed with Unavailable/UnavailableState and zero extent. Reason15 poison is recognized before stale state. Actual input errors take precedence and use F05.",
    "unknown-context": "Unknown fixture context preserves BindingUnavailable framing and returns Unavailable/FramingUnavailable, zero extent. Do not charge unentered main setup/finish/record terms; actual counters govern debit.",
    "context-profile-header-errors": "Keep actual framing stage/classification and zero envelope extent. Preserve only successful main534/47/425 reservations. Every returned input Err has separately funded F05=13, with no reuse of inactive finish credits.",
    "setup-finish-admission": "Main setup failure=>debit0; setup paid then finish failure=>534; setup+finish paid then guard failure=>581. All are pre-candidate input BUDGET errors with zero extent and F05=13 finalization. Exact reservation boundaries await a mechanical map to admitted source.",
    "next-record-preflight": "Next-record funds8191 stop before decode/leaf;8192 permit atomic B471 before decode. B471 is22+425+24. Derive the complete lowered-limit threshold afresh after exact-source setup/report/IO charges; do not reuse a historical threshold or claim capacity.",
    "paid-decode-failure": "With setup/finish paid, one B471 followed by failed decode produces public debit1006, even with zero leaf replies. Two such paid charges produce1431. Input error suppresses all extent and routes through F05=13; no refund.",
    "paid-latched-skip": "One paid record then a second B471 whose leaf is skipped yields public debit1431 with setup/finish paid. Count actual charges independently of calls. First refusal/poison stays latched; later framing error zeroes extent without refund.",
    "late-record-footer-EOF-metadata": "Late actual error overrides closed/refused/CAP/poisoned state, preserves exact framing classification and534*S_paid+47*F_paid+425*N_B, and clears all eleven extent fields. Dedicated F05=13 pays returned input Err finalization.",
    "outer-safety-and-allocation": "Output safety/Budget construction/allocation errors remain outer Err with no aggregate. No public debit or extent is fabricated. No source write, truncate, reopen, clone owner or unauthorized fault API.",
    "bounded-IO-and-report-errors": "Preserve existing bounded IO and fixed report failure semantics. Returned input Err uses F05=13; output/write/postwrite failure is outer Err with no aggregate. Partial physical output is failed evidence, never an observation.",
    "finite-stage-and-failure-sequences": "Finite transition/reason/state/coordinate behavior is unchanged; each successful normal private admission costs425. Retain independent Failure cursors, legal Idle Release, no resumption and phase5 terminality. No semantic authority.",
    "candidate-and-arena-footprint": "One retained Candidate2048; only bytes888..983 and twelve named scalar cells change through the leaf. G112 precedes mutation; no per-record owner, rezero, allocator, IO or callback. Underfunded/refused controls compare whole snapshots.",
    "public-API-positive": "Future positive compiler probe uses exact admitted safe-File entry and immutable getters. Public report stays49152 bytes, semantics/acceptance stay false. Compile/execution is currently forbidden.",
    "public-API-negative": "Future separate negative probes reject private record/leaf access, arbitrary-word/trust-bool construction, aggregate mutation, observation Copy, aggregate Clone, raw serializer and descriptor/authority constructors. No probe compiled now.",
    "old-framing-and-fixed-report": "Preserve accepted old entry/ABI/report/version/mask/reserved zeros. New public debit is selected534/47/425; truthful total authored steps include separately reserved wrapper/G. Paired report differences require an exact field allowlist. No original64 retry.",
    "complete-memory-and-lifetime-handoff": "Selected contract names24656-byte upper within41984 reservation/65536 ceiling; behavioral checks do not qualify exact-source accounting. Candidate source, types, moves, Results and lexical overlap remain pending final accounting review.",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def verify_baseline() -> int:
    raw = (BASE / "seal.json").read_bytes()
    assert sha(raw) == BASE_SEAL
    members = json.loads(raw)["members"]
    assert len(members) == 39
    for row in members:
        data = (ROOT / row["path"]).read_bytes()
        assert len(data) == row["bytes"] and sha(data) == row["sha256"], row["path"]
    return len(members)


def main() -> None:
    assert not (OWN / "seal.json").exists(), "preserve the frozen preparation"
    count = verify_baseline()
    selected_bytes = (ROOT / SELECTION).read_bytes()
    assert sha(selected_bytes) == SELECTION_SHA
    selected = json.loads(selected_bytes)
    assert selected["selected"] == {
        "leaf": 425, "W": 24, "B": 471, "G": 112, "T": 42,
        "finish": 47, "F": 42, "setup_selected": 534, "setup_actual_bound": 329,
        "F_base": 29, "F_early_error": 13,
    }
    assert selected["public_formula"] == "534*S_paid + 47*F_paid + 425*N_B"
    snapshot = OWN / "inputs" / "correction-numeric-contract-selection.json"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    assert not snapshot.exists()
    snapshot.write_bytes(selected_bytes)
    baseline = json.loads((BASE / "baseline.json").read_bytes())
    assert {case["id"] for case in baseline["cases"]} == set(DETAILS)
    cases = [{
        "id": case["id"],
        "status": "pending-no-candidate-access-or-execution",
        "preaccess_case_sha256": sha(json.dumps(case, sort_keys=True, separators=(",", ":")).encode()),
        "frozen_behavior": case,
        "selected_numeric_expectation": DETAILS[case["id"]],
    } for case in baseline["cases"]]
    matrix = {
        "schema": 1,
        "status": "selected-expectations-prepared-all-controls-pending",
        "root_selection": SELECTION,
        "root_selection_sha256": SELECTION_SHA,
        "protected_baseline_seal_sha256": BASE_SEAL,
        "parameter_bindings": BINDINGS,
        "public_formula": selected["public_formula"],
        "expected_public_debit_examples": {
            "setup_failure": 0, "finish_failure_after_setup": 534,
            "guard_failure_after_setup_and_finish": 581,
            "setup_finish_paid_no_record": 581,
            "setup_finish_paid_one_record_decode_failure": 1006,
            "setup_finish_paid_two_records_second_leaf_skipped": 1431,
        },
        "funding_route": {
            "input_Err": "dedicated outer F05=13, even when finish47 was paid; no refund or inactive credit reassignment",
            "input_Ok": "finish47; F05 stays unused; successful walk setup/finish is implied",
            "G112": "prepaid before candidate mutation, usable at most once, total authored steps only",
        },
        "private_underfunded_values_inclusive": [0, 424],
        "positive_private_funding_controls": [425, 426],
        "cases": cases,
        "prepared_source_scope": {
            "private_controls.rs": "six pending methods covering R1, poison product, absent backing, all underfunded values, exact funding and last checked cell",
            "expected_observation.rs": "pending normalized public assertions; actual safe-File adapter is not yet supplied",
            "owned_runner.py": "unexecuted future bounded runner; its qualification is pending",
        },
        "candidate_or_proposal_accessed": False,
        "compiler_calls": 0,
        "cost_dependent_executions": 0,
        "behavioral_passes_claimed": 0,
        "implementation_acceptance": False,
        "ga_gate_promotions": 0,
    }
    write_json(OWN / "selected-cases.json", matrix)
    commands = []
    for label, argv in [("revision", ["git", "rev-parse", "HEAD"]), ("git-version", ["git", "--version"])]:
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, check=True, timeout=10, start_new_session=True)
        (OWN / "commands").mkdir(exist_ok=True)
        for name, data in [("stdout", result.stdout), ("stderr", result.stderr)]:
            (OWN / "commands" / f"{label}.{name}").write_bytes(data)
        commands.append({"argv": argv, "returncode": result.returncode, "timeout_seconds": 10,
                         "stdout_sha256": sha(result.stdout), "stderr_sha256": sha(result.stderr),
                         "scope": "read-only identity; no compiler or process discovery"})
    assert verify_baseline() == count
    assert sha((ROOT / SELECTION).read_bytes()) == SELECTION_SHA
    receipt = {
        "schema": 1,
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": [sys.executable, "-B", str(Path(__file__).relative_to(ROOT))],
        "python": sys.version,
        "script_sha256": sha(Path(__file__).read_bytes()),
        "scope": "static contract parameter binding, source preparation and artifact integrity only",
        "commands": commands,
        "revision_context": (OWN / "commands/revision.stdout").read_text().strip(),
        "selected_contract_sha256": SELECTION_SHA,
        "protected_baseline_sha256": BASE_SEAL,
        "protected_members_verified_unchanged_before_after": count,
        "pending_control_count": len(cases),
        "status": "prepared-and-frozen-no-behavior-execution",
        "candidate_accessed": False,
        "operation_proposal_or_producer_packet_accessed": False,
        "compiler_or_analyzer_or_oracle_executed": False,
        "runner_imported_or_executed": False,
        "native_UI_capture_simulator_emulator_device_process_discovery": False,
        "original64_retried": False,
        "artifact_validation": "Pinned selection, all32 case IDs, exact selected dictionary and public formula; original39 baseline member hashes preserved. No product result evaluated.",
        "cleanup": "Only synchronous git identity children; no test runtime, owned scratch or native/capture process created.",
        "remaining": "Root exact-source handoff, mechanical adapter/name mapping, runner qualification, actual bounded behavioral execution and final accounting review.",
        "implementation_accepted": False,
        "ga_gate_promotions": 0,
    }
    write_json(OWN / "receipt.json", receipt)
    summary = {"status": receipt["status"], "pending_controls": len(cases),
               "protected_baseline_members_unchanged": count, "selected_contract_sha256": SELECTION_SHA,
               "compiler_calls": 0, "cost_dependent_executions": 0}
    write_json(OWN / "commands/prepare.stdout.json", summary)
    members = []
    for path in sorted(OWN.rglob("*")):
        if path.is_file() and path.name not in ("seal.json", "seal.sha256"):
            data = path.read_bytes()
            members.append({"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": sha(data)})
    write_json(OWN / "seal.json", {"schema": 1, "scope": "selected-contract supplemental preparation only; no acceptance", "members": members,
                                 "excluded": [str((OWN / "seal.json").relative_to(ROOT)), str((OWN / "seal.sha256").relative_to(ROOT))]})
    digest = sha((OWN / "seal.json").read_bytes())
    (OWN / "seal.sha256").write_text(digest + "  " + str((OWN / "seal.json").relative_to(ROOT)) + "\n")
    print(json.dumps({**summary, "seal_sha256": digest, "members": len(members), "bytes": sum(row["bytes"] for row in members)}, sort_keys=True))


if __name__ == "__main__":
    main()
