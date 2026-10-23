#!/usr/bin/env python3
"""Check proposal artifacts only. This program never builds or runs the engine."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path


EXPECTED_NAMES = (
    "authority_and_static_parts", "fixed_arenas_and_initialization_limits",
    "retained_initializers_and_ordered_segments", "initialize_once_and_stateful_calls",
    "recursive_frame_pins_and_partial_enter", "indirect_calls_full_structural_signature",
    "all_admitted_operations_and_numeric_capacity", "actual_wasi_all_descriptors",
    "host_counter_entry_and_failure_order", "lifetime_cumulative_budgets",
    "independent_zero_limits_and_first_exhaustion", "memory_growth_overlap_and_commit",
    "every_allocation_ordinal", "requested_capacity_and_ticket_atomicity",
    "every_work_prefix_and_cancellation_ordinal", "deadline_inside_each_execution_loop",
    "first_failure_actual_wasi_observations", "cleanup_tails_phases_and_no_effects",
    "frozen_layout_allocation_work_error_parity", "downstream_privacy_and_closed_surface",
)
EXPECTED_LIMITS = {
    "tickets": 86, "frames": 64, "values": 16384, "controls": 4096,
    "memory_pages": 768, "state_bytes": 134217728, "combined_bytes": 268435456,
    "fuel": 100000000, "execution_work": 1000000000, "host_calls": 32768,
    "deadline_ms": 30000, "memory_overlap_767_768": 100597760,
}
FALSE_FIELDS = (
    "implementation_authorized", "implementation_accepted", "target_execution_authorized",
    "target_instantiated", "target_initialized", "target_invoked", "physical_device_runs",
    "ga_gate_state_changes", "cache_implementation_accepted", "observed_fuel_control_delta_accepted",
)
HELPERS = (
    "instruction_with_wasi", "charge_fuel_with_wasi", "checked_usage",
    "work_with_wasi", "drop_reserved_with_wasi", "finish_owned_cleanup",
)
ANCHORS = (
    "45852204fbcced037d8e530876b619d9ed1c2ce1", "ExecutionParts", "SwiftFrame",
    "same execution header", "same header ticket", "exact previous bound",
    "one-shot", "86 authoritative tickets", "100,597,760", "first cause",
    "53,777,114", "79,832", "188,428,924", "54,827,522", "46,713/46,713",
    "all 11", "no engine-run option", "foreign/missing", "all are pending now",
    "root approval of one exact bounded runner", "independent review is pending",
)


def check(manifest: dict, document: str) -> list[str]:
    errors = []

    def need(condition: bool, label: str) -> None:
        if not condition:
            errors.append(label)

    need(manifest.get("schema") == "mixer.swift-executor-stage-contract.v1", "schema")
    need(manifest.get("artifact_only") is True, "artifact-only boundary")
    for field in FALSE_FIELDS:
        need(manifest.get(field) is False, field + " must remain false")
    need(manifest.get("selected_agent") == {
        "model": "gpt-6.1-sol", "reasoning_effort": "xhigh", "fresh_context": True,
    }, "bounded agent configuration")
    need(manifest.get("limits") == EXPECTED_LIMITS, "frozen limits")
    need(manifest.get("document", {}).get("sha256") == hashlib.sha256(document.encode()).hexdigest(),
         "document digest")
    expected_sections = [f"C{i:02}" for i in range(1, 10)]
    need(manifest.get("required_contract_sections") == expected_sections, "contract section registry")
    for section in expected_sections:
        need(document.count("<!-- " + section + ":") == 1, "unique section " + section)
    # Text checks are artifact completeness checks, never semantic or OTA authority.
    normalized = " ".join(document.lower().replace("**", "").split())
    for anchor in ANCHORS + HELPERS:
        need(anchor.lower() in normalized, "document anchor: " + anchor)
    need(manifest.get("required_observed_helpers") == list(HELPERS), "observed helper registry")
    cleanup = manifest.get("cleanup", {})
    for field in ("prepare_or_enlarge_allowed", "admission_allowed", "work_allowed",
                  "services_allowed", "cancel_deadline_checks_allowed"):
        need(cleanup.get(field) is False, "cleanup " + field)
    for field in ("same_header_ticket", "first_failure_immutable", "intact_rejection",
                  "tail_owns_original_control"):
        need(cleanup.get(field) is True, "cleanup " + field)
    need(cleanup.get("completion_returns") == "unit", "cleanup completion")
    need(cleanup.get("foundation_counts") == {
        "SwiftRunFailure": 4, "SwiftRunUsage": 4, "ReservationTicket": 6, "WasiUsage": 2,
    }, "foundation final tail counts")
    layout = manifest.get("measured_layout_map", [])
    need(len(layout) == 8, "pending layout phase inventory")
    need(len({entry.get("name") for entry in layout}) == 8, "unique layout phase names")
    for entry in layout:
        need(entry.get("status") == "pending", "layout remains pending")
        need(bool(entry.get("required_types_and_scope")), "named layout scope")
        for field in ("target", "toolchain", "measurements", "simultaneous_counts"):
            need(entry.get(field) is None, "no invented layout " + field)
    tests = manifest.get("required_synthetic_tests", [])
    expected = ["experimental_swift_reactor::execution_tests::swift_executor_" + n for n in EXPECTED_NAMES]
    need([entry.get("function") for entry in tests] == expected, "exact 20 synthetic functions")
    seen_assertions = set()
    covered_sections = set()
    for entry in tests:
        need(entry.get("status") == "pending", "implementation test pending")
        need(entry.get("profiles") == ["debug", "release"], "both test profiles")
        assertions = entry.get("assertions", [])
        need(len(assertions) >= 3, "required assertion matrix")
        for assertion in assertions:
            ident = assertion.get("id")
            need(bool(ident) and ident not in seen_assertions, "unique assertion identifier")
            seen_assertions.add(ident)
            need(len(assertion.get("required", "")) >= 40, "concrete assertion")
        sections = entry.get("contract_sections", [])
        need(bool(sections) and set(sections) <= set(expected_sections), "known coverage section")
        covered_sections.update(sections)
    need(covered_sections == set(expected_sections), "all contract sections covered")
    need("zero tests is failure" in manifest.get("required_test_selection", ""), "nonempty exact tests")
    need(manifest.get("future_command_status", "").startswith("pending;"), "engine commands pending")
    template = manifest.get("future_synthetic_command_template", [])
    need("--exact" in template and "{function}" in template and "[--release]" in template,
         "exact future synthetic command")
    commands = manifest.get("regression_commands", [])
    need(len(commands) == 16, "full frozen regression matrix")
    for entry in commands:
        need(entry.get("status") == "pending" and isinstance(entry.get("argv"), list),
             "regression pending command")
    need(len(manifest.get("prerequisites", [])) >= 5, "prerequisites")
    need(len(manifest.get("explicit_pending", [])) >= 7, "external/implementation pending")
    return errors


def mutations(manifest: dict, document: str) -> list[dict]:
    cases = []

    def bad(name: str, change) -> None:
        altered = copy.deepcopy(manifest)
        change(altered)
        result = check(altered, document)
        if not result:
            raise AssertionError("mutation escaped: " + name)
        cases.append({"mutation": name, "rejected": True, "errors": result})

    bad("authorizes exact target", lambda m: m.update(target_execution_authorized=True))
    bad("claims executor acceptance", lambda m: m.update(implementation_accepted=True))
    bad("claims cache acceptance", lambda m: m.update(cache_implementation_accepted=True))
    bad("omits observed fuel prerequisite", lambda m: m["required_observed_helpers"].pop())
    bad("raises combined cap", lambda m: m["limits"].update(combined_bytes=536870912))
    bad("cleanup requires admission", lambda m: m["cleanup"].update(admission_allowed=True))
    bad("cleanup changes ticket tail", lambda m: m["cleanup"].update(same_header_ticket=False))
    bad("invents measured layout", lambda m: m["measured_layout_map"][0].update(measurements={"size": 520}))
    bad("drops a named test", lambda m: m["required_synthetic_tests"].pop())
    bad("drops release coverage", lambda m: m["required_synthetic_tests"][0].update(profiles=["debug"]))
    bad("marks unrun test passed", lambda m: m["required_synthetic_tests"][0].update(status="passed"))
    bad("duplicates assertion identity", lambda m: m["required_synthetic_tests"][0]["assertions"][1].update(
        id=m["required_synthetic_tests"][0]["assertions"][0]["id"]))
    bad("removes assertion matrix", lambda m: m["required_synthetic_tests"][0].update(assertions=[]))
    bad("reports device run", lambda m: m.update(physical_device_runs=True))
    altered_doc = document.replace("<!-- C08:", "<!-- REMOVED:")
    altered_manifest = copy.deepcopy(manifest)
    altered_manifest["document"]["sha256"] = hashlib.sha256(altered_doc.encode()).hexdigest()
    result = check(altered_manifest, altered_doc)
    if not result:
        raise AssertionError("missing cleanup section mutation escaped")
    cases.append({"mutation": "removes cleanup section with valid digest", "rejected": True, "errors": result})
    return cases


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mutation-checks", action="store_true")
    options = parser.parse_args()
    here = Path(__file__).resolve().parent
    root = here.parents[1]
    manifest = json.loads((here / "acceptance.json").read_text())
    document = (root / manifest["document"]["path"]).read_text()
    errors = check(manifest, document)
    result = {
        "scope": "artifact-only; no engine build, validation, instantiation or invocation",
        "contract_checks_passed": not errors,
        "synthetic_test_functions_pending": len(EXPECTED_NAMES),
        "implementation_tests_executed": 0,
        "target_execution_authorized": False,
        "errors": errors,
    }
    if options.mutation_checks and not errors:
        result["mutation_checks"] = mutations(manifest, document)
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
