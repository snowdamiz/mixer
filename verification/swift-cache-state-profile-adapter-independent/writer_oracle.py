#!/usr/bin/env python3
"""Contract-only writer oracle. Never imports or executes the product writer."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).absolute().parent
BLOCK, BLOCKS, LIMIT = 4096, 625, 32
BODY = BLOCK * BLOCKS


def h(data):
    return hashlib.sha256(data).hexdigest()


def outcome(code, acknowledged, attempts):
    return {"success": code == 0, "code": code, "stage": 0 if code == 0 else 4,
            "offset": acknowledged, "output_bytes": acknowledged,
            "output_attempts": attempts}


def case(name, pattern, expected, blocks=None, physical_fault=None):
    return {"id": name, "default_block_actions": pattern,
            "block_overrides": blocks or {}, "expected": expected,
            "physical_fault": physical_fault,
            "unconsumed_action_is_not_an_actual_call": True}


I = ["interrupted"]
R = ["remaining"]
B = lambda n: ["bytes", n]
E, Z, O = ["error"], ["zero"], ["overreport"]


def cases():
    return [
        case("full-625-blocks", [R], outcome(0, BODY, 625)),
        case("all-blocks-call31-completes", [I] * 30 + [R], outcome(0, BODY, 19375)),
        case("all-blocks-call32-completes", [I] * 31 + [R], outcome(0, BODY, 20000)),
        case("all-blocks-32-valid128", [B(128)] * 32, outcome(0, BODY, 20000)),
        case("first-call32-completes", [R], outcome(0, BODY, 656), {"0": [I] * 31 + [R]}),
        case("first-call32-completes-after31-short", [R], outcome(0, BODY, 656), {"0": [B(1)] * 31 + [R]}),
        case("first-call31-completes", [R], outcome(0, BODY, 655), {"0": [I] * 30 + [R]}),
        case("first-call32-interrupted-no33", [R], outcome(12, 0, 32), {"0": [I] * 32 + [["forbidden33"]]}),
        case("first-call32-short1-no33", [R], outcome(12, 1, 32), {"0": [I] * 31 + [B(1), ["forbidden33"]]}),
        case("first-32-short1-no33", [R], outcome(12, 32, 32), {"0": [B(1)] * 32 + [["forbidden33"]]}),
        case("first-call32-error-specific", [R], outcome(9, 0, 32), {"0": [I] * 31 + [E]}),
        case("first-call32-zero-specific", [R], outcome(10, 0, 32), {"0": [I] * 31 + [Z]}),
        case("first-call32-overreport-specific", [R], outcome(11, 0, 32), {"0": [I] * 31 + [O]}),
        case("first-error", [E], outcome(9, 0, 1)),
        case("first-zero", [Z], outcome(10, 0, 1)),
        case("first-overreport", [O], outcome(11, 0, 1)),
        case("first-usize64-max-overreport", [["bytes", 18446744073709551615]], outcome(11, 0, 1)),
        case("partial17-error", [B(17), E], outcome(9, 17, 2)),
        case("partial17-zero", [B(17), Z], outcome(10, 17, 2)),
        case("partial17-overreport", [B(17), O], outcome(11, 17, 2)),
        case("partial17-call32-interrupted", [B(17)] + [I] * 31 + [["forbidden33"]], outcome(12, 17, 32)),
        case("later-block-partial17-error", [R], outcome(9, 4113, 3), {"1": [B(17), E]}),
        case("last-block-call32-zero", [R], outcome(10, 2555904, 656), {"624": [I] * 31 + [Z]}),
        case("max-global-call20000-zero", [I] * 31 + [R], outcome(10, 2555904, 20000), {"624": [I] * 31 + [Z]}),
        case("max-global-call20000-short1", [I] * 31 + [R], outcome(12, 2555905, 20000), {"624": [I] * 31 + [B(1), ["forbidden33"]]}),
        case("max-global-call20000-overreport", [I] * 31 + [R], outcome(11, 2555904, 20000), {"624": [I] * 31 + [O]}),
        case("max-global-call20000-error", [I] * 31 + [R], outcome(9, 2555904, 20000), {"624": [I] * 31 + [E]}),
        case("error-side-effect-not-acknowledged", [E], outcome(9, 0, 1), physical_fault={"on_call": 1, "write_body_prefix_before_error": 3}),
        case("overreport-side-effect-not-acknowledged", [O], outcome(11, 0, 1), physical_fault={"on_call": 1, "write_body_prefix_before_overreport": 7}),
    ]


def interpret(c):
    acknowledged = attempts = 0
    trace = hashlib.sha256()
    for block in range(BLOCKS):
        remaining = BLOCK
        actions = c["block_overrides"].get(str(block), c["default_block_actions"])
        for local in range(LIMIT):
            assert local < len(actions), (c["id"], "unspecified action", block, local)
            action = actions[local]
            assert action[0] != "forbidden33", "a forbidden actual call was attempted"
            attempts += 1
            trace.update(json.dumps([block, local + 1, remaining, acknowledged, attempts, action], separators=(",", ":")).encode() + b"\n")
            kind = action[0]
            if kind == "error":
                return outcome(9, acknowledged, attempts), trace.hexdigest()
            if kind == "zero":
                return outcome(10, acknowledged, attempts), trace.hexdigest()
            if kind == "interrupted":
                pass
            else:
                n = remaining if kind == "remaining" else remaining + 1 if kind == "overreport" else action[1]
                if n > remaining:
                    return outcome(11, acknowledged, attempts), trace.hexdigest()
                assert 1 <= n <= remaining
                acknowledged += n
                remaining -= n
                if remaining == 0:
                    break
            if local + 1 == LIMIT:
                return outcome(12, acknowledged, attempts), trace.hexdigest()
        assert remaining == 0
    return outcome(0, acknowledged, attempts), trace.hexdigest()


def main():
    fixture = HERE / "fixtures/minimum-abi29.expected-row-body.bin"
    body = fixture.read_bytes()
    assert len(body) == BODY
    rows = cases()
    assert len({c["id"] for c in rows}) == len(rows) == 29
    for c in rows:
        actual, trace_hash = interpret(c)
        assert actual == c["expected"], (c["id"], actual, c["expected"])
        assert actual["output_attempts"] <= 20000
        c["protocol_trace_sha256"] = trace_hash
        acknowledged = actual["output_bytes"]
        c["acknowledged_expected_prefix_sha256"] = h(body[:acknowledged])
        if c["physical_fault"]:
            fault = c["physical_fault"]
            n = next(v for k, v in fault.items() if k.startswith("write_body_prefix_"))
            c["scripted_physical_expected"] = {"bytes": n, "sha256": h(body[:n]),
                "basis": "explicit side effect script; never inferred from acknowledgement"}
        else:
            c["scripted_physical_expected"] = {"bytes": acknowledged,
                "sha256": h(body[:acknowledged]),
                "basis": "future private fault adapter must forward exactly each valid acknowledged prefix to actual File"}
    result = {"schema": 1, "at": datetime.now(timezone.utc).isoformat(),
        "argv": sys.argv, "python": sys.version,
        "script_sha256": h(Path(__file__).read_bytes()),
        "contract_sha256": h((HERE / "inputs/protocol-amendment.md").read_bytes()),
        "independent_row_body_sha256": h(body), "cases": rows,
        "case_count": len(rows), "scope": "predeclared contract expectations and test-support interpreter only",
        "real_File_or_product_writer_executed": False,
        "none_of_these_cases_is_actual_product_runtime_evidence": True,
        "success_code_and_stage_zero_are_oracle_only_not_a_product_Error": True}
    (HERE / "writer-cases.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print("PASS test-support writer protocol:29 predeclared cases; no product or File execution")


if __name__ == "__main__":
    main()
