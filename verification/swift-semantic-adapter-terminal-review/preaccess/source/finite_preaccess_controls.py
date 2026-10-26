"""Independent finite projection controls; no producer or Rust code executes."""
from pathlib import Path
import json
import hashlib
import sys

OUT = Path(__file__).resolve().parents[1]


def normalize(mode, supplied):
    result = list(supplied)
    result[26:32] = [0] * 6
    if mode == "suppressed":
        result[2:21] = [0] * 19
        result[24:26] = [0, 0]
    elif mode == "live-idle":
        result[8] = 0
        for index in [9, 14, 18, 19]:
            result[index] = (1 << 64) - 1
    elif mode != "live-active-cap":
        raise ValueError(mode)
    return result


def main():
    raw = (OUT / "cases.json").read_bytes()
    corpus = json.loads(raw)
    words = corpus["word_order"]
    checks = []
    def check(name, condition):
        assert condition, name
        checks.append(name)
    check("exact32-unique-words",len(words)==32 and len(set(words))==32)
    check("known-fixed-first-and-last",words[:2]==["boundary","reason"] and words[-2:]==["reserved0","reserved1"])
    vectors={row["id"]:row for row in corpus["projection_vectors"]}
    for row in vectors.values():
        expected=row["expected32"]
        check(row["id"]+"-width",len(expected)==32 and all(type(v) is int and 0<=v<1<<64 for v in expected))
        check(row["id"]+"-fixed-point",normalize(row["mode"],expected)==expected)
        check(row["id"]+"-authority-reserved",expected[26:32]==[0]*6)
        if row["mode"]=="suppressed":
            check(row["id"]+"-exact-debit",expected[21]==512*row["setup_paid"]+256*row["finish_paid"]+7680*row["charged_records"])
            check(row["id"]+"-paid-flags",expected[22:24]==[row["setup_paid"],row["finish_paid"]])
    for row in corpus["rejected_full32_counterexamples"]:
        bad=row["bad32"];expected=row["expected32"]
        check(row["id"]+"-full32",len(bad)==len(expected)==32 and bad!=expected)
        # Debit/field permutation controls are detected by exact full-row equality;
        # normalizer-only controls additionally demonstrate repair to the fixture.
        check(row["id"]+"-reject-exact",bad!=vectors[row["base_vector"]]["expected32"])
        if row["id"].startswith(("stale-suppressed-","authority-reserved-","idle-stale-")):
            check(row["id"]+"-independent-normalization",normalize(row["mode"],bad)==expected)
    check("distinct-terminal-scenario-ids",len({row["id"] for row in corpus["terminal_scenarios"]})==len(corpus["terminal_scenarios"]))
    check("every-original-decision-explicit",all(row["original_contract_decision_required"] for row in corpus["terminal_scenarios"]))
    for first in ["ordinary-refusal","first-Failure"]:
        group=[row for row in corpus["terminal_scenarios"] if row["id"].startswith("absorbing-"+first+"-")]
        check(first+"-15independent-tails",len(group)==15)
        check(first+"-absorbing-dispatch",all(row["given"]["semantic_calls_after_terminal"]==0 for row in group))
    check("semantic-cost-uses-paid-not-calls",vectors["Z-charged-before-read-no-loan"]["expected32"][21]==8448)
    check("finish-only-semantic-cost",vectors["Z-finish-only"]["expected32"][21:24]==[256,0,1])
    check("zero-calls-can-be-setup-finish-paid",vectors["Z-setup-finish-zero-calls"]["expected32"][21:24]==[768,1,1])
    # This is a corpus/normalizer test count, never a source/Rust/product count.
    result={"schema":1,"scope":"reviewer-owned finite preaccess consistency and normalization only",
            "cases_sha256":hashlib.sha256(raw).hexdigest(),"checks_passed":len(checks),
            "checks":checks,"terminal_scenarios_not_executed_against_correction":len(corpus["terminal_scenarios"]),
            "Rust_product_tests":0,"correction_accessed":False,
            "producer_models_imported_or_executed":False,
            "native_device_GA":False}
    (OUT/"finite-control-result.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({key:result[key] for key in ["scope","cases_sha256","checks_passed",
         "terminal_scenarios_not_executed_against_correction","Rust_product_tests","correction_accessed"]},indent=2))


if __name__=="__main__":
    main()
