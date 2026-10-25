#!/usr/bin/env python3
"""Derive a comparison from immutable model/historical bytes; no producer execution."""
from fractions import Fraction
import hashlib
import json
from pathlib import Path

from model import traces

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def read(path):
    return json.loads(path.read_bytes())


def ratio(numerator, denominator):
    value = Fraction(numerator, denominator)
    return {"fraction": str(value), "decimal": float(value)}


def main():
    frozen = read(HERE / "model-attempt-1/stdout")
    adaptive = read(ROOT / "verification/swift-adaptive-retention-design/stdout.json")
    cost = read(ROOT / "verification/swift-cost-retention-candidate/result-summary.json")
    pairs = []
    for name, modes in frozen["traces"].items():
        baseline = modes["baseline-lru"]
        candidate = modes["plan-aware-cold-insertion"]
        prior = adaptive["traces"][name]["adaptive_model"]
        pairs.append({"case": name, "baseline_interval_decodes": baseline["misses"],
                      "candidate_interval_decodes": candidate["misses"],
                      "candidate_added_policy_estimate": candidate["added"],
                      "candidate_avoided_decodes": candidate["avoided_decodes"],
                      "candidate_policy_only_coverage": ratio(candidate["added"], candidate["avoided_decodes"]) if candidate["avoided_decodes"] > 0 else None,
                      "adaptive_interval_decodes": prior["decodes"],
                      "adaptive_added_policy_estimate": prior["estimated_added_hit_policy_credits"] + prior["estimated_added_miss_policy_credits"]})
    sequences = traces()
    sequence_bytes = (json.dumps(sequences, indent=2, sort_keys=True) + "\n").encode()
    trace_path = HERE / "synthetic-traces.json"
    if trace_path.exists():
        assert trace_path.read_bytes() == sequence_bytes
    else:
        trace_path.write_bytes(sequence_bytes)
    result = {"selection": "withhold-implementation-selection-no-live-integration-no-full-target",
              "frozen_contract_sha256": hashlib.sha256((HERE / "contract.json").read_bytes()).hexdigest(),
              "first_model_stdout_sha256": hashlib.sha256((HERE / "model-attempt-1/stdout").read_bytes()).hexdigest(),
              "synthetic_trace_bytes_sha256": hashlib.sha256(sequence_bytes).hexdigest(),
              "finite_interval_comparison": pairs,
              "historical_cost_candidate_actual_engine_work": [{"case": row["case"], "baseline_credits": row["baseline"]["traceWork"],
                    "candidate_credits": row["candidate"]["traceWork"], "ratio": ratio(row["candidate"]["traceWork"], row["baseline"]["traceWork"])} for row in cost["traces"]],
              "original_failure_sensitivity_not_prediction": {
                    "mean_repeated_build_credits": ratio(34500496, 61142),
                    "adaptive_four_credit_hit_tax": 537576 * 4,
                    "candidate_eight_credit_tax_if_baseline_miss_count_unchanged": 61628 * 8,
                    "candidate_tax_fraction_of_fixed_budget_if_baseline_misses_unchanged": ratio(61628 * 8, 64000000),
                    "limitation": "Baseline counts are not candidate counts. Model policy estimates omit original work and body-size effects and cannot forecast real-target progress."},
              "memory_contract": {"new_persistent_policy_bytes": 0, "new_policy_allocations": 0, "new_tickets": 0,
                    "prospective_scan_outcome_repr_c_64bit_bytes": 32,
                    "prospective_full_inventory_formula": "3 * align8(3*32 + 3*R + 2*8 + 3*8 + 4*1 + 4*8) + DeltaExisting",
                    "R": "Measured size_of<Result<ScanOutcome, SwiftRunFailure>>, unmeasured because no VM candidate was implemented",
                    "DeltaExisting": "Measured enlargement of every existing inventory affected by the changed scan return type; unmeasured and cannot be zero-assumed",
                    "scope": "Explicit prospective authored named-value model only. No Rust layout, cache fixed reservation, operation reservation, physical stack/RSS or allocator measurement is claimed."},
              "limitations": ["Actual target call-order bytes unavailable in selected aggregate telemetry", "Existing phase control adds17 model decodes", "Full64 resident-to-new64 phase adds64 model decodes", "Count-plan reuse means prior successful scan, not necessarily prior completed decode", "Model assertions/global state validation are test instrumentation, not included in proposed eight-credit live path", "No actual VM hit-byte parity, work prefixes, Rust inventory, decoder, cleanup ledger or timing evidence", "No product or full-target execution selected"]}
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
