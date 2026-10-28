#!/usr/bin/env python3
"""Prepare the selected alternate diagnostic capture; never load its controller."""
from pathlib import Path
import copy
import datetime
import difflib
import hashlib
import json
import time

D = Path(__file__).resolve().parent
R = D.parents[1]
OLD = R / "verification/swift-root-bound-dispatch-physical-capture-v1"
OLD_BASE = R / "verification/swift-root-bound-dispatch-physical-plan/capture-plan.json"
OLD_BASE_SHA = "bed9476b169810452ac0932605784125365f57c897d1e3bf74cd9eaa6ebb8184"
OLD_PLAN_SHA = "3534a9d4bc5428335b3dec4cc295f0b55b1a8ea1c778e265fabdcb9fefb6743e"
OLD_ARGV_SHA = "4022ae1057439fe5ae31d18675a884b2dc3e56f317a8ddced08bfb163a410aaa"
OLD_CONTROLLER_SHA = "1c8036e0dcd5e173c2e379ee6e711c06644638f6fb2caad312c4d41f29ddd98f"
OLD_SEAL_SHA = "550f6e81fd3abcd5ad74999d953638d99f426f710d48369792922801f753430d"
PYTHON = "/opt/homebrew/Cellar/python@3.14/3.14.8/Frameworks/Python.framework/Versions/3.14/bin/python3.14"
RELEASE = R / "verification/swift-semantic-adapter-root-review/dispatch-retained-physical-capture-release.json"
BUILD = D / "command"
BASE = D / "base-capture-plan.json"
ASSESSMENT = R / "verification/swift-physical-source-reachability"
START = time.monotonic()


def check(value, message):
    if not value:
        raise RuntimeError(message)


def deadline():
    check(time.monotonic() - START < 55, "preparation 55-second wall ceiling")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def row(path, base=R):
    deadline()
    check(path.is_file() and not path.is_symlink(), "regular input required: " + str(path))
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while raw := stream.read(262144):
            deadline()
            h.update(raw)
            size += len(raw)
    return {"path": str(path.relative_to(base)) if path.is_relative_to(base) else str(path),
            "bytes": size, "sha256": h.hexdigest()}


def read_json(path, expected=None):
    check(path.stat().st_size <= 1048576, "metadata size bound")
    if expected is not None:
        check(row(path)["sha256"] == expected, "pinned metadata changed: " + str(path))
    return json.loads(path.read_bytes())


def put(name, value):
    raw = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    check(len(raw) <= 1048576, "owned metadata size bound")
    with (D / name).open("xb") as stream:
        stream.write(raw)


def text(name, value):
    with (D / name).open("x") as stream:
        stream.write(value)


def once(value, old, new):
    check(value.count(old) == 1, "controller replacement must be unique: " + old)
    return value.replace(old, new, 1)


def patch(name, before, after, old_name, new_name):
    delta = "".join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                      fromfile=old_name, tofile=new_name))
    text(name, delta)


def main():
    check(not (D / "seal.json").exists() and not (D / "runtime").exists() and not BUILD.exists(), "fresh owned preparation required")
    check(not RELEASE.exists(), "fresh independent review/release is still required")
    old_base = read_json(OLD_BASE, OLD_BASE_SHA)
    old_plan = read_json(OLD / "plan.json", OLD_PLAN_SHA)
    old_seal = read_json(OLD / "seal.json", OLD_SEAL_SHA)
    check(sha(canonical(old_seal["members"])) == old_seal["tree_sha256"], "original packet tree")
    prior_paths = [OLD_BASE, OLD / "seal.json"]
    for member in old_seal["members"]:
        path = OLD / member["path"]
        check(row(path, OLD) == member, "original packet member changed")
        prior_paths.append(path)
    old_controller = OLD / "run-capture.py"
    check(row(old_controller)["sha256"] == OLD_CONTROLLER_SHA, "proven controller identity")
    check(sha(canonical(old_base["argv"])) == OLD_ARGV_SHA, "original argv identity")
    check(old_base["bounds"] == old_plan["bounds"], "proven bounds differ")

    old_inputs = read_json(OLD / "input-manifest.json")
    input_paths = []
    for item in old_inputs["inputs"]:
        path = Path(item["path"])
        path = path if path.is_absolute() else R / path
        check(row(path) == item, "prior approved input changed: " + str(path))
        input_paths.append(path)
    source_manifest_path = R / old_base["source_manifest"]["path"]
    source_manifest = read_json(source_manifest_path, old_base["source_manifest"]["sha256"])
    check(len(source_manifest["members"]) == source_manifest["member_count"] == 146, "source146 count")
    check(sha(canonical(source_manifest["members"])) == old_base["source_tree_sha256"], "source146 aggregate tree")
    source = Path(old_base["source_directory"])
    for member in source_manifest["members"]:
        check(row(source / member["path"], source) == member, "source146 changed")
    check(sorted(str(p.relative_to(source)) for p in source.rglob("*") if p.is_file()) ==
          sorted(member["path"] for member in source_manifest["members"]), "exact source roster changed")
    tools = read_json(R / old_base["toolchain_manifest"]["path"], old_base["toolchain_manifest"]["sha256"])
    check(len(tools["members"]) == 67 and sha(canonical(tools["members"])) == tools["tree_sha256"], "approved tool manifest")

    assessment_paths = sorted(p for p in ASSESSMENT.iterdir() if p.is_file())
    assessment_before = [row(path) for path in assessment_paths]
    check(row(ASSESSMENT / "inspection.json")["sha256"] == "1e00d6dd45569a7bdb568028293c23442043bb27d4177a0e7a9ca1334198bf72", "source assessment changed")
    check(row(ASSESSMENT / "findings.md")["sha256"] == "b9fd2c05562ea79a637c3e6fd585de9787f4ec66d2a25261cbf24202166d2a1f", "source findings changed")
    extra_paths = [R / "verification/swift-physical-map-independent/review-result.json",
                   R / "verification/swift-semantic-adapter-root-review/dispatch-physical-mapping-selection.json"]
    input_paths = list(dict.fromkeys(input_paths + prior_paths + assessment_paths + extra_paths))
    before = [row(path) for path in input_paths]
    check(len(before) <= 384 and sum(item["bytes"] for item in before) <= 4294967296, "approved runtime input bounds")

    base = copy.deepcopy(old_base)
    argv = old_base["argv"][:]
    emit_index = len(argv) - 1
    check(argv[emit_index].startswith("--emit=llvm-ir="), "expected final emit option")
    argv[emit_index] = "--emit=llvm-ir=" + str(BUILD / "dispatch.ll") + ",asm=" + str(BUILD / "dispatch.s")
    argv[emit_index:emit_index] = ["-C", "link-dead-code=yes"]
    argv_sha = sha(canonical(argv))
    base.update(argv=argv, argv_sha256_canonical_JSON=argv_sha,
                approach="alternate-diagnostic-retained-physical-region-evidence",
                status="SOURCE_ONLY_ALT_DIAGNOSTIC_CAPTURE_PROPOSED_NOT_RELEASED",
                owned_output_directory=str(BUILD), alternate_diagnostic_configuration_only=True,
                link_dead_code=True, original_capture_qualified=False, runtime_admission_accepted=False,
                frontier_complete=False, complete_capacity_accepted=False,
                original_capture_plan=row(OLD_BASE), original_argv_sha256=OLD_ARGV_SHA,
                source_reachability_assessment=row(ASSESSMENT / "inspection.json"))
    base["environment"]["TMPDIR"] = str(BUILD / "tmp")
    base["inspection_only_settings"] = old_base["inspection_only_settings"] + ["link-dead-code=yes (alternate diagnostic configuration only)"]
    base["root_release_required"] = {"path": str(RELEASE.relative_to(R)), "compiler_lane_released": True,
        "compiler_invocations": 1, "automatic_retries": 0, "exact_capture_plan_sha256_required": True,
        "exact_reviewed_controller_sha256_required": True}
    base["qualifies_only_this_exact_build_not_previous_Debug_opt2_or_future_product"] = True
    base["target_mapping_may_still_fail"] = True
    check(base["bounds"] == old_base["bounds"], "capture bounds changed")
    restored_argv = argv[:]
    check(restored_argv[-3:-1] == ["-C", "link-dead-code=yes"], "only selected retention option")
    del restored_argv[-3:-1]
    restored_argv[-1] = old_base["argv"][-1]
    check(restored_argv == old_base["argv"], "unselected compiler argv delta")
    child_environment = copy.deepcopy(base["environment"])
    child_environment["TMPDIR"] = old_base["environment"]["TMPDIR"]
    check(child_environment == old_base["environment"], "unselected child environment delta")
    put("base-capture-plan.json", base)
    base_sha = row(BASE)["sha256"]
    put("argv.json", {"schema": 1, "argv": argv, "argv_sha256_canonical_JSON": argv_sha,
                      "only_compiler_option_added": ["-C", "link-dead-code=yes"],
                      "separate_emit_directory": str(BUILD), "source_unchanged": True,
                      "alternate_diagnostic_configuration_only": True, "execution_authorized": False})

    # Byte-for-byte policy reuse. Extra/missing/changed eager-codegen diagnostics refuse.
    for name in ("diagnostic-policy.json", "diagnostic-policy-provenance.json"):
        with (D / name).open("xb") as stream:
            stream.write((OLD / name).read_bytes())
        check(row(D / name)["sha256"] == row(OLD / name)["sha256"], "diagnostic reuse differs")
    put("diagnostic-policy-reuse.json", {"schema": 1, "prior_policy": row(OLD / "diagnostic-policy.json"),
        "prior_provenance": row(OLD / "diagnostic-policy-provenance.json"), "byte_identical": True,
        "source_paths_and_warning_spans_unchanged": True, "actual_alternate_diagnostics_not_observed": True,
        "extra_missing_or_different_record_refuses": True, "no_warning_suppression_or_policy_adaptation": True})

    plan = copy.deepcopy(old_plan)
    for key in ("argv", "environment", "cwd", "bounds", "source_directory", "source_tree_sha256", "source_manifest",
                "compiler", "toolchain_manifest", "SDK_manifest", "owned_output_directory", "argv_sha256_canonical_JSON", "approach"):
        plan[key] = copy.deepcopy(base[key])
    plan.update(status="FROZEN_ALT_DIAGNOSTIC_CONTROLLER_SOURCE_AWAITING_INDEPENDENT_REVIEW_AND_ROOT_RELEASE",
                base_capture_plan=row(BASE), controller_path=str(D / "run-capture.py"),
                controller_argv=[PYTHON, "-B", str(D / "run-capture.py")],
                reference_controller=row(old_controller), original_capture_plan=row(OLD_BASE),
                original_controller_plan=row(OLD / "plan.json"), original_argv_sha256=OLD_ARGV_SHA,
                source_reachability_assessment=row(ASSESSMENT / "inspection.json"),
                alternate_diagnostic_configuration_only=True, link_dead_code=True,
                original_capture_qualified=False, runtime_admission_accepted=False,
                target_mapping_may_still_fail=True,
                ownership_selection="New owned lane command/TMPDIR and runtime outputs; original capture outputs and frozen packets unchanged.",
                source_edits=0, frontier_complete=False, complete_capacity_accepted=False)
    plan["controller_environment"]["TMPDIR"] = str(BUILD / "tmp")
    plan["controller_environment_provenance"]["separate_TMPDIR_only"] = True
    plan["inspection_only_settings"] = base["inspection_only_settings"]
    plan["root_release_required"]["path"] = str(RELEASE.relative_to(R))
    plan["verifier_binding"].update(capture_plan_sha256=base_sha, argv_sha256=argv_sha,
        link_dead_code=True, alternate_diagnostic_configuration_only=True)
    check(plan["python_tool"] == old_plan["python_tool"] and plan["python_version_from_this_preparation"] ==
          old_plan["python_version_from_this_preparation"], "saved Python identity changed")
    check(plan["retained_evidence_bounds"] == old_plan["retained_evidence_bounds"], "retention bounds changed")
    for key in ("argv", "environment", "cwd", "bounds", "source_directory", "source_tree_sha256", "source_manifest", "compiler", "toolchain_manifest", "SDK_manifest"):
        check(canonical(plan[key]) == canonical(base[key]), "alternate base/controller mismatch: " + key)
    put("plan.json", plan)
    plan_sha = row(D / "plan.json")["sha256"]

    old_text = old_controller.read_text()
    controller = old_text
    replacements = [
        ('"""One root-released unchanged-source IR/assembly capture; never a host run."""',
         '"""One root-released alternate diagnostic retained IR/assembly capture; never a host run."""'),
        ('LANE = ROOT / "verification/swift-root-bound-dispatch-physical-capture-v1"',
         'LANE = ROOT / "verification/swift-root-bound-dispatch-retained-capture-v1"'),
        ('BASE_PLAN = ROOT / "verification/swift-root-bound-dispatch-physical-plan/capture-plan.json"',
         'BASE_PLAN = LANE / "base-capture-plan.json"'),
        ('BASE_PLAN_SHA = "' + OLD_BASE_SHA + '"', 'BASE_PLAN_SHA = "' + base_sha + '"'),
        ('BASE_ARGV_SHA = "' + OLD_ARGV_SHA + '"', 'BASE_ARGV_SHA = "' + argv_sha + '"'),
        ('PLAN_SHA = "' + OLD_PLAN_SHA + '"', 'PLAN_SHA = "' + plan_sha + '"'),
        ('RELEASE = ROOT / "verification/swift-semantic-adapter-root-review/dispatch-physical-capture-release.json"',
         'RELEASE = ROOT / "' + str(RELEASE.relative_to(R)) + '"'),
        ('BUILD = ROOT / "verification/swift-root-bound-dispatch-physical-plan/command"', 'BUILD = LANE / "command"'),
        ('               "all_results_local_geometry_only": True, "complete_capacity_accepted": False,',
         '               "all_results_local_geometry_only": True, "complete_capacity_accepted": False,\n               "alternate_diagnostic_configuration_only": True, "original_capture_qualified": False, "runtime_admission_accepted": False,'),
        ('capture_observation = {"schema": 1, "status": "captured-artifacts-only", "binding": plan["verifier_binding"],',
         'capture_observation = {"schema": 1, "status": "captured-artifacts-only", "binding": plan["verifier_binding"],\n            "alternate_diagnostic_configuration_only": True, "original_capture_qualified": False, "runtime_admission_accepted": False,'),
        ('"all_results_local_geometry_only": True, "complete_capacity_accepted": False,\n            "physical_capacity_prices_backings_root_funding_product_GA_accepted": False})',
         '"all_results_local_geometry_only": True, "complete_capacity_accepted": False,\n            "alternate_diagnostic_configuration_only": True, "original_capture_qualified": False, "runtime_admission_accepted": False,\n            "physical_capacity_prices_backings_root_funding_product_GA_accepted": False})'),
    ]
    for old, new in replacements:
        controller = once(controller, old, new)
    text("run-capture.py", controller)
    controller_sha = row(D / "run-capture.py")["sha256"]
    patch("controller-delta.patch", old_text, controller, "proven-capture-v1/run-capture.py", "retained-capture-v1/run-capture.py")
    patch("base-plan-delta.patch", OLD_BASE.read_text(), BASE.read_text(), "original/capture-plan.json", "retained-capture-v1/base-capture-plan.json")
    patch("controller-plan-delta.patch", (OLD / "plan.json").read_text(), (D / "plan.json").read_text(), "original/plan.json", "retained-capture-v1/plan.json")
    put("change-inventory.json", {"schema": 1, "proven_controller": row(old_controller),
        "original_base_plan": row(OLD_BASE), "original_controller_plan": row(OLD / "plan.json"),
        "compiler_option_delta": ["-C", "link-dead-code=yes"], "other_compiler_options_unchanged": True,
        "path_delta": "New lane base/plan/controller/release, separate command/emit/TMPDIR and retained runtime paths",
        "controller_replacements": [{"before": old, "after": new} for old, new in replacements],
        "controller_change_scope": "Bindings/docstring and three alternate-diagnostic output scope records only; command, diagnostics, custody, deadline, hashing, cleanup, signal cutoff logic unchanged.",
        "diagnostic_policy_byte_identical": True, "source146_unchanged": True,
        "bounds_byte_identical": True, "retained_evidence_bounds_unchanged": True,
        "controller_import_syntax_check_or_execution": False, "automatic_retry": False,
        "all_four_target_mapping_may_still_fail": True})
    put("release-schema.json", {"schema": 1, "path": str(RELEASE.relative_to(R)),
        "preparation_does_not_supply_or_authorize_this_release": True,
        "required_fields": {"schema": 1, "compiler_lane_released": True, "compiler_invocations": 1, "automatic_retries": 0,
            "reserved_output_authorized": True, "base_capture_plan_sha256": base_sha,
            "controller_plan_sha256": plan_sha, "argv_sha256": argv_sha, "controller_sha256": controller_sha,
            "capture_packet_seal_sha256": "exact seal.json SHA, filled by root after freeze",
            "independent_source_review_accepted": True,
            "independent_source_review": {"path": "root-selected verification/.../seal.json", "bytes": "exact bytes", "sha256": "exact SHA"},
            "independent_source_review_subject": {"base_capture_plan_sha256": base_sha,
                "controller_plan_sha256": plan_sha, "controller_sha256": controller_sha,
                "capture_packet_seal_sha256": "same exact capture seal SHA"},
            "semantic_map_approved": False, "actual_verifier_input_run_released": False}})

    put("input-manifest.json", {"schema": 1, "inputs": before,
        "original_source_members": 146, "compiler_sysroot_members": 67,
        "source_tree_sha256": base["source_tree_sha256"], "base_capture_plan_sha256": base_sha,
        "argv_sha256": argv_sha, "original_argv_sha256": OLD_ARGV_SHA,
        "reference_controller_sha256": OLD_CONTROLLER_SHA,
        "preparation_imports_controller_or_verifier": False,
        "original_raw_stderr_or_actual_capture_artifacts_parsed": False,
        "alternate_diagnostic_configuration_only": True})
    check([row(path) for path in input_paths] == before, "before/after approved input inventory differs")
    check([row(path) for path in assessment_paths] == assessment_before, "source assessment changed")
    check(not BUILD.exists() and not (D / "runtime").exists(), "runtime directory created during preparation")
    check(row(OLD / "seal.json")["sha256"] == OLD_SEAL_SHA, "prior capture changed")
    summary = {"status": "SOURCE_ONLY_ALT_DIAGNOSTIC_CAPTURE_CONTROLLER_PREPARED",
        "compiler_controller_dummy_test_version_runtime_invocations": 0,
        "argv_sha256": argv_sha, "original_argv_sha256": OLD_ARGV_SHA,
        "source_members": 146, "tool_members": 67, "bounds_unchanged": True,
        "alternate_diagnostic_configuration_only": True, "frontier_complete": False, "complete_capacity_accepted": False}
    text("preparation.stdout", json.dumps(summary, sort_keys=True) + "\n")
    with (D / "preparation.stderr").open("xb"):
        pass
    deadline()
    put("preparation-receipt.json", {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": [PYTHON, "-B", str(Path(__file__).resolve())], "cwd": str(R),
        "python_version_query_performed": False, "python_version_label_from_prior_plan_only": old_plan["python_version_from_this_preparation"],
        "python_tool": old_plan["python_tool"], "preparation_source": row(Path(__file__).resolve()),
        "controller_source": row(D / "run-capture.py"), "controller_plan": row(D / "plan.json"),
        "base_capture_plan": row(BASE), "input_manifest": row(D / "input-manifest.json"),
        "stdout": row(D / "preparation.stdout"), "stderr": row(D / "preparation.stderr"),
        "elapsed_seconds": time.monotonic() - START, "wall_ceiling_seconds": 55,
        "scope": "Source preparation and bounded immutable-file hashing only; no controller import, syntax check, compiler/version/test/native/process probe, geometry verifier or recapture.",
        "compiler_capture_version_model_test_native_runtime_actual_saved_input_process_probes": 0,
        "prior_frozen_packets_source_assessment_and_canonical_metadata_changed": False,
        "new_command_and_runtime_directories_created": False,
        "alternate_diagnostic_configuration_only": True, "fresh_root_release_still_required": True})
    members = [row(path, D) for path in sorted(D.rglob("*")) if path.is_file() and path.name != "seal.json"]
    check(len(members) <= 64 and sum(item["bytes"] for item in members) <= 8388608, "preparation packet bounds")
    seal = {"schema": 1, "status": "FROZEN_ALT_DIAGNOSTIC_CAPTURE_CONTROLLER_SOURCE_AWAITING_REVIEW",
        "members": members, "member_count": len(members), "member_bytes": sum(item["bytes"] for item in members),
        "tree_sha256": sha(canonical(members)), "base_capture_plan_sha256": base_sha,
        "controller_plan_sha256": plan_sha, "controller_sha256": controller_sha, "argv_sha256": argv_sha,
        "original_argv_sha256": OLD_ARGV_SHA, "proven_controller_sha256": OLD_CONTROLLER_SHA,
        "compiler_controller_import_syntax_test_dummy_or_process_probes": 0,
        "raw_capture_only": True, "alternate_diagnostic_configuration_only": True,
        "original_capture_qualified": False, "runtime_admission_accepted": False,
        "frontier_complete": False, "complete_capacity_accepted": False,
        "canonical_or_global_metadata_changed": False, "fresh_root_release_still_required": True}
    put("seal.json", seal)
    print(json.dumps({"status": seal["status"], "members": len(members), "seal_sha256": row(D / "seal.json")["sha256"],
        "base_capture_plan_sha256": base_sha, "controller_plan_sha256": plan_sha,
        "controller_sha256": controller_sha, "argv_sha256": argv_sha, "elapsed_seconds": time.monotonic() - START}, sort_keys=True))


if __name__ == "__main__":
    main()
