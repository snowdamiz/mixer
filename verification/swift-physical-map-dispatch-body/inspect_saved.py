#!/usr/bin/env python3
"""Bounded offline index of the exact root-selected saved artifacts; no toolchain execution."""
from pathlib import Path
import datetime, hashlib, json, platform, re, signal, subprocess, sys, time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
START = time.monotonic()
signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("55 second command bound")))
signal.alarm(50)
def sha(raw): return hashlib.sha256(raw).hexdigest()
def write(name, value):
    p = OUT / name
    p.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
def pin(path):
    raw = (ROOT / path).read_bytes()
    return {"path": path, "bytes": len(raw), "sha256": sha(raw)}, raw

selection_path = "verification/swift-semantic-adapter-root-review/dispatch-physical-mapping-selection.json"
selection_pin, selection_raw = pin(selection_path)
selection = json.loads(selection_raw)
inputs = [selection_pin]
for name in ("capture_acceptance", "target_frontier"):
    expected = selection[name]
    actual, raw = pin(expected["path"])
    assert actual == expected, (name, actual, expected)
    inputs.append(actual)
frontier = json.loads((ROOT / selection["target_frontier"]["path"]).read_bytes())
acceptance = json.loads((ROOT / selection["capture_acceptance"]["path"]).read_bytes())
for name in ("receipt", "capture_observation", "observations", "independent_terminal_review"):
    expected = acceptance[name]
    actual, raw = pin(expected["path"])
    assert actual == expected
    inputs.append(actual)
anchors = []
for target in frontier["targets"]:
    if target["id"] not in ("Dispatch", "Body"): continue
    record = {"id": target["id"], "source": target["source"], "retained_MIR": target["retained_MIR"]}
    for kind in ("source", "retained_MIR"):
        span = target[kind]
        actual, raw = pin(span["file"]["path"])
        assert actual == span["file"]
        assert sha(raw[span["byte_begin"]:span["byte_end"]]) == span["span_sha256"]
        inputs.append(actual)
        (OUT / (target["id"].lower() + "." + kind + ".txt")).write_bytes(raw[span["byte_begin"]:span["byte_end"]])
    anchors.append(record)

artifacts = []
for expected in selection["artifacts"]:
    path = ROOT / expected["path"]
    stat_before = path.stat()
    actual, raw = pin(expected["path"])
    assert actual == expected
    assert stat_before == path.stat()
    lines = raw.splitlines(keepends=True)
    offsets, running = [], 0
    for line in lines:
        offsets.append(running); running += len(line)
    offsets.append(running)
    record = {"input": actual, "line_count": len(lines), "stat_before": {"size": stat_before.st_size, "mtime_ns": stat_before.st_mtime_ns, "inode": stat_before.st_ino}, "candidates": []}
    record["whole_artifact_literal_occurrences"] = {term: raw.count(term.encode()) for term in ("dispatch_v1", "run_prepaid_admitted_fixture_v1", "run_one_admitted_fixture_v1", "AdmittedFixtureOutcomeV1", "ReservationV1", "PrepaidOwnedV1", "host_account_v1.rs", "initial_profile_v1.rs")}
    record["whole_artifact_line_coverage"] = {"first": 1, "last_inclusive": len(lines), "bytes_covered": running, "no_input_truncation": running == len(raw)}
    record["module_context_prefix"] = {"line_begin": 1, "line_end_inclusive": 4 if path.suffix == ".ll" else 2, "text": b"".join(lines[:4 if path.suffix == ".ll" else 2]).decode(), "explicitly_bounded_excerpt_not_a_whole_function": True}
    if path.suffix == ".ll":
        active = None
        all_definitions = 0
        all_definition_ends = 0
        declaration_or_alias_hits = []
        for ix, line in enumerate(lines):
            if line.startswith(b"define "):
                assert active is None
                all_definitions += 1
                active = ix
            if active is not None and line.rstrip() == b"}":
                header = lines[active]
                if b"dispatch_v1" in header or b"run_prepaid_admitted_fixture_v1" in header:
                    body = raw[offsets[active]:offsets[ix+1]]
                    item = {"line_begin": active+1, "line_end_inclusive": ix+1, "byte_begin": offsets[active], "byte_end_exclusive": offsets[ix+1], "bytes": len(body), "sha256": sha(body), "header": header.decode().rstrip(), "excerpt_path": "llvm-candidate-%02d.ll" % len(record["candidates"])}
                    (OUT / item["excerpt_path"]).write_bytes(body)
                    record["candidates"].append(item)
                active = None
                all_definition_ends += 1
            if line.startswith((b"declare ", b"@")) and any(term in line for term in (b"dispatch_v1", b"run_prepaid_admitted_fixture_v1")):
                declaration_or_alias_hits.append({"line": ix+1, "text": line.decode().rstrip()})
        assert active is None
        record["all_LLVM_actual_definitions"] = all_definitions
        record["all_LLVM_actual_definition_ends"] = all_definition_ends
        record["target_declaration_or_global_alias_hits"] = declaration_or_alias_hits
        metadata = []
        for ix, line in enumerate(lines):
            if line.startswith(b"!") and any(needle in line for needle in (b"dispatch_v1", b"run_prepaid_admitted_fixture_v1", b"AdmittedFixtureOutcomeV1", b"initial_profile_v1.rs", b"host_account_v1.rs")):
                metadata.append({"line": ix+1, "byte_begin": offsets[ix], "byte_end_exclusive": offsets[ix+1], "text": line.decode().rstrip()})
        write("llvm-target-metadata-hits.json", metadata)
        defs = []
        for ix, line in enumerate(lines):
            if line.startswith(b"define ") and (b"run_one_admitted_fixture_v1" in line):
                defs.append({"line": ix+1, "text": line.decode().rstrip()})
        write("caller-closure-definition-headers.json", defs)
    else:
        hits = []
        for ix, line in enumerate(lines):
            if (b"dispatch_v1" in line or b"run_prepaid_admitted_fixture_v1" in line):
                hits.append({"line": ix+1, "byte_begin": offsets[ix], "byte_end_exclusive": offsets[ix+1], "text": line.decode().rstrip()})
        record["target_text_hits"] = hits
        record["all_assembly_cfi_startproc"] = sum(line.strip() == b".cfi_startproc" for line in lines)
        record["all_assembly_cfi_endproc"] = sum(line.strip() == b".cfi_endproc" for line in lines)
        record["all_assembly_function_begin_labels"] = sum(bool(re.fullmatch(rb"Lfunc_begin\d+:\n?", line)) for line in lines)
        record["all_assembly_function_end_labels"] = sum(bool(re.fullmatch(rb"Lfunc_end\d+:\n?", line)) for line in lines)
        # Initial structural excerpts are explicitly bounded and are not whole functions.
        structural = []
        for ix, line in enumerate(lines):
            if line.rstrip().endswith(b":") and (b"dispatch_v1" in line or b"run_prepaid_admitted_fixture_v1" in line):
                structural.append({"line_begin": max(1, ix-4), "line_end_inclusive": min(len(lines), ix+16), "text": b"".join(lines[max(0,ix-5):ix+16]).decode()})
        write("assembly-label-structural-excerpts.json", structural)
    # Required after hash is an independent read from disk of the exact same saved file.
    after_pin, after_raw = pin(expected["path"])
    assert after_pin == expected
    stat_after = path.stat()
    assert stat_before == stat_after
    record["disk_sha256_after_index"] = after_pin["sha256"]
    record["disk_stat_unchanged_after_index"] = True
    artifacts.append(record)

assert sum(item["input"]["bytes"] for item in artifacts) <= selection["bounds"]["maximum_total_raw_artifact_bytes"]
index = {"schema": 1, "status": "INCOMPLETE_NO_UNIQUE_ACTUAL_DISPATCH_OR_BODY_DEFINITION", "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "source146_tree_sha256_from_accepted_frontier": frontier["source146_tree_sha256"], "source146_full_tree_not_rehashed_here": True, "tool": {"python": sys.version, "implementation": platform.python_implementation(), "script_sha256": sha(Path(__file__).read_bytes())}, "command": ["python3", "verification/swift-physical-map-dispatch-body/inspect_saved.py"], "raw_artifact_unique_bytes": sum(item["input"]["bytes"] for item in artifacts), "raw_artifact_full_hash_passes_each": 2, "inputs": list({item["path"]: item for item in inputs}.values()), "anchors": anchors, "artifacts": artifacts, "elapsed_seconds": time.monotonic()-START, "no_compiler_native_test_model_verifier_or_geometry_run": True}
write("index-candidates.json", index)
targets = []
for anchor in anchors:
    targets.append({"id": anchor["id"], "status": "incomplete-no-unique-actual-native-definition-found", "source_anchor": anchor["source"], "retained_MIR_anchor": anchor["retained_MIR"], "MIR_is_not_native_presence_evidence": True, "unique_LLVM_definition": None, "LLVM_definition_whole_span": None, "LLVM_definition_sha256": None, "native_assembly_function": None, "native_assembly_whole_span": None, "native_assembly_whole_sha256": None, "linkage_identity": None, "source_debug_to_linkage_chain": None, "native_call_edge_provenance": None, "required_native_facts": next(item["required_native_facts"] for item in frontier["targets"] if item["id"] == anchor["id"]), "all_required_native_facts_pending": True})
write("mapping.json", {"schema": 1, "status": "INCOMPLETE", "targets": targets, "input_index": "index-candidates.json", "evidence": {"both_saved_artifacts_rehashed_before_and_after": True, "LLVM_entire_definitions_scanned_with_complete_start_end_census": True, "exact_target_identifier_hits_LLVM": {term: artifacts[0]["whole_artifact_literal_occurrences"][term] for term in ("dispatch_v1", "run_prepaid_admitted_fixture_v1")}, "exact_target_identifier_hits_assembly": {term: artifacts[1]["whole_artifact_literal_occurrences"][term] for term in ("dispatch_v1", "run_prepaid_admitted_fixture_v1")}, "matching_LLVM_actual_definitions": len(artifacts[0]["candidates"]), "matching_LLVM_declaration_or_global_alias_hits": len(artifacts[0]["target_declaration_or_global_alias_hits"]), "target_debug_hits_file": "llvm-target-metadata-hits.json", "generic_MIR_never_promoted_to_native_monomorphization": True}, "limitations": ["No unique actual definition means no whole-function span/hash, linkage, debug/source chain, or native call edge can be supplied for either target.", "A source DIFile mention is not a native function definition.", "The no-candidate result does not establish why codegen omitted the targets; private/reachability/DCE cause is not proven.", "No substitute symbol, compiler invocation, retry, flags, source/wrapper/reachability change, or capture fallback was used.", "Numeric region geometry, aliases, capacity, prices, backings, native call peaks, cleanup/destruction and acceptance remain unknown pending separately selected evidence.", "Text inspection is local mapping evidence only; no actual geometry-verifier input, certificate, physical acceptance, product or GA qualification is authorized or performed."], "frontier_complete": False, "actual_verifier_input_run_released": False, "physical_peak_accepted": False, "product_GA_accepted": False})
derived = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
assert derived <= selection["bounds"]["maximum_derived_bytes_each_partition"]
print(json.dumps({"status": index["status"], "elapsed_seconds": time.monotonic()-START, "raw_unique_bytes": index["raw_artifact_unique_bytes"], "derived_bytes_before_final_seal": derived, "LLVM_definition_census": artifacts[0]["all_LLVM_actual_definitions"], "assembly_cfi_census": artifacts[1]["all_assembly_cfi_startproc"], "whole_artifact_literal_occurrences": [item["whole_artifact_literal_occurrences"] for item in artifacts], "both_inputs_unchanged": True}, indent=2))
