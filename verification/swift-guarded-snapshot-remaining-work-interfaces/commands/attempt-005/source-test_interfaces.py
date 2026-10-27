#!/usr/bin/env python3
"""Pure composer controls; synthetic arithmetic never qualifies an input."""
import copy
import json
from pathlib import Path
import unittest
from composer import (context, bind, evaluate_synthetic, SyntheticInputs, Context,
                      Refused, MAX, natural, add, mul, total)

D = Path(__file__).resolve().parent
adverse = []

class Interfaces(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = context()
        cls.old, cls.direct, cls.proposal = cls.ctx.original, cls.ctx.direct, cls.ctx.expected_proposal
        cls.accepted = bind(cls.old, cls.direct, ctx=cls.ctx)
        cls.candidate = bind(cls.old, cls.direct, cls.proposal, mode="conditional-review-candidate", ctx=cls.ctx)

    def refuses(self, label, call):
        with self.assertRaises(Refused, msg=label): call()
        adverse.append(label)

    def rebound(self, value, **kwargs):
        return bind(value, self.direct, self.proposal, mode="conditional-review-candidate", ctx=self.ctx, **kwargs)

    def inputs(self, binding=None):
        b = binding or self.candidate
        return {k: (0 if not d["positive"] else 3) for k, d in b["remaining_symbols"].items()}

    def test_accepted_nine_are_distinct_from_fourteen_candidates(self):
        self.assertEqual(len(self.accepted["explicit_obligation_resolutions"]), 9)
        self.assertEqual(len(self.accepted["remaining_symbols"]), 26)
        self.assertEqual(len(self.candidate["explicit_obligation_resolutions"]), 23)
        self.assertEqual(len(self.candidate["remaining_symbols"]), 12)
        self.assertEqual(self.accepted["added_constructor_request_supplement"], 0)
        self.assertEqual(self.candidate["added_constructor_request_supplement"], 55381)
        self.assertEqual(self.old["symbols"], self.candidate["original_35_symbols"])

    def test_no_bound_or_grant_in_either_mode(self):
        for b in (self.accepted, self.candidate):
            for key in ("accepted_bound", "operational_grant", "root_policy_selected", "native_or_GA", "proposed_fourteen_root_selected"):
                self.assertIs(b[key], False)
        for mode in ("accepted", "operational", "root-selected", "", None):
            self.refuses("forbidden-mode:" + str(mode), lambda m=mode: bind(self.old, self.direct, mode=m, ctx=self.ctx))

    def test_context_cannot_be_a_dictionary_or_substituted(self):
        self.refuses("no-context", lambda: bind(self.old, self.direct))
        self.refuses("dict-context", lambda: bind(self.old, self.direct, ctx={}))
        bad = copy.deepcopy(self.old); bad["whole_host"]["fixed"] += 1
        forged = Context(bad, self.direct, self.proposal, {})
        self.refuses("forged-context", lambda: bind(bad, self.direct, self.proposal, mode="conditional-review-candidate", ctx=forged))

    def test_original_model_scope_and_authority_are_exact(self):
        paths = [("schema",), ("source_tree_sha256",), ("host_tree_sha256",), ("unit",),
                 ("operational_grant",), ("product451814442_aggregate_credit",),
                 ("whole_host", "fixed"), ("P0", "fixed")]
        for path in paths:
            bad = copy.deepcopy(self.old); obj = bad
            for k in path[:-1]: obj = obj[k]
            obj[path[-1]] = "foreign"
            self.refuses("foreign-whole:" + "/".join(path), lambda b=bad: self.rebound(b))
        for key in self.old["symbols"]:
            bad = copy.deepcopy(self.old); del bad["symbols"][key]
            self.refuses("omitted-frozen-symbol:" + key, lambda b=bad: self.rebound(b))

    def test_direct_receipt_must_cover_only_exact_selected_nine(self):
        for i in range(9):
            bad = copy.deepcopy(self.direct); del bad["exact_export_scope"][i]
            self.refuses("omitted-direct:" + str(i), lambda b=bad: bind(self.old, b, ctx=self.ctx))
        for change in ("extra", "tree", "authority"):
            bad = copy.deepcopy(self.direct)
            if change == "extra": bad["exact_export_scope"].append(copy.deepcopy(bad["exact_export_scope"][0]))
            elif change == "tree": bad["source_tree_sha256"] = "foreign"
            else: bad["actual_root_policy_or_grant"] = True
            self.refuses("direct-receipt:" + change, lambda b=bad: bind(self.old, b, ctx=self.ctx))

    def test_fourteen_scope_is_complete_and_no_default_price(self):
        for i in range(14):
            bad = copy.deepcopy(self.proposal); del bad["exact_proposed_symbol_scope"][i]
            self.refuses("omitted-proposed:" + str(i), lambda b=bad: bind(self.old, self.direct, b, mode="conditional-review-candidate", ctx=self.ctx))
        for price in (0, 1, 1000000):
            bad = copy.deepcopy(self.proposal); bad["private_price"] = price
            self.refuses("arbitrary-private-price:" + str(price), lambda b=bad: bind(self.old, self.direct, b, mode="conditional-review-candidate", ctx=self.ctx))
        self.refuses("candidate-in-accepted-mode", lambda: bind(self.old, self.direct, self.proposal, ctx=self.ctx))
        self.refuses("missing-candidate", lambda: bind(self.old, self.direct, mode="conditional-review-candidate", ctx=self.ctx))

    def test_payloads_callbacks_and_own_rows_cannot_disappear(self):
        for i, row in enumerate(self.proposal["callee_boundary_rows"]):
            for key in ("typed_payload_multiplicities", "authored_callback_multiplicities", "accepted_named_row_multiplicities", "primitive_event_multiplicities", "covered_expression"):
                bad = copy.deepcopy(self.proposal); del bad["callee_boundary_rows"][i][key]
                self.refuses(f"omitted-coverage:{i}:{key}", lambda b=bad: bind(self.old, self.direct, b, mode="conditional-review-candidate", ctx=self.ctx))

    def test_atomic_pure_callback_stays_once_in_logical_unit(self):
        row = next(x for x in self.proposal["callee_boundary_rows"] if x["node"] == "core_fixed_store_and_after")
        self.assertEqual(row["authored_callback_multiplicities"]["closure::85c9f09d812588039367"], 1)
        for count in (0, 2, "unbounded"):
            bad = copy.deepcopy(self.proposal); bad["logical_atomic_callback"]["count"] = count
            self.refuses("atomic-callback-change:" + str(count), lambda b=bad: bind(self.old, self.direct, b, mode="conditional-review-candidate", ctx=self.ctx))
        bad = copy.deepcopy(self.proposal); bad["logical_atomic_callback"]["dynamic_retry_or_CPU_claim"] = True
        self.refuses("dynamic-retry-claim", lambda: bind(self.old, self.direct, bad, mode="conditional-review-candidate", ctx=self.ctx))

    def test_allocation_request_prices_are_independent_exact_sums(self):
        # This arithmetic does not call the producer formula or resource model.
        expected = {"slots": (64, 136, 8704), "pins": (64, 16, 1024),
                    "patches": (512, 32, 16384), "index": (192, 1, 192), "plans": (512, 56, 28672)}
        result = 0
        for row in self.proposal["constructor_allocation_requests"]:
            n, size, backing = expected[row["field"]]
            self.assertEqual((row["max_requested_elements"], row["element_size"], row["max_requested_bytes"]), (n, size, backing))
            self.assertEqual(n * size, backing)
            self.assertEqual(sum(row["native_fields"].values()), 80)
            result += backing + len(["one logical reservation interface"]) + 8 + 24 + 8 + 8 + 8 + 16 + 8
        self.assertEqual(result, 55381)
        self.assertEqual(result, self.proposal["constructor_allocation_supplement"])
        self.assertEqual(self.candidate["whole_host"]["fixed"] - self.old["whole_host"]["fixed"], result)

    def test_allocations_require_every_field_count_and_bound(self):
        for i, row in enumerate(self.proposal["constructor_allocation_requests"]):
            for key in ("max_calls", "max_requested_elements", "element_size", "max_requested_bytes", "logical_interface_events", "supplement"):
                for value in (0, 1, -1, True, "8"):
                    if row[key] == value and type(row[key]) is type(value): continue
                    bad = copy.deepcopy(self.proposal); bad["constructor_allocation_requests"][i][key] = value
                    self.refuses(f"request-mutation:{i}:{key}:{value!r}", lambda b=bad: bind(self.old, self.direct, b, mode="conditional-review-candidate", ctx=self.ctx))
            for key in row["native_fields"]:
                bad = copy.deepcopy(self.proposal); del bad["constructor_allocation_requests"][i]["native_fields"][key]
                self.refuses(f"request-field-omission:{i}:{key}", lambda b=bad: bind(self.old, self.direct, b, mode="conditional-review-candidate", ctx=self.ctx))

    def test_allocation_funded_once_before_any_dispatch(self):
        for p in self.old["child"]:
            delta = self.candidate["child"][p]["fixed"] - self.old["child"][p]["fixed"]
            self.assertEqual(delta, 55381 if p == "P4_selected_route" else 0)
        self.assertEqual(self.candidate["P0"], self.old["P0"])
        self.assertEqual(total([self.candidate["P0"], *self.candidate["child"].values()]), self.candidate["whole_host"])

    def test_synthetic_evaluation_matches_independent_integer_arithmetic(self):
        for b in (self.accepted, self.candidate):
            for value in (1, 2, 9, 65536):
                values = {k: value for k in b["remaining_symbols"]}
                result = evaluate_synthetic(b, SyntheticInputs(values, "arithmetic-control"), ctx=self.ctx)
                expected = b["whole_host"]["fixed"] + sum(v * values[k] for k, v in b["whole_host"]["terms"].items())
                self.assertEqual(result["whole_host"], expected)
                self.assertFalse(result["accepted_bound"] or result["operational_grant"])

    def test_all_twelve_external_inputs_remain_mandatory(self):
        for key in self.candidate["remaining_symbols"]:
            values = self.inputs(); del values[key]
            self.refuses("missing-remaining:" + key, lambda v=values: evaluate_synthetic(self.candidate, SyntheticInputs(v, "missing-control"), ctx=self.ctx))
        values = self.inputs(); values["extra"] = 1
        self.refuses("unknown-remaining", lambda: evaluate_synthetic(self.candidate, SyntheticInputs(values, "extra-control"), ctx=self.ctx))

    def test_external_inputs_reject_boolean_negative_string_float_overflow(self):
        for key in self.candidate["remaining_symbols"]:
            for value in (-1, True, False, 1.5, "1", None, MAX + 1):
                values = self.inputs(); values[key] = value
                self.refuses("invalid-remaining:" + key + ":" + repr(value), lambda v=values: evaluate_synthetic(self.candidate, SyntheticInputs(v, "invalid-control"), ctx=self.ctx))
            if self.candidate["remaining_symbols"][key]["positive"]:
                values = self.inputs(); values[key] = 0
                self.refuses("zero-required:" + key, lambda v=values: evaluate_synthetic(self.candidate, SyntheticInputs(v, "zero-control"), ctx=self.ctx))

    def test_I_U_zero_only_explicit_synthetic_values_not_defaults(self):
        values = self.inputs()
        self.assertEqual(values["P0_inspections"], 0)
        self.assertEqual(values["P0_usage_reads"], 0)
        evaluate_synthetic(self.candidate, SyntheticInputs(values, "explicit-zero-I-U-arithmetic-only"), ctx=self.ctx)
        self.refuses("plain-values-not-bound", lambda: evaluate_synthetic(self.candidate, values, ctx=self.ctx))
        self.refuses("unlabelled-synthetic", lambda: evaluate_synthetic(self.candidate, SyntheticInputs(values, ""), ctx=self.ctx))

    def test_binding_authority_or_total_cannot_be_altered(self):
        for key in ("accepted_bound", "root_policy_selected", "operational_grant", "native_or_GA", "proposed_fourteen_root_selected"):
            bad = copy.deepcopy(self.candidate); bad[key] = True
            self.refuses("grant-escalation:" + key, lambda b=bad: evaluate_synthetic(b, SyntheticInputs(self.inputs(), "tamper-control"), ctx=self.ctx))
        bad = copy.deepcopy(self.candidate); bad["whole_host"]["fixed"] -= 1
        self.refuses("lost-fixed-action", lambda: evaluate_synthetic(bad, SyntheticInputs(self.inputs(), "omission-control"), ctx=self.ctx))

    def test_arithmetic_rejects_wrap_and_noninteger(self):
        for a in (0, 1, 17, 55381, MAX // 2, MAX):
            for b in (0, 1, 17, 55381, MAX // 2, MAX):
                if a + b <= MAX: self.assertEqual(add(a, b), a + b)
                else: self.refuses(f"add-overflow:{a}:{b}", lambda a=a,b=b: add(a,b))
                if a * b <= MAX: self.assertEqual(mul(a, b), a * b)
                else: self.refuses(f"mul-overflow:{a}:{b}", lambda a=a,b=b: mul(a,b))
        for value in (-1, True, "1", 1.0, None, MAX + 1):
            self.refuses("not-natural:" + repr(value), lambda v=value: natural(v))

    def test_remaining_input_arithmetic_overflow_refuses(self):
        for key in self.candidate["remaining_symbols"]:
            values = self.inputs(); values[key] = MAX
            self.refuses("evaluation-overflow:" + key, lambda v=values: evaluate_synthetic(self.candidate, SyntheticInputs(v, "overflow-control"), ctx=self.ctx))

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Interfaces)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {"schema": 1, "test_methods": result.testsRun, "failures": len(result.failures),
        "errors": len(result.errors), "adverse_cases": len(adverse), "adverse_case_names": adverse,
        "passed": result.wasSuccessful(), "scope": "offline synthetic arithmetic/source-interface controls only",
        "accepted_bound": False, "operational_grant": False}
    import sys
    raw = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
    if "--check" in sys.argv:
        if (D / "test-results.json").read_bytes() != raw: raise Refused("changed-test-results")
    else:
        if (D / "seal.json").exists(): raise Refused("frozen-packet")
        (D / "test-results.json").write_bytes(raw)
    raise SystemExit(0 if result.wasSuccessful() else 1)
