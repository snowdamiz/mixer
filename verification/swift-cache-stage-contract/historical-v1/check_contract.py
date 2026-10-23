#!/usr/bin/env python3
"""Check this proposed contract; optionally execute its future synthetic suite.

The artifact check is not engine evidence. --run-synthetic is fail-closed until
the named product tests exist; a filter selecting zero tests never passes.
This script has no full-reactor, device, publication or signing command.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ENV = dict(os.environ)
if Path("/opt/homebrew/opt/rustup/bin").is_dir():
    ENV["PATH"] = "/opt/homebrew/opt/rustup/bin:" + ENV.get("PATH", "")
REQUIRED_TESTS = {
    "same_abi_descriptors_and_authority",
    "decoder_opcode_and_count_build_parity",
    "parameters_and_function_inclusive_depth",
    "permanent_patch_arena_exact_requests",
    "entry_and_combined_admission_precedes_allocation",
    "zero_limits_and_exact_narrowing",
    "pins_hits_lru_and_eviction",
    "foreign_stale_nonce_and_control_ownership",
    "construction_and_operation_phase_boundaries",
    "every_constructor_allocation_ordinal",
    "every_miss_allocation_ordinal_and_capacity_fault",
    "every_work_prefix_and_cancellation_boundary",
    "deadline_inside_decode_and_reset",
    "first_cause_retains_actual_wasi_usage",
    "component_cleanup_and_first_cleanup_invariant",
    "sticky_failure_has_no_new_effects",
    "frozen_layout_allocation_work_error_snapshots",
    "external_surface_and_borrow_privacy",
}


def command(args):
    executable = shutil.which(args[0], path=ENV.get("PATH"))
    if executable is None:
        return {"argv": args, "exit_code": 127, "stdout": "", "stderr": "executable unavailable: " + args[0]}
    result = subprocess.run(args, cwd=ROOT, env=ENV, text=True, capture_output=True)
    return {
        "argv": args,
        "resolved_executable": executable,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check():
    plan = json.loads((HERE / "acceptance.json").read_text())
    require(plan["schema"] == "mixer-swift-cache-stage-contract-v1", "wrong schema")
    require(plan["status"] == "proposed_contract_implementation_pending", "proposal status changed")
    require(plan["root_freeze_required"] is True, "root freeze must be required")
    require(plan["target_execution_authorized"] is False, "target execution forbidden")
    require(plan["device_runs_authorized"] is False, "device runs forbidden")
    require(plan["fixture_contract"]["instantiation_permitted_by_this_cache_suite"] is False, "cache fixtures must not instantiate")
    require(plan["test_module"] == "experimental_swift_reactor::cache_tests", "wrong owned test module")
    require(plan["features"] == "experimental-swift-reactor,experimental-span-execution", "wrong synthetic feature set")
    tests = plan["tests"]
    require(len(tests) == len(REQUIRED_TESTS), "required test count changed")
    require({test["name"] for test in tests} == REQUIRED_TESTS, "required test inventory changed")
    require(all(test["status"] == "pending" and len(test["assertions"]) >= 3 for test in tests), "implementation claims or incomplete assertions")
    require((ROOT / plan["contract"]).is_file(), "contract file missing")
    require(len(plan["explicit_pending"]) >= 8, "pending gate inventory incomplete")
    expected = {
        "runtime_ticket_maximum": 86,
        "proof_tickets": 2,
        "cache_fixed_buffer_tickets": 3,
        "cache_header_tickets": 1,
        "resident_or_incoming_entry_tickets": 64,
        "swift_patch_capacity": 512,
        "legacy_patch_capacity": 128,
        "parameters_per_signature": 128,
        "parameters_plus_declared_locals": 256,
        "function_inclusive_controls": 512,
        "legacy_layout_changes": 0,
    }
    require(plan["fixed_inventory"] == expected, "fixed resource inventory changed")
    require(all(args[0] == "cargo" for args in plan["regression_commands"]), "unexpected regression executable")
    return plan


def source_manifest(plan):
    source = {}
    for folder in ("vm/src", "vm/tests", "vm/tools"):
        for path in sorted((ROOT / folder).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                source[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    for name in ("vm/Cargo.toml", "vm/Cargo.lock", plan["contract"]):
        path = ROOT / name
        if path.is_file():
            source[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in sorted(HERE.glob("*")):
        if path.is_file() and path.name != "proposal-receipt.json":
            source[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return source


def run_synthetic(plan, output):
    output = output.resolve()
    require(output != HERE and HERE not in output.parents, "Keep run evidence outside frozen contract artifacts")
    output.mkdir(parents=True, exist_ok=False)
    tools = [command(args) for args in (["rustc", "-Vv"], ["cargo", "-V"], [sys.executable, "--version"])]
    source = source_manifest(plan)
    source_digest = hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()
    receipt = {
        "scope": "named original same-ABI synthetic cache tests only; no instantiation",
        "target_execution_authorized": False,
        "status": "running",
        "revision": command(["git", "rev-parse", "HEAD"]),
        "dirty_state": command(["git", "status", "--short"]),
        "tools": tools,
        "source_manifest": source,
        "source_manifest_sha256": source_digest,
        "commands": [],
        "external_review_and_other_gates": "pending",
    }
    if any(item["exit_code"] != 0 for item in tools):
        receipt["status"] = "tool_unavailable"
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        return 1
    for mode in ("debug", "release"):
        for test in plan["tests"]:
            name = plan["test_module"] + "::" + test["name"]
            args = ["cargo", "test", "--locked", "--manifest-path", "vm/Cargo.toml", "--lib", "--features", plan["features"]]
            if mode == "release":
                args.append("--release")
            args.extend([name, "--", "--exact", "--nocapture"])
            result = command(args)
            combined = result["stdout"] + result["stderr"]
            # The Cargo test runner must execute this exact function once.
            result["exactly_one_passed"] = bool(
                re.search(r"^running 1 test$", combined, re.MULTILINE)
                and re.search(r"^test result: ok\. 1 passed; 0 failed; 0 ignored;", combined, re.MULTILINE)
            )
            receipt["commands"].append(result)
            after = source_manifest(plan)
            receipt["source_manifest_after"] = after
            if after != source:
                receipt["status"] = "source_changed_during_commands"
                (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
                return 1
            if result["exit_code"] != 0 or not result["exactly_one_passed"]:
                receipt["status"] = "failed_or_test_missing"
                (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
                return 1
    receipt["status"] = "named_synthetic_commands_passed_review_pending"
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-synthetic", type=Path, metavar="NEW_OUTPUT_DIRECTORY")
    args = parser.parse_args()
    plan = check()
    if args.run_synthetic:
        return run_synthetic(plan, args.run_synthetic)
    print(json.dumps({
        "contract_artifacts": "consistent",
        "required_named_tests": len(plan["tests"]),
        "implementation_evidence": "pending",
        "root_freeze": "pending",
        "target_execution_authorized": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
