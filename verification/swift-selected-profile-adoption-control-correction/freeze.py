#!/usr/bin/env python3
"""Validate and freeze this lane after its selected finite host correction."""
import importlib.util
import json
from pathlib import Path
import shutil
from datetime import datetime, timezone

OWN = Path(__file__).resolve().parent
assert not (OWN / "seal.json").exists(), "Frozen packets may not be rerun or mutated"
spec = importlib.util.spec_from_file_location("owned_evidence", OWN / "evidence.py")
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)
assert ev.manifest(ev.SOURCE) == ev.read(OWN / "source-manifest.json")
assert ev.manifest(OWN / "host") == ev.read(OWN / "host-support-manifest.json")
assert ev.manifest(OWN / "host") == ev.manifest(ev.ORIGINAL / "host")
source = ev.read(OWN / "source-manifest.json")
selection = ev.read(OWN / "inputs/selection.json")
before = (OWN / "inputs/control_tests.before.rs").read_text()
after = (ev.SOURCE / ev.TARGET).read_text()
expected = """        + super::super::execution::CONSTRUCTION_BOOTSTRAP_BYTES
        // Keep selected-owner ingress, moves, cleanup and wrapper places in
        // both floors while isolating the optional-observation increment.
        + super::super::retained_profile_loader_v1::ADOPTION_ENTRY_BYTES_V1
        + super::super::retained_profile_loader_v1::ADOPTION_MOVE_BYTES_V1
        + ADOPTION_CLEANUP_BYTES_V1
        + super::super::cache::INITIAL_PROFILE_WRAPPER_SOURCE_PLACES_V1;"""
assert after.replace(expected, "        + super::super::execution::CONSTRUCTION_BOOTSTRAP_BYTES;") == before
assert after.count(expected) == 1
ev.write(OWN / "source-delta-contract.json", {
    "schema": 1, "only_changed_source_path": ev.TARGET,
    "before": ev.identity(OWN / "inputs/control_tests.before.rs"),
    "after": ev.identity(ev.SOURCE / ev.TARGET),
    "named_floors_added_verbatim": selection["named_floors"],
    "exact_selected_replacement_reversed_to_original_bytes": True,
    "all_other_function_and_file_bytes_unchanged": True,
    "observation_historical_headroom_refusal_assertions_and_budgets_unchanged": True,
    "production_control_module_cfg_test_gate": "src/experimental_swift_reactor/control.rs:1811-1813 unchanged",
    "changed_types_layouts_limits_or_production_behavior": False})


def catalog(root, paths):
    entries = []
    for path in paths:
        d = ev.read(path)
        entry = {"receipt": ev.identity(path), "label": d["label"],
                 "original_source_tree_sha256": d.get("source_tree_sha256"),
                 "exit_code": d["exit_code"], "expectation_met": d.get("expectation_met"),
                 "executed_artifact": d.get("executed_artifact"),
                 "stdout": d.get("stdout"), "stderr": d.get("stderr"),
                 "rerun_for_corrected_tree": False}
        # These are references into verified immutable inputs, not reattributed copies.
        assert path.is_relative_to(root)
        entries.append(entry)
    return entries


old_matrix = ev.read(ev.ORIGINAL / "final-required-command-matrix.json")
candidate_paths = [ev.ORIGINAL / path for _, path in sorted(old_matrix["by_label"].items())]
independent_paths = sorted(ev.INDEPENDENT.glob("**/commands/*/receipt.json"))
assert len(candidate_paths) == 266 and len(independent_paths) == 329
old_candidate = catalog(ev.ORIGINAL, candidate_paths)
old_independent = catalog(ev.INDEPENDENT, independent_paths)
assert all(entry["expectation_met"] for entry in old_candidate)
assert sum(entry["expectation_met"] is False for entry in old_independent) == 1
ev.write(OWN / "historical-command-attribution.json", {
    "schema": 1, "corrected_source_tree_sha256": source["tree_sha256"],
    "warning": "No historical command or binary is relabeled to this corrected full-tree digest. Exact unchanged-path projection composes finite prior evidence only.",
    "candidate": {"commands": 266, "entries": old_candidate,
                  "original_matrix_omitted_full_control_module": True},
    "independent": {"commands": 329, "passed_expectations": 328, "failed_expectations": 1,
                    "entries": old_independent,
                    "preserved_failure": "I1 original Debug control36pass1fail; optimized full controls originally unrun"}})

commands = sorted((OWN / "commands").glob("*/receipt.json"))
assert len(commands) == 9
fresh = [ev.read(p) for p in commands]
assert all(d["exit_code"] == 0 and d["terminally_waited"] and d["supervisor_killed_for"] is None for d in fresh)
assert all(d["source_tree_sha256"] == source["tree_sha256"] for d in fresh)
known_runners = {ev.identity(OWN / "evidence.py")["sha256"],
                 ev.identity(OWN / "runner-history/before-output-parser-correction.py")["sha256"]}
assert all(d["runner"]["sha256"] in known_runners for d in fresh)
for d in fresh:
    for stream in ["stdout", "stderr"]:
        assert ev.identity(Path(d[stream]["path"])) == d[stream]
    assert d["elapsed_seconds"] < 60 and d["timeout_seconds"] == 55
results = {mode: ev.read(OWN / f"control-result-{mode}.json") for mode in ["debug", "optimized"]}
for mode, result in results.items():
    assert result["passed"] == 37 and result["failed"] == result["ignored"] == 0
    assert result["methods"] == ev.read(OWN / "control-methods.json")["original_names"]
    assert result["source_tree_sha256"] == source["tree_sha256"]
    output = next(Path(d["stdout"]["path"]).read_text() for d in fresh if d["label"] == f"full-control-{mode}")
    assert "old_floor=366432 new_floor=366896 added=464" in output
ev.write(OWN / "corrected-validation-matrix.json", {
    "schema": 1, "source_tree_sha256": source["tree_sha256"],
    "fresh_required_commands": 6, "fresh_context_commands": 3,
    "by_label": {d["label"]: str(p.relative_to(OWN)) for d, p in zip(fresh, commands)},
    "original_control_methods_each_mode": 37, "test_executions": 74,
    "failed_tests": 0, "ignored_or_skipped_tests": 0,
    "modes": ["Debug", "optimized"], "full_original_control_module_required": True,
    "historical_matrix_omission_corrected_explicitly": True,
    "other428_methods_filtered_out_per_suite": "outside selected test-only delta; finite prior path-bound evidence retained, no new full-suite claim",
    "historical_command_attribution": "historical-command-attribution.json",
    "original_candidate_and_independent_commands_replayed": False})
ev.write(OWN / "orchestration-observations.json", {
    "schema": 1, "entry": "python3 evidence.py prepare; terminal exit0; copied/verified exact144source+11support and both original closed seals",
    "subcommands_in_order": ["tools", "compile debug", "suite debug", "summarize debug", "compile optimized", "suite optimized"],
    "suite_debug_outer_exit": 1, "suite_debug_test_child_exit": 0,
    "first_parser_error_preserved": "runner-failures/001-debug-output-parser.json",
    "debug_child_replayed_after_parser_error": False,
    "old_runner_bytes_preserved": "runner-history/before-output-parser-correction.py",
    "all_other_subcommands_terminal_exit": 0,
    "host_command_outputs": "commands/*/{stdout,stderr,receipt.json}",
    "read_only_preparation_filename_miss_preserved": "preparation/inspection-failure.json"})

# The owned direct compiler/test children are all terminal. Remove only this lane's scratch.
assert ev.WORK.is_dir() and ev.WORK.parent == OWN
scratch = ev.inventory(ev.WORK)
ev.write(OWN / "owned-scratch-removal.json", {"schema": 1, "before_removal": scratch,
          "terminal_direct_children": 9, "removed_only": str(ev.WORK),
          "File_drop_or_exit_or_unlink_proves_close_success": False})
shutil.rmtree(ev.WORK)
ev.write(OWN / "inputs/frozen-custody-after.json", ev.verify_frozen())
limits = ["Independent corrected-delta review and root scoped acceptance pending",
          "Original266 candidate and329 independent command receipts retain their actual original source digests; no full unrelated replay",
          "Existing201 layout identities/envelopes retained, not newly measured by this test-only correction",
          "Original nested Cargo external_surface_and_borrow_privacy wrapper remains unrun; bounded compiler-source controls are separately attributed",
          "Raw APFS cwd/executable path and raw nonUTF8 argv0 full-entry cases remain unrun",
          "Native/device/simulator/emulator/runtime/UI/capture/process inventories paused and unused",
          "No loader operational storage admission, File close-success, authenticated-package or hostile-launcher guarantee",
          "Exporter/context/canonical integration, FieldLog immutable package qualification, OTA/store/customer/operations and GA pending"]
ev.write(OWN / "receipt.json", {"schema": 1, "at": datetime.now(timezone.utc).isoformat(),
    "status": "I1-test-expectation-correction-host-pass-awaiting-independent-delta-review-and-root-acceptance",
    "selection": ev.identity(ev.SELECTION), "source_tree_sha256": source["tree_sha256"],
    "source_members": 144, "only_source_delta": ev.TARGET,
    "unchanged_source_members": 143, "unchanged_host_support_members": 11,
    "full_original_control_methods_each_mode": 37, "passed_tests": 74,
    "failed_tests": 0, "ignored_or_skipped_tests": 0,
    "fresh_commands": 9, "all_fresh_child_commands_passed": True,
    "fresh_command_timeout_seconds": 55, "all_direct_children_terminally_waited": True,
    "retained_runner_output_parser_failures": 1, "retained_read_only_inspection_failures": 1,
    "original_I1_failure_retained": True, "historical_candidate_required_commands": 266,
    "historical_independent_commands": 329, "historical_source_digests_preserved": True,
    "original201_layout_identities_preserved": True, "new_layout_measurements": False,
    "original_assertions_limits_and_budgets_preserved": True,
    "observed_unit_observation_old_floor": 366432, "observed_unit_observation_required_floor": 366896,
    "observed_observation_increment": 464, "four_existing_named_unit_floors_total": 89720,
    "existing_production_foundation": 366312, "production_remeasured_here": False,
    "original_frozen_packets_mutated_or_scripts_executed": False,
    "canonical_or_native_or_operational_or_GA_accepted": False,
    "cleanup": {"owned_scratch_removed": not ev.WORK.exists(), "other_projects_touched": False,
                "File_drop_or_process_exit_is_close_success": False,
                "native_UI_capture_or_process_inventory_used": False}, "limitations": limits})
(OWN / "README.md").write_text("""# Selected-profile adoption I1 control correction

This separate packet changes only the expected `non_observation_shapes` sum and
its explanatory comment in `control_tests.rs`. It adds the four existing named
entry, move, cleanup and initial-wrapper floors. The production formula, all
observation/headroom/refusal assertions and budgets, all other143 source files,
and all11 host support files retain the original candidate bytes.

Fresh aarch64 macOS Debug and optimized builds each run all37 original control
methods:74 passed,0 failed,0 ignored or skipped. The observation boundary prints
historical floor366432, required floor366896 and unchanged increment464. The
Debug child passed before an orchestration-only multiline-output parser error;
that error and the original runner bytes are retained. Reprocessing its captured
stdout avoided an unnecessary test replay. Both compiles retain two preexisting
Copy-drop warnings from unchanged `control_operations_tests.rs`.

The original candidate2941-member packet and independent1834-member packet are
immutable inputs. Both closed seals were reverified before copying and after
cleanup. The independent original Debug36pass1fail output is preserved verbatim.
The original266-command required matrix omitted the control module; it was not
complete. The corrected validation matrix explicitly requires all37 controls in
both modes. This correction adds9 bounded child commands, including3 tool/source
context commands. Every direct child was terminally waited; owned scratch was
removed. No File close-success is inferred from drop, exit or removal.

`historical-command-attribution.json` references all266 candidate and329
independent receipts with their exact actual original source digests. None are
relabeled to this corrected full-tree digest. `unchanged-source-paths.json`
records the exact143 unchanged paths supporting finite production evidence
composition. Four original201-record layout reports retain their original bytes
and source attribution; this test-only correction does not claim new layout or
performance measurements. See the receipt for remaining unrun scopes.

Independent corrected-delta review and root scoped acceptance remain pending.
There is no canonical/exporter/context/native/operational/GA acceptance. Native
runtime, UI, capture and process inventories remain paused. Never rerun scripts
inside this frozen packet; an independent reviewer must use separately owned
copies. No original frozen orchestration was imported or executed.
""")
# Suppress import cache custody noise: this is only our own newly created cache.
cache = OWN / "__pycache__"
if cache.exists():
    shutil.rmtree(cache)
members = ev.inventory(OWN)
assert not ev.WORK.exists()
seal = {"schema": 1, "scope": "I1 named-floor test expectation correction and finite macOS host control evidence",
        "member_count": len(members), "member_bytes": sum(m["bytes"] for m in members), "members": members}
ev.write(OWN / "seal.json", seal)
actual = [m for m in ev.inventory(OWN) if m["path"] != "seal.json"]
assert actual == seal["members"]
print(json.dumps({"released": True, "source_tree_sha256": source["tree_sha256"],
                  "seal": ev.identity(OWN / "seal.json"), "members": len(members),
                  "member_bytes": seal["member_bytes"], "control_passed": 74,
                  "independent_delta_review": "pending"}))
