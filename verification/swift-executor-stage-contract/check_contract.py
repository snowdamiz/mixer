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
EXPECTED_ASSERTION_COUNTS = (3, 3, 4, 3, 4, 3, 4, 4, 4, 3, 4, 4, 4, 3, 4, 4, 4, 5, 4, 4)
EXPECTED_LIMITS = {
    "tickets": 86, "frames": 64, "values": 16384, "controls": 4096,
    "memory_pages": 768, "state_bytes": 134217728, "combined_bytes": 268435456,
    "fuel": 100000000, "execution_work": 1000000000, "host_calls": 32768,
    "deadline_ms": 30000, "memory_overlap_767_768": 100597760,
}
FALSE_FIELDS = (
    "implementation_authorized", "implementation_accepted", "target_execution_authorized",
    "target_instantiated", "target_initialized", "target_invoked", "physical_device_runs",
    "ga_gate_state_changes", "cache_implementation_accepted",
)
ORIGINAL_RECEIPT = "62f825ab418b207c057f384b2c0afdbfabb3fee50e0db75e945f0d3448f092de"
CONTROL_OVERLAY = "55e0e89c5da57347f02fd13dfb97296c19c3ace7d94fc11109dd224c9046b79f"
CACHE_FREEZE = "7214cb876a18df7ddedc364acc52f57cc04b2b8916968ef360ee4a0eb7f28089"
BASELINE = "39199ae5475de5d03926807ce60add5dcb0741c2"
OBSERVATION_BASELINE = "3a1bb5a455973bde841a4b57993277fa2c054569"
OBSERVATION_ASSIGNMENT = {
    "nested_control_parameters": 5, "retained_caller_observations": 1,
    "counts_every_copy_binding": True, "last_use_elision_allowed": False,
    "other_phase_padding_allowed": False, "embedded_payload_reuse_allowed": False,
    "disjoint_execution_envelope_until_final_header": True,
    "component_outcomes_end_before_next_phase": True,
    "final_field_shape_map_status": "pending implementation blocker",
}
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
    "root approval of one exact bounded runner", "independently accepted",
    "five simultaneously active", "one retained caller observation",
    "no last-use/compiler elision", "disjoint execution permanent envelope until final header",
    "implementation blocker", "six optional shapes", "16,504", "+464-byte",
    "sufficient-three-option proposal", ORIGINAL_RECEIPT, CONTROL_OVERLAY, CACHE_FREEZE,
)


def check(manifest: dict, document: str) -> list[str]:
    errors = []

    def need(condition: bool, label: str) -> None:
        if not condition:
            errors.append(label)

    need(manifest.get("schema") == "mixer.swift-executor-stage-contract.v2", "schema")
    need(manifest.get("proposal_revision") == 2, "proposal revision")
    need(manifest.get("baseline_revision") == BASELINE, "accepted correction baseline")
    need(manifest.get("artifact_only") is True, "artifact-only boundary")
    for field in FALSE_FIELDS:
        need(manifest.get(field) is False, field + " must remain false")
    for field in ("observed_fuel_control_delta_accepted", "foundation_observation_correction_accepted"):
        need(manifest.get(field) is True, field + " separately accepted prerequisite")
    need(manifest.get("cache_contract_revision") == 3, "accepted cache contract v3")
    need(manifest.get("historical_v1") == {
        "preservation": "verification/swift-executor-stage-contract/historical-v1/preservation.json",
        "original_receipt_sha256": ORIGINAL_RECEIPT, "exact_bytes_preserved": True,
    }, "exact v1 history boundary")
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
        "SwiftRunFailure": 4, "SwiftRunUsage": 4, "ReservationTicket": 6, "Option<WasiUsage>": 6,
    }, "foundation final tail counts")
    need(cleanup.get("observation_assignment") == OBSERVATION_ASSIGNMENT,
         "five nested parameters plus one caller; disjoint final map pending")
    foundation = manifest.get("accepted_foundation", {})
    for field, value in {
        "acceptance": "verification/swift-observation-accounting/acceptance.json",
        "independent_bindings": 522, "producer_bindings": 859, "base_revision": OBSERVATION_BASELINE,
        "control_overlay_sha256": CONTROL_OVERLAY, "measured_host_target": "aarch64-apple-darwin",
        "raw_wasi_usage_bytes": 104, "optional_wasi_usage_bytes": 112, "alignment": 8,
        "optional_observation_shapes": 6, "observation_bytes": 672,
        "old_observation_bytes": 208, "foundation_delta_bytes": 464, "foundation_bytes": 16504,
    }.items():
        need(foundation.get(field) == value, "accepted host foundation: " + field)
    cache = manifest.get("accepted_cache_contract", {})
    need(cache.get("revision") == 3 and cache.get("freeze_sha256") == CACHE_FREEZE,
         "source-bound cache v3 freeze")
    need(cache.get("implementation_accepted") is False, "cache implementation remains unaccepted")
    need("no dependency acceptance" in cache.get("reported_18_per_mode_prefreeze", ""),
         "pre-freeze tests are not acceptance")
    supersession = manifest.get("review_supersession", {})
    need(supersession.get("sufficient_three_option_proposal_superseded") is True,
         "superseding six-option review")
    need(supersession.get("minimum_successful_wasi_refund_optional_shapes") == 3,
         "three remains component success minimum only")
    need(supersession.get("superseding_addendum") ==
         "verification/swift-executor-contract-review/foundation-tail-addendum.md", "review addendum")
    need(supersession.get("chain_map") ==
         "verification/swift-executor-contract-review/observation-chain-map.json", "observation chain map")
    sequence = manifest.get("implementation_sequence", {})
    need("measured layout model" in sequence.get("original_v1_wording", ""),
         "explicit original sequencing wording")
    for field in ("bounded_type_layout_prerequisite_requires_cache_acceptance",
                  "bounded_type_layout_prerequisite_requires_separate_assignment"):
        need(sequence.get(field) is True, "type/layout prerequisite " + field)
    for field in ("current_implementation_assignment", "public_route_authorized"):
        need(sequence.get(field) is False, "no new assignment/route: " + field)
    need(sequence.get("actual_selected_field_lifetime_layout_evidence") ==
         "pending implementation acceptance blocker", "chosen field/lifetime/layout acceptance blocker")
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
    for index, entry in enumerate(tests):
        need(entry.get("status") == "pending", "implementation test pending")
        need(entry.get("profiles") == ["debug", "release"], "both test profiles")
        assertions = entry.get("assertions", [])
        need(index < len(EXPECTED_ASSERTION_COUNTS) and
             len(assertions) == EXPECTED_ASSERTION_COUNTS[index], "exact required assertion matrix")
        for assertion in assertions:
            ident = assertion.get("id")
            need(bool(ident) and ident not in seen_assertions, "unique assertion identifier")
            seen_assertions.add(ident)
            need(len(assertion.get("required", "")) >= 40, "concrete assertion")
        sections = entry.get("contract_sections", [])
        need(bool(sections) and set(sections) <= set(expected_sections), "known coverage section")
        covered_sections.update(sections)
    need(covered_sections == set(expected_sections), "all contract sections covered")
    need(len(seen_assertions) == 75, "all 75 named assertions retained")
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
    bad("drops final observation accounting assertion", lambda m: m["required_synthetic_tests"][17]["assertions"].pop())
    bad("reports device run", lambda m: m.update(physical_device_runs=True))
    bad("reverts two raw observations", lambda m: m["cleanup"].update(foundation_counts={
        "SwiftRunFailure": 4, "SwiftRunUsage": 4, "ReservationTicket": 6, "WasiUsage": 2}))
    bad("uses superseded three optional shapes", lambda m: m["cleanup"]["foundation_counts"].update({"Option<WasiUsage>": 3}))
    bad("uses two optional shapes", lambda m: m["cleanup"]["foundation_counts"].update({"Option<WasiUsage>": 2}))
    bad("uses five optional shapes", lambda m: m["cleanup"]["foundation_counts"].update({"Option<WasiUsage>": 5}))
    bad("uses six raw rather than optional shapes", lambda m: m["cleanup"].update(foundation_counts={
        "SwiftRunFailure": 4, "SwiftRunUsage": 4, "ReservationTicket": 6, "WasiUsage": 6}))
    bad("omits fifth nested parameter", lambda m: m["cleanup"]["observation_assignment"].update(nested_control_parameters=4))
    bad("keeps second caller copy without envelope", lambda m: m["cleanup"]["observation_assignment"].update(retained_caller_observations=2))
    bad("relies on last-use elision", lambda m: m["cleanup"]["observation_assignment"].update(last_use_elision_allowed=True))
    bad("borrows another phase padding", lambda m: m["cleanup"]["observation_assignment"].update(other_phase_padding_allowed=True))
    bad("reuses embedded observation payload", lambda m: m["cleanup"]["observation_assignment"].update(embedded_payload_reuse_allowed=True))
    bad("drops disjoint execution envelope early", lambda m: m["cleanup"]["observation_assignment"].update(disjoint_execution_envelope_until_final_header=False))
    bad("overlaps component outcome phases", lambda m: m["cleanup"]["observation_assignment"].update(component_outcomes_end_before_next_phase=False))
    bad("claims final chosen field map verified", lambda m: m["cleanup"]["observation_assignment"].update(final_field_shape_map_status="verified"))
    bad("wrong accepted control overlay", lambda m: m["accepted_foundation"].update(control_overlay_sha256="0" * 64))
    bad("wrong optional shape width", lambda m: m["accepted_foundation"].update(optional_wasi_usage_bytes=104))
    bad("wrong accepted cache freeze", lambda m: m["accepted_cache_contract"].update(freeze_sha256="0" * 64))
    bad("claims prefreeze cache acceptance", lambda m: m["accepted_cache_contract"].update(implementation_accepted=True))
    bad("forgets observed fuel acceptance", lambda m: m.update(observed_fuel_control_delta_accepted=False))
    bad("wrong preserved v1 receipt", lambda m: m["historical_v1"].update(original_receipt_sha256="0" * 64))
    bad("revives superseded review", lambda m: m["review_supersession"].update(sufficient_three_option_proposal_superseded=False))
    bad("forgets accepted six-option prerequisite", lambda m: m.update(foundation_observation_correction_accepted=False))
    bad("assigns unapproved type/layout implementation", lambda m: m["implementation_sequence"].update(current_implementation_assignment=True))
    altered_doc = document.replace("<!-- C08:", "<!-- REMOVED:")
    altered_manifest = copy.deepcopy(manifest)
    altered_manifest["document"]["sha256"] = hashlib.sha256(altered_doc.encode()).hexdigest()
    result = check(altered_manifest, altered_doc)
    if not result:
        raise AssertionError("missing cleanup section mutation escaped")
    cases.append({"mutation": "removes cleanup section with valid digest", "rejected": True, "errors": result})
    return cases


def check_preserved(here: Path) -> tuple[int, list[str]]:
    root = here.parents[1]
    preservation = json.loads((here / "historical-v1/preservation.json").read_text())
    errors = []
    if preservation.get("original_receipt_sha256") != ORIGINAL_RECEIPT:
        errors.append("wrong v1 preservation receipt")
    entries = preservation.get("files", [])
    if len(entries) != 24 or len({item["preserved_path"] for item in entries}) != 24:
        errors.append("v1 preservation must bind all 24 original artifacts")
    for item in entries:
        data = (root / item["preserved_path"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != item["sha256"] or len(data) != item["bytes"]:
            errors.append("changed preserved artifact: " + item["preserved_path"])
    receipt = here / "historical-v1/verification/swift-executor-stage-contract/receipt.json"
    if hashlib.sha256(receipt.read_bytes()).hexdigest() != ORIGINAL_RECEIPT:
        errors.append("original producer receipt bytes changed")
    return len(entries), errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mutation-checks", action="store_true")
    options = parser.parse_args()
    here = Path(__file__).resolve().parent
    root = here.parents[1]
    manifest = json.loads((here / "acceptance.json").read_text())
    document = (root / manifest["document"]["path"]).read_text()
    errors = check(manifest, document)
    preserved_count, preservation_errors = check_preserved(here)
    errors.extend(preservation_errors)
    result = {
        "scope": "artifact-only; no engine build, validation, instantiation or invocation",
        "contract_checks_passed": not errors,
        "synthetic_test_functions_pending": len(EXPECTED_NAMES),
        "implementation_tests_executed": 0,
        "original_v1_artifacts_preserved": preserved_count,
        "target_execution_authorized": False,
        "errors": errors,
    }
    if options.mutation_checks and not errors:
        result["mutation_checks"] = mutations(manifest, document)
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
