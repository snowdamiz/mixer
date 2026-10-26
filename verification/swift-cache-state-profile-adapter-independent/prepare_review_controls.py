#!/usr/bin/env python3
"""Freeze independent obligations, byte patches and roster/argument guards."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys

HERE = Path(__file__).absolute().parent


def sha(b):
    return hashlib.sha256(b).hexdigest()


def dump(name, value):
    (HERE / name).write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def roster_guard(expected, compiled, selected, result, bridge_expected, bridge_actual):
    # Runtime credit must be tied to exact frozen fully qualified names later.
    assert expected and len(expected) == len(set(expected)), "empty/duplicate required roster"
    assert compiled and len(compiled) == len(set(compiled)), "empty/duplicate compiler inventory"
    assert selected and len(selected) == len(set(selected)), "empty/duplicate selected namespace"
    assert set(selected) == set(expected), "missing/unexpected selected names"
    assert set(selected) <= set(compiled), "selected name absent from compiler inventory"
    assert result == {"passed": len(selected), "failed": 0, "ignored": 0,
                      "filtered": len(compiled) - len(selected)}, "wrong runtime result counts"
    assert bridge_expected and len(bridge_expected) == len(set(bridge_expected)), "empty/duplicate bridge contract"
    assert len(bridge_actual) == len(set(bridge_actual)), "duplicate bridge invocation credit"
    assert set(bridge_actual) == set(bridge_expected), "missing/unexpected bridge invocation"


def argv_guard(role, args, mode):
    assert mode in ("debug", "optimized")
    assert ("-O" in args) == (mode == "optimized"), "wrong compilation mode"
    assert not any(a.startswith("-A") or a.startswith("--allow") for a in args), "warning suppression"
    if role == "unchanged-fixture-library":
        assert "--edition=2021" in args and "--crate-type=lib" in args
        assert "--crate-name" in args and "-o" in args
        assert not any(a.startswith("-D") or a.startswith("--deny") for a in args), "fixture exception requires normal diagnostics"
    else:
        assert role in ("new-adapter", "new-bridge")
        assert "-Dwarnings" in args or ("-D" in args and "warnings" in args), "new source lacks strict policy"


def self_controls():
    good = dict(expected=["n::row", "n::file", "n::layout"],
        compiled=["old::a", "old::b", "n::row", "n::file", "n::layout"],
        selected=["n::row", "n::file", "n::layout"],
        result={"passed": 3, "failed": 0, "ignored": 0, "filtered": 2},
        bridge_expected=["positive", "identity-negative", "authority-false"],
        bridge_actual=["positive", "identity-negative", "authority-false"])
    roster_guard(**good)
    mutations = []
    for label, key, value in [
        ("empty-required", "expected", []),
        ("duplicate-required", "expected", good["expected"] + ["n::row"]),
        ("empty-compiled", "compiled", []),
        ("duplicate-compiled", "compiled", good["compiled"] + ["n::row"]),
        ("compiler-missing-selected", "compiled", good["compiled"][:-1]),
        ("empty-selected", "selected", []),
        ("selected-missing-file", "selected", ["n::row", "n::layout"]),
        ("selected-unexpected", "selected", ["n::row", "n::file", "n::extra"]),
        ("selected-duplicate", "selected", good["selected"] + ["n::row"]),
        ("bridge-empty-contract", "bridge_expected", []),
        ("bridge-duplicate-contract", "bridge_expected", good["bridge_expected"] + ["positive"]),
        ("bridge-missing", "bridge_actual", good["bridge_actual"][:-1]),
        ("bridge-unexpected", "bridge_actual", good["bridge_actual"] + ["other"]),
        ("bridge-duplicate-credit", "bridge_actual", good["bridge_actual"] + ["positive"]),
    ]:
        trial = copy.deepcopy(good); trial[key] = value
        mutations.append((label, trial))
    for key, value in [("passed", 2), ("failed", 1), ("ignored", 1), ("filtered", 0)]:
        trial = copy.deepcopy(good); trial["result"][key] = value
        mutations.append(("result-" + key, trial))
    rows = []
    for label, trial in mutations:
        try:
            roster_guard(**trial)
        except AssertionError as e:
            rows.append({"id": label, "refused": True, "reason": str(e)})
        else:
            raise AssertionError(("bad roster accepted", label))
    normal = ["--edition=2021", "--crate-name", "closed", "--crate-type=lib", "source/library/analyzer.rs", "-o", "owned/lib.rlib"]
    for mode in ("debug", "optimized"):
        argv_guard("unchanged-fixture-library", normal + (["-O"] if mode == "optimized" else []), mode)
        argv_guard("new-bridge", ["-Dwarnings"] + (["-O"] if mode == "optimized" else []), mode)
    for label, role, args, mode in [
        ("fixture-strict-warning-command", "unchanged-fixture-library", normal + ["-Dwarnings"], "debug"),
        ("fixture-suppressed-warning-command", "unchanged-fixture-library", normal + ["-Awarnings"], "debug"),
        ("fixture-wrong-mode", "unchanged-fixture-library", normal + ["-O"], "debug"),
        ("new-bridge-policy-relaxed", "new-bridge", [], "debug"),
        ("new-adapter-policy-relaxed", "new-adapter", [], "debug"),
        ("new-source-suppressed", "new-adapter", ["-Dwarnings", "-Awarnings"], "debug"),
    ]:
        try:
            argv_guard(role, args, mode)
        except AssertionError as e:
            rows.append({"id": label, "refused": True, "reason": str(e)})
        else:
            raise AssertionError(("bad argv accepted", label))
    return rows


def row_patches():
    body = (HERE / "fixtures/minimum-abi29.expected-row-body.bin").read_bytes()
    assert len(body) == 2560000
    undef = struct.pack("<IIQQQ", 0, 0xffffffff, 0xffffffffffffffff, 0, 0)
    defined = body[34 * 32:35 * 32]
    adjacent = struct.unpack("<IIQQQ", body[35 * 32:36 * 32])
    cases = [
        ("defined-not-boolean", 34, 0, struct.pack("<I", 2), "schema-refusal", "any stream"),
        ("reserved-nonzero", 34, 24, struct.pack("<Q", 1), "schema-refusal", "any stream"),
        ("type-outside-actual-count", 34, 4, struct.pack("<I", 36), "schema-refusal", "any stream"),
        ("offset-absent-on-defined", 34, 8, struct.pack("<Q", 0xffffffffffffffff), "schema-refusal", "any stream"),
        ("length-absent-on-defined", 34, 16, struct.pack("<Q", 0xffffffffffffffff), "schema-refusal", "any stream"),
        ("body-end-past-source", 34, 16, struct.pack("<Q", 89), "schema-refusal", "any stream"),
        ("import-type-not-sentinel", 0, 4, struct.pack("<I", 0), "schema-refusal", "any stream"),
        ("import-offset-not-sentinel", 0, 8, struct.pack("<Q", 0), "schema-refusal", "any stream"),
        ("import-length-not-zero", 0, 16, struct.pack("<Q", 1), "schema-refusal", "any stream"),
        ("defined-cleared-without-sentinels", 34, 0, struct.pack("<I", 0), "schema-refusal", "any stream"),
        ("different-equal-body-offset", 34, 8, struct.pack("<Q", adjacent[2]), "body-identity-refusal", "unchanged body-bearing row34 record"),
        ("different-in-range-type", 34, 4, struct.pack("<I", 35), "body-identity-refusal", "unchanged body-bearing row34 record"),
        ("different-in-range-length", 34, 16, struct.pack("<Q", 1), "body-identity-refusal", "unchanged body-bearing row34 record"),
        ("defined-row-replaced-by-valid-undefined", 34, 0, undef, "body-identity-refusal", "unchanged body-bearing row34 record"),
        ("valid-defined-import-collusion", 0, 0, defined, "independent-owner-row-comparison-refusal", "synthetic matching event may pass; not an analyzer provenance check"),
        ("valid-defined-tail-collusion", 79999, 0, defined, "independent-owner-row-comparison-refusal", "synthetic matching event may pass; not an analyzer provenance check"),
    ]
    rows = []
    for name, row, field, replacement, expected, applies in cases:
        offset = row * 32 + field
        before = body[offset:offset + len(replacement)]
        assert len(before) == len(replacement) and before != replacement
        mutated = body[:offset] + replacement + body[offset + len(replacement):]
        assert len(mutated) == len(body)
        rows.append({"id": name, "row": row, "raw_row_body_offset": offset,
            "profile_offset_with_synthetic_header": 512 + offset,
            "before_hex": before.hex(), "replacement_hex": replacement.hex(),
            "expected_disposition": expected, "applicability": applies,
            "mutated_row_body_sha256": sha(mutated),
            "all_four_authority_values": [False] * 4,
            "actual_analyzer_invoked": False})
    return {"baseline": "fixtures/minimum-abi29.expected-row-body.bin", "baseline_sha256": sha(body),
        "cases": rows, "case_count": len(rows),
        "phase_only_stream_in_range_mutation_not_automatically_rejected": True,
        "collusive_synthetic_row_and_event_is_not_actual_owner_binding": True,
        "scope": "independent frozen byte patches and later expected applicability, no analyzer runtime evidence"}


def main():
    obligations = []
    def add(kind, name, credit):
        obligations.append({"id": kind + ":" + name, "kind": kind,
            "required_evidence": credit, "actual_method_or_invocation_name": None,
            "runtime_credit": False})
    for name in ["actual-sealed-owner-only", "minimal-abi29-all80000", "wide-offset-leb-type129-all80000",
                 "maximum-total80000-candidate", "imports-and-undefined-sentinels", "equal-body-distinct-offsets",
                 "out-of-range80000", "out-of-range-u32max", "owner-unchanged-on-success-and-fault",
                 "invalid-wasm-no-owner"]:
        add("rows", name, "actual selected Rust validator/adapter in both modes; refusal/unreachable distinctions retained")
    for name in ["fresh-empty-regular-full-bytes", "prefilled-no-truncate", "empty-offset1-no-write",
                 "directory-not-regular", "readonly-file-write-error", "retained-partial-bytes",
                 "error-side-effects-no-rollback", "metadata-error-applicability", "position-error-applicability"]:
        add("file", name, "actual safely owned File and exact fields/physical bytes, or explicit host/unreachable limit")
    for c in json.loads((HERE / "writer-cases.json").read_bytes())["cases"]:
        add("writer", c["id"], "actual selected private writer loop; exact requested/call/error/counter trace and File bytes")
    for name in ["row-observation-error-layout", "full-results-caller-layout", "all-simultaneous-places",
                 "snapshot-construction-lifetime", "one-buffer-no-body-copy", "complete-work-and-callees",
                 "all-error-applicability", "unchanged-public-api"]:
        add("source-proof", name, "full frozen source/caller accounting and actual compiler layouts in both modes")
    patches = row_patches()
    for c in patches["cases"]:
        add("bridge", c["id"], c["expected_disposition"] + "; " + c["applicability"])
    for name in ["actual-row-file-positive", "all-four-authority-literal-false", "phase-only-no-false-join-claim",
                 "failure14-unavailable", "cap-unknown-tail", "late-footer-drift-output-fault",
                 "normal-library-vs-strict-new-diagnostics", "body-origin-vs-synthetic-context"]:
        add("bridge", name, "separate complete actual invocation roster in both modes; unchanged fixture semantics")
    assert len({c["id"] for c in obligations}) == len(obligations)
    dump("review-roster.json", {"schema": 1, "obligations": obligations,
        "obligation_count": len(obligations), "modes": ["debug", "optimized"],
        "binding_state": "preaccess; actual names and source closure must be frozen after root release before execution",
        "namespace_complete": False, "product_runtime_claim": False})
    dump("row-patches.json", patches)
    controls = self_controls()
    dump("support-control-results.json", {"schema": 1, "at": datetime.now(timezone.utc).isoformat(),
        "argv": sys.argv, "python": sys.version, "script_sha256": sha(Path(__file__).read_bytes()),
        "negative_controls": controls, "negative_control_count": len(controls),
        "valid_support_roster_and_role_argv_accepted": True,
        "scope": "preaccess test-support guards only; no actual compiler listing, compiler, bridge, product or File run",
        "no_active_producer_access": True})
    print(f"PASS test support:{len(obligations)}predeclared obligations;{patches['case_count']}byte patches;{len(controls)}negative roster/argument controls")


if __name__ == "__main__":
    main()
