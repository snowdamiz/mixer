#!/usr/bin/env python3
"""Fail-closed amended conditional composer. No operational or accepted-bound API."""
from __future__ import annotations
from dataclasses import dataclass
import json
from pathlib import Path
from derive import build, canonical, digest, Refused, SOURCE, HOST, DIRECT_SHA

D = Path(__file__).resolve().parent
MAX = (1 << 64) - 1
ORIGINAL_CANONICAL_SHA = "2aff6b1c12f46a770472da66cbc5acedbd4d4c76077a72175a24b769a3349cf9"
DIRECT_CANONICAL_SHA = "7f0f8b9ae39966159d910722118b343ce1fe8943a452d3a416cc66a4abfa80e5"
PROPOSAL_CANONICAL_SHA = "cc2b27e0886dbeced24f4c37d01b305ed3d563986d60894a8d50284cf3e5b9b8"
PHASES = ("P1_setup", "P1_loader", "P2_arguments", "P3_before_store", "P4_selected_route", "P5_payload_teardown")

def natural(n):
    if type(n) is not int or n < 0 or n > MAX: raise Refused("not-u64")
    return n

def add(*items):
    value = 0
    for item in items:
        natural(item)
        if value > MAX - item: raise Refused("add-overflow")
        value += item
    return value

def mul(a, b):
    natural(a); natural(b)
    if a and b > MAX // a: raise Refused("multiply-overflow")
    return a * b

def linear(value):
    if type(value) is not dict or set(value) != {"fixed", "terms"}: raise Refused("linear-schema")
    natural(value["fixed"])
    if type(value["terms"]) is not dict: raise Refused("term-schema")
    for key, coeff in value["terms"].items():
        if type(key) is not str or not key or natural(coeff) == 0: raise Refused("term-schema")
    return value

def total(expressions):
    fixed = 0
    terms = {}
    for e in expressions:
        linear(e)
        fixed = add(fixed, e["fixed"])
        for k, c in e["terms"].items(): terms[k] = add(terms.get(k, 0), c)
    return {"fixed": fixed, "terms": dict(sorted(terms.items()))}

@dataclass(frozen=True)
class Context:
    """Constructed only by exact frozen-source validation; contains no grant."""
    original: dict
    direct: dict
    expected_proposal: dict
    expected_outputs: dict

def context():
    outputs, original, direct, _ = build()
    return Context(original, direct, outputs["amendment-proposal.json"], outputs)

def bind(original, direct, proposal=None, *, mode="accepted-nine-only", ctx=None):
    if not isinstance(ctx, Context): raise Refused("frozen-source-context-required")
    if digest(canonical(ctx.original)) != ORIGINAL_CANONICAL_SHA or digest(canonical(ctx.direct)) != DIRECT_CANONICAL_SHA or digest(canonical(ctx.expected_proposal)) != PROPOSAL_CANONICAL_SHA:
        raise Refused("context-source-or-unit-substitution")
    if original != ctx.original: raise Refused("whole-exact-source-unit-symbol-binding")
    if direct != ctx.direct: raise Refused("exact-selected-nine-receipt-required")
    if mode not in ("accepted-nine-only", "conditional-review-candidate"):
        raise Refused("no-operational-or-acceptance-mode")
    if type(original.get("schema")) is not int or original["schema"] != 1: raise Refused("whole-schema")
    if original["source_tree_sha256"] != SOURCE or original["host_tree_sha256"] != HOST: raise Refused("source-unit")
    direct_symbols = {x["symbol"] for x in direct["exact_export_scope"]}
    resolutions = {key: {"basis": "root-selected-nine-exact-direct-clarification", "receipt_sha256": DIRECT_SHA}
                   for key in sorted(direct_symbols)}
    supplement = 0
    if mode == "accepted-nine-only":
        if proposal is not None: raise Refused("unselected-proposal-in-accepted-mode")
    else:
        if proposal != ctx.expected_proposal: raise Refused("exact-source-backed-fourteen-proposal-required")
        if proposal["root_selected"] or proposal["accepted_bound"] or proposal["operational_grant"]:
            raise Refused("candidate-cannot-grant")
        proposed = proposal["exact_proposed_symbol_scope"]
        if not len(proposed) == len(set(proposed)) == 14: raise Refused("fourteen-exact-symbols")
        if direct_symbols.intersection(proposed): raise Refused("scope-overlap")
        for key in proposed:
            if key not in original["symbols"]: raise Refused("unknown-proposed-obligation")
            resolutions[key] = {"basis": "proposed-exact-interface-coverage-root-review-required",
                                "proposal_sha256": digest(canonical(proposal))}
        supplement = natural(proposal["constructor_allocation_supplement"])
        if supplement != 55381: raise Refused("derived-request-supplement-required")
    parts = {}
    if tuple(original["child"]) != PHASES: raise Refused("six-ordered-phases-required")
    for name, value in original["child"].items():
        linear(value)
        parts[name] = {"fixed": add(value["fixed"], supplement if name == "P4_selected_route" else 0),
            "terms": {k: n for k, n in value["terms"].items() if k not in resolutions}}
    p0 = original["P0"]
    whole = total([p0, *parts.values()])
    expected = {"fixed": add(original["whole_host"]["fixed"], supplement),
        "terms": {k: n for k, n in original["whole_host"]["terms"].items() if k not in resolutions}}
    if whole != expected: raise Refused("component-omission-or-misplacement")
    if len(whole["terms"]) != (26 if mode == "accepted-nine-only" else 12): raise Refused("unresolved-scope")
    return {"schema": 1, "status": mode, "source_tree_sha256": SOURCE, "host_tree_sha256": HOST,
        "unit": original["unit"], "original_35_symbols": original["symbols"],
        "explicit_obligation_resolutions": resolutions, "child": parts, "P0": p0, "whole_host": whole,
        "remaining_symbols": {k: original["symbols"][k] for k in whole["terms"]},
        "added_constructor_request_supplement": supplement,
        "proposed_fourteen_root_selected": False, "accepted_bound": False,
        "root_policy_selected": False, "operational_grant": False,
        "product451814442_aggregate_credit": 0, "native_or_GA": False}

@dataclass(frozen=True)
class SyntheticInputs:
    values: dict
    label: str

def evaluate_synthetic(binding, inputs, *, ctx=None):
    if not isinstance(ctx, Context): raise Refused("frozen-source-context-required")
    if not isinstance(inputs, SyntheticInputs) or not inputs.label: raise Refused("explicit-synthetic-inputs-required")
    # Validate the *entire* binder output, including authority and unchanged P0,
    # rather than trusting a dict carrying the right final constant.
    proposal = ctx.expected_proposal if binding.get("status") == "conditional-review-candidate" else None
    if binding != bind(ctx.original, ctx.direct, proposal, mode=binding.get("status"), ctx=ctx):
        raise Refused("binding-altered")
    values = inputs.values
    symbols = binding["remaining_symbols"]
    if type(values) is not dict or set(values) != set(symbols): raise Refused("missing-or-unknown-remaining-input")
    for k, d in symbols.items():
        n = natural(values[k])
        if n == 0 and d["positive"]: raise Refused("positive-required:" + k)
    def calc(e):
        linear(e)
        return add(e["fixed"], *(mul(n, values[k]) for k, n in e["terms"].items()))
    parts = {k: calc(e) for k, e in binding["child"].items()}
    p0 = calc(binding["P0"])
    whole = calc(binding["whole_host"])
    if add(p0, *parts.values()) != whole: raise Refused("arithmetic-composition")
    return {"synthetic_label": inputs.label, "child": parts, "P0": p0, "whole_host": whole,
        "accepted_bound": False, "root_policy_selected": False, "operational_grant": False,
        "native_or_GA": False}

def main():
    ctx = context()
    for name, mode, p in [("accepted-nine-binding.json", "accepted-nine-only", None),
            ("conditional-candidate-binding.json", "conditional-review-candidate", ctx.expected_proposal)]:
        result = bind(ctx.original, ctx.direct, p, mode=mode, ctx=ctx)
        raw = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
        import sys
        if "--check" in sys.argv:
            if (D / name).read_bytes() != raw: raise Refused("changed-output:" + name)
        else:
            if (D / "seal.json").exists(): raise Refused("frozen-packet")
            (D / name).write_bytes(raw)
    print(json.dumps({"status": "pass", "accepted_only_remaining": 26,
        "candidate_remaining": 12, "allocation_supplement": 55381, "operational_grant": False}))

if __name__ == "__main__": main()
