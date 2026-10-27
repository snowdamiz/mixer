#!/usr/bin/env python3
"""Independent source-work arithmetic and finite geometry controls; no VM runs."""
from pathlib import Path
import datetime
import hashlib
import json
import platform
import struct
import subprocess
import sys

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
REPO = OUT.parent.parent
ENC = OUT.parent / "swift-guarded-snapshot-encoder-implementation"
T, H = 4096, 2560
WIDTHS = (0, 3, 1, 5, 3, 4, 4, 4, 4)
CAPS = (67108864, 512, 8192, 34, 79966, 8192, 4096, 4096, 4096)
EXPECTED_SEAL = "eadbe533d23459573ead21c7a9bac54ae929b98cdbc76dd47aebe34b5ceb2b1f"
EXPECTED_TREE = "447719d8fef2928674d9d196266408ca72c70ce152cf0251807d2c3bcd7e7c43"
DIRECTION = "verification/swift-semantic-adapter-root-review/guarded-snapshot-composition-interface-direction.json"
EXPECTED_DIRECTION = "87c5e62198270a04266cd897f141bef254ad6b3593a9e952e86bc08c79e5e51d"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def inputs():
    assert sha((ENC / "seal.json").read_bytes()) == EXPECTED_SEAL
    seal = json.loads((ENC / "seal.json").read_text())
    assert seal["member_count"] == len(seal["members"]) == 1256
    for member in seal["members"]:
        path = ENC / member["path"]
        raw = path.read_bytes()
        assert len(raw) == member["bytes"] and sha(raw) == member["sha256"], str(path)
    source = json.loads((ENC / "final-source-manifest.json").read_text())
    assert source["member_count"] == len(source["members"]) == 144
    assert source["tree_sha256"] == EXPECTED_TREE
    canonical = json.dumps(source["members"], sort_keys=True, separators=(",", ":")).encode()
    assert sha(canonical) == EXPECTED_TREE
    host = (ENC / "host/encoder.rs").read_bytes()
    body = (ENC / "source/vm/src/experimental/swift.rs").read_bytes()
    assert host in body
    assert body[:body.index(host)].count(b"\n") + 1 == 732
    assert sha((REPO / DIRECTION).read_bytes()) == EXPECTED_DIRECTION
    paths = [
        ENC / "seal.json", ENC / "final-source-manifest.json", ENC / "source-delta.json",
        ENC / "host/encoder.rs", ENC / "host/loops.md", ENC / "host/source-places.json",
        REPO / DIRECTION,
        OUT.parent / "swift-guarded-snapshot-export-admission-design/design.md",
    ]
    for member in source["members"]:
        if member["path"] in (
            "src/experimental/account.rs", "src/experimental/swift.rs",
            "src/experimental_swift_reactor/control.rs", "src/experimental_swift_reactor/cache.rs",
            "src/experimental_swift_reactor/cache/initial_profile_v1.rs",
            "src/experimental_swift_reactor/retained_profile_loader_v1.rs",
            "src/experimental_wasi/accounted.rs", "src/experimental_wasi/mod.rs",
        ):
            paths.append(ENC / "source/vm" / member["path"])
    return {
        "encoder_seal": EXPECTED_SEAL, "source_tree": EXPECTED_TREE,
        "source_members_verified": 144, "encoder_packet_members_verified": 1256,
        "host_body_exactly_inline_at_swift_line": 732,
        "reads": [{"path": str(p.relative_to(REPO)), "bytes": p.stat().st_size,
                   "sha256": sha(p.read_bytes())} for p in paths],
    }


def ledger():
    # Expressions below are manual source decomposition under cost-convention.md,
    # not an AST/regex counter or dynamic proof of the implementation.
    get, put, require, word, span, entry = 9, 14, 12, 7, 24, 20
    words = lambda n: 4 + 20*n
    identity = 2 + 64 + 1 + (8 + 4 + 8) + (2 + 8*(3 + 3 + 1 + 1 + 1 + 8))
    assert identity == 225
    provenance_parts = {
        "entry_return": 2, "clear": 576, "magic": 1+1+8,
        "limits_binding": 2,
        "values_binding_fields_conversions_slots": 1+8+3*(1+1+1+3+2)+3,
        "eight_scalar_loop": 2+8*(3+4+1+1+1+1+8),
        "digest_array_and_six_copies": 12+2+6*(3+4+1+1+1+32),
        "identities_place_and_four_encodes": 1+2+4*(3+4+1+16+identity+1+64),
        "ok": 1,
    }
    provenance = sum(provenance_parts.values())
    assert provenance == 2306
    runtime_parts = {
        "entry_return": 2, "clear": 512, "magic": 10,
        "original_budget_getter_copy_and_binding": 38, "scalar_reference": 2,
        "optional_actual_wasi_getter_chain": 36, "closure_binding": 1,
        "seventeen_limits_slots_fields_conversions": 135,
        "four_envelope_words_array_loop": 85,
        "seventeen_run_words_loop": 325, "wasi_option_pattern": 4,
        "twelve_wasi_words_array_loop": 262, "eight_guard_scalar_words_array_loop": 170,
        "ok": 1,
    }
    runtime = sum(runtime_parts.values())
    assert runtime == 1583
    runtime_validation_parts = {
        "entry_return": 2, "run_caps_array_binding": 18,
        "seventeen_run_cap_checks": 2+17*(3+2+get+1+1+require+2),
        "wasi_caps_array_binding": 8,
        "seven_wasi_cap_checks": 2+7*(3+2+get+1+1+require+2),
        "presence_get_binding": get+1,
        "presence_and_owner_check": 1+get+1+1+require+2,
        "five_grant_checks": 2+5*(2+2+get+1+require+2),
        "absent_branch": 2,
        "twelve_absent_words_checks": 2+12*(2+2+get+1+require+2),
        "final_eleven_equations_including_fifteen_gets": 15*get+17+10+require,
    }
    runtime_validation = sum(runtime_validation_parts.values())
    assert runtime_validation == 1444
    directory_parts = {
        "two_accumulators_and_loop_setup": 4, "nine_range_steps": 18,
        "source_inventory_plus_eight_metadata_inventories": 32+8*82,
        "nine_inventory_result_and_tuple_patterns": 9*8,
        "nine_capacity_native_category_checks": 9*29,
        "nine_bytes_branch_upper_bounds": 9*11,
        "nine_charge_checks": 9*17, "nine_source_or_metadata_branches": 9*2,
        "source_equation": 19,
        "eight_charge_updates_observation_arrays_duplicate_checks": 8*(7+11+2+get+1+require+2),
        "nine_directory_arrays_and_words": 9*(8+1+words(8)+2),
        "nine_extent_updates": 9*7,
    }
    directories = sum(directory_parts.values())
    assert directories == 3322
    # name, immutable host encoder lines, decomposed value
    init = [
        ("borrow_snapshot and transitive proof/provenance getters", "149-160", 2+11+6+12+4),
        ("into_cursor entry/return", "162-402", 2),
        ("layout checks including refusal carriers", "163-170", 17),
        ("policy match including refusal carriers", "171-174", 4),
        ("header zeroing, binding, magic", "175-176", H+1+10),
        ("proof metadata bindings, usage/observations copies", "177-180", 4+21+41),
        ("source conversion and binding", "181", 1+1+word+2+1),
        ("eleven scalar header words", "182-198", 11+10+words(11)),
        ("provenance bridge, region conversion and error propagation", "199-205", provenance+10),
        ("five validation word copies", "206-209", 2+5*(2+2+get+1+2+put)),
        ("duplicate source equations", "210", 2*get+2+1+require+2),
        ("ten usage words", "211-226", 70+3+10+words(10)),
        ("two observation Options", "227-228", 2*(1+6+1)),
        ("twenty observations words", "229-254", 130+10+20+words(20)),
        ("memory and table presence errors", "255-256", 2*(1+2+8+2+1)),
        ("two declaration Options", "257-258", 2*(1+6+1)),
        ("thirteen metadata words", "259-277", 8+4+30+13+words(13)),
        ("runtime bridge and call boundary", "278-284", runtime+10),
        ("usage/source/deadline equation", "285-293", 4+4+(get+1)+(1+get+1)+3+require+2),
        ("validation caps array and five checks", "294-297", 6+2+5*(3+2+get+1+1+require+2)),
        ("nine shape equations", "298-313", 2+2+3+5+3+2+2+2+2+8+require+2),
        ("thirteen declaration equations", "314-331", 3+3+3+6+4+4+3+2+3+2+4+4+12+require+2),
        ("nine inventories, directories, checked extents", "332-384", directories),
        ("final charge and extent equations", "385-390", 10+1+(get+1)+1+2+require+2),
        ("34 resolved enum encodings", "391-393", 3+34*(3+1+3+2+put)),
        ("runtime validation and two count conversions", "394", runtime_validation+22),
        ("extent word patch", "395", put),
        ("cursor four slots and Result", "396-401", 5),
    ]
    fixed = sum(row[2] for row in init)
    assert fixed == 14224, fixed
    common = 2+2+3+4+1+1+(3+3+2+8)
    assert common == 29
    record_arms = {
        "signature": common+20+4+1+1+4+1+require+2+16,
        "parameter": common+20+1+3+5,
        "import": common+entry+2*(1+span+2)+21+15,
        "function": common+entry+(1+span+2)+21+11,
        "global": common+entry+(1+span+2)+15,
        "export": common+entry+(1+span+2)+16+13,
        "data_or_element": common+entry+2+(1+span+2)+13,
        "unknown_section": 2+2+3+4+1+8+1,
    }
    assert record_arms == {"signature":90,"parameter":58,"import":139,"function":108,
                           "global":91,"export":105,"data_or_element":91,"unknown_section":21}
    probe = 2 + 2*(3+get+1) + 5 + 6
    common_iteration = 5+3+2+2+15+2+2
    branch = {"header":5+8+6, "source":12+8+6+5,
              "metadata_without_record":3+9+4+3+2+2+4+5+5}
    assert probe == 39 and common_iteration == 31 and max(branch.values()) == 37
    # The final while condition may evaluate its complete five-action boolean
    # expression on a partial last block; two generic for-loop setup actions
    # cannot substitute for that final condition.
    block_fixed = 2+4+2+4+5+9
    assert block_fixed == 26
    return {
        "schema":1, "convention":"cost-convention.md",
        "source_reference_base":"../swift-guarded-snapshot-encoder-implementation/host/encoder.rs",
        "helpers":{"get":get,"put":put,"require":require,"word":word,"span":span,
                   "entry_macro_with_binding":entry,"words":"4+20n",
                   "identity_encode":identity,"provenance":provenance,"runtime":runtime,
                   "runtime_validation":runtime_validation},
        "transitive_sources": {
            "Buffer_len_get_inventory":"source/vm/src/experimental/account.rs:232-240,329-332",
            "guard_getters_runtime":"source/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs:249-267",
            "cache_proof":"source/vm/src/experimental_swift_reactor/cache.rs:1497-1499",
            "adopted_getters":"source/vm/src/experimental_swift_reactor/control.rs:350-356",
            "original_budget":"source/vm/src/experimental_swift_reactor/control.rs:822-824",
            "body_getters":"source/vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs:150-153",
            "identity_encode":"source/vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs:204-222",
            "provenance":"source/vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs:1388-1402",
            "wasi_configuration":"source/vm/src/experimental_wasi/accounted.rs:432;src/experimental_wasi/mod.rs:638",
        },
        "provenance_parts":provenance_parts,"runtime_parts":runtime_parts,
        "runtime_validation_parts":runtime_validation_parts,"directory_parts":directory_parts,
        "fixed_initialization":[{"name":n,"lines":l,"credits":v} for n,l,v in init],
        "fixed_total":fixed,"record_common":common,"record_branches":record_arms,
        "next_block":{"fixed":block_fixed,"iteration_common":common_iteration,
                      "branch_without_record_or_bytes":branch,"iteration_coefficient":68,
                      "directory_probe":probe,"record_visit":max(record_arms.values()),"copied_byte":1,
                      "lines":{"fixed":"584-589,636-641","common":"592-612",
                               "probe":"602-609","header":"593-599","source":"613-623",
                               "metadata":"624-634","record":"423-527"}},
    }


def shape(source, counts):
    assert len(counts) == 8 and source >= 0 and all(n >= 0 for n in counts)
    cursor = H+source
    sections = []
    for sid, n in enumerate(counts, 1):
        end = cursor + 8*WIDTHS[sid]*n
        sections.append((sid, cursor, end))
        cursor = end
    return sections, cursor


def closed(source, counts):
    sections, extent = shape(source, counts)
    chunks = ((H+source-1)//T - H//T + 1) if source else 0
    visits = []
    splits = []
    for sid, start, end in sections:
        # No floating point or E+T-1 ceiling arithmetic.
        internal = max(0, (end-1)//T - start//T) if end > start else 0
        split = internal if start % 8 else 0
        splits.append(split)
        visits.append((end-start)//8 + split)
    words = sum(visits)
    blocks = extent//T + (extent % T != 0)
    return {"E":extent,"B":blocks,"L":sum(WIDTHS[i+1]*n for i,n in enumerate(counts)),
            "N":sum(counts),"C":chunks,"W_sid":visits,"K_sid":splits,
            "W":words,"I":1+chunks+words,
            "D":chunks+sum((sid+2)*v for sid,v in enumerate(visits)),"Q":extent}


def reference(source, counts):
    # Interval-emitting reference for encoder.rs 592-634. No source bytes, VM,
    # proof, budget, RuntimeControl, guard or writer is constructed or executed.
    sections, extent = shape(source, counts)
    ranges = [(0, H, H+source)] + sections
    at, blocks, total = 0, [], {"I":0,"D":0,"W":0,"Q":0,"C":0,"H_chunks":0}
    by_sid = [0]*8
    while at < extent:
        used = 0
        b = {"I":0,"D":0,"W":0,"Q":0}
        while used < T and at < extent:
            b["I"] += 1
            if at < H:
                n = min(H-at, T-used)
                total["H_chunks"] += 1
            else:
                for sid, start, end in ranges:
                    b["D"] += 1
                    if start <= at < end:
                        break
                else:
                    raise AssertionError("directory not found")
                if sid == 0:
                    n = min(end-at, T-used)
                    total["C"] += 1
                else:
                    skip = (at-start) % 8
                    n = min(8-skip, T-used)
                    b["W"] += 1
                    by_sid[sid-1] += 1
            assert n > 0
            used += n
            at += n
            b["Q"] += n
        assert b["I"] <= 515 and b["W"] <= 513 and b["D"] <= 9*b["I"] and b["Q"] <= T
        blocks.append(b)
        for k in ("I","D","W","Q"):
            total[k] += b[k]
    total["B"], total["W_sid"] = len(blocks), by_sid
    expected = closed(source, counts)
    for k in ("I","D","W","Q","C","B","W_sid"):
        assert total[k] == expected[k], (source, counts, k, total[k], expected[k])
    assert total["H_chunks"] == 1
    assert sum(expected["K_sid"]) <= expected["B"]-1
    return expected, blocks


def encoder_cost(c):
    return 14224 + 26*(c["B"]+1) + 68*c["I"] + 39*c["D"] + 139*c["W"] + c["Q"]


def compare_old(c):
    attempts = 32*c["B"]
    original_r = 32768 + 36*c["E"] + 4096*c["B"] + 64*c["N"] + 16*c["L"] + 32*attempts + 8*c["B"]
    return {"old_P":16384,"old_R":original_r,"old_P_plus_R":16384+original_r,
            "encoder_only_bound":encoder_cost(c),
            "total_inequality_proven":False,
            "reason":"No writer/control implementation cost is inferred; term rationale differs from actual loops."}


def record_reference(sid, record, within=0):
    """Counted branch/reference model, never an actual Rust component call."""
    trace = [("entry_metadata_source_span_match", 12)]

    def charge(name, credits):
        trace.append((name, credits))

    def finish(error):
        total = sum(c for _,c in trace)
        assert total <= 139, (sid, trace)
        return error, total, trace

    if sid not in range(1,9):
        charge("unknown_section_field_error", 9)
        return finish(20)
    charge("entry_lookup_including_possible_field_error", 20)
    if record is None:
        return finish(16)
    if sid == 1:
        charge("signature_parameter_range", 25)
        first, count = record["parameters"]
        if first+count > 2:
            return finish(17)
        charge("signature_array", 16)
    elif sid == 2:
        charge("parameter_array_and_type_match", 9)
    else:
        if sid in (7,8):
            charge("data_element_branch", 2)
        for offset, length in record["spans"]:
            charge("span_argument_check_propagation", 27)
            if offset+length > 8:
                return finish(15)
        if sid in (3,4):
            charge("type_index_check", 21)
            if record["type_index"] >= 2:
                return finish(18)
        if sid == 6:
            charge("export_kind_check", 16)
            if record["kind"] > 3:
                return finish(19)
        charge("arm_array", {3:15,4:11,5:15,6:13,7:13,8:13}[sid])
    charge("output_binding_and_get_copied_field_error", 17)
    return finish(None if within < 5 else 21)


def controls(cost):
    checks = {"word_fragment_states":0,"source_end_alignments":0,"full_geometry_shapes":0,
              "record_reference_cases":0,"span_boundary_states":0}
    maximum = {"I":515,"D":9*515,"W":513,"Q":4096}
    max_cost = 26+68*maximum["I"]+39*maximum["D"]+139*maximum["W"]+maximum["Q"]
    assert max_cost == 291214
    # Every possible incoming partial word and remaining block capacity.
    for skip in range(8):
        for remaining in range(1, T+1):
            left, visits, current_skip = remaining, 0, skip
            while left:
                n = min(8-current_skip, left)
                left -= n
                current_skip = 0
                visits += 1
            assert visits == (remaining+skip)//8 + ((remaining+skip)%8 != 0)
            assert visits <= 513
            # Failure before any fragment's copy is a prefix, including final visit.
            assert visits-1 <= 512
            checks["word_fragment_states"] += 1
    # Vary every source ending offset on the block grid, all eight section
    # selectors, zero sections and two spans of boundary-crossing lengths.
    for residue in range(T):
        source = (residue-H) % T
        selector = residue % 8
        counts = [0]*8
        counts[selector] = (residue % 17) + 1
        counts[(selector+3)%8] = 513 if residue % 257 == 0 else residue % 5
        reference(source, counts)
        checks["source_end_alignments"] += 1
        checks["full_geometry_shapes"] += 1
    samples = [(0,[0]*8), (0,[1]*8), (1,[1]*8), (1536,[0,0,0,0,0,0,0,1025]),
               (1537,[0,0,0,0,0,0,0,1025]), (8191,[2,0,3,0,2,0,3,0]),
               (8192,[2,0,3,0,2,0,3,0])]
    for sid in range(8):
        for source in (0,1,1535,1536,1537,4095,4096,4097):
            counts = [0]*8
            counts[sid] = 2050
            samples.append((source, counts))
    for source, counts in samples:
        reference(source, counts)
        checks["full_geometry_shapes"] += 1
    # Count actual reference branches and their late-error prefixes, rather
    # than treating a count of arbitrary integers as a behavioral control.
    records = {1:{"parameters":(0,2)}, 2:{},
               3:{"spans":[(0,1),(1,1)],"type_index":1},
               4:{"spans":[(2,2)],"type_index":1},
               5:{"spans":[(3,1)]},6:{"spans":[(4,1)],"kind":3},
               7:{"spans":[(5,1)]},8:{"spans":[(6,1)]}}
    cases = []
    for sid, record in records.items():
        cases.extend([(sid,record,0,None),(sid,None,0,16),(sid,record,5,21)])
        for index in range(len(record.get("spans",[]))):
            bad = {**record,"spans":list(record["spans"])}
            bad["spans"][index] = (8,1)
            cases.append((sid,bad,0,15))
    cases.extend([(0,{},0,20),(9,{},0,20),(1,{"parameters":(2,1)},0,17),
                  (3,{**records[3],"type_index":2},0,18),
                  (4,{**records[4],"type_index":2},0,18),
                  (6,{**records[6],"kind":4},0,19)])
    traces = []
    for sid, record, within, expected in cases:
        error, credits, trace = record_reference(sid,record,within)
        assert error == expected, (sid,record,within,error,expected)
        checks["record_reference_cases"] += 1
        traces.append({"sid":sid,"within":within,"expected_error":expected,
                       "model_credits":credits,"trace":trace})
    for source in (0,1,8,67108864,(1<<64)-1):
        for offset in (0,1,7,8,(1<<32)-1):
            for length in (0,1,7,8,(1<<32)-1):
                end = offset+length
                accepted = end <= (1<<64)-1 and end <= source
                # Independent subtraction form avoids constructing an invalid
                # unsigned sum; these two finite formulations must agree.
                assert accepted == (offset <= source and length <= source-offset)
                assert 2+5+2+1+1+1+12 == 24
                checks["span_boundary_states"] += 1
    return {"finite_controls":checks,"per_call_counter_ceiling":maximum,
            "per_call_work_ceiling":max_cost,"record_model_traces":traces,
            "actual_encoder_runtime_executed":False}


def witnesses():
    result = []
    for name in ("host-debug-selected-baseline-none", "host-debug-selected-segments-none"):
        path = ENC / "runs" / name / "actual.mixsnb02"
        data = path.read_bytes()
        assert data[:8] == b"MIXSNB02"
        directories = [struct.unpack_from("<8Q", data, 1600+64*sid) for sid in range(9)]
        source = directories[0][1]
        counts = [d[1] for d in directories[1:]]
        c, blocks = reference(source, counts)
        assert c["E"] == len(data)
        result.append({"path":str(path.relative_to(REPO)),"sha256":sha(data),"source":source,
                       "metadata_counts":counts,"geometry":c,"blocks":blocks,
                       "comparison":compare_old(c)})
    simple, _ = reference(0,[1,0,0,0,0,0,0,0])
    assert simple["N"] == 1 and simple["W"] == 3
    maximum = closed(CAPS[0],list(CAPS[1:]))
    assert maximum["E"] == 69765152 and maximum["L"] == 331716 and maximum["N"] == 109184
    return {"frozen_actual_artifacts":result,
            "once_per_record_counterexample":{"kind":"geometry-only signature; not an admitted proof",
                "N":simple["N"],"word_visits":simple["W"],"width":3,
                "explanation":"one record_word lookup/full validation per encoded word, not once per record"},
            "independent_maximum_envelope":{"not_a_genuine_fixture":True,"geometry":maximum,
                                             "comparison":compare_old(maximum)}}


def main():
    before = inputs()
    costs = ledger()
    result = {"schema":1,"status":"source-audited-encoder-bound-no-runtime-authorization",
              **controls(costs),**witnesses(),
              "limits":["Independent scalar-action convention, not runtime instrumentation or CPU/RSS",
                        "No selected composition debit, stop/control/writer/syscall/cleanup work proved",
                        "No encoder/wrapper/VM/native/device/UI/capture runtime executed",
                        "No additional ExecutionWork grant, refund, raised original limit or OTA authorization",
                        "Whole-stream bound requires abort on first encoder error and at most one terminal None"]}
    after = inputs()
    assert before == after
    summary = {"status":result["status"],"fixed":costs["fixed_total"],
               "block":"26+68I+39D+139W+Q","finite_controls":result["finite_controls"],
               "per_call_ceiling":result["per_call_work_ceiling"],
               "custody":"1256 packet members, 144 source members, before==after"}
    if (OUT / "seal.json").exists():
        frozen = json.loads((OUT / "seal.json").read_text())
        for member in frozen["members"]:
            path = OUT / member["path"]
            assert path.stat().st_size == member["bytes"] and sha(path.read_bytes()) == member["sha256"]
        for name, value in (("cost-ledger.json",costs),("results.json",result),("input-custody.json",before)):
            assert json.loads((OUT/name).read_text()) == json.loads(json.dumps(value)), name
        print(json.dumps(summary,sort_keys=True))
        return
    save("input-custody.json", before)
    save("cost-ledger.json", costs)
    save("results.json", result)
    revision = subprocess.check_output(["git","rev-parse","HEAD"],cwd=REPO,text=True).strip()
    receipt = {"schema":1,"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "command":"python3 verification/swift-guarded-snapshot-encoder-work-correction/audit.py",
               "python":platform.python_version(),"executable":sys.executable,"repository_head":revision,
               "audit_script_sha256":sha(Path(__file__).read_bytes()),
               "source_tree_sha256":EXPECTED_TREE,"source_member_count":144,
               "input_seal_sha256":EXPECTED_SEAL,"exit_code":0,"scope":result["status"],
               "outputs":{name:sha((OUT/name).read_bytes()) for name in
                          ("cost-ledger.json","results.json","input-custody.json")},
               "stdout":json.dumps(summary,sort_keys=True),"stderr":"",
               "cleanup":"No compiled products or disposable/native instances created; no cleanup needed."}
    save("command-receipt.json",receipt)
    print(json.dumps(summary,sort_keys=True))


if __name__ == "__main__":
    main()
