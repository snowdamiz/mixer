#!/usr/bin/env python3
"""Bounded offline receipt and exact-target identity review; no product execution."""
import hashlib
import json
import pathlib
import re
import signal
import stat
import sys
import time

signal.alarm(50)
START = time.monotonic()
OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parents[1]
CAP = pathlib.Path("verification/swift-root-bound-dispatch-retained-capture-v1")
RUNTIME = CAP / "runtime"
SOURCE = pathlib.Path("verification/swift-guarded-snapshot-root-result-lifetime-implementation/source/vm")
FRONTIER = pathlib.Path("verification/swift-root-bound-dispatch-physical-plan/target-frontier.json")
RELEASE = pathlib.Path("verification/swift-semantic-adapter-root-review/dispatch-retained-physical-capture-release.json")
INDEPENDENT = pathlib.Path("verification/swift-root-bound-dispatch-retained-capture-independent/seal.json")
TREE = "91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f"
EXPECTED = {
    "dispatch.ll": (66974303, "788126f146f9da84a8e190c87b638bb4ae284a8321cce2ac6f47ffda64b7880a"),
    "dispatch.s": (44456451, "c6bac3481f6c5ad1223e4a3ae1a069505cf3bf32450fbfb338b073b2a25e0894"),
}
INPUTS = {}
CHECKS = []


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def check(condition, name):
    if not condition:
        raise ValueError(name)
    CHECKS.append(name)


def read(path):
    absolute = ROOT / path
    check(stat.S_ISREG(absolute.lstat().st_mode), "regular input: " + str(path))
    data = absolute.read_bytes()
    INPUTS[str(path)] = {"path": str(path), "bytes": len(data), "sha256": sha(data)}
    return data


def load(path):
    return json.loads(read(path))


def put(name, data):
    if not isinstance(data, bytes):
        data = (json.dumps(data, sort_keys=True, indent=2) + "\n").encode()
    used = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file() and p.name != name)
    check(used + len(data) <= 16 * 1024 * 1024, "derived 16MiB bound: " + name)
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": sha(data)}


def span(lines, first, last, path):
    # Zero based, half open indices. Preserve every original byte and newline.
    data = b"".join(lines[first:last])
    return {
        "file": INPUTS[str(path)], "line_begin": first + 1,
        "line_end_inclusive": last,
        "byte_begin": sum(map(len, lines[:first])),
        "byte_end": sum(map(len, lines[:last])), "span_sha256": sha(data),
    }, data


release = load(RELEASE)
independent = load(INDEPENDENT)
check(INPUTS[str(INDEPENDENT)]["sha256"] == "905fd623ebfee585a79efc5e422e6e1d80736dd251d622dae2a34c6c72f02881", "exact independent source seal")
check(release["independent_source_review"]["sha256"] == INPUTS[str(INDEPENDENT)]["sha256"], "release binds independent seal")
check(release["compiler_lane_released"] is True and release["semantic_map_approved"] is False, "capture-only root release")
plan = load(CAP / "plan.json")
check(INPUTS[str(CAP / "plan.json")]["sha256"] == release["controller_plan_sha256"], "released controller plan")
controller = read(CAP / "run-capture.py")
check(sha(controller) == release["controller_sha256"], "controller read and hashed only")
check(sha(read(CAP / "seal.json")) == release["capture_packet_seal_sha256"], "released capture packet seal")
check(sha(canonical(plan["argv"])) == release["argv_sha256"], "exact released argv")
receipt = load(RUNTIME / "receipt.json")
observation = load(RUNTIME / "capture-observation.json")
observations = load(RUNTIME / "observations.json")
check(receipt["status"] == observation["status"] == "captured-artifacts-only", "terminal captured-artifacts-only")
check(receipt["observations_sha256"] == INPUTS[str(RUNTIME / "observations.json")]["sha256"], "whole observations hash")
check(receipt["capture_observation_sha256"] == INPUTS[str(RUNTIME / "capture-observation.json")]["sha256"], "whole capture observation hash")
for key in ["controller_sha256", "packet_seal_sha256", "base_plan_sha256", "plan_sha256"]:
    other = {"packet_seal_sha256": "capture_packet_seal_sha256", "base_plan_sha256": "base_capture_plan_sha256", "plan_sha256": "controller_plan_sha256"}.get(key, key)
    check(receipt[key] == release[other], "receipt release binding: " + key)
check(receipt["finalization_errors"] == [] and observations["errors"] == [], "no terminal errors")
check(receipt["observed_signals"] == [] and not receipt["signal_record_overflow"], "recorded cutoff signals empty")
check(receipt["signal_cutoff_seconds"] < 55, "recorded capture under 55 seconds")
check(observation["compiler_exit"] == 0 and observation["capture_complete"] and observation["bounds_met"] and not observation["truncated"], "complete untruncated compiler capture")
check(observation["cleanup_complete"] and observation["owned_groups_closed"] and observations["generated_directory_removed"], "recorded owned cleanup complete")
check(len(observations["commands"]) == 1 and observations["automatic_retries"] == 0, "one command no retry")
command = observations["commands"][0]
check(command["argv"] == plan["argv"] and command["returncode"] == 0 and command["kind"] == "compiler-capture", "recorded exact compiler invocation")
check(command["reaped"] and command["group_absent"] and command["custody"] and command["full_streams_captured"], "recorded custody reap and absence")
before, after = observations["pins_before"], observations["pins_after"]
check(len(before) == len(after) == 308 and before == after and observations["all_pins_rechecked"], "308 equal before after pins")
check(len({pin["path"] for pin in before}) == 308, "308 distinct pin paths")
stderr = read(RUNTIME / "compile.stderr")
stdout = read(RUNTIME / "compile.stdout")
records = [json.loads(line) for line in stderr.splitlines()]
policy = load(CAP / "diagnostic-policy.json")
check(records == policy["records"] and len(records) == 4, "exact policy diagnostic records")
check(len(stdout) == 0 and len(stderr) == 8104, "complete diagnostic stream lengths")
for name, data in [("stderr", stderr), ("stdout", stdout)]:
    check(command[name]["bytes"] == len(data) and command[name]["sha256"] == sha(data), "recorded stream hash: " + name)
manifest_path = pathlib.Path(plan["source_manifest"]["path"])
manifest = load(manifest_path)
check(INPUTS[str(manifest_path)] == plan["source_manifest"], "pinned source manifest")
check(manifest["member_count"] == len(manifest["members"]) == 146, "source146 member count")
check(sha(canonical(manifest["members"])) == manifest["tree_sha256"] == plan["source_tree_sha256"] == TREE, "source146 canonical tree")
source_pins = {pin["path"]: pin for pin in before}
for member in manifest["members"]:
    path = SOURCE / member["path"]
    data = read(path)
    check(len(data) == member["bytes"] and sha(data) == member["sha256"], "source member exact: " + member["path"])
    check(source_pins[str(ROOT / path)]["sha256"] == member["sha256"], "source member capture-bound: " + member["path"])
frontier = load(FRONTIER)
check(frontier["source146_tree_sha256"] == TREE, "original target source binding")
source_spans = []
for target in frontier["targets"]:
    src = target["source"]
    data = read(pathlib.Path(src["file"]["path"]))
    check(len(data) == src["file"]["bytes"] and sha(data) == src["file"]["sha256"], "target source file: " + target["id"])
    excerpt = data[src["byte_begin"]:src["byte_end"]]
    check(sha(excerpt) == src["span_sha256"], "target source byte span: " + target["id"])
    source_spans.append({"id": target["id"], "binding": src, "excerpt": put("excerpts/" + target["id"] + ".rs", excerpt)})
raw = {}
for name, (length, digest) in EXPECTED.items():
    path = RUNTIME / "generated" / name
    raw[name] = read(path)
    check(len(raw[name]) == length and sha(raw[name]) == digest, "exact retained raw artifact: " + name)
    actual = next(item for item in observation["outputs"] if item["name"] == ("ir" if name.endswith(".ll") else "asm"))
    check(actual["bytes"] == length and actual["sha256"] == digest, "terminal raw artifact hash: " + name)
check(sum(map(len, raw.values())) == 111430754 <= 128 * 1024 * 1024, "exact distinct raw pair within 128MiB")
ir_path = RUNTIME / "generated/dispatch.ll"
asm_path = RUNTIME / "generated/dispatch.s"
ir = raw["dispatch.ll"].splitlines(keepends=True)
asm = raw["dispatch.s"].splitlines(keepends=True)
metadata = {}
definitions = []
declarations = 0
for index, line in enumerate(ir):
    match = re.match(rb"!(\d+) = (.*)", line)
    if match:
        metadata[int(match[1])] = (index, line.decode().rstrip("\n"))
    if line.startswith(b"define "):
        symbol = re.search(rb"@([^ (]+)\(", line)[1].decode()
        definitions.append((index, symbol))
    declarations += line.startswith(b"declare ")


def role(symbol):
    if symbol.endswith("127run_one_admitted_fixture_v1"):
        return "Caller"
    if symbol.startswith("_RNCN") and "127run_one_admitted_fixture_v10" in symbol:
        return "Closure"
    if "13ReservationV111dispatch_v1" in symbol and "24AdmittedFixtureOutcomeV1" in symbol and "27run_one_admitted_fixture_v10" in symbol:
        return "Dispatch"
    if symbol.endswith("131run_prepaid_admitted_fixture_v1"):
        return "Body"
    return None


matches = {key: [] for key in ["Caller", "Closure", "Dispatch", "Body"]}
for first, symbol in definitions:
    if role(symbol):
        matches[role(symbol)].append((first, symbol))
check(all(len(values) == 1 for values in matches.values()), "four unique exact native definitions; absent or ambiguous stops without fallback")
target_map = []
all_metadata = set()
target_bodies = {}
target_asm = {}
for identity in ["Caller", "Closure", "Dispatch", "Body"]:
    first, symbol = matches[identity][0]
    last = next(i + 1 for i in range(first + 1, len(ir)) if ir[i] == b"}\n")
    check(not any(line.startswith(b"define ") for line in ir[first + 1:last]), "whole definition boundary: " + identity)
    ir_span, ir_data = span(ir, first, last, ir_path)
    debug_id = int(re.search(rb"!dbg !(\d+)", ir[first])[1])
    debug_text = metadata[debug_id][1]
    check("distinct !DISubprogram(" in debug_text and "DISPFlagDefinition" in debug_text and 'linkageName: "' + symbol + '"' in debug_text, "native definition debug linkage: " + identity)
    file_id = int(re.search(r"file: !(\d+)", debug_text)[1])
    file_text = metadata[file_id][1]
    source_file = next(target["source"]["file"]["path"] for target in frontier["targets"] if target["id"] == identity)
    check('filename: "' + source_file + '"' in file_text, "native debug source path: " + identity)
    source_data = (ROOT / source_file).read_bytes()
    check('checksum: "' + hashlib.md5(source_data).hexdigest() + '"' in file_text, "native debug source checksum: " + identity)
    source_line = {"Caller": 853, "Closure": 861, "Dispatch": 134, "Body": 863}[identity]
    check(re.search(r"\bline: " + str(source_line) + r"\b", debug_text), "native debug source line: " + identity)
    assembly_symbol = "_" + symbol
    locations = [i for i, line in enumerate(asm) if line == (assembly_symbol + ":\n").encode()]
    check(len(locations) == 1, "unique assembly symbol: " + identity)
    a_first = locations[0]
    a_last = next(i + 1 for i in range(a_first + 1, len(asm)) if asm[i].strip() == b".cfi_endproc")
    a_span, a_data = span(asm, a_first, a_last, asm_path)
    check(a_data.count(b".cfi_startproc") == 1 and len(re.findall(rb"^Lfunc_end\d+:$", a_data, re.M)) == 1, "whole assembly function: " + identity)
    file_number = int(re.search(rb"\.loc\s+(\d+)\s+" + str(source_line).encode() + rb"\s+0\b", a_data)[1])
    file_defs = [(i, line) for i, line in enumerate(asm) if re.match(rb"\s*\.file\s+" + str(file_number).encode() + rb"\s", line)]
    check(len(file_defs) == 1 and source_file.encode() in file_defs[0][1], "assembly source file mapping: " + identity)
    target_bodies[identity] = (symbol, first, last, ir_data)
    target_asm[identity] = (a_first, a_last, a_data)
    ids = {int(value) for value in re.findall(rb"!(\d+)", ir_data)}
    ids.add(debug_id)
    ids.add(file_id)
    all_metadata.update(ids)
    target_map.append({
        "id": identity, "symbol": symbol, "assembly_symbol": assembly_symbol,
        "unique_definition": True, "source": next(item["binding"] for item in source_spans if item["id"] == identity),
        "definition_debug_id": debug_id, "debug_source_file_id": file_id,
        "llvm_definition": ir_span, "llvm_excerpt": put("excerpts/" + identity + ".ll", ir_data),
        "assembly_function": a_span, "assembly_excerpt": put("excerpts/" + identity + ".s", a_data),
        "assembly_file_directive": {"line": file_defs[0][0] + 1, "text": file_defs[0][1].decode().rstrip("\n")},
        "llvm_basic_blocks": sum(bool(re.match(rb"^[A-Za-z_][A-Za-z_0-9.]*:", line)) for line in ir[first:last]),
        "llvm_normal_returns": sum(bool(re.match(rb"\s+ret ", line)) for line in ir[first:last]),
        "llvm_resume_exits": sum(bool(re.match(rb"\s+resume ", line)) for line in ir[first:last]),
    })

# Keep complete function text; only preserve metadata needed for identity, source
# scopes, direct instruction locations and the actual Dispatch type parameters.
todo = list(all_metadata)
while todo:
    identity = todo.pop()
    text = metadata[identity][1]
    follow = [int(value) for value in re.findall(r"(?:scope|file): !(\d+)", text)]
    if "!DISubprogram(" in text:
        follow += [int(value) for value in re.findall(r"templateParams: !(\d+)", text)]
    if re.match(r"!\d+ = !\{", text) or "!DITemplateTypeParameter(" in text:
        follow += [int(value) for value in re.findall(r"!(\d+)", text.split(" = ", 1)[1])]
    for child in follow:
        if child not in all_metadata:
            all_metadata.add(child)
            todo.append(child)
check(len(all_metadata) < 2048, "bounded identity metadata selection")
debug_records = [{"id": identity, "line": metadata[identity][0] + 1, "text": metadata[identity][1]} for identity in sorted(all_metadata)]
put("debug-map.json", {"schema": 1, "raw_file": INPUTS[str(ir_path)], "selection": "all direct four-definition metadata references, source scope/file chains and Dispatch template parameters; not a complete module metadata index", "records": debug_records})
edges = []
for parent, child in [("Caller", "Dispatch"), ("Dispatch", "Closure"), ("Closure", "Body")]:
    symbol, first, last, data = target_bodies[parent]
    callee = target_bodies[child][0]
    call_lines = [(i, ir[i]) for i in range(first, last) if re.search(rb"\b(?:call|invoke)\b.*@" + re.escape(callee.encode()) + rb"\(", ir[i])]
    a_first, a_last, a_data = target_asm[parent]
    branches = [(i, asm[i]) for i in range(a_first, a_last) if re.match(rb"\s*bl\s+_" + re.escape(callee.encode()) + rb"\s*$", asm[i])]
    check(len(call_lines) == len(branches) == 1, "unique LLVM and assembly edge: " + parent + " -> " + child)
    location = int(re.search(rb"!dbg !(\d+)", call_lines[0][1])[1])
    check(location in all_metadata, "callsite metadata retained: " + parent)
    edges.append({"caller": parent, "callee": child, "llvm": {"line": call_lines[0][0] + 1, "text": call_lines[0][1].decode().rstrip("\n"), "debug_location": location, "debug_text": metadata[location][1]}, "assembly": {"line": branches[0][0] + 1, "text": branches[0][1].decode().rstrip("\n")}})
caller_text = target_bodies["Caller"][3]
closure_construct = [(i, ir[i]) for i in range(target_bodies["Caller"][1], target_bodies["Caller"][2]) if b"store ptr %fixture, ptr %_25" in ir[i]]
check(len(closure_construct) == 1, "one Caller closure construction")
closure_location = int(re.search(rb"!dbg !(\d+)", closure_construct[0][1])[1])
check("line: 861, column: 36," in metadata[closure_location][1], "exact closure creation at 861:36")
dispatch_debug = metadata[next(item["definition_debug_id"] for item in target_map if item["id"] == "Dispatch")][1]
check("dispatch_v1<" in dispatch_debug and "::AdmittedFixtureOutcomeV1, " in dispatch_debug and "::run_one_admitted_fixture_v1::{closure_env#0}>" in dispatch_debug, "actual admitted Dispatch type and exact closure environment")
put("call-edges.json", {"schema": 1, "edges": edges, "closure_construction": {"line": closure_construct[0][0] + 1, "text": closure_construct[0][1].decode().rstrip("\n"), "debug_location": closure_location, "debug_text": metadata[closure_location][1]}, "generic_MIR_used_for_native_identity": False})
body_first, body_last, body_asm = target_asm["Body"]
lsda = re.search(rb"\.cfi_lsda\s+\d+,\s+(\S+)", body_asm)[1]
check(asm[body_last].strip() == b".section\t__TEXT,__gcc_except_tab", "Body exception table begins after function")
lsda_end = next(i for i in range(body_last + 1, len(asm)) if asm[i].lstrip().startswith(b".section"))
lsda_span, lsda_data = span(asm, body_last, lsda_end, asm_path)
check(lsda + b":\n" in lsda_data, "complete referenced Body exception table")
put("body-exception-table.json", {"schema": 1, "span": lsda_span, "excerpt": put("excerpts/Body-exception-table.s", lsda_data), "semantic_cleanup_or_unwind_analysis_complete": False})
put("source-bindings.json", {"schema": 1, "source146_tree_sha256": TREE, "all146_current_hashes_match": True, "all146_captured_pins_match": True, "targets": source_spans})
put("target-map.json", {"schema": 1, "status": "ALL_FOUR_EXACT_NATIVE_TARGET_IDENTITIES_RESOLVED_FOR_ROOT_SEMANTIC_REVIEW", "raw_pair_bytes": 111430754, "source146_tree_sha256": TREE, "module_definition_count": len(definitions), "module_declaration_count": declarations, "candidate_counts": {key: len(value) for key, value in matches.items()}, "targets": target_map, "target_identity_mapping_complete": True, "frontier_complete": False, "semantic_geometry_approved": False, "generic_MIR_promoted": False})

# Re-read only the same two raw files for the expressly allowed posthash.
posthash = []
for name, (length, digest) in EXPECTED.items():
    path = RUNTIME / "generated" / name
    data = (ROOT / path).read_bytes()
    check(len(data) == length and sha(data) == digest, "raw afterhash unchanged: " + name)
    posthash.append(INPUTS[str(path)])
for path in [RELEASE, INDEPENDENT, FRONTIER, CAP / "plan.json", RUNTIME / "receipt.json", RUNTIME / "observations.json", RUNTIME / "capture-observation.json"]:
    check(sha((ROOT / path).read_bytes()) == INPUTS[str(path)]["sha256"], "review control input afterhash unchanged: " + str(path))
elapsed = time.monotonic() - START
check(elapsed < 50, "review command bounded below 55 seconds")
put("review-inputs.json", {"schema": 1, "inputs": [INPUTS[key] for key in sorted(INPUTS)], "raw_pair_posthash": posthash})
put("terminal-review.json", {
    "schema": 1, "status": "FROZEN_TERMINAL_RECEIPT_ACCEPTED_AND_EXACT_FOUR_TARGET_IDENTITIES_MAPPED",
    "terminal_capture_receipt_accepted": True, "target_identity_mapping_complete": True,
    "recorded_capture_seconds": receipt["signal_cutoff_seconds"], "recorded_compiler_exit": 0,
    "recorded_cleanup_complete": True, "cleanup_claim_independently_process_probed": False,
    "source146_current_hashes_verified": True, "recorded_before_after_pin_count": 308,
    "recorded_before_after_pins_identical": True,
    "warnings": [record["message"] for record in records], "diagnostic_records_exact_policy_match": True,
    "alternate_diagnostic_configuration_only": True, "link_dead_code": True,
    "compiler_tool_version_from_saved_capture_only": observations["compiler_version_from_prior_pinned_receipt"],
    "review_python_executable": sys.executable, "review_python_runtime": sys.version,
    "version_probe_invocations": 0, "compiler_controller_import_execution_native_model_test_geometry_or_process_probe_invocations": 0,
    "computer_use_or_screen_capture": False, "physical_device_or_simulator_emulator_run": False,
    "original_capture_qualified": False, "original_missing_target_cause_proved": False,
    "runtime_admission_accepted": False, "frontier_complete": False,
    "semantic_geometry_approved": False, "complete_capacity_accepted": False,
    "physical_capacity_prices_backings_root_funding_product_GA_accepted": False,
    "original_capture_all_four_missing_remains_unchanged": True,
    "scope": "Offline terminal/hashes and exact native source/definition/assembly/call-edge identity mapping of the retained alternate diagnostic pair only; root semantic review required before geometry facts.",
    "unresolved": ["physical arena identities and offsets", "sret and native stack slot correspondence", "all-path frame and coexisting call peaks", "deeper setup/loader/leaf/stdlib/drop/unwind calls", "all backing ownership/capacities", "destruction continuation", "physical phones and native runtime checks paused"],
    "review_elapsed_seconds_before_seal": elapsed, "per_command_wall_limit_seconds": 55,
    "distinct_raw_bytes": 111430754, "maximum_distinct_raw_bytes": 128 * 1024 * 1024,
    "maximum_derived_bytes": 16 * 1024 * 1024, "silent_truncation": False,
    "checks": CHECKS,
})
summary = "Terminal receipt accepted; all four exact native target identities mapped. Alternate diagnostic pair only; semantic geometry, runtime admission, capacity and GA remain unaccepted.\n"
put("review-output.txt", summary.encode())
members = []
for path in sorted(OUT.rglob("*")):
    if path.is_file() and path.name != "seal.json":
        data = path.read_bytes()
        members.append({"path": str(path.relative_to(OUT)), "bytes": len(data), "sha256": sha(data)})
seal = {"schema": 1, "status": "FROZEN_OFFLINE_TERMINAL_AND_NATIVE_TARGET_IDENTITY_MAPPING", "members": members, "member_count": len(members), "member_bytes": sum(item["bytes"] for item in members), "tree_sha256": sha(canonical(members)), "source146_tree_sha256": TREE, "target_identity_mapping_complete": True, "frontier_complete": False, "semantic_geometry_approved": False, "runtime_admission_accepted": False, "complete_capacity_accepted": False, "original_capture_qualified": False, "root_semantic_review_required": True}
put("seal.json", seal)
print(summary, end="")
print(json.dumps({"member_count": len(members), "member_bytes": seal["member_bytes"], "tree_sha256": seal["tree_sha256"], "elapsed_seconds": time.monotonic() - START}, sort_keys=True))
