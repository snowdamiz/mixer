#!/usr/bin/env python3
"""Source-only interface clarification. Reads released frozen data, never runs it."""
from __future__ import annotations
import collections
import gzip
import hashlib
import json
import sys
from pathlib import Path

D = Path(__file__).resolve().parent
R = D.parents[1]
V = R / "verification"
SOURCE = "690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185"
HOST = "027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2"
PRODUCER = "verification/swift-guarded-snapshot-whole-host-work-composition"
INDEPENDENT = "verification/swift-guarded-snapshot-whole-host-work-independent"
WHOLE_SEAL = "95c1a3087b36996dc06e8411f97e3ebce2610120f9ac742326824a52ab9c63ca"
INDEPENDENT_SEAL = "7d18cb048499cac2cb62bec2b4a954d1d032b1fbd950cb6f6941d181debc024b"
ACCEPT = "verification/swift-semantic-adapter-root-review/guarded-snapshot-whole-host-work-host-acceptance.json"
ACCEPT_SHA = "d797f7c9a86259fdb40700c290e5f83488142117a355f7b5826c1d92710a784f"
DIRECT = "verification/swift-semantic-adapter-root-review/guarded-snapshot-direct-adapter-contract-amendment.json"
DIRECT_SHA = "af33b1faed65d1de6764520f7f6a3eb08a2877b2612b5d8c4fdee36ea55dfcff"
LEAF = ("private_std_compiler_lowering_and_requested_backing_allowance",
        "retained_dynamic_resource_backing_and_native_transfer_allowance")
OUTSIDE = ["private standard-library and panic/unwind implementation",
           "compiler lowering and physical copies", "allocator/kernel implementation and physical overhead",
           "private retries and retry-driven reevaluation of a closed pure callback",
           "CPU instructions, time, stack and RSS"]

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

class Refused(ValueError):
    pass

class Reader:
    def __init__(self):
        self.files = {}
        self.checks = []

    def check(self, name, value):
        if not value:
            raise Refused(name)
        self.checks.append(name)

    def raw(self, path, expected=None):
        p = Path(path)
        self.check("relative-input:" + str(p), not p.is_absolute() and ".." not in p.parts)
        raw = (R / p).read_bytes()
        actual = {"bytes": len(raw), "sha256": digest(raw)}
        if expected is not None:
            self.check("input-binding:" + str(p), actual == expected)
        self.files[str(p)] = actual
        return raw

    def pinned(self, path, sha):
        raw = self.raw(path)
        self.check("pin:" + str(path), digest(raw) == sha)
        return json.loads(raw)

    def packet(self, path, sha, count):
        seal = self.pinned(path + "/seal.json", sha)
        self.check("packet-count:" + path, len(seal["members"]) == count)
        members = {}
        for m in seal["members"]:
            self.check("unique-member:" + path + "/" + m["path"], m["path"] not in members)
            members[m["path"]] = {k: m[k] for k in ("bytes", "sha256")}
            self.raw(path + "/" + m["path"], members[m["path"]])
        return members

def resource_price(row, cuts):
    price = row["structural_occurrence_allowance"] * (1 + row["inline_bytes"])
    for name, count in row["resource_frontiers"].items():
        c = cuts[name]
        part = c["interface_work"] + c["native_resource_backing"]
        dynamic = row.get("dynamic_resource_elements", {}).get(name)
        if dynamic:
            part += c["max_live_elements"] * resource_price(dynamic, c["element_cuts"])
        price += count * part
    return price

def build():
    r = Reader()
    r.packet(PRODUCER, WHOLE_SEAL, 50)
    r.packet(INDEPENDENT, INDEPENDENT_SEAL, 99)
    accept = r.pinned(ACCEPT, ACCEPT_SHA)
    direct = r.pinned(DIRECT, DIRECT_SHA)
    custody = json.loads(r.raw(PRODUCER + "/input-custody.json"))["files"]

    def frozen(rel):
        r.check("released-input:" + rel, rel in custody)
        return json.loads(r.raw(rel, custody[rel]))

    whole = json.loads(r.raw(PRODUCER + "/work-interface.json"))
    original_roster = json.loads(r.raw(PRODUCER + "/private-export-allowance-roster.json"))
    typed = json.loads(r.raw(PRODUCER + "/typed-callee-imports.json"))
    graph = frozen("verification/swift-guarded-snapshot-leaf-callee-cost/callee-ledger.json")
    bound = frozen("verification/swift-guarded-snapshot-leaf-callee-cost-independent/bound-cost-interface.json")
    shell = frozen("verification/swift-guarded-snapshot-leaf-shell-cost/operation-ledger.json")
    contract = frozen("verification/swift-guarded-snapshot-resource-cost/contract.json")
    cuts = frozen("verification/swift-guarded-snapshot-resource-cost/resource-cuts.json")
    rows = frozen("verification/swift-guarded-snapshot-resource-cost/rows.json")
    internal = frozen("verification/swift-guarded-snapshot-resource-cost/internal-rows.json")
    manifest = frozen("verification/swift-guarded-snapshot-host-composition/source-manifest.json")
    host = frozen("verification/swift-guarded-snapshot-host-composition/host-support-manifest.json")
    r.check("source146-manifest", len(manifest["members"]) == 146 and digest(canonical(manifest["members"])) == SOURCE)
    r.check("host11-manifest", len(host["members"]) == 11 and digest(canonical(host["members"])) == HOST)
    source = {}
    source_records = {}
    for m in manifest["members"]:
        p = "verification/swift-guarded-snapshot-host-composition/overlay/vm/" + m["path"]
        if p not in custody:
            p = "verification/swift-guarded-snapshot-funding-implementation/source/vm/" + m["path"]
        expected = {k: m[k] for k in ("bytes", "sha256")}
        source[m["path"]] = r.raw(p, expected).decode()
        source_records[m["path"]] = {"path": p, **expected}
    for m in host["members"]:
        r.raw("verification/swift-real-profile-loader-binding/host/" + m["path"],
              {k: m[k] for k in ("bytes", "sha256")})
    r.check("accept-exact-source", accept["source"]["tree_sha256"] == SOURCE and accept["source"]["host_tree_sha256"] == HOST)
    r.check("direct-exact-source", direct["source_tree_sha256"] == SOURCE and direct["host_tree_sha256"] == HOST)
    r.check("whole-unit", whole["unit"] == "abstract logical source/typed aggregate/destructor interface occurrences plus requested native-byte allowances; excludes CPU/private implementations/physical allocation/stack/RSS/time")
    r.check("whole-scope", len(whole["symbols"]) == 35 and whole["whole_host"]["fixed"] == 895084428322997895)
    r.check("no-grant", not whole["operational_grant"] and whole["product451814442_aggregate_credit"] == 0)
    r.check("native-closed", bound["remaining_native_terms"] == 0 and all(not x["native"] for x in bound["exports"].values()))
    direct_symbols = [x["symbol"] for x in direct["exact_export_scope"]]
    r.check("nine-exact-direct", len(direct_symbols) == len(set(direct_symbols)) == 9)
    r.check("direct-roster", direct_symbols == [x["symbol"] for x in original_roster["exports"][:9]])
    r.check("all21-exports", set(graph["exports"]) == set(bound["exports"]) == {x["export"] for x in original_roster["exports"]})

    # Named row reuse is exact source146 body reuse, not aggregate credit.
    for n, row in graph["nodes"].items():
        b = row.get("binding")
        if b:
            r.check("body-hash:" + n, digest(b["source"].encode()) == b["sha256"])
            r.check("body-source146:" + n, b["source"] in source[b["path"]])
        if "parts" in row:
            r.check("own-parts:" + n, sum(row["parts"].values()) == row["own"])
    for n, b in graph["source_bindings"].items():
        r.check("authored-body-hash:" + n, digest(b["source"].encode()) == b["sha256"])
        r.check("authored-body-source146:" + n, b["source"] in source[b["path"]])
    for b in graph["constructor_applicability"]["source_rebindings"]:
        if "function" not in b:
            raw = source[b["path"]].encode()
            r.check("constructor-whole-file:" + b["path"], len(raw) == b["bytes"] and digest(raw) == b["sha256"])
    r.check("constructor-pending", not graph["constructor_applicability"]["writer_encoder_initializer_entered"] and not graph["constructor_applicability"]["changed_snapshot_commit_storage_entered"])
    r.check("constructor-price", sum(graph["constructor_applicability"]["terms"].values()) == graph["nodes"]["accepted_constructor_region"]["own"] == 451718715)

    prices = {x["type"].replace(" ", ""): resource_price(x, cuts) for x in rows + internal["rows"]}
    decoded = json.loads(r.raw(PRODUCER + "/additive-decoded-function-row.json"))
    r.check("decoded-row", decoded["price"] == 231526438)
    prices["DecodedFunction"] = decoded["price"]
    for key, value in typed["typed_imports"].items():
        r.check("typed-import:" + key, prices[key[9:].replace(" ", "")] == value)
    for e, row in bound["exports"].items():
        fixed = row["fixed"] + sum(count * typed["typed_imports"][t] for t, count in row["payload"].items())
        terms = {row["required_private_primitive_cut"]: 1}
        for name, count in row["unsized"].items():
            if name == "str": terms["L_str"] = 2 * count
            elif name == "[Option<ReservationTicket>]":
                r.check("exact-array-only", e == "callee::accounted::AccountedWasi::snapshot_pair_v1" and count == 8)
                fixed += 2 * count * 112
            else: raise Refused("uncovered-unsized:" + name)
        r.check("typed-export:" + e, typed["exports"][e] == {"fixed": fixed, "terms": terms})

    # Independently walk every exact export; never import a producer's Python.
    active = set()
    def walk(node, stack=()):
        r.check("acyclic:" + node, node not in stack)
        r.check("known-node:" + node, node in graph["nodes"])
        active.add(node)
        row = graph["nodes"][node]
        visits = collections.Counter({node: 1})
        primitive = collections.Counter(row.get("primitive", {}))
        payload = collections.Counter(row.get("payload", {}))
        for child, count in row["calls"].items():
            r.check("positive-call:" + node + ":" + child, type(count) is int and count > 0)
            vs, ps, ds = walk(child, stack + (node,))
            for target, values in ((visits, vs), (primitive, ps), (payload, ds)):
                for key, value in values.items(): target[key] += value * count
        return visits, primitive, payload

    exports = []
    callbacks = []
    for old in original_roster["exports"]:
        e, node = old["export"], old["node"]
        vs, prim, payload = walk(node)
        r.check("primitive-roster:" + e, dict(prim) == old["primitive_callsite_occurrences"])
        r.check("payload-roster:" + e, dict(payload) == bound["exports"][e]["payload"])
        named = collections.Counter()
        for x in old["accepted_named_source_rows"]: named[x["node"]] += x["count"]
        expected = {k: n for k, n in vs.items() if graph["nodes"][k]["kind"].startswith("accepted-")}
        r.check("named-row-roster:" + e, dict(named) == expected)
        cb = {k: n for k, n in vs.items() if k.startswith("closure::")}
        exports.append({"export": e, "symbol": old["symbol"], "node": node,
            "status": "root-selected-nine-direct-clarification" if old["symbol"] in direct_symbols else "proposed-remaining-interface-clarification",
            "callsite_coefficient": whole["whole_host"]["terms"][old["symbol"]],
            "covered_expression": typed["exports"][e],
            "visited_node_multiplicities": dict(sorted(vs.items())),
            "authored_callback_multiplicities": dict(sorted(cb.items())),
            "primitive_event_multiplicities": dict(sorted(prim.items())),
            "accepted_named_row_multiplicities": dict(sorted(named.items())),
            "typed_payload_multiplicities": dict(sorted(payload.items())),
            "source_and_native_operand_rule": "All authored caller role occurrences retain the exact frozen source/native coefficients and qualified source146 layouts. Named accepted rows retain only their own parts and child counts.",
            "additional_request_rule": "Five fresh constructor allocation requests are supplied explicitly below; no allocation is inferred from a destructor price." if node == "construct_forward" else "No additional dynamic backing is created by this export. Its exact typed teardown frontiers are imported separately; a refund/drop event is not payload teardown.",
            "numeric_private_price_assigned": False})
    for n in sorted(active):
        row = graph["nodes"][n]
        for op in row.get("operations", []):
            prim = [x["target"] for x in op["edges"] if x["kind"] == "closed-primitive"]
            calls = [x["target"] for x in op["edges"] if x["kind"] == "call"]
            if prim and calls:
                callbacks.append({"caller": n, "block": op["block"], "line": op["line"],
                    "code": op["code"], "code_sha256": digest(op["code"].encode()),
                    "weight": op["weight"], "closed_primitive": prim, "authored_callbacks": calls})
    # This callback is closed and pure. One logical evaluation is not a dynamic retry CPU bound.
    atomic_cb = "closure::85c9f09d812588039367"
    cb = graph["nodes"][atomic_cb]
    r.check("atomic-callback-closed", cb["calls"] == {} and cb["payload"] == {} and cb["primitive"] == {"core::num::<impl u64>::checked_add": 1})
    r.check("atomic-callback-once", next(x for x in exports if x["node"] == "core_fixed_store_and_after")["authored_callback_multiplicities"][atomic_cb] == 1)

    # Native query observations are already released data. No compiler or runtime.
    archive_path = "verification/swift-guarded-snapshot-host-composition-independent/commands/exact146-metadata-mir/stdout.gz"
    raw = r.raw(archive_path, custody[archive_path])
    full = gzip.decompress(raw)
    r.check("native-data-raw", digest(full) == "6c924c8088173db78afb1f648b284df7d8d139b3389bd090a9552df4130cfe7a")
    lines = full.decode().splitlines()
    layout_queries = {
        "std::vec::Vec<experimental_swift_reactor::cache::SwiftSlot>": (24, 8),
        "std::vec::Vec<experimental::cache::PinRecord>": (24, 8),
        "std::vec::Vec<experimental::cache::decode::Patch>": (24, 8),
        "std::vec::Vec<std::option::Option<experimental_swift_reactor::cache::ScanPlan>>": (24, 8),
        "std::vec::Vec<u8>": (24, 8),
        "experimental_swift_reactor::cache::SwiftSlot": (136, 8),
        "experimental::cache::PinRecord": (16, 8),
        "experimental::cache::decode::Patch": (32, 8),
        "std::option::Option<experimental_swift_reactor::cache::ScanPlan>": (56, 8),
        "std::result::Result<(), std::collections::TryReserveError>": (16, 8),
    }
    layouts = []
    for ty, (size, alignment) in layout_queries.items():
        line = f"print-type-size type: `{ty}`: {size} bytes, alignment: {alignment} bytes"
        r.check("exact-native-layout:" + ty, lines.count(line) == 1)
        layouts.append({"type": ty, "size": size, "alignment": alignment, "line": line})

    cache_path = "src/experimental_swift_reactor/cache.rs"
    cache = source[cache_path]
    initial_path = "src/experimental_swift_reactor/cache/initial_profile_v1.rs"
    initial = source[initial_path]
    control = source["src/experimental_swift_reactor/control.rs"]
    # Explicit source facts; these are not authorization by syntax analysis.
    facts = [
        (cache_path, "reserve(&mut partial.slots, entries, &mut self.control)?;"),
        (cache_path, "reserve(&mut partial.pins, budget.active_pins, &mut self.control)?;"),
        (cache_path, "reserve(&mut partial.patches, PATCH_CAPACITY, &mut self.control)?;"),
        (cache_path, "reserve(&mut partial.index, RESIDENT_INDEX_BYTES, &mut self.control)?;"),
        (cache_path, "reserve(&mut partial.plans, PLAN_CAPACITY, &mut self.control)?;"),
        (cache_path, "values.try_reserve_exact(requested).map_err(|_| {"),
        (cache_path, "control.exact(requested, values.capacity())?;"),
        (cache_path, "const PATCH_CAPACITY: usize = 512;"),
        (cache_path, "const PLAN_CAPACITY: usize = 512;"),
        (cache_path, "const RESIDENT_INDEX_BYTES: usize = RESIDENT_INDEX_SLOTS * 3;"),
        (cache_path, "const RESIDENT_INDEX_SLOTS: usize = 64;"),
        (initial_path, "Err(AError::WorkAuditPending)"),
        ("src/experimental_swift_reactor/control.rs", "budget.cache_entries > 64"),
        ("src/experimental_swift_reactor/control.rs", "budget.active_pins > 64"),
    ]
    source_facts = []
    for path, text in facts:
        r.check("source-fact:" + text, text in source[path])
        start = source[path].index(text)
        source_facts.append({"path": path, "file_binding": source_records[path],
            "line": source[path][:start].count("\n") + 1, "text": text, "sha256": digest(text.encode())})
    allocations = []
    # A complete explicit source-level reserve interface, conservatively charged
    # again: reference+Vec header+count+Layout size/alignment+return+pointer.
    # B is cumulative requested backing, not allocator physical allocation.
    fields = {"receiver_reference": 8, "receiver_vec_header": 24, "requested_elements": 8,
              "layout_size": 8, "layout_alignment": 8, "result_unit_or_TryReserveError": 16,
              "returned_pointer": 8}
    for field, n, size, cap in [("slots", 64, 136, 8704), ("pins", 64, 16, 1024),
            ("patches", 512, 32, 16384), ("index", 192, 1, 192), ("plans", 512, 56, 28672)]:
        r.check("request-product:" + field, n * size == cap)
        allocations.append({"field": field, "max_calls": 1, "max_requested_elements": n,
            "element_size": size, "max_requested_bytes": cap,
            "logical_interface_events": 1, "native_fields": fields,
            "supplement": cap + 1 + sum(fields.values()),
            "rule": "Fresh empty Vec, one authored try_reserve_exact. Subsequent pushes fit the checked requested capacity; no cache execution or mutation is admitted. Private allocator retries/physical over-allocation remain outside this logical request unit."})
    supplement = sum(x["supplement"] for x in allocations)
    r.check("allocation-native-fields", sum(fields.values()) == 80)
    r.check("five-request-backing", sum(x["max_requested_bytes"] for x in allocations) == 54976)
    r.check("five-request-supplement", supplement == 55381)

    proposed_symbols = [x["symbol"] for x in exports if x["status"].startswith("proposed-")] + list(LEAF)
    r.check("fourteen-proposed", len(proposed_symbols) == len(set(proposed_symbols)) == 14)
    resolved = set(direct_symbols + proposed_symbols)
    r.check("twentythree-resolution", len(resolved) == 23 and resolved <= set(whole["symbols"]))
    remaining = {k: v for k, v in whole["whole_host"]["terms"].items() if k not in resolved}
    r.check("twelve-outside-lane", len(remaining) == 12 and not any(k.startswith("private_") or k.startswith("retained_dynamic_") for k in remaining))
    proposal = {"schema": 1, "status": "proposed-source146-fourteen-interface-amendment-for-root-review",
        "source_tree_sha256": SOURCE, "host_tree_sha256": HOST, "unit": whole["unit"],
        "producer_seal_sha256": WHOLE_SEAL, "independent_seal_sha256": INDEPENDENT_SEAL,
        "selected_nine_receipt_sha256": DIRECT_SHA,
        "exact_proposed_symbol_scope": proposed_symbols,
        "callee_boundary_rows": [x for x in exports if x["status"].startswith("proposed-")],
        "whole_leaf_boundary_rows": [
            {"symbol": LEAF[0], "resolution": "All eight source bodies/205 roles/598 written operations retain complete inline scalar/native and finite pointee occurrence surfaces. Exact authored primitive events and callback edges, all21 callee expressions and all33 typed payload/resource rows remain imported. Only private implementation/lowering/panic/retries/CPU remain outside the declared unit; no extra numeric private price is introduced.", "additional_price_assigned": False},
            {"symbol": LEAF[1], "resolution": "Incoming proof/source/metadata/Cancellation backing remains charged in the accepted setup/loader/entry/resource components. Every outgoing owned leaf/callee payload retains its complete typed destruction/resource-request price. The one new in-unit creation frontier is the five fresh cache Vec allocation requests, supplied once as the constructor supplement. Resource teardown is not reused as allocation work; no transfer/drop/alias credit is subtracted.", "additional_price_assigned": False}],
        "constructor_allocation_requests": allocations, "constructor_allocation_supplement": supplement,
        "resource_contract_sha256": custody["verification/swift-guarded-snapshot-resource-cost/contract.json"]["sha256"],
        "logical_atomic_callback": {"node": atomic_cb, "count": 1, "pure": True, "dynamic_retry_or_CPU_claim": False},
        "outside_unit": OUTSIDE, "no_numeric_zero_or_one_private_assignment": True,
        "frozen_35_symbol_interface_rewritten": False, "root_selected": False,
        "conditional_review_only": True, "accepted_bound": False, "operational_grant": False,
        "product451814442_aggregate_credit": 0, "native_runtime_or_GA": False}
    report = {"schema": 1, "status": "source-backed-candidate-fourteen-clarifications-with-explicit-allocation-supplement",
        "source_tree_sha256": SOURCE, "host_tree_sha256": HOST,
        "accepted_nine_symbols": direct_symbols, "proposed_fourteen_symbols": proposed_symbols,
        "accepted_only_remaining_symbols": 26, "candidate_remaining_symbols": len(remaining),
        "candidate_expression": {"fixed": whole["whole_host"]["fixed"] + supplement, "terms": remaining},
        "original_constant_retained": whole["whole_host"]["fixed"], "added_request_supplement": supplement,
        "frozen_symbol_count": 35, "callee_exports": len(exports), "active_graph_nodes": len(active),
        "callback_sites": len(callbacks), "typed_payload_imports": len(typed["typed_imports"]),
        "native_request_backing_bytes": 54976, "request_native_field_bytes_per_call": 80,
        "source_facts": len(source_facts), "checks": len(r.checks),
        "selected_bound": False, "complete_root_policy_or_funding": False,
        "remaining": ["L_str and all incoming/forwarded provenance", "five actual path/native-open requests and original error request", "actual P0 root/caller/fixture/backing with finite I/U", "exact compiled-standard-library/executable/session correspondence", "whole-host storage/lifetime integration and policy selection", "genuine loader/writer/healthy cleanup and final native/FieldLog/OTA/GA qualification"],
        "activity": "Python source/offline derivation only; no compiler/runtime/native/UI/capture/global inventory/Git or frozen writes"}
    outputs = {"amendment-proposal.json": proposal,
        "interface-roster.json": {"schema": 1, "source_tree_sha256": SOURCE, "exports": exports,
            "authored_callback_sites": callbacks, "source_facts": source_facts, "native_layout_observations": layouts,
            "incoming_resource_frontiers": sorted(cuts), "accepted_resource_contract": contract["binding"]},
        "composition-report.json": report,
        "input-custody.json": {"schema": 1, "files": dict(sorted(r.files.items()))}}
    return outputs, whole, direct, r.checks

def main():
    outputs, _, _, checks = build()
    for name, value in outputs.items():
        raw = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
        if "--check" in sys.argv:
            if (D / name).read_bytes() != raw: raise Refused("changed-output:" + name)
        else:
            if (D / "seal.json").exists(): raise Refused("frozen-packet")
            (D / name).write_bytes(raw)
    print(json.dumps({"status": "pass", "checks": len(checks), "proposed": 14,
                      "accepted": 9, "allocation_supplement": 55381, "operational_grant": False}))

if __name__ == "__main__": main()
