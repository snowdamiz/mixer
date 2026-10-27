#!/usr/bin/env python3
"""Separately accountable offline reader. Imports no candidate model code."""
from __future__ import annotations
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys

D = Path(__file__).resolve().parent
R = D.parents[1]
C = "verification/swift-guarded-snapshot-remaining-work-interfaces"
W = "verification/swift-guarded-snapshot-whole-host-work-composition"
RELEASE = "verification/swift-semantic-adapter-root-review/guarded-snapshot-remaining-work-frozen-release.json"
RELEASE_SHA = "a933afc7d88f6b5ce85049bd1dae79ee525f05e6a6f2898e855f40cdb6de9b4a"
SEAL_SHA = "e644f57466368837445abd57506edeab9ab87135571b354be4ee772e31ddf23a"
SOURCE = "690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185"
HOST = "027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2"
DIRECT = "verification/swift-semantic-adapter-root-review/guarded-snapshot-direct-adapter-contract-amendment.json"
ACCEPT = "verification/swift-semantic-adapter-root-review/guarded-snapshot-whole-host-work-host-acceptance.json"
files, checks = {}, []

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

def require(label, value):
    if not value:
        raise AssertionError(label)
    checks.append(label)

def raw(path, expected=None):
    p = Path(path)
    require("safe-relative:" + str(p), not p.is_absolute() and ".." not in p.parts)
    target = R / p
    require("not-symlink:" + str(p), not target.is_symlink())
    data = target.read_bytes()
    info = {"bytes": len(data), "sha256": sha(data)}
    if expected is not None:
        require("exact-input:" + str(p), canonical(info) == canonical(expected))
    files[str(p)] = info
    return data

def read(path):
    return json.loads(raw(path))

def candidate(name):
    return read(C + "/" + name)

def pin(path, expected):
    data = raw(path)
    require("pinned:" + path, sha(data) == expected)
    return json.loads(data)

def price(row, cuts):
    """Re-expand each structural/resource occurrence without candidate helpers."""
    value = row["structural_occurrence_allowance"] * (row["inline_bytes"] + 1)
    for key, count in row["resource_frontiers"].items():
        cut = cuts[key]
        part = cut["interface_work"] + cut["native_resource_backing"]
        if key in row.get("dynamic_resource_elements", {}):
            part += cut["max_live_elements"] * price(row["dynamic_resource_elements"][key], cut["element_cuts"])
        value += count * part
    return value

def sum_linear(items):
    terms = Counter()
    fixed = 0
    for item in items:
        require("exact-linear-schema", set(item) == {"fixed", "terms"})
        require("integer-fixed", type(item["fixed"]) is int and 0 <= item["fixed"] < 2**64)
        fixed += item["fixed"]
        for key, count in item["terms"].items():
            require("integer-positive-coefficient:" + key, type(count) is int and 0 < count < 2**64)
            terms[key] += count
    require("sum-fits-u64", fixed < 2**64 and all(n < 2**64 for n in terms.values()))
    return {"fixed": fixed, "terms": dict(sorted(terms.items()))}

def main():
    release = pin(RELEASE, RELEASE_SHA)
    seal = pin(C + "/seal.json", SEAL_SHA)
    require("release-identity", release["path"] == C and release["seal_sha256"] == SEAL_SHA)
    require("release-no-selection", release["amendment_selected"] is False and release["operational_grant"] is False)
    require("candidate-seal-count", len(seal["members"]) == seal["member_count"] == release["members"] == 103)
    names = set()
    for member in seal["members"]:
        require("candidate-member-unique:" + member["path"], member["path"] not in names)
        names.add(member["path"])
        raw(C + "/" + member["path"], {k: member[k] for k in ("bytes", "sha256")})
    require("candidate-seal-bytes", sum(m["bytes"] for m in seal["members"]) == seal["bytes"] == release["bytes"] == 937922)
    require("candidate-members-exact", names == {str(p.relative_to(R / C)) for p in (R / C).rglob("*") if p.is_file() and p.name != "seal.json"})
    custody = candidate("input-custody.json")["files"]
    require("candidate-input-roster-320", len(custody) == 320)
    for path, info in custody.items():
        raw(path, info)
    direct = pin(DIRECT, "af33b1faed65d1de6764520f7f6a3eb08a2877b2612b5d8c4fdee36ea55dfcff")
    acceptance = pin(ACCEPT, "d797f7c9a86259fdb40700c290e5f83488142117a355f7b5826c1d92710a784f")
    proposal, roster = candidate("amendment-proposal.json"), candidate("interface-roster.json")
    original = read(W + "/work-interface.json")
    accepted, amended = candidate("accepted-nine-binding.json"), candidate("conditional-candidate-binding.json")
    graph = read("verification/swift-guarded-snapshot-leaf-callee-cost/callee-ledger.json")
    bound = read("verification/swift-guarded-snapshot-leaf-callee-cost-independent/bound-cost-interface.json")
    typed = read(W + "/typed-callee-imports.json")
    old_roster = read(W + "/private-export-allowance-roster.json")
    shell = read("verification/swift-guarded-snapshot-leaf-shell-cost/operation-ledger.json")
    actual_edges = read(W + "/actual-edges.json")
    cuts = read("verification/swift-guarded-snapshot-resource-cost/resource-cuts.json")
    rows = read("verification/swift-guarded-snapshot-resource-cost/rows.json")
    rows += read("verification/swift-guarded-snapshot-resource-cost/internal-rows.json")["rows"]
    decoded = read(W + "/additive-decoded-function-row.json")
    require("all33-resource-rows-preserved", len(rows) == typed["accepted_resource_rows"] == 33)
    prices = {row["type"].replace(" ", ""): price(row, cuts) for row in rows}
    prices["DecodedFunction"] = price(decoded["row"], cuts)
    require("decoded-exact", prices["DecodedFunction"] == decoded["price"] == 231526438)
    require("nineteen-payload-imports", len(typed["typed_imports"]) == 19)
    for key, value in typed["typed_imports"].items():
        require("independent-resource-price:" + key, value == prices[key.removeprefix("payload::").replace(" ", "")])

    manifest = read("verification/swift-guarded-snapshot-host-composition/source-manifest.json")
    host = read("verification/swift-guarded-snapshot-host-composition/host-support-manifest.json")
    require("source146-canonical-tree", len(manifest["members"]) == 146 and sha(canonical(manifest["members"])) == SOURCE)
    require("host11-canonical-tree", len(host["members"]) == 11 and sha(canonical(host["members"])) == HOST)
    sources, source_paths = {}, {}
    for member in manifest["members"]:
        path = "verification/swift-guarded-snapshot-host-composition/overlay/vm/" + member["path"]
        if path not in custody:
            path = "verification/swift-guarded-snapshot-funding-implementation/source/vm/" + member["path"]
        require("source-released:" + member["path"], path in custody)
        sources[member["path"]] = raw(path, {k: member[k] for k in ("bytes", "sha256")}).decode()
        source_paths[member["path"]] = path
    for member in host["members"]:
        raw("verification/swift-real-profile-loader-binding/host/" + member["path"], {k: member[k] for k in ("bytes", "sha256")})
    for binding_name, binding in list(graph["source_bindings"].items()) + [(n, r["binding"]) for n, r in graph["nodes"].items() if "binding" in r]:
        require("sourcebody-hash:" + binding_name, sha(binding["source"].encode()) == binding["sha256"])
        require("sourcebody-exact146:" + binding_name, binding["source"] in sources[binding["path"]])
    for node_name,row in graph["nodes"].items():
        if "parts" in row:
            require("accepted-own-parts", sum(row["parts"].values()) == row["own"])
        if "operations" in row:
            # Inline-only drops are logical adapter events, distinct from the
            # separately imported resource-owning payload rows. The inherited
            # concrete core frame normalizes its generic Copy Result drop; its
            # authored operation/role surfaces are still retained in full.
            adapters = sum(op["weight"] for op in row["operations"] for edge in op["edges"] if edge["kind"] == "payload" and edge["target"] not in row["payload"])
            if node_name == "core_before_fixed_store":
                require("core-concrete-Copy-result-normalization", adapters == 1 and graph["typed_inline_drop_adapters"]["payload::Result<(), SwiftRunFailure>"]["actual_payload"] is False)
                adapters = 0
            expected = sum(op["source"] * op["weight"] for op in row["operations"]) + sum(row["primitive"].values()) + adapters
            require("authored-source-primitives-inline-drops:" + node_name, row["own"] == expected)
    require("eight-source-frames", len(shell["functions"]) == 8)
    require("all205-role-surfaces", sum(len(f["roles"]) for f in shell["functions"]) == 205)
    require("all598-written-operations", sum(len(b["lines"]) for f in shell["functions"] for b in f["blocks"].values()) == 598)
    for f in shell["functions"]:
        b = f["binding"]
        # Bind the exact fn fragment; line starts also contain visibility and
        # indentation which the released fn fragment intentionally excludes.
        data,signature = sources[b["path"]].encode(), b["signature"].encode()
        at,matches = 0,[]
        while True:
            at = data.find(signature,at)
            if at < 0: break
            fragment = data[at:at+b["source_function_bytes"]]
            if sha(fragment) == b["source_function_sha256"]: matches.append(at)
            at += 1
        require("shell-body-binding:" + f["function"], len(matches) == 1)

    # A fresh stack traversal, independent of the candidate recursive traversal.
    active, coverage = set(), []
    for exported in roster["exports"]:
        visits, primitives, payloads, unsized = Counter(), Counter(), Counter(), Counter()
        work = [(exported["node"], 1, ())]
        while work:
            node, multiplier, ancestors = work.pop()
            require("acyclic:" + node, node not in ancestors)
            active.add(node)
            row = graph["nodes"][node]
            visits[node] += multiplier
            for target, field in ((primitives, "primitive"), (payloads, "payload"), (unsized, "unsized")):
                for key, count in row.get(field, {}).items():
                    require("positive-node-count:" + node + ":" + key, type(count) is int and count > 0)
                    target[key] += multiplier * count
            for child, count in row["calls"].items():
                require("positive-edge:" + node + ":" + child, type(count) is int and count > 0)
                work.append((child, count * multiplier, ancestors + (node,)))
        e = exported["export"]
        b = bound["exports"][e]
        old = next(x for x in old_roster["exports"] if x["export"] == e)
        require("visit-roster:" + e, dict(visits) == exported["visited_node_multiplicities"])
        require("primitive-roster:" + e, dict(primitives) == exported["primitive_event_multiplicities"] == old["primitive_callsite_occurrences"])
        require("payload-roster:" + e, dict(payloads) == exported["typed_payload_multiplicities"] == b["payload"])
        require("unsized-roster:" + e, dict(unsized) == b["unsized"])
        require("accepted-own-child-roster:" + e, {k:n for k,n in visits.items() if graph["nodes"][k]["kind"].startswith("accepted-")} == exported["accepted_named_row_multiplicities"])
        require("callback-roster:" + e, {k:n for k,n in visits.items() if k.startswith("closure::")} == exported["authored_callback_multiplicities"])
        fixed = b["fixed"] + sum(prices[t.removeprefix("payload::").replace(" ", "")] * n for t,n in payloads.items())
        terms = {b["required_private_primitive_cut"]: 1}
        for kind, count in unsized.items():
            if kind == "str":
                terms["L_str"] = count * 2
            else:
                require("only-actual-four-ticket-array", kind == "[Option<ReservationTicket>]" and e == "callee::accounted::AccountedWasi::snapshot_pair_v1" and count == 8)
                fixed += count * 2 * (4 * (3 + 1 + 24))
        require("qualified-native-no-extra-term:" + e, b["native"] == {})
        require("typed-export-complete:" + e, exported["covered_expression"] == typed["exports"][e] == {"fixed": fixed, "terms": terms})
        require("actual-export-callsite-coefficient:" + e, exported["callsite_coefficient"] == actual_edges["33cut_occurrences"][e] == original["whole_host"]["terms"][exported["symbol"]])
        coverage.append({"export": e, "visits": dict(sorted(visits.items())), "primitive_events": dict(sorted(primitives.items())), "payloads": dict(sorted(payloads.items())), "fixed_with_payloads": fixed, "terms": terms})
    require("exact21exports83nodes", len(roster["exports"]) == len(graph["exports"]) == 21 and len(active) == 83)
    require("constructor-payload-full", sum(prices[k.removeprefix("payload::").replace(" ", "")] * n for k,n in bound["exports"]["callee::construct_snapshot_in_scope_v1"]["payload"].items()) == typed["constructor_exact_payload"] == 136709543157)
    require("constructor-own-region", sum(graph["constructor_applicability"]["terms"].values()) == graph["nodes"]["accepted_constructor_region"]["own"] == 451718715)
    require("no-aggregate-credit", graph["constructor_applicability"]["product451814442_transferred"] is False and graph["constructor_applicability"]["product_work_discount"] == 0 and actual_edges["product_aggregate_credit"] == 0)
    require("constructor-success-snapshot-closed", graph["constructor_applicability"]["writer_encoder_initializer_entered"] is False and graph["constructor_applicability"]["changed_snapshot_commit_storage_entered"] is False)

    # Count every primitive+callback co-occurrence directly from operation edges.
    callback_sites = []
    for name in sorted(active):
        row = graph["nodes"][name]
        for op in row.get("operations", []):
            primitives = [x["target"] for x in op["edges"] if x["kind"] == "closed-primitive"]
            callbacks = [x["target"] for x in op["edges"] if x["kind"] == "call"]
            if not primitives or not callbacks:
                continue
            key = (name, op["line"], op["block"])
            matches = [x for x in roster["authored_callback_sites"] if (x["caller"],x["line"],x["block"]) == key]
            require("exact-callback-site:" + str(key), len(matches) == 1)
            x = matches[0]
            require("callback-native-source-surface:" + str(key), x["code"] == op["code"] and x["code_sha256"] == sha(op["code"].encode()) and x["weight"] == op["weight"] and x["authored_callbacks"] == callbacks and x["closed_primitive"] == primitives)
            expected = ["core_callback_before", "core_fixed_store_and_after"] if name == "core_before_fixed_store" else callbacks
            require("callback-charged-edges:" + str(key), x["paid_graph_edges"] == expected)
            callback_sites.append(key)
    require("nineteen-authored-callback-sites", len(callback_sites) == len(set(callback_sites)) == len(roster["authored_callback_sites"]) == 19)
    atomic = graph["nodes"]["closure::85c9f09d812588039367"]
    require("atomic-pure-closed", atomic["calls"] == atomic["payload"] == atomic["unsized"] == {} and atomic["primitive"] == {"core::num::<impl u64>::checked_add": 1})
    require("atomic-logical-once", proposal["logical_atomic_callback"] == {"node":"closure::85c9f09d812588039367", "count":1, "pure":True, "dynamic_retry_or_CPU_claim":False} and graph["nodes"]["core_fixed_store_and_after"]["calls"]["closure::85c9f09d812588039367"] == 1)
    phase = graph["core_phase_binding"]
    before, after = graph["nodes"]["core_callback_before"], graph["nodes"]["core_fixed_store_and_after"]
    whole_callback = graph["nodes"]["closure::c431121f0512d03c77fd"]
    def opid(op): return (op["line"],op["block"],op["code"])
    pre_ops, post_ops, all_ops = [set(map(opid,r["operations"])) for r in (before,after,whole_callback)]
    zero_policy_only = {(530,"bb20","_37 = const ();"),(531,"bb20","goto -> bb26;")}
    require("phase-union-selected-positive-policy-complete", pre_ops | post_ops == all_ops - zero_policy_only and not zero_policy_only & (pre_ops | post_ops))
    control_source = sources["src/experimental_swift_reactor/control.rs"]
    require("concrete-positive-policy-source", "Self::adopt_body_core_v1::<SnapshotAdoptionV1>(body,budget,started,cancellation)?" in control_source and "const FIXED_EXECUTION_WORK_V1: u64 = SNAPSHOT_FIXED_EXECUTION_WORK_V1;" in control_source and "451_703_621 + 33_613 + 68_781 + 7_155 + 1_272;" in control_source and phase["ordinary_zero_policy_refused_by_evaluator"] is True)
    require("phase-shared-exits-only", {x[1] for x in pre_ops & post_ops} == set(phase["overlap_blocks"]) == {"bb3", "bb69"})
    store = opid(phase["counter_store"])
    require("store-only-after", store in post_ops and store not in pre_ops)
    require("five-after-reservations", after["calls"]["accepted::admit"] == 5)
    require("outer-frame-prepaid-once", graph["nodes"]["core_before_fixed_store"]["calls"]["core_callback_before"] == 1 and "closure::c431121f0512d03c77fd" not in graph["nodes"]["core_before_fixed_store"]["calls"] and phase["outer_frame_charged_before_once"] is True and phase["all_shared_exit_scaffolding_prepaid_before"] is True)

    archive_path = graph["full_source146_layout_binding"]["path"]
    archive = raw(archive_path, custody[archive_path])
    layout_data = gzip.decompress(archive)
    require("source146-layout-data-exact", sha(layout_data) == "6c924c8088173db78afb1f648b284df7d8d139b3389bd090a9552df4130cfe7a")
    layout_lines = layout_data.decode().splitlines()
    for observation in roster["native_layout_observations"]:
        line = f"print-type-size type: `{observation['type']}`: {observation['size']} bytes, alignment: {observation['alignment']} bytes"
        require("exact-native-layout:" + observation["type"], observation["line"] == line and layout_lines.count(line) == 1)

    cache, control, initial = (sources[x] for x in ("src/experimental_swift_reactor/cache.rs", "src/experimental_swift_reactor/control.rs", "src/experimental_swift_reactor/cache/initial_profile_v1.rs"))
    for fact in roster["source_facts"]:
        source = sources[fact["path"]]
        require("bound-sourcefact:" + fact["sha256"], fact["file_binding"]["path"] == source_paths[fact["path"]] and sha(fact["text"].encode()) == fact["sha256"] and fact["text"] in source and source[:source.index(fact["text"])].count("\n") + 1 == fact["line"])
    constructor = cache[cache.index("    fn construct_partial("):cache.index("    pub(crate) fn complete<T>(self, returned_phase_storage: T)", cache.index("    fn construct_partial("))]
    require("only-five-authored-reserves", constructor.count("reserve(&mut partial.") == 5)
    require("fresh-empty-five-vectors", "slots: Vec::new(),\n            pins: Vec::new(),\n            patches: Vec::new(),\n            index: Vec::new(),\n            plans: Vec::new()," in cache)
    require("request-once-then-exact-capacity", cache.count("values.try_reserve_exact(requested)") == 1 and "control.exact(requested, values.capacity())?;" in cache)
    require("budget-bound-before-core-store", control.index("control.check_budget(cursor)?;") < control.index("control.execution_work = P::FIXED_EXECUTION_WORK_V1;"))
    require("budget-source-maximums", "cache_entries: 64," in control and "active_pins: 64," in control and "if attempted > limit" in control)
    require("original-row-helper-not-removed", "write_initial_profile_rows_v1(&initial,row_output)" in initial)
    require("snapshot-emission-refuses", "fn proposed_emission_work_v1(_shape:&SnapshotShapeV1)->Result<u64,AError>" in initial and "Err(AError::WorkAuditPending)" in initial)
    vectors = [("slots",64,136,"entries"),("pins",64,16,"budget.active_pins"),("patches",512,32,"PATCH_CAPACITY"),("index",128+64,1,"RESIDENT_INDEX_BYTES"),("plans",512,56,"PLAN_CAPACITY")]
    fields = {"receiver_reference":8,"receiver_vec_header":24,"requested_elements":8,"layout_size":8,"layout_alignment":8,"result_unit_or_TryReserveError":16,"returned_pointer":8}
    require("native-target-field-widths", graph["layouts"]["usize"] == graph["layouts"]["&mut Vec<u8>"] == 8 and graph["layouts"]["Vec<u8>"] == 24 and sum(fields.values()) == 80)
    backing = supplement = 0
    allocation_rows = []
    for (field,count,size,expression), row in zip(vectors,proposal["constructor_allocation_requests"]):
        statement = f"reserve(&mut partial.{field}, {expression}, &mut self.control)?;"
        require("unique-reserve-source:" + field, constructor.count(statement) == 1)
        require("bounded-push-source:" + field, f"for _ in 0..{expression}" in constructor and f"partial.{field}.push(" in constructor)
        expected_bytes = count * size
        expected_price = expected_bytes + 1 + sum(fields.values())
        require("allocation-fields:" + field, canonical(row["native_fields"]) == canonical(fields))
        require("allocation-exact-identity:" + field, row["field"] == field and type(row["max_calls"]) is int and row["max_calls"] == 1 and type(row["logical_interface_events"]) is int and row["logical_interface_events"] == 1)
        require("allocation-exact-product:" + field, (row["max_requested_elements"], row["element_size"], row["max_requested_bytes"], row["supplement"]) == (count,size,expected_bytes,expected_price))
        backing += expected_bytes
        supplement += expected_price
        allocation_rows.append({"field":field,"elements":count,"element_bytes":size,"requested_bytes":expected_bytes,"interface_event_and_native_bytes":81,"supplement":expected_price})
    require("five-total54976plus405", len(proposal["constructor_allocation_requests"]) == 5 and backing == 54976 and supplement == proposal["constructor_allocation_supplement"] == 55381)
    # Concrete multiplicities show resource cuts were neither replaced nor lost.
    require("cache66decoded-retained", graph["nodes"]["cache_cleanup"]["payload"]["payload::DecodedFunction"] == 66)
    require("cache68drops200callbacks130removal", graph["nodes"]["cache_cleanup"]["calls"]["accepted::drop_reserved_with_wasi"] == 68 and graph["nodes"]["cache_cleanup"]["calls"]["accepted::wasi_usage"] == 200 and graph["nodes"]["cache_cleanup"]["calls"]["authored::3a47c62a96a08ea26ee1"] == 130)
    require("two-cache-loops-bounded", [(x["max_iterations"],x["block_visits_upper"]) for x in graph["nodes"]["cache_cleanup"]["loops"]] == [(64,65),(64,65)])
    require("two-drop-callers-retained", actual_edges["33cut_occurrences"]["callee::std::mem::drop::<Option<experimental_swift_reactor::cache::SwiftFunctionCache>>"] == 2)
    require("two-proof-refunds-retained", graph["nodes"]["drop_proof"]["calls"]["accepted::refund_with_wasi"] == 2 and graph["nodes"]["drop_proof"]["payload"] == {"payload::AdoptionBodyV1":1})

    direct_scope = {x["symbol"] for x in direct["exact_export_scope"]}
    proposed_scope = set(proposal["exact_proposed_symbol_scope"])
    require("exact-disjoint9and14", len(direct_scope) == 9 and len(proposed_scope) == len(proposal["exact_proposed_symbol_scope"]) == 14 and not direct_scope & proposed_scope)
    require("twelve-callee-two-wholeleaf", len(proposal["callee_boundary_rows"]) == 12 and len(proposal["whole_leaf_boundary_rows"]) == 2)
    require("candidate-private-is-coverage-only", proposal["no_numeric_zero_or_one_private_assignment"] is True and all(x["numeric_private_price_assigned"] is False for x in proposal["callee_boundary_rows"]) and all(x["additional_price_assigned"] is False for x in proposal["whole_leaf_boundary_rows"]))
    for b,scope,delta,remaining in ((accepted,direct_scope,0,26),(amended,direct_scope|proposed_scope,supplement,12)):
        require("whole35-symbols-preserved:" + b["status"], len(original["symbols"]) == 35 and canonical(b["original_35_symbols"]) == canonical(original["symbols"]))
        require("exact-removed-obligations:" + b["status"], set(b["explicit_obligation_resolutions"]) == scope)
        require("unchanged-P0:" + b["status"], canonical(b["P0"]) == canonical(original["P0"]))
        require("all-six-phase-order:" + b["status"], tuple(b["child"]) == tuple(original["child"]) == ("P1_setup","P1_loader","P2_arguments","P3_before_store","P4_selected_route","P5_payload_teardown"))
        for phase_name, item in b["child"].items():
            prior = original["child"][phase_name]
            require("phase-delta-no-omission:" + phase_name, item == {"fixed": prior["fixed"] + (delta if phase_name == "P4_selected_route" else 0),"terms":{k:n for k,n in prior["terms"].items() if k not in scope}})
        expected = {"fixed":895084428322997895+delta,"terms":{k:n for k,n in original["whole_host"]["terms"].items() if k not in scope}}
        require("whole-composition:" + b["status"], sum_linear([b["P0"],*b["child"].values()]) == b["whole_host"] == expected)
        require("remaining-inputs:" + b["status"], set(b["remaining_symbols"]) == set(expected["terms"]) and len(b["remaining_symbols"]) == remaining)
        for key in ("accepted_bound","root_policy_selected","operational_grant","native_or_GA","proposed_fourteen_root_selected"):
            require("no-authority:" + b["status"] + ":" + key, b[key] is False)
        require("exact-unit-source:" + b["status"], b["unit"] == original["unit"] == proposal["unit"] and b["source_tree_sha256"] == SOURCE and b["host_tree_sha256"] == HOST)
    require("conditional-fixed-release", amended["whole_host"]["fixed"] == release["candidate_fixed_work"] == 895084428323053276)
    require("all-components-prepaid-before-setup", acceptance["all_components_prepaid_before_setup"] is True)
    tests = candidate("test-results.json")
    require("claimed18and474", tests["test_methods"] == 18 and tests["adverse_cases"] == len(tests["adverse_case_names"]) == 474 and tests["errors"] == tests["failures"] == 0 and tests["passed"] is True)
    history = candidate("attempt-history.json")
    require("two-producer-failures-retained", history["failures_preserved"] == 2 and len([a for a in history["attempts"] if a["returncode"]]) == 2)
    in_lane_review = candidate("independent-review.json")
    require("claimed1140-arithmetic-assertions", in_lane_review["assertions"] == 1140 and in_lane_review["input_files_rehashed"] == 320)
    result = {"schema":1,"status":"independent-offline-source-interface-review-pass-root-selection-required",
        "candidate":{"path":C,"seal_sha256":SEAL_SHA,"members":103,"bytes":937922,"release_sha256":RELEASE_SHA},
        "source_tree_sha256":SOURCE,"host_tree_sha256":HOST,
        "assertions":len(checks),"candidate_custody_inputs":len(custody),"candidate_custody_plus_root_release":len(set(custody)|{RELEASE}),"distinct_external_files_rehashed":len(files),
        "accepted_nine":9,"proposed_callee_core_clarifications":12,"proposed_whole_leaf_clarifications":2,"original_symbols":35,"accepted_only_unresolved":26,"candidate_unresolved":12,
        "requested_backing_bytes":backing,"constructor_supplement":supplement,"conditional_fixed":amended["whole_host"]["fixed"],"candidate_expression":amended["whole_host"],
        "active_graph_nodes":len(active),"callee_exports":21,"authored_callback_sites":len(callback_sites),"resource_rows":33,"typed_payload_imports":19,
        "producer_claims_reproduced_by_separate_command":{"test_methods":18,"adverse_cases":474,"in_lane_arithmetic_assertions":1140,"in_lane_custody_inputs":320},
        "no_blocking_findings":True,"root_selected_fourteen":False,"accepted_bound":False,"actual_root_policy_or_grant":False,"operational_grant":False,"native_or_GA":False,
        "limits":["Recommendation concerns only fourteen exact source146 logical-interface boundary clarifications; root owns amendment selection.","Existing resource rows and qualified native surfaces retain prior root acceptance and conditional compiled-standard-library correspondence; no new compiled/executable/session proof is supplied.","The atomic callback is charged once in the inherited logical interface; dynamic atomic retries and private allocator/library/compiler/kernel/panic/CPU work are outside its unit, not proven physically bounded.","The 55381 supplement is cumulative requested allocation work, not physical allocation, allocator overhead, RSS, time, or storage/lifetime credit. Allocation failure retains the prior conditional source-ceiling convention.","L_str and its incoming/forwarded provenance, five actual native-open requests and native error request, actual P0 root/caller/fixture/backing and finite I/U remain unselected external inputs. No defaults are chosen.","All six components must be prepaid before setup. Conservative before/store frame envelopes retain shared exits and returns; they are not chronological meters.","The concrete SnapshotAdoptionV1 policy has positive fixed work. The phase union excludes exactly the generic ordinary-zero-policy bb20 unit-assignment/jump; it retains all selected-policy operations and double-charges shared bb3/bb69. Ordinary adoption is outside this clarification.","The concrete before-store frame retains every authored operation and primitive. Its prior accepted normalization removes the generic Copy Result destructor adapter, without removing source/native role occurrences or any owned resource frontier.","Whole-host source integration, root policy, storage/lifetime composition, immutable fixture/build/compiler/session/executable binding, genuine loader/writer/healthy cleanup, FieldLog, OTA and GA remain separate pending gates.","No compiler or product/fixture/loader/writer/destructor runtime ran. Native simulator/emulator/device, UI automation and capture remain paused. No inventory, Git, root-metadata, source, or frozen-reference write occurred."],
        "count_disposition":"320 is the candidate input-custody roster. Adding the separately pinned root release makes 321; candidate's own sealed members are a further separately verified input set."}
    outputs = {"review.json":result,"coverage.json":{"exports":coverage,"allocation_rows":allocation_rows,"callback_sites":[list(x) for x in callback_sites]},"input-custody.json":{"schema":1,"files":dict(sorted(files.items()))},"assertions.json":{"checks":checks}}
    for name,value in outputs.items():
        data = (json.dumps(value,indent=2,sort_keys=True)+"\n").encode()
        if "--check" in sys.argv:
            require("unchanged-review-output:" + name, (D/name).read_bytes() == data)
        else:
            if (D/"seal.json").exists(): raise AssertionError("frozen-independent-review")
            (D/name).write_bytes(data)
    print(json.dumps({k:result[k] for k in ("status","assertions","candidate_custody_inputs","distinct_external_files_rehashed","constructor_supplement","conditional_fixed","operational_grant")}))

if __name__ == "__main__":
    main()
