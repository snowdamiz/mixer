#!/usr/bin/env python3
"""Original static contract review; does not authorize or execute guest code."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("--candidate", required=True)
parser.add_argument("--expected-contract-sha256", required=True)
parser.add_argument("--expected-header-sha256", required=True)
args = parser.parse_args()
if not (1 <= len(args.candidate) <= 64 and all(c.isascii() and (c.isalnum() or c in "-_") for c in args.candidate)):
    parser.error("candidate must be a short ASCII name")
out = BASE / args.candidate
out.mkdir(exist_ok=False)
checks = []
commands = []
captured = {}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(name):
    data = (ROOT / name).read_bytes()
    captured[name] = {"sha256": digest(data), "bytes": len(data)}
    return data


def check(name, condition, detail=None):
    checks.append({"name": name, "passed": bool(condition), "detail": detail})


def run(argv):
    result = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True)
    commands.append({"argv": argv, "exit_code": result.returncode,
                     "stdout": result.stdout, "stderr": result.stderr})
    return result


def pairs(items):
    value = {}
    for key, child in items:
        if key in value:
            raise ValueError("duplicate decoded key")
        value[key] = child
    return value


def strict_json(data):
    def invalid_constant(value):
        raise ValueError("non-JSON numeric constant")
    return json.loads(data.decode("utf-8", errors="strict"), object_pairs_hook=pairs,
                      parse_constant=invalid_constant)


contract_bytes = read("contracts/guest-ui-event-v1.json")
header_bytes = read("vm/include/mixer_vm_guest_ui.h")
(out / "contract.json").write_bytes(contract_bytes)
(out / "header.h").write_bytes(header_bytes)
check("reviewed_contract_bytes", digest(contract_bytes) == args.expected_contract_sha256)
check("reviewed_header_bytes", digest(header_bytes) == args.expected_header_sha256)
contract = strict_json(contract_bytes)
seal_bytes = read("verification/guest-ui-design/root-accepted.json")
seal = strict_json(seal_bytes)
design_bytes = read(seal["design_path"])
inspection_bytes = read("verification/guest-ui-design/inspection.json")
inspection = strict_json(inspection_bytes)
check("accepted_design_seal", seal["status"] == "root_accepted" and
      digest(design_bytes) == seal["design_sha256"] and
      digest(inspection_bytes) == seal["inspection_sha256"])

references_ok = all(digest(read(name)) == expected for name, expected in contract["references"].items())
check("all_normative_reference_hashes", references_ok)
preserved = []
for name, previous in inspection["captured_files"].items():
    if name.startswith("contracts/") or name in ("vm/include/mixer_vm.h", "vm/include/mixer_vm_capability.h"):
        preserved.append(name)
        check("frozen:" + name, digest(read(name)) == previous["sha256"])
check("preservation_inventory_complete", set(contract["preservation"]) == {
    name for name in preserved if name.startswith("contracts/")})
check("all_declared_preservation_hashes", all(digest(read(name)) == expected
      for name, expected in contract["preservation"].items()))

selection = contract["selection"]
check("explicit_unchanged_base_tuple", [selection[k] for k in (
    "identity_schema", "release_schema", "guest_abi", "ui_schema", "base_profile", "native_feature")] ==
    [2, 3, 2, 1, "mixer-table-memory-v3", "experimental-capability-native"])
check("fixed_startup_and_milestones", selection["startup_export"] == "mixer_guest_ui_start_v1" and
      selection["milestones"] == ["feature_started", "first_screen"])
check("dependency_binding", selection["required_dependencies"] == [
    {"id": "mixer.guest-ui-event-v1", "version": "1", "artifact_sha256": "SHA256 of these exact contract bytes"},
    {"id": "mixer.guest-ui-native-header-v1", "version": "1", "artifact_sha256": digest(header_bytes)},
])
check("strict_facade_reservation_text", all(value in selection["legacy_rejection"] for value in
      ["before reservation/store", "either exact reserved dependency ID", "any version/hash",
       "reserved UI startup", "complete exact triple", "No auto-detection"]))
check("fixed_export_types", [(e["name"], e["parameters"], e["results"], e["defined"])
      for e in contract["exports"]] == [
          ("mixer_guest_ui_start_v1", [], ["i32"], True),
          ("mixer_guest_ui_event_v1", ["i32"], ["i32"], True),
          ("mixer_guest_capability_ready_v1", [], [], True),
      ])

memory = contract["memory"]
expected_fields = [
    {"offset": 0, "type": "u32", "name": "magic", "value": 0x3155494D},
    {"offset": 4, "type": "u32", "name": "size", "value": 32},
    {"offset": 8, "type": "u32", "name": "document_offset"},
    {"offset": 12, "type": "u32", "name": "document_length", "minimum": 1, "maximum": 65536},
    {"offset": 16, "type": "u32", "name": "event_offset"},
    {"offset": 20, "type": "u32", "name": "event_capacity", "value": 4096},
    {"offset": 24, "type": "u64", "name": "reserved", "value": 0},
]
check("exact_control_header", memory["header_bytes"] == 32 and memory["count"] == 1 and
      memory["header_fields"] == expected_fields and
      memory["fixed_for_session"] == ["header_offset", "event_offset", "event_capacity"])
check("independent_header_layout_arithmetic", struct.calcsize("<IIIIIIQ") == 32 and
      struct.pack("<I", memory["header_fields"][0]["value"]) == b"MIU1")
document = contract["document"]
check("narrow_ui_limits", [document[k] for k in ("schema", "maximum_bytes", "maximum_nodes",
      "maximum_depth", "maximum_children_per_node", "maximum_string_utf8_bytes")] ==
      [1, 65536, 256, 16, 64, 4096] and set(document["supported_kinds"]) == {"vStack", "text", "button"})
event = contract["event"]
check("event_shape", event["mandatory_keys"] == ["schemaVersion", "sequence", "revision", "nodeID",
      "actionID", "event", "value"] and event["maximum_bytes"] == 4096 and
      type(event["schemaVersion"]) is int and event["schemaVersion"] == 1 and
      event["event"] == "activate" and event["value"] is None)
check("event_lexical_constraints", all(word in event["raw_validation"] for word in
      ["closed object", "duplicate decoded keys", "unknown/missing", "BOM", "UTF8/surrogates",
       "coercion/exponents/fractions/signs/leading zeros/overflow", "trailing values"]) and
      all("Positive shortest unsigned decimal UInt64" in event[key] for key in ("sequence", "revision")))
max_identifier_json = 2 * 128 * 6
fixed_event_json = len(json.dumps({**event["example"], "nodeID": "", "actionID": "",
    "sequence": (1 << 64) - 1, "revision": (1 << 64) - 1}, separators=(",", ":"), sort_keys=True).encode())
check("conservative_event_encoding_fits", max_identifier_json + fixed_event_json <= event["maximum_bytes"],
      {"conservative_bytes": max_identifier_json + fixed_event_json})
check("exact_existing_required_export_domain", contract["validation"]["required_export_error"] == {
    "operation": "validation", "native_status": 1, "machine_code": "capability_export",
    "typed_kind": "validation.requiredDefinedExport", "function": None, "offset": 0,
    "fuel_used": 0, "host_calls_used": 0,
})
check("validation_not_execution", contract["validation"]["instance"] is False and
      contract["validation"]["phases"] == ["download finish before staging", "each selection consumption",
                                             "same captured tuple before construction"])

delivery = contract["bounded_delivery"]
for key in ("accepted_events_including_running_and_unconsumed_result", "pending_frames", "claimed_frames",
            "displayed_snapshots", "worker_last_snapshots", "presentation_consumers_per_attempt"):
    check("bounded:" + key, delivery[key] == 1 and type(delivery[key]) is int)
check("host_reset_and_old_callback_scope", all(value in delivery["rebinding"] for value in
      ["fresh private MixerUIHost", "captured exchange/issuer", "rejected after rebinding", "never reconstruct"]))
check("single_attachment_before_allocation", all(value in delivery["native_attachment"] for value in
      ["one active", "before allocating a second", "Detach invalidates"]))
check("no_execution_source_ownership_backedge", "DispatchSource/external-execution-source" in delivery["ownership"])
check("fixed_consumer_actual_join", all(value in delivery["presentation"] for value in
      ["weak model", "without suspension", "before next wait", "actual Task.value before replacement"]))
check("delivery_control_refresh", all(value in delivery["refresh"] for value in
      ["Admission", "result consumption", "stop", "busy/lag"]))
check("wake_shutdown_is_explicit", "wake_finish" in delivery and all(word in delivery["wake_finish"].lower()
      for word in ["reader", "waiter", "outside", "pending", "retirement", "signal", "finish", "coordinator", "signals"]))
check("ui_failure_domain_closed", contract["terminal"]["ui_phases"] ==
      ["validation", "startup", "event", "wake", "presentation"] and
      contract["terminal"]["ui_codes"] == ["requiredExport", "startupResult", "header", "memoryRange",
      "bufferChanged", "document", "revisionRegressed", "sameRevisionMutation", "eventEncoding",
      "eventResult", "sequenceExhausted", "presentationInvariant"])
check("health_is_not_presentation_alone", all(value in contract["health"]["first_screen"] for value in
      ["bound private native wrapper", "current live generation/frame", "attached visible nonempty",
       "foreground scene", "subsequent display interval", "insufficient"]) and
      "Observation interval" in contract["health"]["qualification"])

# Verify current source observations remain the ones manually reviewed, rather than
# using text-pattern checks as proof that a VM implements the proposed contract.
for name in ("vm/src/experimental_capability_guest/mod.rs", "vm/src/capability_ffi/api.rs",
             "vm/src/capability_ffi/error.rs", "vm/src/ffi.rs",
             "experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/Failure.swift"):
    check("reviewed_source_unchanged:" + name,
          digest(read(name)) == inspection["captured_files"][name]["sha256"])
for name in ("vm/src/capability_ffi/preflight.rs", "vm/src/capability_ffi/types.rs",
             str(Path(__file__).relative_to(ROOT))):
    read(name)

clang_version = run(["clang", "--version"])
for language, source in (("c11", "header_signature.c"), ("c++17", "header_signature.cpp")):
    argv = ["clang", "-std=" + language, "-fsyntax-only", "-Wall", "-Wextra", "-Werror",
            "-I", str(ROOT / "vm/include"), str(BASE / source)]
    result = run(argv)
    check("host_header_syntax_and_declared_type:" + language, result.returncode == 0)
    read(str((BASE / source).relative_to(ROOT)))
check("candidate_unchanged_during_check", (ROOT / "contracts/guest-ui-event-v1.json").read_bytes() == contract_bytes and
      (ROOT / "vm/include/mixer_vm_guest_ui.h").read_bytes() == header_bytes)
head = run(["git", "rev-parse", "HEAD"]).stdout.strip()
tree = run(["git", "rev-parse", "HEAD^{tree}"]).stdout.strip()
run(["git", "--version"])
report = {
    "schema": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "command": ["python3", "verification/guest-ui-contract-review/check_contract.py", *sys.argv[1:]],
    "python_version": platform.python_version(), "source_revision": head, "source_tree": tree,
    "accepted_design_sha256": seal["design_sha256"], "contract_sha256": digest(contract_bytes),
    "header_sha256": digest(header_bytes), "checks": checks,
    "passed": all(item["passed"] for item in checks), "commands": commands, "captured_files": captured,
    "scope": "Original static consistency review plus host C/C++ syntax/type/layout assertions only. No guest module execution, runtime ABI implementation validation, native UI/device run, signing/publication, or GA gate pass.",
    "clarification": "Accepted design source prohibition means DispatchSource/external execution source; its required two concrete data-only wake queues remain allowed. Accepted design bytes and seal unchanged.",
}
(out / "receipt.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
failed = [item["name"] for item in checks if not item["passed"]]
print(json.dumps({"passed": report["passed"], "checks": len(checks), "failed": failed,
                  "receipt": str((out / "receipt.json").relative_to(ROOT))}))
sys.exit(0 if report["passed"] else 1)
