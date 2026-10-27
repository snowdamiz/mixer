#!/usr/bin/env python3
"""Independent offline arithmetic/evidence reader; imports no producer/composer."""
import hashlib
import json
from pathlib import Path
import sys

D = Path(__file__).resolve().parent
R = D.parents[1]
checks = []

def require(name, value):
    if not value: raise AssertionError(name)
    checks.append(name)

def sha(raw): return hashlib.sha256(raw).hexdigest()
def read(rel): return json.loads((R / rel).read_text())
def own(name): return json.loads((D / name).read_text())

def add_expr(expressions):
    fixed = 0
    coefficients = {}
    for expression in expressions:
        require("review-linear-schema", set(expression) == {"fixed", "terms"})
        fixed += expression["fixed"]
        for k, v in expression["terms"].items(): coefficients[k] = coefficients.get(k, 0) + v
    require("review-u64", 0 <= fixed <= (1 << 64) - 1 and all(0 < v <= (1 << 64) - 1 for v in coefficients.values()))
    return {"fixed": fixed, "terms": dict(sorted(coefficients.items()))}

def resource(row, cuts):
    subtotal = (1 + row["inline_bytes"]) * row["structural_occurrence_allowance"]
    for name, n in row["resource_frontiers"].items():
        cut = cuts[name]
        part = cut["interface_work"] + cut["native_resource_backing"]
        if name in row.get("dynamic_resource_elements", {}):
            part += cut["max_live_elements"] * resource(row["dynamic_resource_elements"][name], cut["element_cuts"])
        subtotal += n * part
    return subtotal

def main():
    custody = own("input-custody.json")["files"]
    for path, info in custody.items():
        p = Path(path)
        require("safe-input:" + path, not p.is_absolute() and ".." not in p.parts)
        raw = (R / p).read_bytes()
        require("frozen-input:" + path, info == {"bytes": len(raw), "sha256": sha(raw)})
    p = own("amendment-proposal.json")
    roster = own("interface-roster.json")
    accepted = own("accepted-nine-binding.json")
    candidate = own("conditional-candidate-binding.json")
    report = own("composition-report.json")
    original = read("verification/swift-guarded-snapshot-whole-host-work-composition/work-interface.json")
    direct = read("verification/swift-semantic-adapter-root-review/guarded-snapshot-direct-adapter-contract-amendment.json")
    graph = read("verification/swift-guarded-snapshot-leaf-callee-cost/callee-ledger.json")
    bound = read("verification/swift-guarded-snapshot-leaf-callee-cost-independent/bound-cost-interface.json")
    typed = read("verification/swift-guarded-snapshot-whole-host-work-composition/typed-callee-imports.json")
    cuts = read("verification/swift-guarded-snapshot-resource-cost/resource-cuts.json")
    rows = read("verification/swift-guarded-snapshot-resource-cost/rows.json")
    rows += read("verification/swift-guarded-snapshot-resource-cost/internal-rows.json")["rows"]
    prices = {x["type"].replace(" ", ""): resource(x, cuts) for x in rows}
    # Independently expand the additive row using the same qualified resource
    # frontier prices, rather than trusting its recorded price.
    row = read("verification/swift-guarded-snapshot-whole-host-work-composition/additive-decoded-function-row.json")
    prices["DecodedFunction"] = resource(row["row"], cuts)
    require("DecodedFunction-independent", prices["DecodedFunction"] == 231526438)
    for key, value in typed["typed_imports"].items():
        require("independent-payload:" + key, prices[key[9:].replace(" ", "")] == value)
    require("nineteen-payloads", len(typed["typed_imports"]) == 19)
    require("source146", {p["source_tree_sha256"], original["source_tree_sha256"], candidate["source_tree_sha256"], accepted["source_tree_sha256"]} == {"690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185"})
    require("host11", {p["host_tree_sha256"], original["host_tree_sha256"], candidate["host_tree_sha256"], accepted["host_tree_sha256"]} == {"027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2"})
    require("exact-unit", original["unit"] == p["unit"] == candidate["unit"] == accepted["unit"])
    require("no-frozen-rewrite", len(original["symbols"]) == 35 and candidate["original_35_symbols"] == accepted["original_35_symbols"] == original["symbols"])
    direct_scope = {x["symbol"] for x in direct["exact_export_scope"]}
    proposed_scope = set(p["exact_proposed_symbol_scope"])
    require("accepted-scope-nine", len(direct_scope) == 9 and set(accepted["explicit_obligation_resolutions"]) == direct_scope)
    require("proposed-scope-fourteen", len(proposed_scope) == 14 and not proposed_scope.intersection(direct_scope))
    require("candidate-scope-twentythree", set(candidate["explicit_obligation_resolutions"]) == direct_scope | proposed_scope)
    require("no-positive-price-assignment", p["no_numeric_zero_or_one_private_assignment"] is True and all(x["numeric_private_price_assigned"] is False for x in p["callee_boundary_rows"]))
    require("all-wholeleaf-obligations-explicit", len(p["whole_leaf_boundary_rows"]) == 2 and all(x["symbol"] in proposed_scope for x in p["whole_leaf_boundary_rows"]))
    require("twelve-callee-proposals", len(p["callee_boundary_rows"]) == 12)
    require("twentyone-callee-coverage", len(roster["exports"]) == 21 and {x["export"] for x in roster["exports"]} == set(graph["exports"]))
    # Recompute the transitive node counts with a separate explicit stack.
    for exported in roster["exports"]:
        node_counts, primitives, payloads = {}, {}, {}
        stack = [(exported["node"], 1, ())]
        while stack:
            node, multiplier, ancestors = stack.pop()
            require("no-recursion:" + node, node not in ancestors)
            node_counts[node] = node_counts.get(node, 0) + multiplier
            row = graph["nodes"][node]
            for target, source_key in ((primitives, "primitive"), (payloads, "payload")):
                for k, n in row[source_key].items(): target[k] = target.get(k, 0) + multiplier * n
            for child, count in row["calls"].items(): stack.append((child, multiplier * count, ancestors + (node,)))
        require("independent-visits:" + exported["node"], node_counts == exported["visited_node_multiplicities"])
        require("independent-primitives:" + exported["node"], primitives == exported["primitive_event_multiplicities"])
        require("independent-payload-multiplicity:" + exported["node"], payloads == exported["typed_payload_multiplicities"])
        b = bound["exports"][exported["export"]]
        subtotal = b["fixed"]
        for t, count in payloads.items(): subtotal += prices[t[9:].replace(" ", "")] * count
        coefficients = {b["required_private_primitive_cut"]: 1}
        for t, count in b["unsized"].items():
            if t == "str": coefficients["L_str"] = 2 * count
            else:
                require("exact-array-frontier", t == "[Option<ReservationTicket>]" and count == 8)
                subtotal += 2 * count * (4 * (4 + 24))
        require("independent-export-price:" + exported["node"], exported["covered_expression"] == {"fixed": subtotal, "terms": coefficients})
        expected_callbacks = {k: n for k, n in node_counts.items() if k.startswith("closure::")}
        require("callbacks-retained:" + exported["node"], expected_callbacks == exported["authored_callback_multiplicities"])
    require("atomic-pure-once", p["logical_atomic_callback"] == {"node": "closure::85c9f09d812588039367", "count": 1, "pure": True, "dynamic_retry_or_CPU_claim": False})
    require("explicit-split-callback", sum(x["paid_graph_edges"] == ["core_callback_before", "core_fixed_store_and_after"] for x in roster["authored_callback_sites"]) == 1)
    # Exact per-vector source ceilings and request surfaces, derived anew.
    vectors = [("slots", 64, 136), ("pins", 64, 16), ("patches", 512, 32), ("index", 128 + 64, 1), ("plans", 512, 56)]
    request_total = 0
    backing_total = 0
    for source, item in zip(vectors, p["constructor_allocation_requests"]):
        name, count, element = source
        require("request-identity:" + name, item["field"] == name and item["max_calls"] == 1)
        backing = count * element
        require("request-source-product:" + name, (item["max_requested_elements"], item["element_size"], item["max_requested_bytes"]) == (count, element, backing))
        # ABI widths have exact source146 target/layout provenance in roster.
        fields = {"receiver_reference": 8, "receiver_vec_header": 24, "requested_elements": 8,
            "layout_size": 8, "layout_alignment": 8, "result_unit_or_TryReserveError": 16, "returned_pointer": 8}
        require("request-native-fields:" + name, item["native_fields"] == fields)
        require("request-events:" + name, item["logical_interface_events"] == 1)
        price = backing + 1 + 8 + 24 + 8 + 8 + 8 + 16 + 8
        require("request-price:" + name, item["supplement"] == price)
        request_total += price
        backing_total += backing
    require("five-requests", len(p["constructor_allocation_requests"]) == len(vectors) == 5)
    require("backing-total", backing_total == 54976)
    require("supplement-total", request_total == p["constructor_allocation_supplement"] == 55381)
    for fact in roster["source_facts"]:
        binding = fact["file_binding"]
        text = (R / binding["path"]).read_text()
        require("fact-hash:" + fact["sha256"], sha(fact["text"].encode()) == fact["sha256"])
        require("fact-source-line:" + fact["sha256"], fact["text"] in text and text[:text.index(fact["text"])].count("\n") + 1 == fact["line"])
    for b, scope, delta in ((accepted, direct_scope, 0), (candidate, direct_scope | proposed_scope, request_total)):
        expected = {"fixed": 895084428322997895 + delta,
            "terms": {k: v for k, v in original["whole_host"]["terms"].items() if k not in scope}}
        require("whole-arithmetic:" + b["status"], b["whole_host"] == expected)
        require("six-component-sum:" + b["status"], add_expr([b["P0"], *b["child"].values()]) == expected)
        for k in b["child"]:
            require("request-phase-only:" + b["status"] + ":" + k,
                b["child"][k]["fixed"] == original["child"][k]["fixed"] + (delta if k == "P4_selected_route" else 0))
        require("P0-unmodified:" + b["status"], b["P0"] == original["P0"])
        for key in ("accepted_bound", "root_policy_selected", "operational_grant", "native_or_GA", "proposed_fourteen_root_selected"):
            require("no-authority:" + b["status"] + ":" + key, b[key] is False)
    require("candidate-exact-report", candidate["whole_host"] == report["candidate_expression"])
    require("candidate-twelve-pending", len(candidate["remaining_symbols"]) == 12)
    tests = own("test-results.json")
    require("adverse-controls-pass", tests["passed"] is True and tests["failures"] == tests["errors"] == 0)
    result = {"schema": 1, "status": "independent-offline-arithmetic-and-source-roster-pass",
        "assertions": len(checks), "input_files_rehashed": len(custody),
        "source146": True, "root_selected_nine": 9, "proposed_fourteen": 14,
        "remaining_candidate_inputs": 12, "requested_backing_bytes": backing_total,
        "allocation_supplement": request_total, "candidate_fixed": candidate["whole_host"]["fixed"],
        "test_methods": tests["test_methods"], "adverse_cases": tests["adverse_cases"],
        "frozen_interface_rewritten": False, "root_selected_fourteen": False,
        "selected_bound": False, "operational_grant": False, "native_or_GA": False,
        "limitation": "This independent reader is in the producing lane; a separately accountable root/independent-agent review must select the fourteen amendments. It imports no composer/producer model code and grants no operational authority."}
    raw = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
    if "--check" in sys.argv:
        if (D / "independent-review.json").read_bytes() != raw: raise AssertionError("changed-review")
    else:
        if (D / "seal.json").exists(): raise AssertionError("frozen-packet")
        (D / "independent-review.json").write_bytes(raw)
    print(json.dumps(result, sort_keys=True))

if __name__ == "__main__": main()
